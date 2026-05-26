"""Task handlers for the background worker.

Each handler receives a payload dict and returns a result dict.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from project_model.schema import AdaptationProject, AssetResource, AssetType, Emotion

from .parser import parse_novel
from .promoter import promote

DATA_DIR = Path(os.environ.get("GALGAME_DB_DIR", str(Path(__file__).resolve().parent.parent.parent.parent / "api" / "data")))


def _update_job_progress(job_id: str, progress: float) -> None:
    """Update the progress column of a generation_jobs row."""
    db_path = DATA_DIR / "galgame.db"
    if not db_path.exists():
        return
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "UPDATE generation_jobs SET progress = ?, updated_at = ? WHERE id = ?",
        (progress, datetime.utcnow().isoformat() + "Z", job_id),
    )
    conn.commit()
    conn.close()


def _save_draft_to_db(draft: dict[str, Any], project_id: str) -> dict[str, Any]:
    """Persist a parse draft to the shared SQLite DB and return it with IDs filled."""
    db_path = DATA_DIR / "galgame.db"
    saved = dict(draft)
    saved["project_id"] = project_id
    saved["draft_id"] = saved.get("draft_id") or f"draft_{project_id}_{uuid4().hex[:8]}"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """INSERT OR REPLACE INTO parse_drafts (id, project_id, data, created_at)
           VALUES (?, ?, ?, ?)""",
        (
            saved["draft_id"],
            project_id,
            json.dumps(saved, ensure_ascii=False),
            datetime.utcnow().isoformat() + "Z",
        ),
    )
    conn.commit()
    conn.close()
    return saved


def _save_project_to_db(project: AdaptationProject) -> None:
    """Save an AdaptationProject to the shared SQLite DB."""
    db_path = DATA_DIR / "galgame.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """INSERT OR REPLACE INTO projects (id, title, author, data, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            project.project_id,
            project.title,
            project.author,
            project.model_dump_json(),
            project.created_at,
            project.updated_at,
        ),
    )
    conn.commit()
    conn.close()


def handle_parse_draft(payload: dict[str, Any]) -> dict[str, Any]:
    """Parse novel text into a draft structure using LLM (multi-step pipeline)."""
    novel_text = payload.get("novel_text", "")
    target_length = payload.get("target_length", "10min_demo")
    project_id = payload.get("project_id", "")
    job_id = payload.get("job_id", "")

    if not novel_text.strip():
        return {"status": "error", "error": "Empty novel text"}

    def on_step(progress: float) -> None:
        if job_id:
            _update_job_progress(job_id, progress)

    # Step 1: LLM parse
    draft = parse_novel(novel_text, target_length, on_step=on_step)

    # Step 2: Persist draft before promoting
    draft = _save_draft_to_db(draft, project_id)

    # Step 3: Promote to validated AdaptationProject
    project = promote(draft, project_id or None)

    # Step 4: Persist to DB
    _save_project_to_db(project)

    return {
        "status": "ok",
        "project_id": project.project_id,
        "draft": draft,
        "characters_count": len(draft.get("characters", [])),
        "scenes_count": len(draft.get("scenes", [])),
    }


def _load_project_from_db(project_id: str) -> AdaptationProject | None:
    """Read an AdaptationProject from the SQLite DB."""
    db_path = DATA_DIR / "galgame.db"
    if not db_path.exists():
        return None
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT data FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return AdaptationProject.model_validate_json(row[0])


def _save_project_to_db_slim(project: AdaptationProject) -> None:
    """Save an AdaptationProject back to the SQLite DB (minimal columns)."""
    db_path = DATA_DIR / "galgame.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "UPDATE projects SET data = ?, updated_at = ? WHERE id = ?",
        (project.model_dump_json(), datetime.utcnow().isoformat() + "Z", project.project_id),
    )
    conn.commit()
    conn.close()


def handle_generate_asset(payload: dict[str, Any]) -> dict[str, Any]:
    """Generate an asset (background, sprite) via ComfyUI/SD and save to project."""
    from .comfyui import generate_background, generate_character_sprite

    target_type = payload.get("target_type", "")
    project_id = payload.get("project_id", "")
    description = payload.get("description", "")
    scene_id = payload.get("scene_id", "")
    character_id = payload.get("character_id", "")
    character_name = payload.get("character_name", "")
    character_desc = payload.get("character_description", "")
    emotion = payload.get("emotion", "neutral")
    width = payload.get("width", 1280)
    height = payload.get("height", 720)

    try:
        # Generate image
        if target_type == "background":
            asset_url = generate_background(description, width, height)
        elif target_type == "character_sprite":
            asset_url = generate_character_sprite(character_name, character_desc, emotion)
        else:
            return {"status": "error", "error": f"Unsupported asset type: {target_type}"}

        if asset_url is None:
            return {"status": "error", "error": "Image generation timed out"}

        # Save asset to project
        asset_id = f"ast_{uuid4().hex[:8]}"
        resource = AssetResource(
            id=asset_id,
            url=asset_url,
            asset_type=AssetType(target_type),
            generator="comfyui",
        )

        project = _load_project_from_db(project_id)
        if project is not None:
            project.asset_resources[asset_id] = resource

            if target_type == "background" and scene_id and scene_id in project.scenes:
                project.scenes[scene_id].background_id = asset_id

            if target_type == "character_sprite" and character_id and character_id in project.characters:
                project.characters[character_id].asset_ids[Emotion(emotion)] = asset_id

            _save_project_to_db_slim(project)

        return {
            "status": "ok",
            "asset_url": asset_url,
            "asset_id": asset_id,
            "asset_type": target_type,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_export_renpy(payload: dict[str, Any]) -> dict[str, Any]:
    """Export a project to Ren'Py format.

    Placeholder: returns a mock result. Will be wired in Phase 5.
    """
    return {
        "status": "ok",
        "message": "Ren'Py export not yet wired.",
        "export_path": None,
    }


TASK_HANDLERS = {
    "parse_draft": handle_parse_draft,
    "generate_asset": handle_generate_asset,
    "export_renpy": handle_export_renpy,
}
