"""psycopg 3 connection pool for Ingress microservice."""

from __future__ import annotations

import os
from psycopg_pool import AsyncConnectionPool

_pool: AsyncConnectionPool | None = None

def get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cashbuffer")
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url.startswith("postgresql+psycopg://"):
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url

async def get_ingress_db_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        _pool = AsyncConnectionPool(
            conninfo=get_database_url(),
            min_size=2,
            max_size=10,
            open=False,
            timeout=5.0,
        )
        await _pool.open()
    return _pool

async def close_ingress_db_pool() -> None:
    global _pool
    if _pool is not None and not _pool.closed:
        await _pool.close()
        _pool = None
