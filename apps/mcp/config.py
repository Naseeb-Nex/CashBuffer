from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class MCPConfig:
    """Configuration for CashBuffer Phase 2C MCP Server."""

    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql://user:password@localhost:5432/cashbuffer"
        )
    )
    pool_min_size: int = field(
        default_factory=lambda: int(os.getenv("DB_POOL_MIN_SIZE", "1"))
    )
    pool_max_size: int = field(
        default_factory=lambda: int(os.getenv("DB_POOL_MAX_SIZE", "10"))
    )
    pool_timeout: float = field(
        default_factory=lambda: float(os.getenv("DB_POOL_TIMEOUT", "30.0"))
    )
    server_name: str = field(
        default_factory=lambda: os.getenv("MCP_SERVER_NAME", "cashbuffer-mcp")
    )
    auth_provider_type: str = field(
        default_factory=lambda: os.getenv("AUTH_PROVIDER", "jwt")
    )
    jwt_secret: str = field(
        default_factory=lambda: os.getenv("JWT_SECRET", "")
    )
    jwt_algorithms: list[str] = field(
        default_factory=lambda: [os.getenv("JWT_ALGORITHM", "HS256")]
    )
    jwt_audience: str | None = field(
        default_factory=lambda: os.getenv("JWT_AUDIENCE", None)
    )
    jwt_issuer: str | None = field(
        default_factory=lambda: os.getenv("JWT_ISSUER", None)
    )

    def get_psycopg_conninfo(self) -> str:
        """
        Normalize database connection string for native psycopg 3.
        Removes dialect suffixes (+asyncpg, +psycopg, etc.)
        """
        url = self.database_url
        if "+asyncpg" in url:
            url = url.replace("+asyncpg", "")
        if "+psycopg2" in url:
            url = url.replace("+psycopg2", "")
        if "+psycopg" in url:
            url = url.replace("+psycopg", "")
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        return url
