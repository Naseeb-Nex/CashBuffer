from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from apps.mcp.auth import forbid_user_supplied_authority, require_auth_context
from apps.mcp.db import DatabasePool, get_db_pool
from apps.mcp.schemas import (
    CategoryBreakdownItem,
    MonthlySummaryParams,
    MonthlySummaryResponse,
)


async def execute_monthly_summary(
    year: int,
    month: int,
    ctx: Any = None,
    pool: DatabasePool | None = None,
    **extra_kwargs: Any,
) -> dict[str, Any]:
    """
    Executes a read-only monthly summary for the authenticated tenant.
    Enforces tenant boundaries via verified auth context.
    Rejects any caller-supplied authority.
    """
    if extra_kwargs:
        forbid_user_supplied_authority(extra_kwargs)

    # Validate parameters with Pydantic
    params = MonthlySummaryParams(year=year, month=month)

    # Authenticate and obtain tenant authority
    auth_ctx = require_auth_context(ctx)
    tenant_id = auth_ctx.tenant_id

    # Compute month boundaries
    start_date = date(params.year, params.month, 1)
    if params.month == 12:
        next_month = date(params.year + 1, 1, 1)
    else:
        next_month = date(params.year, params.month + 1, 1)
    end_date = next_month - timedelta(days=1)

    db = pool or get_db_pool()

    summary_sql = """
        SELECT
            COALESCE(SUM(CASE WHEN is_inflow = TRUE THEN amount ELSE 0 END), 0.0) AS total_inflow,
            COALESCE(SUM(CASE WHEN is_inflow = FALSE THEN amount ELSE 0 END), 0.0) AS total_outflow,
            COUNT(*) AS transaction_count,
            COUNT(CASE WHEN category_id IS NULL OR status != 'categorized' THEN 1 END) AS uncategorized_count
        FROM transactions
        WHERE user_id = %s
          AND record_date >= %s
          AND record_date <= %s;
    """

    breakdown_sql = """
        SELECT
            t.category_id,
            COALESCE(c.name, 'Uncategorized') AS category_name,
            COALESCE(SUM(t.amount), 0.0) AS total_amount,
            COUNT(*) AS transaction_count
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id AND c.user_id = %s
        WHERE t.user_id = %s
          AND t.is_inflow = FALSE
          AND t.record_date >= %s
          AND t.record_date <= %s
        GROUP BY t.category_id, c.name
        ORDER BY total_amount DESC;
    """

    async with db.acquire_read_only() as conn:
        async with conn.cursor() as cur:
            await cur.execute(summary_sql, (tenant_id, start_date, end_date))
            summary_row = await cur.fetchone()

            await cur.execute(breakdown_sql, (tenant_id, tenant_id, start_date, end_date))
            breakdown_rows = await cur.fetchall()

    total_inflow = round(float(summary_row["total_inflow"]), 2) if summary_row else 0.0
    total_outflow = round(float(summary_row["total_outflow"]), 2) if summary_row else 0.0
    tx_count = int(summary_row["transaction_count"]) if summary_row else 0
    uncat_count = int(summary_row["uncategorized_count"]) if summary_row else 0
    net_buffer = round(total_inflow - total_outflow, 2)

    category_breakdown = [
        CategoryBreakdownItem(
            category_id=row["category_id"],
            category_name=row["category_name"],
            total_amount=round(float(row["total_amount"]), 2),
            transaction_count=int(row["transaction_count"]),
        )
        for row in (breakdown_rows or [])
    ]

    response = MonthlySummaryResponse(
        year=params.year,
        month=params.month,
        total_inflow=total_inflow,
        total_outflow=total_outflow,
        net_buffer=net_buffer,
        transaction_count=tx_count,
        uncategorized_count=uncat_count,
        category_breakdown=category_breakdown,
    )
    return response.model_dump(mode="json")
