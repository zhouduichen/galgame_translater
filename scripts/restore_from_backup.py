#!/usr/bin/env python3
"""
Restore a Galgame Translater SQLite database from a backup created by
migrate_v1_to_v2.py (or any SQLite backup file).

Usage:
    python scripts/restore_from_backup.py <backup_path> [--dest PATH]

Requirements:
    - API and Worker must be stopped before restoration.
    - The script checks that the source backup is not locked.

The restore uses SQLite's backup() API to create a consistent snapshot.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


def _check_not_locked(path: Path) -> None:
    """Verify the database is not currently locked by another process."""
    try:
        conn = sqlite3.connect(str(path), timeout=1)
        conn.execute("SELECT 1")
        conn.close()
    except sqlite3.OperationalError as e:
        print(f"ERROR: Database {path} is locked or unreachable: {e}")
        print("Make sure API and Worker are stopped before restoring.")
        sys.exit(1)


def restore(backup_path: Path, dest_path: Path | None = None) -> None:
    """Restore a backed-up SQLite database to the target location.

    Args:
        backup_path: Path to the .bak.<timestamp>.db backup file.
        dest_path: Target path. Defaults to removing the .bak suffix.
    """
    if not backup_path.exists():
        print(f"ERROR: Backup not found: {backup_path}")
        sys.exit(1)

    if dest_path is None:
        # Remove .bak.<timestamp> suffix to get original name
        stem = backup_path.stem  # e.g. galgame.db.bak.20260531
        parts = stem.split(".bak.")
        if len(parts) >= 2 and parts[0].endswith(".db"):
            parts[0] = parts[0][:-3]  # remove .db
        dest_path = backup_path.parent / f"{parts[0]}.db"

    if dest_path.exists():
        _check_not_locked(dest_path)

    print(f"  Source: {backup_path}")
    print(f"  Dest:   {dest_path}")

    src_conn = sqlite3.connect(str(backup_path))
    dst_conn = sqlite3.connect(str(dest_path))

    try:
        src_conn.backup(dst_conn, pages=1024)
        print("  Restore complete.")

        # Verify integrity
        verify_conn = sqlite3.connect(str(dest_path))
        cursor = verify_conn.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        if result and result[0] == "ok":
            print("  Integrity check: PASS")
        else:
            print(f"  WARNING: Integrity check: {result}")
        verify_conn.close()
    except Exception as e:
        print(f"ERROR: Restore failed: {e}")
        sys.exit(1)
    finally:
        dst_conn.close()
        src_conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Restore a Galgame Translater SQLite database from backup.",
    )
    parser.add_argument("backup", type=Path, help="Path to the .bak.<timestamp>.db file")
    parser.add_argument(
        "--dest", type=Path, default=None,
        help="Target database path (default: derived from backup filename)",
    )
    args = parser.parse_args()

    restore(args.backup, args.dest)


if __name__ == "__main__":
    main()
