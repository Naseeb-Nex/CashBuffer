import logging

from psycopg_pool import AsyncConnectionPool

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: AsyncConnectionPool | None = None

def get_psycopg_conninfo(url: str) -> str:
    """Validate native psycopg 3 connection URL."""
    if not url.startswith("postgresql://"):
        raise ValueError("DATABASE_URL must use native postgresql:// scheme")
    return url

async def get_db_pool() -> AsyncConnectionPool | None:
    """Acquires the shared psycopg 3 async connection pool."""
    global _pool
    conninfo = get_psycopg_conninfo(settings.DATABASE_URL)
    if not conninfo.startswith("postgresql://"):
        return None

    if _pool is None or _pool.closed:
        candidate_pool = None
        try:
            candidate_pool = AsyncConnectionPool(
                conninfo=conninfo,
                min_size=1,
                max_size=10,
                open=False,
                timeout=10.0,
            )
            await candidate_pool.open(wait=True, timeout=10.0)
            _pool = candidate_pool
        except Exception as e:
            logger.warning(f"Failed to open native psycopg 3 connection pool: {e}")
            if candidate_pool is not None and not candidate_pool.closed:
                try:
                    await candidate_pool.close()
                except Exception:
                    pass
            _pool = None
            return None
    return _pool

async def close_db_pool() -> None:
    """Closes the shared psycopg 3 async connection pool."""
    global _pool
    if _pool is not None and not _pool.closed:
        await _pool.close()
        _pool = None
