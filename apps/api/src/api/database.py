from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from project_model.schema import (
    AdaptationProject,
    ExportArtifact,
    ExportFormat,
    GenerationJob,
    JobStatus,
    ParseDraft,
)
from project_model.schema_version import MIGRATION_LOG_TABLE, REQUIRED_MIGRATIONS
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
)
from sqlalchemy import (
    text as sa_text,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DEFAULT_DB = _DEFAULT_DATA_DIR / "galgame.db"
DEFAULT_GENERATED_DIR = _DEFAULT_DATA_DIR / "generated"
DATABASE_URL = os.getenv("GALGAME_DATABASE_URL", f"sqlite:///{_DEFAULT_DB.as_posix()}")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class ProjectRow(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    author = Column(String, default="")
    data = Column(Text, nullable=False)  # JSON-serialized AdaptationProject
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ParseDraftRow(Base):
    __tablename__ = "parse_drafts"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False, index=True)
    data = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class GenerationJobRow(Base):
    __tablename__ = "generation_jobs"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False, index=True)
    job_type = Column(String, nullable=False)
    status = Column(String, default=JobStatus.pending.value)
    progress = Column(Float, default=0.0)
    idempotency_key = Column(String, nullable=True, index=True)
    payload = Column(Text, default="{}")
    result = Column(Text, default="{}")
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    locked_until = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExportRow(Base):
    __tablename__ = "exports"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False, index=True)
    format = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(Text, default="{}")


def init_db():
    is_new_database = not inspect(engine).has_table("generation_jobs")
    Base.metadata.create_all(engine)
    _migrate_add_idempotency_key()
    if is_new_database and engine.dialect.name == "sqlite":
        _bootstrap_schema_version()


def _bootstrap_schema_version() -> None:
    """Record the current schema for databases created directly from metadata."""
    conn = engine.connect()
    try:
        conn.execute(sa_text(f"""
            CREATE TABLE IF NOT EXISTS {MIGRATION_LOG_TABLE} (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                version     TEXT    NOT NULL,
                name        TEXT    NOT NULL UNIQUE,
                description TEXT    NOT NULL DEFAULT '',
                checksum    TEXT    NOT NULL,
                applied_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                duration_ms INTEGER
            )
        """))
        for name in REQUIRED_MIGRATIONS:
            conn.execute(
                sa_text(f"""
                    INSERT OR IGNORE INTO {MIGRATION_LOG_TABLE}
                        (version, name, description, checksum, duration_ms)
                    VALUES ('V2', :name, 'Fresh database bootstrap', 'bootstrap', 0)
                """),
                {"name": name},
            )
        conn.commit()
    finally:
        conn.close()


def _migrate_add_idempotency_key():
    """Add idempotency_key column to generation_jobs if not present (SQLite compat)."""
    conn = engine.connect()
    try:
        result = conn.execute(sa_text("PRAGMA table_info(generation_jobs)"))
        columns = [row[1] for row in result]
        if "idempotency_key" not in columns:
            conn.execute(sa_text(
                "ALTER TABLE generation_jobs ADD COLUMN idempotency_key VARCHAR"
            ))
            conn.commit()
    finally:
        conn.close()


# ─── Serialization helpers ───────────────────────────────────────────────────


def save_project(session: Session, project: AdaptationProject) -> None:
    existing = session.get(ProjectRow, project.project_id)
    now = datetime.utcnow()
    row = ProjectRow(
        id=project.project_id,
        title=project.title,
        author=project.author,
        data=project.model_dump_json(),
        created_at=existing.created_at if existing else now,
        updated_at=now,
    )
    session.merge(row)
    session.commit()


def load_project(session: Session, project_id: str) -> AdaptationProject | None:
    row = session.get(ProjectRow, project_id)
    if row is None:
        return None
    return AdaptationProject.model_validate_json(row.data)


def delete_project(session: Session, project_id: str) -> bool:
    """Delete a project and all related data. Returns True if found.

    Also removes export zip files from disk before deleting DB rows.
    """
    row = session.get(ProjectRow, project_id)
    if row is None:
        return False

    # Clean up export zip files on disk
    export_rows = session.query(ExportRow).filter(ExportRow.project_id == project_id).all()
    for erow in export_rows:
        try:
            fp = Path(erow.file_path)
            if fp.exists():
                fp.unlink()
        except Exception:
            pass  # best-effort cleanup

    session.query(ParseDraftRow).filter(ParseDraftRow.project_id == project_id).delete()
    session.query(GenerationJobRow).filter(GenerationJobRow.project_id == project_id).delete()
    session.query(ExportRow).filter(ExportRow.project_id == project_id).delete()
    session.delete(row)
    session.commit()
    return True


def save_draft(session: Session, draft: ParseDraft) -> None:
    row = ParseDraftRow(
        id=draft.draft_id,
        project_id=draft.project_id,
        data=draft.model_dump_json(),
    )
    session.merge(row)
    session.commit()


def load_draft(session: Session, project_id: str) -> ParseDraft | None:
    row = (
        session.query(ParseDraftRow)
        .filter(ParseDraftRow.project_id == project_id)
        .order_by(ParseDraftRow.created_at.desc())
        .first()
    )
    if row is None:
        return None
    return ParseDraft.model_validate_json(row.data)


def save_job(session: Session, job: GenerationJob, idempotency_key: str | None = None) -> None:
    existing = session.get(GenerationJobRow, job.job_id)
    now = datetime.utcnow()
    row = GenerationJobRow(
        id=job.job_id,
        project_id=job.project_id,
        job_type=job.job_type,
        status=job.status.value,
        progress=job.progress,
        idempotency_key=idempotency_key,
        payload=json.dumps(job.payload),
        result=json.dumps(job.result),
        error=job.error,
        retry_count=job.retry_count,
        created_at=existing.created_at if existing else now,
        updated_at=now,
    )
    session.merge(row)
    session.commit()


def load_pending_jobs(session: Session, limit: int = 5) -> list[GenerationJob]:
    rows = (
        session.query(GenerationJobRow)
        .filter(GenerationJobRow.status == JobStatus.pending.value)
        .limit(limit)
        .all()
    )
    return [_row_to_job(r) for r in rows]


def _row_to_export(row: ExportRow) -> ExportArtifact:
    return ExportArtifact(
        export_id=row.id,
        project_id=row.project_id,
        format=ExportFormat(row.format),
        file_path=row.file_path,
        file_size_bytes=row.file_size_bytes,
        created_at=row.created_at.isoformat() + "Z" if row.created_at else "",
        metadata=json.loads(row.metadata_json or "{}"),
    )


def save_export(session: Session, export_artifact: ExportArtifact) -> None:
    existing = session.get(ExportRow, export_artifact.export_id)
    now = datetime.utcnow()
    row = ExportRow(
        id=export_artifact.export_id,
        project_id=export_artifact.project_id,
        format=export_artifact.format.value,
        file_path=export_artifact.file_path,
        file_size_bytes=export_artifact.file_size_bytes,
        created_at=existing.created_at if existing else now,
        metadata_json=json.dumps(export_artifact.metadata),
    )
    session.merge(row)
    session.commit()


def load_exports(session: Session, project_id: str) -> list[ExportArtifact]:
    rows = (
        session.query(ExportRow)
        .filter(ExportRow.project_id == project_id)
        .order_by(ExportRow.created_at.desc())
        .all()
    )
    return [_row_to_export(r) for r in rows]


def load_export(session: Session, export_id: str) -> ExportArtifact | None:
    row = session.get(ExportRow, export_id)
    if row is None:
        return None
    return _row_to_export(row)


def _row_to_job(row: GenerationJobRow) -> GenerationJob:
    return GenerationJob(
        job_id=row.id,
        project_id=row.project_id,
        job_type=row.job_type,  # type: ignore
        status=JobStatus(row.status),
        progress=row.progress,
        payload=json.loads(row.payload or "{}"),
        result=json.loads(row.result or "{}"),
        error=row.error,
        retry_count=row.retry_count,
    )
