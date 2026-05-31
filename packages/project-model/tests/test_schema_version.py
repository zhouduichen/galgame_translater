from __future__ import annotations

import sqlite3

import pytest

from project_model.schema_version import (
    MIGRATION_LOG_TABLE,
    REQUIRED_MIGRATIONS,
    check_schema_version,
)


def test_check_schema_version_returns_no_db_for_missing_database(tmp_path) -> None:
    assert check_schema_version(tmp_path / "missing.db") == "NO_DB"


def test_check_schema_version_rejects_database_without_migration_log(tmp_path) -> None:
    db_path = tmp_path / "v1.db"
    sqlite3.connect(db_path).close()

    with pytest.raises(SystemExit) as exc_info:
        check_schema_version(db_path)

    assert exc_info.value.code == 1


def test_check_schema_version_accepts_database_with_required_migrations(tmp_path) -> None:
    db_path = tmp_path / "v2.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        f"""CREATE TABLE {MIGRATION_LOG_TABLE} (
            name TEXT PRIMARY KEY
        )"""
    )
    conn.executemany(
        f"INSERT INTO {MIGRATION_LOG_TABLE} (name) VALUES (?)",
        [(name,) for name in REQUIRED_MIGRATIONS],
    )
    conn.commit()
    conn.close()

    assert check_schema_version(db_path) == "V2"
