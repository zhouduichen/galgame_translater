"""Shared SQLite schema validation for API and worker startup."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

MIGRATION_LOG_TABLE = "_migration_log"
REQUIRED_MIGRATIONS = (
    "add_idempotency_key_col",
    "add_retry_count_col",
    "add_locked_until_col",
)


def _table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cursor.fetchone() is not None


def _migration_applied(cursor: sqlite3.Cursor, name: str) -> bool:
    if not _table_exists(cursor, MIGRATION_LOG_TABLE):
        return False
    cursor.execute(
        f"SELECT 1 FROM {MIGRATION_LOG_TABLE} WHERE name=?",
        (name,),
    )
    return cursor.fetchone() is not None


def check_schema_version(db_path: str | Path) -> str:
    """Return the schema version or stop startup for incomplete V1 databases."""
    db_path = Path(db_path)
    if not db_path.exists():
        return "NO_DB"

    conn = sqlite3.connect(str(db_path), timeout=10)
    cursor = conn.cursor()
    try:
        if not _table_exists(cursor, MIGRATION_LOG_TABLE):
            print(
                "FATAL: Database schema is V1. "
                "Run `python scripts/migrate_v1_to_v2.py --apply` before starting services."
            )
            sys.exit(1)

        missing = [
            name for name in REQUIRED_MIGRATIONS
            if not _migration_applied(cursor, name)
        ]
    finally:
        conn.close()

    if missing:
        print(
            f"FATAL: Missing required migration(s): {', '.join(missing)}. "
            "Run `python scripts/migrate_v1_to_v2.py --apply`."
        )
        sys.exit(1)

    return "V2"
