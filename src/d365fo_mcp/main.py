"""
D365FO MCP Server

Main entry point for the simplified D365 Finance & Operations MCP server.
"""

import argparse
import asyncio
from pathlib import Path
from typing import Optional
import structlog
from fastmcp import FastMCP

from .config import load_dotenv_if_exists
from .server_factory import ServerFactory, ServerValidator


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)






def main() -> Optional[int]:
    """Main entry point with command line argument parsing"""
    # Load environment variables
    load_dotenv_if_exists()

    parser = argparse.ArgumentParser(description="D365FO MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio"],
        default="stdio",
        help="Transport mode (currently only stdio supported)",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Log level (default: info)",
    )
    parser.add_argument(
        "--validate-config", action="store_true", help="Validate configuration and exit"
    )
    parser.add_argument("--init-db", action="store_true", help="Initialize database and exit")

    args = parser.parse_args()

    # Configure logging level
    import logging

    log_level = getattr(logging, args.log_level.upper())
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.dev.ConsoleRenderer()
            if args.transport == "stdio"
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Handle special commands
    if args.validate_config:
        asyncio.run(ServerValidator.validate_configuration())
        return 0

    if args.init_db:
        asyncio.run(ServerValidator.initialize_database_only())
        return 0

    # Create fully configured server
    try:
        mcp = asyncio.run(ServerFactory.create_configured_server())
    except Exception as e:
        logger.error("Failed to initialize server", error=str(e))
        return 1

    # Run server (STDIO mode only for v1)
    if args.transport == "stdio":
        # Disable all logging to prevent stdout/stderr contamination in STDIO mode
        import logging

        logging.disable(logging.CRITICAL)

        logger.info("Starting D365FO MCP Server with STDIO transport")
        mcp.run(transport="stdio")
        return 0
    else:
        logger.error("Only STDIO transport is supported in version 0.1.0")
        return 1




if __name__ == "__main__":
    exit_code = main()
    exit(exit_code or 0)
