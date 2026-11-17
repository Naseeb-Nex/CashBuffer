from __future__ import annotations

from datetime import date
from typing import Any, Literal

from apps.mcp.auth import forbid_user_supplied_authority, require_auth_context
from apps.mcp.db import DatabasePool, get_db_pool
from apps.mcp.schemas import (
    TransactionItem,
    TransactionQueryParams,
    TransactionQueryResponse,
)


async def execute_query_transactions(
    limit: int = 50,
    offset: int = 0,
    start_date: date | None = None,
    end_date: date | None = None,
    status: Literal["parsed", "needs_review", "categorized"] | None = None,
    category_id: int | None = None,
    search: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    is_inflow: bool | None = None,
    ctx: Any = None,
    pool: DatabasePool | None = None,
    **extra_kwargs: Any,
) -> dict[str, Any]:
    """
    Executes a read-only query on ledger transactions for the authenticated tenant.
    Enforces strict tenant scoping and prevents any caller authority spoofing.
    """
    if extra_kwargs:
        forbid_user_supplied_authority(extra_kwargs)

    params = TransactionQueryParams(
        limit=limit,
        offset=offset,
        start_date=start_date,
        end_date=end_date,
        status=status,
        category_id=category_id,
        search=search,
        min_amount=min_amount,
        max_amount=max_amount,
        is_inflow=is_inflow,
    )

    auth_ctx = require_auth_context(ctx)
    tenant_id = auth_ctx.tenant_id

    # Construct parameterized SQL clauses
    base_filters = ["t.user_id = %s"]
    sql_params: list[Any] = [tenant_id]

    if params.start_date:
        base_filters.append("t.record_date >= %s")
        sql_params.append(params.start_date)

    if params.end_date:
        base_filters.append("t.record_date <= %s")
        sql_params.append(params.end_date)

    if params.status:
        base_filters.append("t.status = %s")
        sql_params.append(params.status)

    if params.category_id is not None:
        base_filters.append("t.category_id = %s")
        sql_params.append(params.category_id)

    if params.search:
        base_filters.append("t.vendor_raw ILIKE %s")
        sql_params.append(f"%{params.search.strip()}%")

    if params.min_amount is not None:
        base_filters.append("t.amount >= %s")
        sql_params.append(params.min_amount)

    if params.max_amount is not None:
        base_filters.append("t.amount <= %s")
        sql_params.append(params.max_amount)

    if params.is_inflow is not None:
        base_filters.append("t.is_inflow = %s")
        sql_params.append(params.is_inflow)

    where_clause = " AND ".join(base_filters)

    count_sql = f"SELECT COUNT(*) AS total FROM transactions t WHERE {where_clause};"

    data_sql = f"""
        SELECT
            t.id,
            t.user_id,
            t.amount,
            t.currency,
            t.is_inflow,
            t.record_date,
            t.vendor_raw,
            t.category_id,
            COALESCE(c.name, 'Uncategorized') AS category_name,
            t.status,
            t.created_at
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id AND c.user_id = %s
        WHERE {where_clause}
        ORDER BY t.record_date DESC, t.id DESC
        LIMIT %s OFFSET %s;
    """

    db = pool or get_db_pool()

    async with db.acquire_read_only() as conn:
        async with conn.cursor() as cur:
            await cur.execute(count_sql, tuple(sql_params))
            count_row = await cur.fetchone()
            total_count = int(count_row["total"]) if count_row else 0

            data_params = [tenant_id] + sql_params + [params.limit, params.offset]
            await cur.execute(data_sql, tuple(data_params))
            rows = await cur.fetchall()

    items = [
        TransactionItem(
            id=row["id"],
            user_id=row["user_id"],
            amount=round(float(row["amount"]), 2),
            currency=row["currency"],
            is_inflow=bool(row["is_inflow"]),
            record_date=row["record_date"],
            vendor_raw=row["vendor_raw"],
            category_id=row["category_id"],
            category_name=row["category_name"],
            status=str(row["status"]),
            created_at=row.get("created_at"),
        )
        for row in (rows or [])
    ]

    has_more = (params.offset + len(items)) < total_count

    response = TransactionQueryResponse(
        items=items,
        total_count=total_count,
        limit=params.limit,
        offset=params.offset,
        has_more=has_more,
    )
    return response.model_dump(mode="json")
