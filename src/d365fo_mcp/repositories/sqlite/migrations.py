"""
SQLite Database Migrations

Handles schema versioning and migration for SQLite repositories.
"""

import sqlite3
from typing import Dict, Any
import structlog

from .schemas import SQLITE_MIGRATIONS

logger = structlog.get_logger(__name__)


async def get_current_schema_version(connection: sqlite3.Connection) -> int:
    """Get current schema version from SQLite database"""
    try:
        cursor = connection.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='schema_migrations'
        """)

        if cursor.fetchone():
            cursor = connection.execute("""
                SELECT MAX(version) as version FROM schema_migrations
            """)
            row = cursor.fetchone()
            version = row[0] if row else None
            return int(version) if version is not None else 0
        else:
            return 0

    except sqlite3.Error:
        return 0


async def apply_migration(connection: sqlite3.Connection, migration: Dict[str, Any]) -> None:
    """Apply a single SQLite migration"""
    version = migration["version"]
    description = migration["description"]
    sql = migration["sql"]

    logger.info(f"Applying SQLite migration {version}: {description}")

    try:
        # Split SQL statements and execute each one
        statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]

        for statement in statements:
            connection.execute(statement)

        # Record migration in tracking table
        connection.execute(
            """
            INSERT OR REPLACE INTO schema_migrations (version, description) 
            VALUES (?, ?)
        """,
            (version, description),
        )

        connection.commit()

        logger.info(f"SQLite migration {version} applied successfully")

    except sqlite3.Error as e:
        connection.rollback()
        raise RuntimeError(f"Failed to apply SQLite migration {version}: {e}") from e


async def run_migrations(connection: sqlite3.Connection) -> None:
    """Run all pending SQLite database migrations"""
    current_version = await get_current_schema_version(connection)

    logger.info(f"Current SQLite schema version: {current_version}")

    pending_migrations = [
        migration for migration in SQLITE_MIGRATIONS 
        if isinstance(migration["version"], int) and migration["version"] > current_version
    ]

    if not pending_migrations:
        logger.info("No pending SQLite migrations")
        return

    logger.info(f"Found {len(pending_migrations)} pending SQLite migrations")

    for migration in pending_migrations:
        await apply_migration(connection, migration)

    final_version = await get_current_schema_version(connection)
    logger.info(f"SQLite schema updated to version {final_version}")


async def reset_database(connection: sqlite3.Connection) -> None:
    """Reset SQLite database by dropping all tables (for development/testing)"""
    logger.warning("Resetting SQLite database - all data will be lost")

    try:
        # Get all table names
        cursor = connection.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)

        tables = [row[0] for row in cursor.fetchall()]

        # Drop all tables
        for table in tables:
            connection.execute(f"DROP TABLE IF EXISTS {table}")

        connection.commit()

        logger.info(f"Dropped {len(tables)} SQLite tables")

        # Run migrations to recreate schema
        await run_migrations(connection)

    except sqlite3.Error as e:
        connection.rollback()
        raise RuntimeError(f"Failed to reset SQLite database: {e}") from e