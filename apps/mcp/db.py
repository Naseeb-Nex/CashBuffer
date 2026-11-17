from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from apps.mcp.config import MCPConfig

logger = logging.getLogger(__name__)


class DatabasePool:
    """
    Native psycopg 3 asynchronous connection pool.
    Exclusively provides read-only connections for MCP tool execution.
    Uses native psycopg 3 only.
    """

    def __init__(
        self,
        conninfo: str | None = None,
        min_size: int = 1,
        max_size: int = 10,
        timeout: float = 30.0,
    ) -> None:
        self.conninfo = conninfo
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout
        self._pool: AsyncConnectionPool | None = None

    @classmethod
    def from_config(cls, config: MCPConfig) -> DatabasePool:
        return cls(
            conninfo=config.get_psycopg_conninfo(),
            min_size=config.pool_min_size,
            max_size=config.pool_max_size,
            timeout=config.pool_timeout,
        )

    @property
    def is_open(self) -> bool:
        return self._pool is not None and not self._pool.closed

    async def open(self) -> None:
        """Initialize and open the async connection pool."""
        if self._pool is None or self._pool.closed:
            if not self.conninfo:
                raise ValueError("Cannot open DatabasePool without valid conninfo.")
            logger.info("Opening native psycopg 3 AsyncConnectionPool (min=%d, max=%d)", self.min_size, self.max_size)
            self._pool = AsyncConnectionPool(
                conninfo=self.conninfo,
                min_size=self.min_size,
                max_size=self.max_size,
                timeout=self.timeout,
                open=False,
            )
            await self._pool.open()

    async def close(self) -> None:
        """Close all connections and shutdown the pool."""
        if self._pool is not None and not self._pool.closed:
            logger.info("Closing native psycopg 3 AsyncConnectionPool")
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def acquire_read_only(self) -> AsyncIterator[AsyncConnection[dict[str, Any]]]:
        """
        Acquires a connection configured strictly for read-only transactions.
        Guarantees:
        1. Connection is set to read_only=True
        2. Row factory produces dictionary records (dict_row)
        3. Transaction rolled back upon exit to prevent state leakage
        """
        if self._pool is None or self._pool.closed:
            raise RuntimeError("DatabasePool is not open. Call `await pool.open()` before acquiring connections.")

        async with self._pool.connection(timeout=self.timeout) as conn:
            await conn.set_read_only(True)
            conn.row_factory = dict_row
            try:
                yield conn
            finally:
                # Always roll back to clean up any transaction state
                await conn.rollback()


_global_pool: DatabasePool | None = None


def get_db_pool() -> DatabasePool:
    """Get the active global DatabasePool."""
    global _global_pool
    if _global_pool is None:
        _global_pool = DatabasePool.from_config(MCPConfig())
    return _global_pool


def set_db_pool(pool: DatabasePool | None) -> None:
    """Set the active global DatabasePool (useful for testing or custom lifecycles)."""
    global _global_pool
    _global_pool = pool
