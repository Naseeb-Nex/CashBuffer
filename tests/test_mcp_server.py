from __future__ import annotations

import time
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from pydantic import ValidationError

from apps.mcp.auth import (
    AuthContext,
    InvalidCredentialsError,
    JWTAuthProvider,
    MissingAuthContextError,
    StaticTokenAuthProvider,
    UnauthorizedAuthorityError,
    auth_scope,
)
from apps.mcp.config import MCPConfig
from apps.mcp.db import DatabasePool
from apps.mcp.schemas import (
    MonthlySummaryParams,
    RecurringBillsParams,
    TransactionQueryParams,
)
from apps.mcp.server import create_server
from apps.mcp.tools.monthly_summary import execute_monthly_summary
from apps.mcp.tools.recurring_bills import (
    _estimate_frequency,
    execute_recurring_bills,
)
from apps.mcp.tools.transactions import execute_query_transactions


def create_mock_pool(cursor_mock: MagicMock | None = None) -> tuple[DatabasePool, MagicMock, MagicMock]:
    pool = MagicMock(spec=DatabasePool)
    conn = MagicMock()
    cur = cursor_mock or MagicMock()

    cur.execute = AsyncMock()
    cur.fetchone = AsyncMock(return_value=None)
    cur.fetchall = AsyncMock(return_value=[])

    cursor_ctx = MagicMock()
    cursor_ctx.__aenter__ = AsyncMock(return_value=cur)
    cursor_ctx.__aexit__ = AsyncMock(return_value=None)
    conn.cursor.return_value = cursor_ctx

    conn.set_read_only = AsyncMock()
    conn.rollback = AsyncMock()

    class AcquireCtx:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    pool.acquire_read_only.return_value = AcquireCtx()
    return pool, conn, cur


# 1. MCP Tool Contract and Discovery Tests
@pytest.mark.asyncio
async def test_mcp_tool_discovery():
    server = create_server()
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}

    assert "monthly_summary" in tool_names
    assert "query_transactions" in tool_names
    assert "recurring_bills" in tool_names

    # Verify tool metadata
    ms_tool = next(t for t in tools if t.name == "monthly_summary")
    assert "year" in ms_tool.input_schema["properties"]
    assert "month" in ms_tool.input_schema["properties"]
    assert "user_id" not in ms_tool.input_schema["properties"]
    assert "tenant_id" not in ms_tool.input_schema["properties"]


# 2. Auth Boundary and Zero-Trust Perimeter Tests
@pytest.mark.asyncio
async def test_auth_boundary_missing_context():
    pool, _, _ = create_mock_pool()

    with pytest.raises(MissingAuthContextError):
        await execute_monthly_summary(year=2026, month=4, pool=pool)

    with pytest.raises(MissingAuthContextError):
        await execute_query_transactions(pool=pool)

    with pytest.raises(MissingAuthContextError):
        await execute_recurring_bills(pool=pool)


@pytest.mark.asyncio
async def test_auth_boundary_forbid_user_supplied_authority():
    pool, _, _ = create_mock_pool()
    auth = AuthContext.create(user_id="legit_tenant")

    async with auth_scope(auth):
        with pytest.raises(UnauthorizedAuthorityError):
            await execute_monthly_summary(year=2026, month=4, pool=pool, user_id="victim_tenant")

        with pytest.raises(UnauthorizedAuthorityError):
            await execute_query_transactions(pool=pool, tenant_id="victim_tenant")

        with pytest.raises(UnauthorizedAuthorityError):
            await execute_recurring_bills(pool=pool, caller_id="victim_tenant")


@pytest.mark.asyncio
async def test_server_call_tool_rejects_user_supplied_authority():
    pool, _, _ = create_mock_pool()
    server = create_server(pool=pool)
    auth = AuthContext.create(user_id="alice")

    async with auth_scope(auth):
        with pytest.raises(UnauthorizedAuthorityError):
            await server.call_tool("monthly_summary", {"year": 2026, "month": 4, "user_id": "bob"})

        with pytest.raises(UnauthorizedAuthorityError):
            await server.call_tool("query_transactions", {"limit": 10, "tenant_id": "bob"})


@pytest.mark.asyncio
async def test_jwt_auth_provider():
    secret = "test-secret-key-123456789012345678"
    provider = JWTAuthProvider(secret_or_key=secret)

    # Valid token
    payload = {"sub": "tenant_123", "email": "test@example.com", "exp": int(time.time()) + 3600}
    token = jwt.encode(payload, secret, algorithm="HS256")
    ctx = await provider.authenticate(f"Bearer {token}")
    assert ctx.user_id == "tenant_123"
    assert ctx.tenant_id == "tenant_123"
    assert ctx.email == "test@example.com"

    # Expired token
    expired_payload = {"sub": "tenant_123", "exp": int(time.time()) - 100}
    expired_token = jwt.encode(expired_payload, secret, algorithm="HS256")
    with pytest.raises(InvalidCredentialsError, match="expired"):
        await provider.authenticate(expired_token)

    # Tampered token
    with pytest.raises(InvalidCredentialsError):
        await provider.authenticate(token + "tampered")

    # Missing sub claim
    no_sub_token = jwt.encode({"email": "foo@bar.com", "exp": int(time.time()) + 3600}, secret, algorithm="HS256")
    with pytest.raises(InvalidCredentialsError, match="mandatory 'sub' claim"):
        await provider.authenticate(no_sub_token)


@pytest.mark.asyncio
async def test_static_token_auth_provider():
    alice_ctx = AuthContext.create(user_id="alice")
    provider = StaticTokenAuthProvider({"alice_token": alice_ctx})

    res = await provider.authenticate("alice_token")
    assert res.user_id == "alice"

    with pytest.raises(InvalidCredentialsError):
        await provider.authenticate("bad_token")


# 3. Parameter Validation Tests
def test_monthly_summary_validation():
    # Valid
    p = MonthlySummaryParams(year=2026, month=4)
    assert p.year == 2026 and p.month == 4

    # Invalid month
    with pytest.raises(ValidationError):
        MonthlySummaryParams(year=2026, month=0)
    with pytest.raises(ValidationError):
        MonthlySummaryParams(year=2026, month=13)

    # Invalid year
    with pytest.raises(ValidationError):
        MonthlySummaryParams(year=1969, month=4)
    with pytest.raises(ValidationError):
        MonthlySummaryParams(year=2101, month=4)


def test_transaction_query_validation():
    # Valid defaults
    p = TransactionQueryParams()
    assert p.limit == 50
    assert p.offset == 0

    # Invalid limits
    with pytest.raises(ValidationError):
        TransactionQueryParams(limit=0)
    with pytest.raises(ValidationError):
        TransactionQueryParams(limit=101)
    with pytest.raises(ValidationError):
        TransactionQueryParams(offset=-1)

    # Start date after end date
    with pytest.raises(ValidationError, match="start_date .* cannot be after end_date"):
        TransactionQueryParams(start_date=date(2026, 5, 1), end_date=date(2026, 4, 1))

    # Min amount > Max amount
    with pytest.raises(ValidationError, match="min_amount .* cannot be greater than max_amount"):
        TransactionQueryParams(min_amount=200.0, max_amount=100.0)

    # Status validation
    with pytest.raises(ValidationError):
        TransactionQueryParams(status="invalid_status")  # type: ignore[arg-type]


def test_recurring_bills_validation():
    # Valid
    p = RecurringBillsParams(min_occurrences=3, lookback_months=6)
    assert p.min_occurrences == 3
    assert p.lookback_months == 6

    # Invalid
    with pytest.raises(ValidationError):
        RecurringBillsParams(min_occurrences=1)
    with pytest.raises(ValidationError):
        RecurringBillsParams(lookback_months=0)


# 4. Tool Execution & Tenant Scoping Tests
@pytest.mark.asyncio
async def test_monthly_summary_execution():
    pool, _, cur = create_mock_pool()
    cur.fetchone.return_value = {
        "total_inflow": 4500.50,
        "total_outflow": 1200.25,
        "transaction_count": 8,
        "uncategorized_count": 2,
    }
    cur.fetchall.return_value = [
        {"category_id": 1, "category_name": "Groceries", "total_amount": 800.00, "transaction_count": 4},
        {"category_id": 2, "category_name": "Utilities", "total_amount": 400.25, "transaction_count": 2},
    ]

    auth = AuthContext.create(user_id="tenant_alpha")
    async with auth_scope(auth):
        res = await execute_monthly_summary(year=2026, month=4, pool=pool)

    assert res["year"] == 2026
    assert res["month"] == 4
    assert res["total_inflow"] == 4500.50
    assert res["total_outflow"] == 1200.25
    assert res["net_buffer"] == 3300.25
    assert res["transaction_count"] == 8
    assert res["uncategorized_count"] == 2
    assert len(res["category_breakdown"]) == 2
    assert res["category_breakdown"][0]["category_name"] == "Groceries"

    # Verify SQL query verified tenant_alpha as %s parameter
    calls = cur.execute.call_args_list
    assert len(calls) == 2
    # Check that tenant_alpha is passed in parameter tuples for both queries
    assert calls[0].args[1][0] == "tenant_alpha"
    assert calls[1].args[1][0] == "tenant_alpha"


@pytest.mark.asyncio
async def test_transaction_query_execution():
    pool, _, cur = create_mock_pool()
    cur.fetchone.return_value = {"total": 1}
    cur.fetchall.return_value = [
        {
            "id": 101,
            "user_id": "tenant_beta",
            "amount": 42.50,
            "currency": "USD",
            "is_inflow": False,
            "record_date": date(2026, 4, 15),
            "vendor_raw": "Coffee Shop",
            "category_id": 5,
            "category_name": "Dining",
            "status": "categorized",
            "created_at": None,
        }
    ]

    auth = AuthContext.create(user_id="tenant_beta")
    async with auth_scope(auth):
        res = await execute_query_transactions(
            limit=10,
            offset=0,
            search="Coffee",
            min_amount=10.0,
            status="categorized",
            pool=pool,
        )

    assert res["total_count"] == 1
    assert len(res["items"]) == 1
    assert res["items"][0]["vendor_raw"] == "Coffee Shop"
    assert res["items"][0]["user_id"] == "tenant_beta"
    assert res["has_more"] is False

    # Check SQL params for tenant scoping
    calls = cur.execute.call_args_list
    count_call_args = calls[0].args[1]
    assert count_call_args[0] == "tenant_beta"


@pytest.mark.asyncio
async def test_recurring_bills_execution():
    pool, _, cur = create_mock_pool()
    cur.fetchall.return_value = [
        {
            "vendor_raw": "Netflix",
            "currency": "USD",
            "average_amount": 15.99,
            "min_amount": 15.99,
            "max_amount": 15.99,
            "occurrence_count": 6,
            "first_payment_date": date(2025, 11, 1),
            "last_payment_date": date(2026, 4, 1),
            "category_name": "Entertainment",
        },
        {
            "vendor_raw": "Gym Membership",
            "currency": "USD",
            "average_amount": 50.00,
            "min_amount": 50.00,
            "max_amount": 50.00,
            "occurrence_count": 4,
            "first_payment_date": date(2026, 1, 1),
            "last_payment_date": date(2026, 4, 1),
            "category_name": "Health",
        },
    ]

    auth = AuthContext.create(user_id="tenant_gamma")
    async with auth_scope(auth):
        res = await execute_recurring_bills(min_occurrences=2, lookback_months=12, pool=pool)

    assert res["bill_count"] == 2
    assert res["bills"][0]["vendor"] == "Netflix"
    assert res["bills"][0]["estimated_frequency"] == "monthly"
    assert res["bills"][0]["estimated_monthly_amount"] == 15.99
    assert res["total_monthly_commitment"] == 65.99

    calls = cur.execute.call_args_list
    assert calls[0].args[1][0] == "tenant_gamma"


def test_frequency_estimation():
    # Weekly: 4 occurrences across 21 days (~7 day interval)
    freq, factor = _estimate_frequency(date(2026, 1, 1), date(2026, 1, 22), 4)
    assert freq == "weekly"

    # Monthly: 4 occurrences across 91 days (~30 day interval)
    freq, factor = _estimate_frequency(date(2026, 1, 1), date(2026, 4, 2), 4)
    assert freq == "monthly"
    assert factor == 1.0

    # Quarterly: 3 occurrences across 180 days (~90 day interval)
    freq, factor = _estimate_frequency(date(2026, 1, 1), date(2026, 7, 1), 3)
    assert freq == "quarterly"


# 5. Database Pool & Read-Only Safety Tests
@pytest.mark.asyncio
async def test_database_pool_read_only_contract():
    pool = DatabasePool(conninfo="postgresql://fake:fake@localhost:5432/fake")
    assert not pool.is_open

    # Cannot acquire from closed pool
    with pytest.raises(RuntimeError, match="DatabasePool is not open"):
        async with pool.acquire_read_only():
            pass

    # Test config normalization (strips +asyncpg)
    cfg = MCPConfig(database_url="postgresql+asyncpg://user:pass@host:5432/db")
    assert cfg.get_psycopg_conninfo() == "postgresql://user:pass@host:5432/db"

    cfg_postgres = MCPConfig(database_url="postgres://user:pass@host:5432/db")
    assert cfg_postgres.get_psycopg_conninfo() == "postgresql://user:pass@host:5432/db"
