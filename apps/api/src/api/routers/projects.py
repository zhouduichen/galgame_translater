from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from project_model.mock_data import MOCK_PARSE_DRAFT, MOCK_PROJECT
from project_model.schema import AdaptationProject, Emotion, ExportArtifact, ExportFormat, GenerationJob, JobStatus, ParseDraft

from ..database import (
    ExportRow,
    GenerationJobRow,
    SessionLocal,
    delete_project,
    load_draft,
    load_export,
    load_exports,
    load_project,
    save_draft,
    save_export,
    save_job,
    save_project,
)

router = APIRouter()


def _compute_idempotency_key(
    target_type: str,
    project_id: str,
    character_id: str | None = None,
    emotion: str | None = None,
    scene_id: str | None = None,
) -> str:
    """Compute a deterministic idempotency key for an asset (API side).

    Must produce identical output to worker.comfyui._compute_idempotency_key.
    """
    if target_type == "character_sprite":
        raw = f"{project_id}:char:{character_id}:emotion:{emotion}"
    elif target_type == "background":
        raw = f"{project_id}:bg:{scene_id}"
    else:
        raw = f"{project_id}:{target_type}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _get_running_asset_keys(session: SessionLocal, project_id: str) -> set[str]:
    """Get idempotency_keys of all pending/running generation jobs for a project."""
    rows = (
        session.query(GenerationJobRow.idempotency_key)
        .filter(
            GenerationJobRow.project_id == project_id,
            GenerationJobRow.job_type == "generate_asset",
            GenerationJobRow.status.in_(["pending", "running"]),
            GenerationJobRow.idempotency_key.isnot(None),
        )
        .all()
    )
    return {row[0] for row in rows if row[0]}


# ─── Request schemas ─────────────────────────────────────────────────────────


class CreateProjectRequest(BaseModel):
    title: str
    author: str = ""


class ExportRequest(BaseModel):
    format: ExportFormat


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
            retry_count=r.retry_count,
        )
        for r in rows
    ]


@router.post("/{project_id}/jobs/{job_id}/cancel")
def cancel_job(project_id: str, job_id: str) -> dict:
    """Cancel a running or pending job."""
    with SessionLocal() as session:
        row = session.get(GenerationJobRow, job_id)
        if row is None or row.project_id != project_id:
            raise HTTPException(404, "Job not found")
        if row.status in ("completed", "permanently_failed", "cancelled"):
            raise HTTPException(400, f"Job already {row.status}")
        row.status = "cancelled"
        session.commit()
    return {"ok": True}


@router.delete("/{project_id}")
def delete_project_endpoint(project_id: str) -> dict:
    """Delete a project and all its drafts, jobs, and exports."""
    with SessionLocal() as session:
        found = delete_project(session, project_id)
    if not found:
        raise HTTPException(404, "Project not found")
    return {"ok": True}


@router.post("/{project_id}/export")
def trigger_export(project_id: str, body: ExportRequest) -> GenerationJob:
    """Submit an export job (renpy or web). Worker processes it asynchronously."""
    with SessionLocal() as session:
        project = load_project(session, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")

    fmt_value = body.format.value
    job_type = f"export_{fmt_value}"
    job = GenerationJob(
        job_id=f"job_{project_id}_{fmt_value}_{uuid4().hex[:8]}",
        project_id=project_id,
        job_type=job_type,
        payload={"project_id": project_id, "format": fmt_value},
    )
    with SessionLocal() as session:
        save_job(session, job)
    return job


@router.get("/{project_id}/exports")
def list_exports(project_id: str) -> list[ExportArtifact]:
    """List all export artifacts for a project (newest first)."""
    with SessionLocal() as session:
        return load_exports(session, project_id)


@router.get("/{project_id}/export/{export_id}/download")
def download_export(project_id: str, export_id: str):
    """Download a completed export zip file."""
    with SessionLocal() as session:
        export = load_export(session, export_id)
    if export is None:
        raise HTTPException(404, "Export not found")
    if export.project_id != project_id:
        raise HTTPException(404, "Export not found for this project")

    file_path = Path(export.file_path)
    if not file_path.exists():
        raise HTTPException(404, "Export file not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type="application/zip",
        filename=file_path.name,
    )


@router.delete("/{project_id}/export/{export_id}")
def delete_export_endpoint(project_id: str, export_id: str) -> dict:
    """Delete a specific export artifact and its zip file."""
    with SessionLocal() as session:
        export = load_export(session, export_id)
        if export is None or export.project_id != project_id:
            raise HTTPException(404, "Export not found for this project")

        # Remove zip file if exists
        fp = Path(export.file_path)
        if fp.exists():
            fp.unlink()

        session.delete(session.get(ExportRow, export_id))
        session.commit()

    return {"ok": True}


@router.post("/{project_id}/generate-assets")
def generate_assets(project_id: str) -> dict:
    """Trigger asset generation for unresolved characters + scenes.

    Layer 1 interception: pre-checks existing asset_resources and running
    jobs before creating new generation jobs. Already-generated assets and
    assets currently being generated are skipped.

    Returns ``count`` (new jobs created) and ``skipped`` (already existing/running).
    """
    with SessionLocal() as session:
        project = load_project(session, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")

    # Collect existing idempotency keys from already-generated assets
    existing_keys: set[str] = set()
    for res in project.asset_resources.values():
        if res.idempotency_key:
            existing_keys.add(res.idempotency_key)

    # Collect keys of jobs that are currently pending/running
    running_keys: set[str] = set()
    with SessionLocal() as session:
        running_keys = _get_running_asset_keys(session, project_id)

    jobs: list[GenerationJob] = []
    skipped = 0
    now = int(datetime.utcnow().timestamp())

    # ── Backgrounds ──
    for scene_id, scene in project.scenes.items():
        bg_desc = scene.visual_description or scene.description
        if not bg_desc:
            continue

        key = _compute_idempotency_key("background", project_id, scene_id=scene_id)
        if key in existing_keys or key in running_keys:
            skipped += 1
            continue

        job = GenerationJob(
            job_id=f"job_{project_id}_bg_{scene_id}_{now}",
            project_id=project_id,
            job_type="generate_asset",
            payload={
                "target_type": "background",
                "idempotency_key": key,
                "description": bg_desc,
                "scene_id": scene_id,
                "project_id": project_id,
            },
        )
        jobs.append(job)

    # ── Character sprites ──
    for char_id, char in project.characters.items():
        visual_desc = char.appearance or char.description
        is_first_emotion = len(char.asset_ids) == 0

        for emotion in (Emotion.neutral, Emotion.happy, Emotion.sad, Emotion.angry, Emotion.surprised, Emotion.shy):
            key = _compute_idempotency_key(
                "character_sprite", project_id, character_id=char_id, emotion=emotion.value,
            )
            if key in existing_keys or key in running_keys:
                skipped += 1
                continue

            job = GenerationJob(
                job_id=f"job_{project_id}_sprite_{char_id}_{emotion.value}_{now}",
                project_id=project_id,
                job_type="generate_asset",
                payload={
                    "target_type": "character_sprite",
                    "idempotency_key": key,
                    "character_id": char_id,
                    "character_name": char.name,
                    "character_description": visual_desc,
                    "emotion": emotion.value,
                    "project_id": project_id,
                    "is_first_emotion": is_first_emotion,
                },
            )
            jobs.append(job)

    # Save jobs with idempotency_key for running-jobs tracking
    with SessionLocal() as session:
        for job in jobs:
            save_job(session, job, idempotency_key=job.payload.get("idempotency_key", ""))

    return {
        "ok": True,
        "job_ids": [j.job_id for j in jobs],
        "count": len(jobs),
        "skipped": skipped,
    }


@router.post("/{project_id}/retry-failed-assets")
def retry_failed_assets(project_id: str) -> dict:
    """Reset all failed/permanently_failed generate_asset jobs to pending for retry."""
    with SessionLocal() as session:
        rows = (
            session.query(GenerationJobRow)
            .filter(
                GenerationJobRow.project_id == project_id,
                GenerationJobRow.job_type == "generate_asset",
                GenerationJobRow.status.in_(["failed", "permanently_failed"]),
            )
            .all()
        )
        for row in rows:
            row.status = "pending"
            row.retry_count = 0
            row.error = None
        session.commit()
    return {"ok": True, "reset_count": len(rows)}
