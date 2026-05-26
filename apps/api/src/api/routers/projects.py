from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from project_model.mock_data import MOCK_PARSE_DRAFT, MOCK_PROJECT
from project_model.schema import AdaptationProject, Emotion, GenerationJob, JobStatus, ParseDraft

from ..database import (
    SessionLocal,
    delete_project,
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
    return _list_projects()


@router.get("")
def list_projects_no_slash() -> dict:
    """List all projects (without trailing slash)."""
    return _list_projects()


def _list_projects() -> dict:
    """Shared implementation for listing projects."""
    with SessionLocal() as session:
        from ..database import ProjectRow

        rows = session.query(ProjectRow).all()
        projects = [{"id": r.id, "title": r.title} for r in rows]
    # Always expose the bundled demo from source so stale local DB rows do not hide updates.
    mock_id = MOCK_PROJECT.project_id
    existing_mock = next((p for p in projects if p["id"] == mock_id), None)
    if existing_mock:
        existing_mock["title"] = MOCK_PROJECT.title
    else:
        projects.insert(0, {"id": mock_id, "title": MOCK_PROJECT.title})
    return {"projects": projects}


@router.post("/")
def create_project(body: CreateProjectRequest) -> dict:
    """Create a new empty project."""
    now = datetime.utcnow().isoformat() + "Z"
    project = AdaptationProject(
        project_id=f"proj_{uuid4().hex}",
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


@router.post("")
def create_project_no_slash(body: CreateProjectRequest) -> dict:
    """Create a new empty project (without trailing slash)."""
    return create_project(body)


@router.get("/{project_id}")
def get_project(project_id: str) -> AdaptationProject:
    if project_id == MOCK_PROJECT.project_id:
        return MOCK_PROJECT
    with SessionLocal() as session:
        project = load_project(session, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    return project


@router.put("/{project_id}")
def update_project(project_id: str, project: AdaptationProject) -> dict:
    if project.project_id != project_id:
        raise HTTPException(400, "Path project_id does not match request body project_id")
    with SessionLocal() as session:
        save_project(session, project)
    return {"ok": True}


# ─── Parsing ─────────────────────────────────────────────────────────────────


@router.post("/{project_id}/parse")
def parse_novel(project_id: str, body: ParseRequest) -> GenerationJob:
    """Submit a novel for LLM parsing. Creates a job; worker processes it async."""
    job = GenerationJob(
        job_id=f"job_{project_id}_parse_{uuid4().hex}",
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
            .limit(200)
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


@router.delete("/{project_id}")
def delete_project_endpoint(project_id: str) -> dict:
    """Delete a project and all its drafts, jobs, and exports."""
    with SessionLocal() as session:
        found = delete_project(session, project_id)
    if not found:
        raise HTTPException(404, "Project not found")
    return {"ok": True}


@router.get("/{project_id}/export/{fmt}")
def export_project(project_id: str, fmt: str) -> dict:
    """Trigger Ren'Py or web export."""
    return {"ok": True, "export_id": f"export_{project_id}_{fmt}", "format": fmt}


@router.post("/{project_id}/generate-assets")
def generate_assets(project_id: str) -> dict:
    """Trigger asset generation for all characters + scenes. Creates individual jobs."""
    with SessionLocal() as session:
        project = load_project(session, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")

    jobs = []
    now = int(datetime.utcnow().timestamp())

    # Generate backgrounds for each scene
    for scene_id, scene in project.scenes.items():
        bg_desc = scene.visual_description or scene.description
        if bg_desc:
            job = GenerationJob(
                job_id=f"job_{project_id}_bg_{scene_id}_{now}",
                project_id=project_id,
                job_type="generate_asset",
                payload={
                    "target_type": "background",
                    "description": bg_desc,
                    "scene_id": scene_id,
                    "project_id": project_id,
                },
            )
            jobs.append(job)

    # Generate sprites for common emotions per character
    for char_id, char in project.characters.items():
        # Build rich visual description from appearance + personality
        visual_desc = char.appearance or char.description
        for emotion in (Emotion.neutral, Emotion.happy, Emotion.sad, Emotion.angry, Emotion.surprised, Emotion.shy):
            job = GenerationJob(
                job_id=f"job_{project_id}_sprite_{char_id}_{emotion.value}_{now}",
                project_id=project_id,
                job_type="generate_asset",
                payload={
                    "target_type": "character_sprite",
                    "character_id": char_id,
                    "character_name": char.name,
                    "character_description": visual_desc,
                    "emotion": emotion.value,
                    "project_id": project_id,
                },
            )
            jobs.append(job)

    with SessionLocal() as session:
        for job in jobs:
            save_job(session, job)

    return {"ok": True, "job_ids": [j.job_id for j in jobs], "count": len(jobs)}
