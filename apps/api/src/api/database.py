from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from project_model.schema import (
    AdaptationProject,
    ExportArtifact,
    GenerationJob,
    JobStatus,
    ParseDraft,
)

DATABASE_URL = os.getenv("GALGAME_DATABASE_URL", "sqlite:///data/galgame.db")
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
    payload = Column(Text, default="{}")
    result = Column(Text, default="{}")
    error = Column(Text, nullable=True)
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
    Base.metadata.create_all(engine)


# ─── Serialization helpers ───────────────────────────────────────────────────


def save_project(session: Session, project: AdaptationProject) -> None:
    row = ProjectRow(
        id=project.project_id,
        title=project.title,
        author=project.author,
        data=project.model_dump_json(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.merge(row)
    session.commit()


def load_project(session: Session, project_id: str) -> AdaptationProject | None:
    row = session.get(ProjectRow, project_id)
    if row is None:
        return None
    return AdaptationProject.model_validate_json(row.data)


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


def save_job(session: Session, job: GenerationJob) -> None:
    row = GenerationJobRow(
        id=job.job_id,
        project_id=job.project_id,
        job_type=job.job_type,
        status=job.status.value,
        progress=job.progress,
        payload=json.dumps(job.payload),
        result=json.dumps(job.result),
        error=job.error,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
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
    )
