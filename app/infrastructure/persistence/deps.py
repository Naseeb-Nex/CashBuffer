from app.infrastructure.persistence.db_pool import get_db_pool
from app.infrastructure.persistence.native_repository import NativeRepository

async def get_repository() -> NativeRepository:
    """FastAPI dependency for NativeRepository backed by psycopg 3 pool."""
    pool = await get_db_pool()
    if pool is None:
        raise RuntimeError("Native psycopg 3 database connection pool is not available.")
    return NativeRepository(pool)
