import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS households (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    base_currency VARCHAR(3) DEFAULT 'USD' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    idp_user_id VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_users_idp_user UNIQUE (idp_user_id)
);
CREATE INDEX IF NOT EXISTS idx_users_idp_user ON users(idp_user_id);

CREATE TABLE IF NOT EXISTS household_members (
    id UUID PRIMARY KEY,
    household_id UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'owner' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_household_user UNIQUE (household_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_members_user ON household_members(user_id);

CREATE TABLE IF NOT EXISTS ingress_configs (
    id UUID PRIMARY KEY,
    household_id UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL DEFAULT 'gmail',
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    interval_minutes INT NOT NULL DEFAULT 60,
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'idle',
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_household_ingress UNIQUE (household_id, provider)
);
CREATE INDEX IF NOT EXISTS idx_ingress_due ON ingress_configs(is_enabled, next_run_at)
    WHERE is_enabled = TRUE;

CREATE TABLE IF NOT EXISTS ingress_sync_state (
    household_id UUID PRIMARY KEY REFERENCES households(id) ON DELETE CASCADE,
    last_history_id VARCHAR(100),
    last_email_internal_date BIGINT,
    total_processed INT DEFAULT 0 NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
"""


class PsycopgIngressRepository:
    """Pure psycopg 3 implementation of ingress persistence."""

    def __init__(self, pool_or_conn: Any):
        self.pool = pool_or_conn
        self._initialized = False

    def _connection(self):
        if hasattr(self.pool, "connection"):
            return self.pool.connection()
        return self.pool

    async def init_tables(self) -> None:
        if self._initialized:
            return
        async with self._connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.execute(CREATE_TABLES_SQL)
        self._initialized = True

    async def get_or_create_user_and_household(
        self, idp_user_id: str, email: str | None = None
    ) -> tuple[str, str]:
        """
        Preserve provider-neutral internal user mapping:
        Resolves external `idp_user_id` -> internal `users.id` (UUID),
        and resolves the user's primary `household_id` (UUID).
        """
        await self.init_tables()
        if not email:
            email = f"{idp_user_id}@cashbuffer.local"

        async with self._connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    # 1. Lookup internal user by idp_user_id
                    await cur.execute(
                        "SELECT id FROM users WHERE idp_user_id = %s;",
                        (idp_user_id,),
                    )
                    user_row = await cur.fetchone()
                    if user_row:
                        user_id = str(user_row["id"])
                    else:
                        new_user_id = str(uuid.uuid4())
                        await cur.execute(
                            """
                            INSERT INTO users (id, idp_user_id, email, created_at)
                            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (idp_user_id) DO UPDATE SET idp_user_id = EXCLUDED.idp_user_id
                            RETURNING id;
                            """,
                            (new_user_id, idp_user_id, email),
                        )
                        inserted = await cur.fetchone()
                        user_id = str(inserted["id"])

                    # 2. Lookup household membership
                    await cur.execute(
                        "SELECT household_id FROM household_members WHERE user_id = %s LIMIT 1;",
                        (user_id,),
                    )
                    member_row = await cur.fetchone()
                    if member_row:
                        household_id = str(member_row["household_id"])
                    else:
                        # Create default household & membership
                        household_id = str(uuid.uuid4())
                        membership_id = str(uuid.uuid4())
                        await cur.execute(
                            """
                            INSERT INTO households (id, name, base_currency, created_at)
                            VALUES (%s, %s, 'USD', CURRENT_TIMESTAMP);
                            """,
                            (household_id, f"{idp_user_id}'s Household"),
                        )
                        await cur.execute(
                            """
                            INSERT INTO household_members (id, household_id, user_id, role, created_at)
                            VALUES (%s, %s, %s, 'owner', CURRENT_TIMESTAMP);
                            """,
                            (membership_id, household_id, user_id),
                        )

                    return user_id, household_id

    async def get_or_create_config(
        self, household_id: str, user_id: str, provider: str = "gmail"
    ) -> dict[str, Any]:
        """Fetches current ingress config, or atomically initializes default config."""
        await self.init_tables()
        config_id = str(uuid.uuid4())
        async with self._connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        INSERT INTO ingress_configs (
                            id, household_id, user_id, provider, is_enabled,
                            interval_minutes, status, next_run_at, created_at
                        )
                        VALUES (%s, %s, %s, %s, TRUE, 60, 'idle', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ON CONFLICT (household_id, provider) DO UPDATE
                        SET household_id = EXCLUDED.household_id
                        RETURNING id, household_id, user_id, provider, is_enabled,
                                  interval_minutes, last_run_at, next_run_at, status, last_error, created_at;
                        """,
                        (config_id, household_id, user_id, provider),
                    )
                    row = await cur.fetchone()
                    return self._format_config_row(row)

    async def update_config(
        self,
        household_id: str,
        user_id: str,
        provider: str = "gmail",
        interval_minutes: int | None = None,
        is_enabled: bool | None = None,
    ) -> dict[str, Any]:
        """Atomically updates schedule interval or enabled status."""
        await self.init_tables()
        config_id = str(uuid.uuid4())
        async with self._connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        INSERT INTO ingress_configs (
                            id, household_id, user_id, provider, is_enabled,
                            interval_minutes, status, next_run_at, created_at
                        )
                        VALUES (%s, %s, %s, %s, COALESCE(%s, TRUE), COALESCE(%s, 60), 'idle', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ON CONFLICT (household_id, provider) DO UPDATE
                        SET is_enabled = COALESCE(%s, ingress_configs.is_enabled),
                            interval_minutes = COALESCE(%s, ingress_configs.interval_minutes)
                        RETURNING id, household_id, user_id, provider, is_enabled,
                                  interval_minutes, last_run_at, next_run_at, status, last_error, created_at;
                        """,
                        (
                            config_id,
                            household_id,
                            user_id,
                            provider,
                            is_enabled,
                            interval_minutes,
                            is_enabled,
                            interval_minutes,
                        ),
                    )
                    row = await cur.fetchone()
                    return self._format_config_row(row)

    async def trigger_sync(
        self, household_id: str, user_id: str, provider: str = "gmail"
    ) -> dict[str, Any]:
        """Atomically triggers immediate sync by setting next_run_at = CURRENT_TIMESTAMP."""
        await self.init_tables()
        config_id = str(uuid.uuid4())
        async with self._connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        INSERT INTO ingress_configs (
                            id, household_id, user_id, provider, is_enabled,
                            interval_minutes, status, next_run_at, created_at
                        )
                        VALUES (%s, %s, %s, %s, TRUE, 60, 'idle', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ON CONFLICT (household_id, provider) DO UPDATE
                        SET next_run_at = CURRENT_TIMESTAMP
                        RETURNING id, household_id, user_id, provider, is_enabled,
                                  interval_minutes, last_run_at, next_run_at, status, last_error, created_at;
                        """,
                        (config_id, household_id, user_id, provider),
                    )
                    row = await cur.fetchone()
                    return self._format_config_row(row)

    async def get_status(
        self, household_id: str, user_id: str, provider: str = "gmail"
    ) -> dict[str, Any]:
        """Returns sync checkpoint state and live ingress daemon status."""
        await self.init_tables()
        config = await self.get_or_create_config(household_id, user_id, provider)
        async with self._connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT last_history_id, last_email_internal_date, total_processed, updated_at
                    FROM ingress_sync_state
                    WHERE household_id = %s;
                    """,
                    (household_id,),
                )
                sync_row = await cur.fetchone()

        total_processed = sync_row["total_processed"] if sync_row else 0
        last_history_id = sync_row["last_history_id"] if sync_row else None
        last_email_internal_date = sync_row["last_email_internal_date"] if sync_row else None
        checkpoint_updated_at = sync_row["updated_at"] if sync_row else None

        return {
            "household_id": household_id,
            "provider": provider,
            "status": config["status"],
            "is_enabled": config["is_enabled"],
            "interval_minutes": config["interval_minutes"],
            "last_run_at": config["last_run_at"],
            "next_run_at": config["next_run_at"],
            "last_error": config["last_error"],
            "total_processed": total_processed,
            "last_history_id": last_history_id,
            "last_email_internal_date": last_email_internal_date,
            "checkpoint_updated_at": checkpoint_updated_at,
        }

    def _format_config_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "household_id": str(row["household_id"]),
            "user_id": str(row["user_id"]),
            "provider": row["provider"],
            "is_enabled": bool(row["is_enabled"]),
            "interval_minutes": int(row["interval_minutes"]),
            "last_run_at": row["last_run_at"],
            "next_run_at": row["next_run_at"],
            "status": row["status"],
            "last_error": row["last_error"],
            "created_at": row["created_at"],
        }


class InMemoryIngressRepository:
    """
    In-memory ingress persistence for fast unit/e2e testing
    and environments where no external PostgreSQL instance is running.
    Maintains exact provider-neutral mapping, atomic trigger/update, and tenant safety.
    """

    def __init__(self):
        self.users: dict[str, dict[str, Any]] = {}  # idp_user_id -> user_dict
        self.households: dict[str, dict[str, Any]] = {}  # user_id -> household_id
        self.configs: dict[tuple[str, str], dict[str, Any]] = {}  # (household_id, provider) -> config
        self.sync_states: dict[str, dict[str, Any]] = {}  # household_id -> sync_state

    async def get_or_create_user_and_household(
        self, idp_user_id: str, email: str | None = None
    ) -> tuple[str, str]:
        if idp_user_id not in self.users:
            user_id = str(uuid.uuid4())
            self.users[idp_user_id] = {
                "id": user_id,
                "idp_user_id": idp_user_id,
                "email": email or f"{idp_user_id}@cashbuffer.local",
                "created_at": datetime.now(timezone.utc),
            }
            household_id = str(uuid.uuid4())
            self.households[user_id] = household_id
        else:
            user_id = self.users[idp_user_id]["id"]
            if user_id not in self.households:
                self.households[user_id] = str(uuid.uuid4())
            household_id = self.households[user_id]

        return user_id, household_id

    async def get_or_create_config(
        self, household_id: str, user_id: str, provider: str = "gmail"
    ) -> dict[str, Any]:
        key = (household_id, provider)
        if key not in self.configs:
            now = datetime.now(timezone.utc)
            self.configs[key] = {
                "id": str(uuid.uuid4()),
                "household_id": household_id,
                "user_id": user_id,
                "provider": provider,
                "is_enabled": True,
                "interval_minutes": 60,
                "last_run_at": None,
                "next_run_at": now,
                "status": "idle",
                "last_error": None,
                "created_at": now,
            }
        return dict(self.configs[key])

    async def update_config(
        self,
        household_id: str,
        user_id: str,
        provider: str = "gmail",
        interval_minutes: int | None = None,
        is_enabled: bool | None = None,
    ) -> dict[str, Any]:
        cfg = await self.get_or_create_config(household_id, user_id, provider)
        if interval_minutes is not None:
            cfg["interval_minutes"] = interval_minutes
        if is_enabled is not None:
            cfg["is_enabled"] = is_enabled
        self.configs[(household_id, provider)] = cfg
        return dict(cfg)

    async def trigger_sync(
        self, household_id: str, user_id: str, provider: str = "gmail"
    ) -> dict[str, Any]:
        cfg = await self.get_or_create_config(household_id, user_id, provider)
        cfg["next_run_at"] = datetime.now(timezone.utc)
        self.configs[(household_id, provider)] = cfg
        return dict(cfg)

    async def get_status(
        self, household_id: str, user_id: str, provider: str = "gmail"
    ) -> dict[str, Any]:
        cfg = await self.get_or_create_config(household_id, user_id, provider)
        sync = self.sync_states.get(household_id, {})
        return {
            "household_id": household_id,
            "provider": provider,
            "status": cfg["status"],
            "is_enabled": cfg["is_enabled"],
            "interval_minutes": cfg["interval_minutes"],
            "last_run_at": cfg["last_run_at"],
            "next_run_at": cfg["next_run_at"],
            "last_error": cfg["last_error"],
            "total_processed": sync.get("total_processed", 0),
            "last_history_id": sync.get("last_history_id"),
            "last_email_internal_date": sync.get("last_email_internal_date"),
            "checkpoint_updated_at": sync.get("updated_at"),
        }
