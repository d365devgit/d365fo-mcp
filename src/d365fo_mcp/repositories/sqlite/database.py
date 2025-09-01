"""
SQLite Database Connection and Infrastructure

Provides database connection management and migrations for SQLite repositories.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Union, Any
import structlog

logger = structlog.get_logger(__name__)


class DatabaseError(Exception):
    """Database operation errors"""
    pass


class Database:
    """SQLite database connection manager"""

    def __init__(self, db_path: Union[str, Path] = "./d365fo-mcp.db"):
        self.db_path = Path(db_path)
        logger.info("Database init", db_path=str(self.db_path), parent=str(self.db_path.parent), cwd=str(Path.cwd()))
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error("Failed to create database directory", db_path=str(self.db_path), parent=str(self.db_path.parent), error=str(e))
            raise
        self._connection: Optional[sqlite3.Connection] = None

    async def initialize(self) -> None:
        """Initialize database and run migrations"""
        from .migrations import run_migrations

        logger.info("Initializing SQLite database", db_path=str(self.db_path))

        connection = await self.get_connection()
        await run_migrations(connection)

        logger.info("SQLite database initialized successfully")

    async def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        if self._connection is None:
            try:
                self._connection = sqlite3.connect(
                    self.db_path, check_same_thread=False, timeout=30.0
                )
                self._connection.row_factory = sqlite3.Row
                self._connection.execute("PRAGMA foreign_keys = ON")
                self._connection.execute("PRAGMA journal_mode = WAL")

                logger.debug("SQLite connection established", db_path=str(self.db_path))

            except sqlite3.Error as e:
                raise DatabaseError(f"Failed to connect to SQLite database: {e}") from e

        return self._connection

    async def close(self) -> None:
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.debug("SQLite connection closed")

    async def __aenter__(self) -> 'Database':
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()