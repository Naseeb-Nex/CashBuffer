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
        """Validate native psycopg 3 PostgreSQL connection URL."""
        if not self.database_url.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must use native postgresql:// scheme")
        return self.database_url
