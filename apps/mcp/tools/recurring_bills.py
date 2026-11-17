from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from apps.mcp.auth import forbid_user_supplied_authority, require_auth_context
from apps.mcp.db import DatabasePool, get_db_pool
from apps.mcp.schemas import (
    RecurringBillItem,
    RecurringBillsParams,
    RecurringBillsResponse,
)


def _estimate_frequency(
    first_date: date, last_date: date, count: int
) -> tuple[str, float]:
    """
    Estimates billing frequency and recurring monthly cost based on observed date interval.
    Returns (cadence_label, monthly_multiplier).
    """
    if count <= 1 or first_date >= last_date:
        return ("monthly", 1.0)

    total_days = (last_date - first_date).days
    avg_interval_days = total_days / float(count - 1)

    if 5 <= avg_interval_days <= 10:
        return ("weekly", 4.333)
    if 11 <= avg_interval_days <= 18:
        return ("bi-weekly", 2.167)
    if 24 <= avg_interval_days <= 36:
        return ("monthly", 1.0)
    if 75 <= avg_interval_days <= 105:
        return ("quarterly", 1.0 / 3.0)
    if 330 <= avg_interval_days <= 400:
        return ("annual", 1.0 / 12.0)

    if avg_interval_days > 0:
        monthly_factor = 30.4375 / avg_interval_days
        return (f"every {round(avg_interval_days)} days", monthly_factor)

    return ("monthly", 1.0)


async def execute_recurring_bills(
    min_occurrences: int = 2,
    lookback_months: int = 12,
    ctx: Any = None,
    pool: DatabasePool | None = None,
    **extra_kwargs: Any,
) -> dict[str, Any]:
    """
    Detects recurring bills and subscriptions from past expenses for the authenticated tenant.
    Enforces strict tenant boundaries and prohibits caller-supplied authority overrides.
    """
    if extra_kwargs:
        forbid_user_supplied_authority(extra_kwargs)

    params = RecurringBillsParams(
        min_occurrences=min_occurrences,
        lookback_months=lookback_months,
    )

    auth_ctx = require_auth_context(ctx)
    tenant_id = auth_ctx.tenant_id

    # Compute lookback cutoff date (approx 31 days per month)
    cutoff_date = date.today() - timedelta(days=params.lookback_months * 31)

    db = pool or get_db_pool()

    bills_sql = """
        SELECT
            t.vendor_raw,
            t.currency,
            ROUND(AVG(t.amount)::numeric, 2) AS average_amount,
            ROUND(MIN(t.amount)::numeric, 2) AS min_amount,
            ROUND(MAX(t.amount)::numeric, 2) AS max_amount,
            COUNT(*) AS occurrence_count,
            MIN(t.record_date) AS first_payment_date,
            MAX(t.record_date) AS last_payment_date,
            COALESCE(c.name, 'Uncategorized') AS category_name
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id AND c.user_id = %s
        WHERE t.user_id = %s
          AND t.is_inflow = FALSE
          AND t.record_date >= %s
        GROUP BY t.vendor_raw, t.currency, c.name
        HAVING COUNT(*) >= %s
        ORDER BY occurrence_count DESC, average_amount DESC;
    """

    async with db.acquire_read_only() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                bills_sql,
                (tenant_id, tenant_id, cutoff_date, params.min_occurrences),
            )
            rows = await cur.fetchall()

    bills: list[RecurringBillItem] = []
    total_monthly = 0.0

    for row in rows or []:
        avg_amt = float(row["average_amount"])
        first_d = row["first_payment_date"]
        last_d = row["last_payment_date"]
        occ_count = int(row["occurrence_count"])

        freq_label, monthly_factor = _estimate_frequency(first_d, last_d, occ_count)
        est_monthly = round(avg_amt * monthly_factor, 2)
        total_monthly += est_monthly

        bills.append(
            RecurringBillItem(
                vendor=row["vendor_raw"],
                currency=row["currency"],
                average_amount=avg_amt,
                min_amount=float(row["min_amount"]),
                max_amount=float(row["max_amount"]),
                occurrence_count=occ_count,
                first_payment_date=first_d,
                last_payment_date=last_d,
                category_name=row["category_name"],
                estimated_frequency=freq_label,
                estimated_monthly_amount=est_monthly,
            )
        )

    response = RecurringBillsResponse(
        bills=bills,
        total_monthly_commitment=round(total_monthly, 2),
        bill_count=len(bills),
    )
    return response.model_dump(mode="json")
