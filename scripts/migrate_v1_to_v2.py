#!/usr/bin/env python3
"""
V1 → V2 database migration script for Galgame Translater.

Usage:
    python scripts/migrate_v1_to_v2.py                   # dry-run (default)
    python scripts/migrate_v1_to_v2.py --apply           # apply migrations
    python scripts/migrate_v1_to_v2.py --apply --force   # apply even if already applied
    python scripts/migrate_v1_to_v2.py --rollback        # print rollback plan (no-op)

Environment:
    GALGAME_DATABASE_URL   SQLite URL (default: sqlite:///apps/api/data/galgame.db)
    GALGAME_DB_DIR         Alternative: data directory path

Design:
    - Idempotent: each migration item checks _migration_log before running.
    - Column-compatible: detects existing columns before ADD COLUMN.
    - Dry-run by default: reports what would change without modifying DB.
    - Auto-backup before data-changing migrations.
    - Service startup calls check_schema_version() to block on missing migrations.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_PROJECT_MODEL_SRC = Path(__file__).resolve().parent.parent / "packages" / "project-model" / "src"
if _PROJECT_MODEL_SRC.is_dir():
    sys.path.insert(0, str(_PROJECT_MODEL_SRC))

from project_model.schema_version import MIGRATION_LOG_TABLE  # noqa: E402, I001


# ── Constants ──────────────────────────────────────────────────────────────

REQUIRED_VERSION = 2
VALID_STATUSES = {"pending", "running", "completed", "failed", "permanently_failed", "cancelled"}

MIGRATIONS: list[dict[str, Any]] = [
    # create_migration_log MUST be first — all later migrations log to it
    {
        "version": 2,
        "name": "create_migration_log",
        "description": "Create _migration_log tracking table",
        "destructive": False,
        "requires_data_cleanup": False,
    },
    {
        "version": 2,
        "name": "add_idempotency_key_col",
        "description": "Add idempotency_key column to generation_jobs",
        "destructive": False,
        "requires_data_cleanup": False,
    },
    {
        "version": 2,
        "name": "add_idempotency_key_index",
        "description": "Create index on generation_jobs(project_id, idempotency_key)",
        "destructive": False,
        "requires_data_cleanup": False,
    },
    {
        "version": 2,
        "name": "add_retry_count_col",
        "description": "Add retry_count column to generation_jobs",
        "destructive": False,
        "requires_data_cleanup": False,
    },
    {
        "version": 2,
        "name": "clean_duplicate_active_jobs",
        "description": (
            "Cancel duplicate pending/running jobs sharing the same "
            "(project_id, job_type, idempotency_key)"
        ),
        "destructive": False,
        "requires_data_cleanup": True,
    },
    {
        "version": 2,
        "name": "create_unique_active_job_index",
        "description": (
            "Add partial unique index on generation_jobs "
            "WHERE status IN ('pending', 'running')"
        ),
        "destructive": False,
        "requires_data_cleanup": True,
    },
    {
        "version": 2,
        "name": "add_locked_until_col",
        "description": "Add locked_until column to generation_jobs for lease-based concurrency",
        "destructive": False,
        "requires_data_cleanup": False,
    },
    {
        "version": 2,
        "name": "validate_status_values",
        "description": "Normalize invalid status values in generation_jobs to 'failed'",
        "destructive": False,
        "requires_data_cleanup": True,
    },
]


# ── Helpers ────────────────────────────────────────────────────────────────


def _resolve_db_path() -> Path:
    """Resolve database path from env or default."""
    url = os.environ.get("GALGAME_DATABASE_URL", "")
    if url:
        # Parse sqlite:///path
        if url.startswith("sqlite:///"):
            return Path(url[10:])
        return Path(url)

    db_dir = os.environ.get("GALGAME_DB_DIR", "")
    if db_dir:
        return Path(db_dir) / "galgame.db"

    # Default: relative to project root
    return Path(__file__).resolve().parent.parent / "apps" / "api" / "data" / "galgame.db"


def _column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cursor.fetchone() is not None


def _index_exists(cursor: sqlite3.Cursor, index_name: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,),
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


def _checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]


def _backup_db(db_path: Path) -> Path:
    """Create a consistent snapshot using SQLite backup API."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = db_path.with_suffix(f".bak.{timestamp}.db")
    src = sqlite3.connect(str(db_path))
    dst = sqlite3.connect(str(backup_path))
    try:
        src.backup(dst, pages=1024)
        print(f"  Backup created: {backup_path.name}")
    finally:
        dst.close()
        src.close()
    return backup_path


# ── Individual Migration Items ─────────────────────────────────────────────


def _mig_add_idempotency_key_col(cursor: sqlite3.Cursor, dry_run: bool) -> str:
    if _column_exists(cursor, "generation_jobs", "idempotency_key"):
        return "SKIP (column already exists)"
    sql = "ALTER TABLE generation_jobs ADD COLUMN idempotency_key VARCHAR"
    if not dry_run:
        cursor.execute(sql)
    return f"OK (`{sql}`)"


def _mig_add_idempotency_key_index(cursor: sqlite3.Cursor, dry_run: bool) -> str:
    if _index_exists(cursor, "idx_generation_jobs_idempotency"):
        return "SKIP (index already exists)"
    if not _column_exists(cursor, "generation_jobs", "idempotency_key"):
        return "SKIP (column idempotency_key does not exist yet)"
    sql = (
        "CREATE INDEX IF NOT EXISTS idx_generation_jobs_idempotency "
        "ON generation_jobs(project_id, idempotency_key)"
    )
    if not dry_run:
        cursor.execute(sql)
    return "OK (`CREATE INDEX ...`)"


def _mig_add_retry_count_col(cursor: sqlite3.Cursor, dry_run: bool) -> str:
    if _column_exists(cursor, "generation_jobs", "retry_count"):
        return "SKIP (column already exists)"
    sql = "ALTER TABLE generation_jobs ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0"
    if not dry_run:
        cursor.execute(sql)
    return f"OK (`{sql}`)"


def _mig_create_migration_log(cursor: sqlite3.Cursor, dry_run: bool) -> str:
    if _table_exists(cursor, MIGRATION_LOG_TABLE):
        return "SKIP (table already exists)"
    sql = f"""
CREATE TABLE IF NOT EXISTS {MIGRATION_LOG_TABLE} (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    version     TEXT    NOT NULL,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT    NOT NULL DEFAULT '',
    checksum    TEXT    NOT NULL,
    applied_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    duration_ms INTEGER
)
"""
    if not dry_run:
        cursor.executescript(sql)
    return "OK (created _migration_log table)"


def _mig_clean_duplicate_active_jobs(cursor: sqlite3.Cursor, dry_run: bool) -> str:
    """Cancel duplicate pending/running jobs with same (project_id, job_type, idempotency_key)."""
    cursor.execute("""
        SELECT COUNT(*) FROM generation_jobs
        WHERE status IN ('pending', 'running')
          AND idempotency_key IS NOT NULL
    """)
    total_active = cursor.fetchone()[0]
    if total_active == 0:
        return "OK (no active jobs to check)"

    cursor.execute("""
        SELECT id, project_id, job_type, idempotency_key, created_at, status
        FROM generation_jobs
        WHERE status IN ('pending', 'running')
          AND idempotency_key IS NOT NULL
        ORDER BY project_id, job_type, idempotency_key, created_at ASC
    """)
    rows = cursor.fetchall()

    # Group by (project_id, job_type, idempotency_key), keep first, cancel rest
    seen: dict[tuple[str, str, str], bool] = {}
    to_cancel: list[str] = []
    for row in rows:
        key = (row[1], row[2], row[3])  # project_id, job_type, idempotency_key
        if key in seen:
            to_cancel.append(row[0])
        else:
            seen[key] = True

    if not to_cancel:
        return f"OK (scanned {total_active} active jobs, no duplicates)"

    if not dry_run:
        placeholders = ",".join("?" for _ in to_cancel)
        cursor.execute(
            "UPDATE generation_jobs SET status='cancelled', updated_at=? "
            f"WHERE id IN ({placeholders})",
            (datetime.now(UTC).isoformat(), *to_cancel),
        )

    return f"DATA CHANGE: cancelled {len(to_cancel)} duplicate job(s) out of {total_active} active"


def _mig_create_unique_active_job_index(cursor: sqlite3.Cursor, dry_run: bool) -> str:
    if _index_exists(cursor, "idx_generation_jobs_active_unique"):
        return "SKIP (index already exists)"
    sql = (
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_generation_jobs_active_unique "
        "ON generation_jobs(project_id, job_type, idempotency_key) "
        "WHERE status IN ('pending', 'running')"
    )
    if not dry_run:
        cursor.execute(sql)
    return "OK (`CREATE UNIQUE INDEX ...` on pending/running jobs)"


def _mig_add_locked_until_col(cursor: sqlite3.Cursor, dry_run: bool) -> str:
    if _column_exists(cursor, "generation_jobs", "locked_until"):
        return "SKIP (column already exists)"
    sql = "ALTER TABLE generation_jobs ADD COLUMN locked_until TEXT"
    if not dry_run:
        cursor.execute(sql)
    return f"OK (`{sql}`)"


def _mig_validate_status_values(cursor: sqlite3.Cursor, dry_run: bool) -> str:
    cursor.execute(
        "SELECT COUNT(*) FROM generation_jobs WHERE status NOT IN ({})".format(
            ",".join("?" for _ in VALID_STATUSES)
        ),
        list(VALID_STATUSES),
    )
    invalid_count = cursor.fetchone()[0]
    if invalid_count == 0:
        return "OK (no invalid status values)"

    if not dry_run:
        now = datetime.now(UTC).isoformat()
        cursor.execute(
            "UPDATE generation_jobs SET status='failed', updated_at=? "
            "WHERE status NOT IN ({})".format(
                ",".join("?" for _ in VALID_STATUSES)
            ),
            [now, *VALID_STATUSES],
        )

    return f"DATA CHANGE: normalized {invalid_count} invalid status value(s) to 'failed'"


# ── Migration Runner ───────────────────────────────────────────────────────


MIGRATION_FNS = {
    "add_idempotency_key_col": _mig_add_idempotency_key_col,
    "add_idempotency_key_index": _mig_add_idempotency_key_index,
    "add_retry_count_col": _mig_add_retry_count_col,
    "create_migration_log": _mig_create_migration_log,
    "clean_duplicate_active_jobs": _mig_clean_duplicate_active_jobs,
    "create_unique_active_job_index": _mig_create_unique_active_job_index,
    "add_locked_until_col": _mig_add_locked_until_col,
    "validate_status_values": _mig_validate_status_values,
}


def run_migration(db_path: Path, apply: bool = False, force: bool = False) -> int:
    """Run all pending migrations. Returns number of items applied/skipped."""
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        return 1

    conn = sqlite3.connect(str(db_path), timeout=30)
    cursor = conn.cursor()

    # Pre-scan: what's pending
    pending: list[dict[str, Any]] = []
    for mig in MIGRATIONS:
        already = _migration_applied(cursor, mig["name"])
        if already and not force:
            continue
        pending.append(mig)

    if not pending:
        print("  All migrations already applied.")
        conn.close()
        return 0

    if not apply:
        print(f"\nMigration plan for {db_path.name}")
        print(f"  Pending migrations: {len(pending)}")
        for mig in pending:
            tag = "DATA CHANGE" if mig["requires_data_cleanup"] else ""
            print(f"    [V{mig['version']}] {mig['name']:42s} {tag}")
        print("\nUse --apply to execute. Use --apply --force to re-apply.")
        conn.close()
        return 0

    # Apply
    print(f"\nApplying {len(pending)} migration(s) to {db_path.name}...")

    # Backup before data-changing migrations
    has_data_changes = any(m["requires_data_cleanup"] for m in pending)
    if has_data_changes:
        _backup_db(db_path)

    for mig in pending:
        fn = MIGRATION_FNS.get(mig["name"])
        if fn is None:
            print(f"  ? {mig['name']}: no handler found")
            continue

        t0 = time.monotonic()
        result = fn(cursor, dry_run=False)
        elapsed = int((time.monotonic() - t0) * 1000)

        # Log migration
        migration_sql = f"migrate_v1_to_v2:{mig['name']}"
        cursor.execute(
            f"""INSERT OR REPLACE INTO {MIGRATION_LOG_TABLE}
                (version, name, description, checksum, applied_at, duration_ms)
                VALUES (?, ?, ?, ?, datetime('now'), ?)""",
            (
                f"V{mig['version']}",
                mig["name"],
                mig["description"],
                _checksum(migration_sql),
                elapsed,
            ),
        )
        conn.commit()

        tag = "DATA" if mig["requires_data_cleanup"] else "    "
        print(f"  [{tag}] {mig['name']:42s} {result} ({elapsed}ms)")

    conn.close()
    return 0


# ── Schema Version Check (for service startup) ──────────────────────────────


# ── Rollback ────────────────────────────────────────────────────────────────


def print_rollback_plan(db_path: Path) -> int:
    """Print rollback instructions for the last batch of migrations."""
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        return 1

    conn = sqlite3.connect(str(db_path), timeout=10)
    cursor = conn.cursor()

    if not _table_exists(cursor, MIGRATION_LOG_TABLE):
        print(f"  No {MIGRATION_LOG_TABLE} found. Nothing to roll back.")
        conn.close()
        return 0

    cursor.execute(
        f"SELECT name, description, applied_at FROM {MIGRATION_LOG_TABLE} ORDER BY id DESC LIMIT 10"
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("  No migrations to roll back.")
        return 0

    print(f"\nRollback plan for {db_path.name}")
    print("  Reverse operations (run in reverse order):")
    for name, desc, applied_at in rows:
        reverse_sql = ""
        if name.endswith("_col"):
            reverse_sql = "    ALTER TABLE ... DROP COLUMN (requires SQLite 3.35+)"
        elif name.endswith("_index"):
            idx_name = name.replace("create_", "idx_")
            reverse_sql = f"    DROP INDEX IF EXISTS {idx_name}"
        elif name == "clean_duplicate_active_jobs":
            reverse_sql = "    (manual restore from backup required)"
        elif name == "create_migration_log":
            reverse_sql = "    DROP TABLE IF EXISTS _migration_log"
        elif name == "validate_status_values":
            reverse_sql = "    (manual restore from backup required)"
        else:
            reverse_sql = "    (no automatic reverse operation)"

        print(f"  -{name:42s} applied={applied_at}")
        print(f"   {reverse_sql}")

    print("\n  To restore from backup:")
    print(f"    python scripts/restore_from_backup.py {db_path}.bak.<timestamp>.db")
    return 0


# ── CLI ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="V1 → V2 database migration for Galgame Translater",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply pending migrations (default: dry-run only)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-apply already-applied migrations (requires --apply)",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Print rollback plan for the last batch of migrations",
    )
    args = parser.parse_args()

    db_path = _resolve_db_path()

    if args.rollback:
        return print_rollback_plan(db_path)

    return run_migration(db_path, apply=args.apply, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
