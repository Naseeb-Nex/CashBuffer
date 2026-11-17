from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from typing import Any, Literal

from pydantic import Field
from typing_extensions import Annotated

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore[attr-defined]
except (ImportError, ModuleNotFoundError):
    from mcp.server.mcpserver import MCPServer as FastMCP

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import CallToolResult

from apps.mcp.auth import (
    AuthProvider,
    JWTAuthProvider,
    auth_scope,
    extract_headers_from_ctx,
    forbid_user_supplied_authority,
    get_current_auth_context,
)
from apps.mcp.config import MCPConfig
from apps.mcp.db import DatabasePool, set_db_pool
from apps.mcp.tools.monthly_summary import execute_monthly_summary
from apps.mcp.tools.recurring_bills import execute_recurring_bills
from apps.mcp.tools.transactions import execute_query_transactions

logger = logging.getLogger(__name__)


class CashBufferMCPServer(MCPServer):
    """
    CashBuffer Phase 2C MCP Server.
    Enforces read-only, multi-tenant boundaries with native psycopg 3 and provider-neutral auth.
    Strictly forbids caller-supplied authority overrides.
    """

    def __init__(
        self,
        name: str = "cashbuffer-mcp",
        config: MCPConfig | None = None,
        pool: DatabasePool | None = None,
        auth_provider: AuthProvider | None = None,
        **kwargs: Any,
    ) -> None:
        self.config = config or MCPConfig()
        self.pool = pool or DatabasePool.from_config(self.config)
        self.auth_provider = auth_provider or (
            JWTAuthProvider(
                secret_or_key=self.config.jwt_secret,
                algorithms=self.config.jwt_algorithms,
                audience=self.config.jwt_audience,
                issuer=self.config.jwt_issuer,
            )
            if self.config.auth_provider_type == "jwt"
            else None
        )

        @asynccontextmanager
        async def default_lifespan(server: MCPServer) -> AsyncIterator[dict[str, Any]]:
            logger.info("Initializing CashBuffer MCP Server...")
            if not self.pool.is_open:
                try:
                    await self.pool.open()
                except Exception as e:
                    logger.warning("Could not auto-open database pool during startup: %s", e)
            set_db_pool(self.pool)
            try:
                yield {"pool": self.pool}
            finally:
                logger.info("Shutting down CashBuffer MCP Server...")
                if self.pool.is_open:
                    await self.pool.close()

        super().__init__(name=name, lifespan=default_lifespan, **kwargs)
        self._register_tools()

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: Context | None = None,
    ) -> CallToolResult:
        """
        Intercept tool calls to enforce:
        1. No user-supplied authority in arguments (zero-trust perimeter)
        2. Transport header authentication if active context not already set
        """
        # Strictly forbid caller-supplied authority keys in arguments
        forbid_user_supplied_authority(arguments)

        # If no active context is set in ContextVar, attempt to authenticate from transport headers
        active_auth = get_current_auth_context(context)
        if active_auth is None and self.auth_provider is not None:
            headers = extract_headers_from_ctx(context)
            if headers:
                auth_header = headers.get("authorization") or headers.get("Authorization")
                if auth_header:
                    try:
                        resolved_auth = await self.auth_provider.authenticate(auth_header)
                        async with auth_scope(resolved_auth):
                            return await super().call_tool(name, arguments, context=context)
                    except Exception as e:
                        logger.debug("Failed header authentication: %s", e)

        return await super().call_tool(name, arguments, context=context)

    def _register_tools(self) -> None:
        server = self
        pool = self.pool

        @server.tool(
            name="monthly_summary",
            description="Calculate read-only monthly financial summary with income, outflow, net buffer, and category breakdown for the authenticated tenant.",
        )
        async def monthly_summary(
            year: Annotated[int, Field(ge=1970, le=2100, description="Calendar year (e.g. 2026)")],
            month: Annotated[int, Field(ge=1, le=12, description="Calendar month (1-12)")],
            ctx: Context,
        ) -> dict[str, Any]:
            return await execute_monthly_summary(year=year, month=month, ctx=ctx, pool=pool)

        @server.tool(
            name="query_transactions",
            description="Query and filter tenant ledger transactions with pagination and optional search filters.",
        )
        async def query_transactions(
            limit: Annotated[int, Field(default=50, ge=1, le=100, description="Max transactions to return (1-100)")] = 50,
            offset: Annotated[int, Field(default=0, ge=0, description="Offset for pagination (>=0)")] = 0,
            start_date: Annotated[date | None, Field(default=None, description="Start date filter (YYYY-MM-DD)")] = None,
            end_date: Annotated[date | None, Field(default=None, description="End date filter (YYYY-MM-DD)")] = None,
            status: Annotated[
                Literal["parsed", "needs_review", "categorized"] | None,
                Field(default=None, description="Categorization status"),
            ] = None,
            category_id: Annotated[int | None, Field(default=None, ge=1, description="Category ID")] = None,
            search: Annotated[str | None, Field(default=None, max_length=100, description="Vendor search query")] = None,
            min_amount: Annotated[float | None, Field(default=None, ge=0.0, description="Minimum amount")] = None,
            max_amount: Annotated[float | None, Field(default=None, ge=0.0, description="Maximum amount")] = None,
            is_inflow: Annotated[bool | None, Field(default=None, description="True for income, False for expense")] = None,
            ctx: Context = None,  # type: ignore[assignment]
        ) -> dict[str, Any]:
            return await execute_query_transactions(
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
                ctx=ctx,
                pool=pool,
            )

        @server.tool(
            name="recurring_bills",
            description="Detect recurring bills and subscriptions from past expenses for the authenticated tenant.",
        )
        async def recurring_bills(
            min_occurrences: Annotated[
                int, Field(default=2, ge=2, le=50, description="Minimum frequency threshold to qualify as recurring")
            ] = 2,
            lookback_months: Annotated[
                int, Field(default=12, ge=1, le=60, description="Lookback window in months (1-60)")
            ] = 12,
            ctx: Context = None,  # type: ignore[assignment]
        ) -> dict[str, Any]:
            return await execute_recurring_bills(
                min_occurrences=min_occurrences,
                lookback_months=lookback_months,
                ctx=ctx,
                pool=pool,
            )

        @server.tool(
            name="detect_recurring_bills",
            description="Detect recurring bills and subscriptions from past expenses for the authenticated tenant.",
        )
        async def detect_recurring_bills(
            min_occurrences: Annotated[
                int, Field(default=2, ge=2, le=50, description="Minimum frequency threshold to qualify as recurring")
            ] = 2,
            lookback_months: Annotated[
                int, Field(default=12, ge=1, le=60, description="Lookback window in months (1-60)")
            ] = 12,
            ctx: Context = None,  # type: ignore[assignment]
        ) -> dict[str, Any]:
            return await execute_recurring_bills(
                min_occurrences=min_occurrences,
                lookback_months=lookback_months,
                ctx=ctx,
                pool=pool,
            )


def create_server(
    config: MCPConfig | None = None,
    pool: DatabasePool | None = None,
    auth_provider: AuthProvider | None = None,
) -> CashBufferMCPServer:
    """Factory creating and configuring the CashBuffer MCP Server."""
    return CashBufferMCPServer(
        config=config,
        pool=pool,
        auth_provider=auth_provider,
    )


# Default package-level server instance
server = create_server()

__all__ = [
    "CashBufferMCPServer",
    "FastMCP",
    "create_server",
    "server",
]
