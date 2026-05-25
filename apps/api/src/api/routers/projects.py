from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from project_model.mock_data import MOCK_PARSE_DRAFT, MOCK_PROJECT
from project_model.schema import AdaptationProject, GenerationJob, JobStatus, ParseDraft

from ..database import (
    SessionLocal,
    load_draft,
    load_project,
    save_draft,
    save_job,
    save_project,
)

router = APIRouter()


# ─── Request schemas ─────────────────────────────────────────────────────────


class CreateProjectRequest(BaseModel):
    title: str
    author: str = ""


class ParseRequest(BaseModel):
    novel_text: str
    target_length: str = "10min_demo"


class UpdateDraftRequest(BaseModel):
    draft: dict


# ─── CRUD ────────────────────────────────────────────────────────────────────


@router.get("/")
def list_projects():
    """List all projects."""
    with SessionLocal() as session:
        from ..database import ProjectRow

        rows = session.query(ProjectRow).all()
        projects = [{"id": r.id, "title": r.title} for r in rows]
    # Always include mock
    mock_id = MOCK_PROJECT.project_id
    if not any(p["id"] == mock_id for p in projects):
        projects.insert(0, {"id": mock_id, "title": MOCK_PROJECT.title})
    return {"projects": projects}


@router.post("/")
def create_project(body: CreateProjectRequest) -> dict:
    """Create a new empty project."""
    now = datetime.utcnow().isoformat() + "Z"
    project = AdaptationProject(
        project_id=f"proj_{int(datetime.utcnow().timestamp())}",
        title=body.title,
        author=body.author,
        characters={},
        scenes={},
        start_scene_id="",
        created_at=now,
        updated_at=now,
    )
    with SessionLocal() as session:
        save_project(session, project)
    return {"id": project.project_id, "ok": True}


@router.get("/{project_id}")
def get_project(project_id: str) -> AdaptationProject:
    with SessionLocal() as session:
        project = load_project(session, project_id)
    if project is None:
        if project_id == MOCK_PROJECT.project_id:
            return MOCK_PROJECT
        raise HTTPException(404, "Project not found")
    return project


@router.put("/{project_id}")
def update_project(project_id: str, project: AdaptationProject) -> dict:
    with SessionLocal() as session:
        save_project(session, project)
    return {"ok": True}


# ─── Parsing ─────────────────────────────────────────────────────────────────


@router.post("/{project_id}/parse")
def parse_novel(project_id: str, body: ParseRequest) -> GenerationJob:
    """Submit a novel for LLM parsing. Creates a job; worker processes it async."""
    job = GenerationJob(
        job_id=f"job_{project_id}_parse",
        project_id=project_id,
        job_type="parse_draft",
        payload={
            "project_id": project_id,
            "novel_text": body.novel_text[:100_000],
            "target_length": body.target_length,
        },
    )
    with SessionLocal() as session:
        save_job(session, job)
    return job


@router.get("/{project_id}/draft")
def get_draft(project_id: str) -> ParseDraft:
    """Get the latest parse draft for a project."""
    if project_id == MOCK_PROJECT.project_id:
        return MOCK_PARSE_DRAFT
    with SessionLocal() as session:
        draft = load_draft(session, project_id)
    if draft is None:
        raise HTTPException(404, "No draft found")
    return draft


@router.put("/{project_id}/draft")
def save_draft_endpoint(project_id: str, body: UpdateDraftRequest) -> dict:
    """Save a parse draft."""
    draft = ParseDraft(**body.draft)
    draft.project_id = project_id
    with SessionLocal() as session:
        save_draft(session, draft)
    return {"ok": True}


# ─── Jobs ────────────────────────────────────────────────────────────────────


@router.get("/{project_id}/jobs")
def list_jobs(project_id: str) -> list[GenerationJob]:
    with SessionLocal() as session:
        from ..database import GenerationJobRow

        rows = (
            session.query(GenerationJobRow)
            .filter(GenerationJobRow.project_id == project_id)
            .order_by(GenerationJobRow.created_at.desc())
            .limit(20)
            .all()
        )
    return [
        GenerationJob(
            job_id=r.id,
            project_id=r.project_id,
            job_type=r.job_type,  # type: ignore
            status=JobStatus(r.status),
            progress=r.progress,
            payload=json.loads(r.payload or "{}"),
            result=json.loads(r.result or "{}"),
            error=r.error,
        )
        for r in rows
    ]


@router.get("/{project_id}/export/{fmt}")
def export_project(project_id: str, fmt: str) -> dict:
    """Trigger Ren'Py or web export."""
    return {"ok": True, "export_id": f"export_{project_id}_{fmt}", "format": fmt}
