import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.domain.models import (
    Category,
    LLMConfig,
    OAuthCredential,
    QuarantinedEmail,
    Transaction,
    TransactionStatus,
    User,
    VendorRule,
)

logger = logging.getLogger(__name__)

class NativeRepository:
    """
    Pure native psycopg 3 repository for CashBuffer Core API.
    Provider-neutral user identity (UUID id, idp_user_id) with tenant scoping.
    """

    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    # -------------------------------------------------------------------------
    # Identity & Households
    # -------------------------------------------------------------------------
    async def get_or_create_user(self, idp_user_id: str, email: str | None = None) -> User:
        """
        Resolves external `idp_user_id` to internal `User` (UUID).
        If user doesn't exist, creates user + default household + household_member.
        """
        if not email:
            email = f"{idp_user_id}@cashbuffer.local"

        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        "SELECT id, idp_user_id, email, telegram_chat_id, created_at, updated_at "
                        "FROM users WHERE idp_user_id = %s;",
                        (idp_user_id,),
                    )
                    row = await cur.fetchone()
                    if row:
                        return User(
                            id=str(row["id"]),
                            idp_user_id=row["idp_user_id"],
                            email=row["email"],
                            telegram_chat_id=row["telegram_chat_id"],
                            created_at=row["created_at"],
                            updated_at=row["updated_at"],
                        )

                    # Create user
                    new_user_id = str(uuid.uuid4())
                    await cur.execute(
                        """
                        INSERT INTO users (id, idp_user_id, email, created_at, updated_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ON CONFLICT (idp_user_id) DO UPDATE SET idp_user_id = EXCLUDED.idp_user_id
                        RETURNING id, idp_user_id, email, telegram_chat_id, created_at, updated_at;
                        """,
                        (new_user_id, idp_user_id, email),
                    )
                    row = await cur.fetchone()
                    user = User(
                        id=str(row["id"]),
                        idp_user_id=row["idp_user_id"],
                        email=row["email"],
                        telegram_chat_id=row["telegram_chat_id"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )

                    # Ensure household exists for user
                    household_id = str(uuid.uuid4())
                    await cur.execute(
                        """
                        INSERT INTO households (id, name, created_by, created_at, updated_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
                        """,
                        (household_id, f"{idp_user_id}'s Household", user.id),
                    )
                    await cur.execute(
                        """
                        INSERT INTO household_members (household_id, user_id, role, joined_at)
                        VALUES (%s, %s, 'owner', CURRENT_TIMESTAMP)
                        ON CONFLICT (household_id, user_id) DO NOTHING;
                        """,
                        (household_id, user.id),
                    )
                    return user

    async def get_user_by_id(self, user_id: str) -> User | None:
        try:
            uuid.UUID(str(user_id))
        except ValueError:
            return None

        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT id, idp_user_id, email, telegram_chat_id, created_at, updated_at "
                    "FROM users WHERE id = %s;",
                    (user_id,),
                )
                row = await cur.fetchone()
                if not row:
                    return None
                return User(
                    id=str(row["id"]),
                    idp_user_id=row["idp_user_id"],
                    email=row["email"],
                    telegram_chat_id=row["telegram_chat_id"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

    async def get_user_by_idp(self, idp_user_id: str) -> User | None:
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT id, idp_user_id, email, telegram_chat_id, created_at, updated_at "
                    "FROM users WHERE idp_user_id = %s;",
                    (idp_user_id,),
                )
                row = await cur.fetchone()
                if not row:
                    return None
                return User(
                    id=str(row["id"]),
                    idp_user_id=row["idp_user_id"],
                    email=row["email"],
                    telegram_chat_id=row["telegram_chat_id"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

    async def get_user_by_telegram_chat_id(self, chat_id: str) -> User | None:
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT id, idp_user_id, email, telegram_chat_id, created_at, updated_at "
                    "FROM users WHERE telegram_chat_id = %s;",
                    (str(chat_id),),
                )
                row = await cur.fetchone()
                if not row:
                    return None
                return User(
                    id=str(row["id"]),
                    idp_user_id=row["idp_user_id"],
                    email=row["email"],
                    telegram_chat_id=row["telegram_chat_id"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

    async def set_telegram_chat_id(self, user_id: str, chat_id: str | None) -> None:
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE users SET telegram_chat_id = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s;",
                        (str(chat_id) if chat_id else None, user_id),
                    )

    async def get_primary_household_id(self, user_id: str) -> str:
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT household_id FROM household_members WHERE user_id = %s LIMIT 1;",
                    (user_id,),
                )
                row = await cur.fetchone()
                if row:
                    return str(row["household_id"])
                # Create household fallback
                hid = str(uuid.uuid4())
                await cur.execute(
                    """
                    INSERT INTO households (id, name, created_by, created_at, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    (hid, "Default Household", user_id),
                )
                await cur.execute(
                    """
                    INSERT INTO household_members (household_id, user_id, role, joined_at)
                    VALUES (%s, %s, 'owner', CURRENT_TIMESTAMP)
                    ON CONFLICT (household_id, user_id) DO NOTHING;
                    """,
                    (hid, user_id),
                )
                return hid

    # -------------------------------------------------------------------------
    # Categories
    # -------------------------------------------------------------------------
    async def get_categories(self, user_id: str) -> list[Category]:
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT id, user_id, household_id, name, parent_id, created_at "
                    "FROM categories WHERE user_id = %s ORDER BY id ASC;",
                    (user_id,),
                )
                rows = await cur.fetchall()
                return [
                    Category(
                        id=row["id"],
                        user_id=str(row["user_id"]),
                        household_id=str(row["household_id"]) if row["household_id"] else None,
                        name=row["name"],
                        parent_id=row["parent_id"],
                        created_at=row["created_at"],
                    )
                    for row in rows
                ]

    async def get_category_by_id(self, user_id: str, category_id: int) -> Category | None:
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT id, user_id, household_id, name, parent_id, created_at "
                    "FROM categories WHERE user_id = %s AND id = %s;",
                    (user_id, category_id),
                )
                row = await cur.fetchone()
                if not row:
                    return None
                return Category(
                    id=row["id"],
                    user_id=str(row["user_id"]),
                    household_id=str(row["household_id"]) if row["household_id"] else None,
                    name=row["name"],
                    parent_id=row["parent_id"],
                    created_at=row["created_at"],
                )

    async def create_category(self, user_id: str, name: str, parent_id: int | None = None) -> Category:
        household_id = await self.get_primary_household_id(user_id)
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        INSERT INTO categories (user_id, household_id, name, parent_id, created_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING id, user_id, household_id, name, parent_id, created_at;
                        """,
                        (user_id, household_id, name, parent_id),
                    )
                    row = await cur.fetchone()
                    return Category(
                        id=row["id"],
                        user_id=str(row["user_id"]),
                        household_id=str(row["household_id"]) if row["household_id"] else None,
                        name=row["name"],
                        parent_id=row["parent_id"],
                        created_at=row["created_at"],
                    )

    async def delete_category(self, user_id: str, category_id: int) -> bool:
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.execute(
                        "DELETE FROM categories WHERE user_id = %s AND id = %s;",
                        (user_id, category_id),
                    )
                    return cur.rowcount > 0

    # -------------------------------------------------------------------------
    # Vendor Rules
    # -------------------------------------------------------------------------
    async def get_vendor_rules(self, user_id: str) -> list[VendorRule]:
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT id, user_id, household_id, vendor_regex, default_category_id, created_at "
                    "FROM vendor_rules WHERE user_id = %s ORDER BY id ASC;",
                    (user_id,),
                )
                rows = await cur.fetchall()
                return [
                    VendorRule(
                        id=row["id"],
                        user_id=str(row["user_id"]),
                        household_id=str(row["household_id"]) if row["household_id"] else None,
                        vendor_regex=row["vendor_regex"],
                        default_category_id=row["default_category_id"],
                        created_at=row["created_at"],
                    )
                    for row in rows
                ]

    async def upsert_vendor_rule(self, user_id: str, vendor_regex: str, category_id: int) -> VendorRule:
        household_id = await self.get_primary_household_id(user_id)
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        "SELECT id FROM vendor_rules WHERE user_id = %s AND vendor_regex = %s;",
                        (user_id, vendor_regex),
                    )
                    existing = await cur.fetchone()
                    if existing:
                        await cur.execute(
                            """
                            UPDATE vendor_rules
                            SET default_category_id = %s, household_id = %s
                            WHERE id = %s
                            RETURNING id, user_id, household_id, vendor_regex, default_category_id, created_at;
                            """,
                            (category_id, household_id, existing["id"]),
                        )
                        row = await cur.fetchone()
                    else:
                        await cur.execute(
                            """
                            INSERT INTO vendor_rules (user_id, household_id, vendor_regex, default_category_id, created_at)
                            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                            RETURNING id, user_id, household_id, vendor_regex, default_category_id, created_at;
                            """,
                            (user_id, household_id, vendor_regex, category_id),
                        )
                        row = await cur.fetchone()
                    return VendorRule(
                        id=row["id"],
                        user_id=str(row["user_id"]),
                        household_id=str(row["household_id"]) if row["household_id"] else None,
                        vendor_regex=row["vendor_regex"],
                        default_category_id=row["default_category_id"],
                        created_at=row["created_at"],
                    )

    async def delete_vendor_rule(self, user_id: str, rule_id: int) -> bool:
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.execute(
                        "DELETE FROM vendor_rules WHERE user_id = %s AND id = %s;",
                        (user_id, rule_id),
                    )
                    return cur.rowcount > 0

    # -------------------------------------------------------------------------
    # Transactions
    # -------------------------------------------------------------------------
    async def get_transaction_by_hash(self, tx_hash: str) -> Transaction | None:
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT id, user_id, household_id, amount, currency, is_inflow, record_date, "
                    "vendor_raw, tx_hash, dedupe_hash, category_id, status, raw_source, raw_email_id, "
                    "email_url, created_at FROM transactions WHERE tx_hash = %s;",
                    (tx_hash,),
                )
                row = await cur.fetchone()
                if not row:
                    return None
                return self._row_to_tx(row)

    async def get_transaction_by_id(self, user_id: str, tx_id: int) -> Transaction | None:
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT id, user_id, household_id, amount, currency, is_inflow, record_date, "
                    "vendor_raw, tx_hash, dedupe_hash, category_id, status, raw_source, raw_email_id, "
                    "email_url, created_at FROM transactions WHERE user_id = %s AND id = %s;",
                    (user_id, tx_id),
                )
                row = await cur.fetchone()
                if not row:
                    return None
                return self._row_to_tx(row)

    async def list_transactions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        status: TransactionStatus | None = None,
        category_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        search: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
    ) -> list[Transaction]:
        query = [
            "SELECT id, user_id, household_id, amount, currency, is_inflow, record_date, "
            "vendor_raw, tx_hash, dedupe_hash, category_id, status, raw_source, raw_email_id, "
            "email_url, created_at FROM transactions WHERE user_id = %s"
        ]
        params: list[Any] = [user_id]

        if status:
            val = status.value if hasattr(status, "value") else str(status)
            query.append("AND status = %s")
            params.append(val)
        if category_id is not None:
            query.append("AND category_id = %s")
            params.append(category_id)
        if start_date:
            query.append("AND record_date >= %s")
            params.append(start_date)
        if end_date:
            query.append("AND record_date <= %s")
            params.append(end_date)
        if search:
            query.append("AND vendor_raw ILIKE %s")
            params.append(f"%{search}%")
        if min_amount is not None:
            query.append("AND amount >= %s")
            params.append(min_amount)
        if max_amount is not None:
            query.append("AND amount <= %s")
            params.append(max_amount)

        query.append("ORDER BY record_date DESC, id DESC LIMIT %s OFFSET %s;")
        params.extend([limit, offset])

        sql = " ".join(query)
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql, tuple(params))
                rows = await cur.fetchall()
                return [self._row_to_tx(r) for r in rows]

    async def insert_transaction(self, tx: Transaction) -> Transaction:
        household_id = tx.household_id or await self.get_primary_household_id(tx.user_id)
        status_val = tx.status.value if hasattr(tx.status, "value") else str(tx.status)
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        INSERT INTO transactions (
                            user_id, household_id, amount, currency, is_inflow, record_date,
                            vendor_raw, tx_hash, dedupe_hash, category_id, status, raw_source,
                            raw_email_id, email_url, created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (tx_hash) DO NOTHING
                        RETURNING id, user_id, household_id, amount, currency, is_inflow, record_date,
                                  vendor_raw, tx_hash, dedupe_hash, category_id, status, raw_source,
                                  raw_email_id, email_url, created_at;
                        """,
                        (
                            tx.user_id,
                            household_id,
                            tx.amount,
                            tx.currency,
                            tx.is_inflow,
                            tx.record_date,
                            tx.vendor_raw,
                            tx.tx_hash,
                            tx.dedupe_hash,
                            tx.category_id,
                            status_val,
                            tx.raw_source,
                            tx.raw_email_id,
                            tx.email_url,
                        ),
                    )
                    row = await cur.fetchone()
                    if row:
                        return self._row_to_tx(row)

                    # Conflict hit, retrieve existing
                    await cur.execute(
                        "SELECT id, user_id, household_id, amount, currency, is_inflow, record_date, "
                        "vendor_raw, tx_hash, dedupe_hash, category_id, status, raw_source, raw_email_id, "
                        "email_url, created_at FROM transactions WHERE tx_hash = %s;",
                        (tx.tx_hash,),
                    )
                    existing = await cur.fetchone()
                    return self._row_to_tx(existing)

    async def update_transaction(
        self,
        user_id: str,
        tx_id: int,
        category_id: int | None = None,
        status: TransactionStatus | None = None,
        vendor_raw: str | None = None,
        amount: float | None = None,
    ) -> Transaction | None:
        updates = []
        params: list[Any] = []
        if category_id is not None:
            updates.append("category_id = %s")
            params.append(category_id)
        if status is not None:
            val = status.value if hasattr(status, "value") else str(status)
            updates.append("status = %s")
            params.append(val)
        if vendor_raw is not None:
            updates.append("vendor_raw = %s")
            params.append(vendor_raw)
        if amount is not None:
            updates.append("amount = %s")
            params.append(amount)

        if not updates:
            return await self.get_transaction_by_id(user_id, tx_id)

        sql = f"UPDATE transactions SET {', '.join(updates)} WHERE user_id = %s AND id = %s RETURNING id, user_id, household_id, amount, currency, is_inflow, record_date, vendor_raw, tx_hash, dedupe_hash, category_id, status, raw_source, raw_email_id, email_url, created_at;"
        params.extend([user_id, tx_id])

        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(sql, tuple(params))
                    row = await cur.fetchone()
                    if not row:
                        return None
                    return self._row_to_tx(row)

    async def delete_transaction(self, user_id: str, tx_id: int) -> bool:
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.execute(
                        "DELETE FROM transactions WHERE user_id = %s AND id = %s;",
                        (user_id, tx_id),
                    )
                    return cur.rowcount > 0

    async def get_financial_summary(
        self,
        user_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        params: list[Any] = [user_id]
        where_clauses = ["user_id = %s"]
        if start_date:
            where_clauses.append("record_date >= %s")
            params.append(start_date)
        if end_date:
            where_clauses.append("record_date <= %s")
            params.append(end_date)

        where_sql = " AND ".join(where_clauses)
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    f"SELECT id, amount, is_inflow, category_id, status FROM transactions WHERE {where_sql};",
                    tuple(params),
                )
                transactions = await cur.fetchall()

                # Get categories
                await cur.execute(
                    "SELECT id, name FROM categories WHERE user_id = %s;",
                    (user_id,),
                )
                cat_rows = await cur.fetchall()
                categories = {c["id"]: c["name"] for c in cat_rows}

                # Get linked accounts count
                await cur.execute(
                    "SELECT COUNT(*) as count FROM oauth_credentials WHERE user_id = %s AND is_valid = TRUE;",
                    (user_id,),
                )
                acct_row = await cur.fetchone()
                linked_accounts = acct_row["count"] if acct_row else 0

        total_inflow = 0.0
        total_outflow = 0.0
        uncategorized_count = 0
        category_totals: dict[int | None, float] = {}

        for tx in transactions:
            amt = float(tx["amount"])
            if tx["is_inflow"]:
                total_inflow += amt
            else:
                total_outflow += amt
                cat_key = tx["category_id"]
                category_totals[cat_key] = category_totals.get(cat_key, 0.0) + amt

            if tx["status"] != TransactionStatus.CATEGORIZED.value or tx["category_id"] is None:
                uncategorized_count += 1

        breakdown = []
        for cat_id, amt in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            cat_name = categories.get(cat_id, "Uncategorized") if cat_id else "Uncategorized"
            breakdown.append({"category_id": cat_id, "category_name": cat_name, "total_amount": round(amt, 2)})

        return {
            "total_inflow": round(total_inflow, 2),
            "total_outflow": round(total_outflow, 2),
            "net_buffer": round(total_inflow - total_outflow, 2),
            "transaction_count": len(transactions),
            "uncategorized_count": uncategorized_count,
            "category_breakdown": breakdown,
            "linked_accounts_count": linked_accounts,
        }

    # -------------------------------------------------------------------------
    # BYO-LLM Config
    # -------------------------------------------------------------------------
    async def get_llm_config(self, user_id: str) -> LLMConfig | None:
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT user_id, provider, model_name, encrypted_key, created_at, updated_at "
                    "FROM llm_configs WHERE user_id = %s;",
                    (user_id,),
                )
                row = await cur.fetchone()
                if not row:
                    return None
                return LLMConfig(
                    user_id=str(row["user_id"]),
                    provider=row["provider"],
                    model_name=row["model_name"],
                    encrypted_key=row["encrypted_key"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

    async def save_llm_config(self, user_id: str, provider: str, model_name: str, encrypted_key: str) -> LLMConfig:
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        INSERT INTO llm_configs (user_id, provider, model_name, encrypted_key, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id) DO UPDATE SET
                            provider = EXCLUDED.provider,
                            model_name = EXCLUDED.model_name,
                            encrypted_key = EXCLUDED.encrypted_key,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING user_id, provider, model_name, encrypted_key, created_at, updated_at;
                        """,
                        (user_id, provider, model_name, encrypted_key),
                    )
                    row = await cur.fetchone()
                    return LLMConfig(
                        user_id=str(row["user_id"]),
                        provider=row["provider"],
                        model_name=row["model_name"],
                        encrypted_key=row["encrypted_key"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )

    # -------------------------------------------------------------------------
    # OAuth Credentials
    # -------------------------------------------------------------------------
    async def add_oauth_credential(
        self,
        user_id: str,
        source: str,
        encrypted_access_token: str,
        encrypted_refresh_token: str,
        expires_at: datetime,
        is_valid: bool = True,
    ) -> OAuthCredential:
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        INSERT INTO oauth_credentials (
                            user_id, source, encrypted_access_token, encrypted_refresh_token,
                            expires_at, is_valid, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        RETURNING id, user_id, source, encrypted_access_token, encrypted_refresh_token,
                                  expires_at, is_valid, created_at, updated_at;
                        """,
                        (
                            user_id,
                            source,
                            encrypted_access_token,
                            encrypted_refresh_token,
                            expires_at,
                            is_valid,
                        ),
                    )
                    row = await cur.fetchone()
                    return self._row_to_oauth(row)

    async def get_expiring_oauth_credentials(self, cutoff: datetime) -> list[OAuthCredential]:
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT id, user_id, source, encrypted_access_token, encrypted_refresh_token, "
                    "expires_at, is_valid, created_at, updated_at FROM oauth_credentials "
                    "WHERE expires_at < %s AND is_valid = TRUE;",
                    (cutoff,),
                )
                rows = await cur.fetchall()
                return [self._row_to_oauth(r) for r in rows]

    async def update_oauth_credential(
        self,
        cred_id: int,
        encrypted_access_token: str,
        expires_at: datetime,
        is_valid: bool = True,
    ) -> None:
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        UPDATE oauth_credentials
                        SET encrypted_access_token = %s, expires_at = %s, is_valid = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s;
                        """,
                        (encrypted_access_token, expires_at, is_valid, cred_id),
                    )

    # -------------------------------------------------------------------------
    # Quarantine Queue
    # -------------------------------------------------------------------------
    async def add_quarantined_email(
        self,
        user_id: str,
        email_text: str,
        error_reason: str,
    ) -> QuarantinedEmail:
        household_id = await self.get_primary_household_id(user_id)
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        INSERT INTO quarantined_emails (
                            user_id, household_id, email_text, error_reason, resolved, created_at
                        )
                        VALUES (%s, %s, %s, %s, FALSE, CURRENT_TIMESTAMP)
                        RETURNING id, user_id, household_id, raw_email_id, email_url,
                                  ingress_payload_id, email_text, error_reason, resolved,
                                  created_at, resolved_at;
                        """,
                        (user_id, household_id, email_text, error_reason),
                    )
                    row = await cur.fetchone()
                    return self._row_to_quarantine(row)

    async def get_quarantined_emails(
        self,
        user_id: str,
        resolved: bool | None = None,
    ) -> list[QuarantinedEmail]:
        query = [
            "SELECT id, user_id, household_id, raw_email_id, email_url, ingress_payload_id, "
            "email_text, error_reason, resolved, created_at, resolved_at FROM quarantined_emails "
            "WHERE user_id = %s"
        ]
        params: list[Any] = [user_id]
        if resolved is not None:
            query.append("AND resolved = %s")
            params.append(resolved)

        query.append("ORDER BY created_at DESC, id DESC;")
        sql = " ".join(query)

        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql, tuple(params))
                rows = await cur.fetchall()
                return [self._row_to_quarantine(r) for r in rows]

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------
    def _row_to_tx(self, row: dict[str, Any]) -> Transaction:
        return Transaction(
            id=row["id"],
            user_id=str(row["user_id"]),
            household_id=str(row["household_id"]) if row["household_id"] else None,
            amount=float(row["amount"]),
            currency=row["currency"],
            is_inflow=bool(row["is_inflow"]),
            record_date=row["record_date"],
            vendor_raw=row["vendor_raw"],
            category_id=row["category_id"],
            status=TransactionStatus(row["status"]) if row["status"] else TransactionStatus.PARSED,
            tx_hash=row["tx_hash"],
            dedupe_hash=row["dedupe_hash"],
            raw_source=row["raw_source"],
            raw_email_id=row["raw_email_id"],
            email_url=row["email_url"],
            created_at=row["created_at"],
        )

    def _row_to_oauth(self, row: dict[str, Any]) -> OAuthCredential:
        return OAuthCredential(
            id=row["id"],
            user_id=str(row["user_id"]),
            source=row["source"],
            encrypted_access_token=row["encrypted_access_token"],
            encrypted_refresh_token=row["encrypted_refresh_token"],
            expires_at=row["expires_at"],
            is_valid=row["is_valid"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _row_to_quarantine(self, row: dict[str, Any]) -> QuarantinedEmail:
        return QuarantinedEmail(
            id=row["id"],
            email_text=row["email_text"],
            error_reason=row["error_reason"],
            user_id=str(row["user_id"]) if row["user_id"] else None,
            household_id=str(row["household_id"]) if row["household_id"] else None,
            raw_email_id=row["raw_email_id"],
            email_url=row["email_url"],
            ingress_payload_id=str(row["ingress_payload_id"]) if row["ingress_payload_id"] else None,
            resolved=bool(row["resolved"]),
            created_at=row["created_at"],
            resolved_at=row["resolved_at"],
        )
