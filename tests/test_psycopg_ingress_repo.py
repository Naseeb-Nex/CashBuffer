from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.persistence.ingress_repository import (
    PsycopgIngressRepository,
)


@pytest.mark.asyncio
async def test_psycopg_ingress_repository_sql_queries():
    """Verify PsycopgIngressRepository executes native psycopg 3 queries with parameters."""
    mock_cursor = AsyncMock()
    mock_cursor.fetchone = AsyncMock()
    mock_cursor.fetchall = AsyncMock()

    mock_conn = MagicMock()
    mock_cursor_ctx = MagicMock()
    mock_cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor.return_value = mock_cursor_ctx

    mock_tx_ctx = MagicMock()
    mock_tx_ctx.__aenter__ = AsyncMock(return_value=None)
    mock_tx_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_conn.transaction.return_value = mock_tx_ctx

    mock_pool = MagicMock()
    mock_pool.connection.return_value.__aenter__.return_value = mock_conn

    repo = PsycopgIngressRepository(mock_pool)

    # 1. Test init_tables
    await repo.init_tables()
    assert mock_cursor.execute.called
    assert "CREATE TABLE IF NOT EXISTS ingress_configs" in mock_cursor.execute.call_args[0][0]

    # 2. Test get_or_create_user_and_household
    mock_cursor.fetchone.side_effect = [
        {"id": "c0000000-0000-0000-0000-000000000001"},  # SELECT id FROM users
        {"household_id": "h0000000-0000-0000-0000-000000000001"},  # SELECT household_id
    ]
    uid, hid = await repo.get_or_create_user_and_household("kinde_sub_123")
    assert uid == "c0000000-0000-0000-0000-000000000001"
    assert hid == "h0000000-0000-0000-0000-000000000001"

    # 3. Test update_config
    mock_cursor.fetchone.side_effect = [
        {
            "id": "cfg_1",
            "household_id": hid,
            "user_id": uid,
            "provider": "gmail",
            "is_enabled": False,
            "interval_minutes": 30,
            "last_run_at": None,
            "next_run_at": None,
            "status": "idle",
            "last_error": None,
            "created_at": None,
        }
    ]
    cfg = await repo.update_config(hid, uid, "gmail", interval_minutes=30, is_enabled=False)
    assert cfg["interval_minutes"] == 30
    assert cfg["is_enabled"] is False

    # 4. Test trigger_sync
    mock_cursor.fetchone.side_effect = [
        {
            "id": "cfg_1",
            "household_id": hid,
            "user_id": uid,
            "provider": "gmail",
            "is_enabled": False,
            "interval_minutes": 30,
            "last_run_at": None,
            "next_run_at": None,
            "status": "idle",
            "last_error": None,
            "created_at": None,
        }
    ]
    triggered = await repo.trigger_sync(hid, uid, "gmail")
    assert triggered["status"] == "idle"
