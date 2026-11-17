"""Tests for standalone Ingress microservice (Phase 2A)."""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.ingress.src.application.scheduler_service import IngressSchedulerService
from apps.ingress.src.application.sync_service import IngressSyncService
from apps.ingress.src.domain.models import IngressJob, ParsedAlert, SyncCheckpoint
from apps.ingress.src.infrastructure.gmail.parsers.axis_bank import AxisBankParser
from apps.ingress.src.infrastructure.persistence.ingress_repository import (
    NativeIngressRepository,
)

def test_axis_bank_parser_debit():
    parser = AxisBankParser()
    text = "INR 1,450.50 has been debited from your A/c on 15-09-2026 at 14:00. Info: UPI/SWIGGY/12345."
    alert = parser.parse(text, raw_email_id="msg_001")
    assert alert is not None
    assert alert.amount == -1450.50
    assert alert.currency == "INR"
    assert alert.is_inflow is False
    assert alert.record_date == date(2026, 9, 15)
    assert "SWIGGY" in alert.vendor_raw
    assert alert.raw_email_id == "msg_001"
    assert alert.email_url == "https://mail.google.com/mail/u/0/#all/msg_001"

def test_axis_bank_parser_credit():
    parser = AxisBankParser()
    text = "INR 75,000.00 has been credited to your A/c on 01-09-2026. Info: ACME_CORP_PAYROLL."
    alert = parser.parse(text, raw_email_id="msg_002")
    assert alert is not None
    assert alert.amount == 75000.00
    assert alert.is_inflow is True
    assert alert.record_date == date(2026, 9, 1)
    assert "ACME_CORP" in alert.vendor_raw

def test_axis_bank_parser_unrecognized():
    parser = AxisBankParser()
    text = "Hello, your monthly newsletter is here."
    assert parser.parse(text) is None

def test_dedupe_hash_computation():
    alert = ParsedAlert(
        amount=-500.0,
        currency="INR",
        is_inflow=False,
        record_date=date(2026, 9, 15),
        vendor_raw="AMAZON",
    )
    hid = uuid.uuid4()
    h1 = alert.compute_dedupe_hash(hid)
    h2 = alert.compute_dedupe_hash(hid)
    assert h1 == h2
    assert len(h1) == 64

@pytest.mark.asyncio
async def test_native_ingress_repository_queries():
    mock_cursor = AsyncMock()
    mock_cursor.fetchall = AsyncMock(return_value=[
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "household_id": "22222222-2222-2222-2222-222222222222",
            "user_id": "33333333-3333-3333-3333-333333333333",
            "provider": "gmail",
            "interval_minutes": 60,
            "next_run_at": datetime.now(timezone.utc),
            "status": "idle",
        }
    ])
    mock_cursor.fetchone = AsyncMock(return_value={"id": 101})

    mock_conn = MagicMock()
    mock_cursor_ctx = MagicMock()
    mock_cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor.return_value = mock_cursor_ctx

    mock_pool = MagicMock()
    mock_pool.connection.return_value.__aenter__.return_value = mock_conn

    repo = NativeIngressRepository(mock_pool)

    # 1. Test fetch_due_jobs
    jobs = await repo.fetch_due_jobs()
    assert len(jobs) == 1
    assert jobs[0].provider == "gmail"

    # 2. Test save_transaction
    alert = ParsedAlert(
        amount=-250.0,
        currency="INR",
        is_inflow=False,
        record_date=date(2026, 9, 15),
        vendor_raw="STARBUCKS",
    )
    saved = await repo.save_transaction(jobs[0].household_id, jobs[0].user_id, alert)
    assert saved is True
    assert "INSERT INTO transactions" in mock_cursor.execute.call_args[0][0]

    # 3. Test quarantine_email
    await repo.quarantine_email(
        household_id=jobs[0].household_id,
        user_id=jobs[0].user_id,
        raw_email_id="err_msg_1",
        email_url="http://mail/err_msg_1",
        email_text="Failed body",
        error_reason="Bad regex",
    )
    assert "INSERT INTO quarantined_emails" in mock_cursor.execute.call_args[0][0]

@pytest.mark.asyncio
async def test_ingress_sync_service_lifecycle():
    mock_repo = AsyncMock()
    mock_repo.get_checkpoint = AsyncMock(return_value=None)
    mock_repo.save_transaction = AsyncMock(return_value=True)
    mock_repo.quarantine_email = AsyncMock()
    mock_repo.update_checkpoint = AsyncMock()
    mock_repo.mark_job_status = AsyncMock()

    mock_client = AsyncMock()
    mock_client.fetch_alert_messages = AsyncMock(return_value=[
        {
            "id": "valid_1",
            "internalDate": 1726400000000,
            "text": "INR 350.00 has been debited on 15-09-2026 Info: SWIGGY",
        },
        {
            "id": "unrecognized_2",
            "internalDate": 1726400010000,
            "text": "Your account statement for August is ready.",
        },
    ])
    mock_client.build_email_url = MagicMock(side_effect=lambda x: f"http://mail/{x}")

    service = IngressSyncService(
        repository=mock_repo,
        email_client=mock_client,
        parser=AxisBankParser(),
    )

    job = IngressJob(
        id=uuid.uuid4(),
        household_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        provider="gmail",
        interval_minutes=30,
        next_run_at=datetime.now(timezone.utc),
        status="idle",
    )

    result = await service.execute_job(job)
    assert result["success"] is True
    assert result["inserted"] == 1
    assert result["quarantined"] == 1

    # Verify calls
    assert mock_repo.save_transaction.await_count == 1
    assert mock_repo.quarantine_email.await_count == 1
    assert mock_repo.update_checkpoint.await_count == 1
    assert mock_repo.mark_job_status.await_count == 1
