import logging

from psycopg_pool import AsyncConnectionPool

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: AsyncConnectionPool | None = None

def get_psycopg_conninfo(url: str) -> str:
    """Normalize SQLAlchemy or asyncpg database URL for native psycopg 3."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url

async def get_db_pool() -> AsyncConnectionPool | None:
    """Acquires the shared psycopg 3 async connection pool."""
    global _pool
    conninfo = get_psycopg_conninfo(settings.DATABASE_URL)
    if not (conninfo.startswith("postgresql://") or conninfo.startswith("postgres://")):
        return None

    if _pool is None or _pool.closed:
        try:
            _pool = AsyncConnectionPool(
                conninfo=conninfo,
                min_size=2,
                max_size=10,
                open=False,
            )
            await _pool.open()
        except Exception as e:
            logger.warning(f"Failed to open native psycopg 3 connection pool: {e}")
            return None
    return _pool

async def close_db_pool() -> None:
    """Closes the shared psycopg 3 async connection pool."""
    global _pool
    if _pool is not None and not _pool.closed:
        await _pool.close()
        _pool = None
