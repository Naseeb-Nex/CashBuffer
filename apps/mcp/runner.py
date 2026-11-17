from __future__ import annotations

import argparse
import logging
import sys

from apps.mcp.server import server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CashBuffer MCP Server (Phase 2C)")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport protocol (stdio, sse, streamable-http)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP/SSE transport")
    parser.add_argument("--port", type=int, default=8001, help="Port for HTTP/SSE transport")

    args = parser.parse_args()

    if args.transport == "stdio":
        server.run(transport="stdio")
    elif args.transport == "sse":
        server.run(transport="sse", host=args.host, port=args.port)
    elif args.transport == "streamable-http":
        server.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
