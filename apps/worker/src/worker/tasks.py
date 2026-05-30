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


def _comfyui_asset_url_to_path(asset_url: str) -> Path | None:
    """Resolve an /api/assets/ URL to a local Path on the worker's filesystem."""
    if not asset_url:
        return None
    filename = asset_url.replace("/api/assets/", "").lstrip("/")
    if not filename:
        return None
    generated_dir = Path(
        os.environ.get(
            "GENERATED_DIR",
            str(Path(__file__).resolve().parent.parent.parent.parent / "api" / "data" / "generated"),
        )
    )
    path = generated_dir / filename
    return path if path.exists() else None


def _is_job_cancelled(job_id: str) -> bool:
    """Check if a job has been cancelled via the API."""
    db_path = DATA_DIR / "galgame.db"
    if not db_path.exists():
        return False
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("SELECT status FROM generation_jobs WHERE id = ?", (job_id,)).fetchone()
        return row is not None and row[0] == "cancelled"
    finally:
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

    should_stop = (lambda: _is_job_cancelled(job_id)) if job_id else None

    # Step 1: LLM parse
    draft = parse_novel(novel_text, target_length, on_step=on_step, should_stop=should_stop)

    if draft.get("status") == "cancelled":
        return draft

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
    """Generate an asset (background, sprite) via ComfyUI/SD.

    Performs pre-generation idempotency check (layer 2 interception):
    if the asset already exists in the project's asset_resources with a
    matching idempotency_key AND the file exists on disk, returns the
    existing asset URL directly — skipping ComfyUI entirely.

    For character sprites, detects if this is an incremental generation
    (non-first emotion) and routes to the inpaint workflow.
    """
    from .comfyui import (
        check_asset_exists,
        generate_background,
        generate_character_sprite,
    )

    target_type = payload.get("target_type", "")
    idempotency_key = payload.get("idempotency_key", "")
    project_id = payload.get("project_id", "")
    description = payload.get("description", "")
    scene_id = payload.get("scene_id", "")
    character_id = payload.get("character_id", "")
    character_name = payload.get("character_name", "")
    character_desc = payload.get("character_description", "")
    emotion = payload.get("emotion", "neutral")
    width = payload.get("width", 1344)
    height = payload.get("height", 768)
    lora_name = payload.get("lora_name", "")
    lora_weight = float(payload.get("lora_weight", 0.8))
    job_id = payload.get("job_id", "")

    try:
        project = _load_project_from_db(project_id)
        if project is None:
            return {"status": "error", "error": f"Project {project_id} not found"}

        # ── Layer 2 interception: pre-generation idempotency check ──
        if idempotency_key:
            existing = check_asset_exists(project.asset_resources, idempotency_key)
            if existing is not None:
                print(f"[worker] Idempotency HIT: {idempotency_key} -> {existing.url}")
                return {
                    "status": "ok",
                    "asset_url": existing.url,
                    "asset_id": existing.id,
                    "cached": True,
                }

        # ── Detect incremental mode for character sprites ──
        base_asset_id: str | None = None
        base_image_path: str | None = None

        if target_type == "character_sprite" and character_id in project.characters:
            char = project.characters[character_id]
            for existing_emotion, aid in char.asset_ids.items():
                if aid in project.asset_resources:
                    base_res = project.asset_resources[aid]
                    base_local = _comfyui_asset_url_to_path(base_res.url)
                    if base_local is not None and base_local.exists():
                        base_asset_id = aid
                        base_image_path = str(base_local)
                        print(f"[worker] Incremental mode: using base {aid} -> {base_image_path}")
                        break

        # ── Generate image ──
        if target_type == "background":
            result = generate_background(
                description, width, height,
                lora_name=lora_name, lora_weight=lora_weight,
                job_id=job_id,
            )
        elif target_type == "character_sprite":
            result = generate_character_sprite(
                character_name, character_desc, emotion,
                lora_name=lora_name, lora_weight=lora_weight,
                job_id=job_id,
                base_asset_id=base_asset_id,
                base_image_path=base_image_path,
                idempotency_key=idempotency_key,
            )
        else:
            return {"status": "error", "error": f"Unsupported asset type: {target_type}"}

        if result.get("status") != "ok":
            return result

        asset_url = result.get("asset_url", "")
        if not asset_url:
            return {"status": "error", "error": "Asset generation returned no URL"}

        # ── Save asset to project with idempotency_key ──
        asset_id = f"ast_{uuid4().hex[:8]}"
        resource = AssetResource(
            id=asset_id,
            url=asset_url,
            asset_type=AssetType(target_type),
            generator="comfyui",
            idempotency_key=idempotency_key or None,
            base_asset_id=base_asset_id,
        )

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
            "webp_url": result.get("webp_url"),
            "asset_id": asset_id,
            "asset_type": target_type,
            "prompt_id": result.get("prompt_id"),
            "cached": False,
            "base_asset_id": base_asset_id,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_export_renpy(payload: dict[str, Any]) -> dict[str, Any]:
    """Export a project to a complete, runnable Ren'Py zip package."""
    from .comfyui import create_renpy_zip

    project_id = payload.get("project_id", "")
    project = _load_project_from_db(project_id)
    if project is None:
        return {"status": "error", "error": f"Project {project_id} not found"}

    # Build character emotion map
    characters = {}
    for cid, char in project.characters.items():
        emotions = {}
        for emotion, asset_id in char.asset_ids.items():
            if asset_id in project.asset_resources:
                emotions[str(emotion)] = project.asset_resources[asset_id].url
        characters[cid] = {
            "name": char.name,
            "emotions": emotions,
        }

    # Build background map
    backgrounds = {}
    for sid, scene in project.scenes.items():
        asset_url = ""
        if scene.background_id and scene.background_id in project.asset_resources:
            asset_url = project.asset_resources[scene.background_id].url
        backgrounds[sid] = {
            "name": scene.title or sid,
            "asset_url": asset_url,
            "description": scene.description or "",
        }

    export_id = f"export_{project_id}_renpy_{uuid4().hex[:8]}"
    zip_path = create_renpy_zip(export_id, project.title, characters, backgrounds)
    file_size = zip_path.stat().st_size if zip_path.exists() else 0

    # Record in exports table
    db_path = DATA_DIR / "galgame.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """INSERT OR REPLACE INTO exports (id, project_id, format, file_path, file_size_bytes, created_at, metadata_json)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            export_id, project_id, "renpy", str(zip_path), file_size,
            datetime.utcnow().isoformat() + "Z",
            json.dumps({"characters_count": len(characters), "backgrounds_count": len(backgrounds)}),
        ),
    )
    conn.commit()
    conn.close()

    return {
        "status": "ok",
        "export_id": export_id,
        "format": "renpy",
        "file_path": str(zip_path),
        "file_size_bytes": file_size,
        "characters_count": len(characters),
        "backgrounds_count": len(backgrounds),
    }


def handle_export_web(payload: dict[str, Any]) -> dict[str, Any]:
    """Export a project to a standalone Web player zip package."""
    from .comfyui import create_web_zip

    project_id = payload.get("project_id", "")
    project = _load_project_from_db(project_id)
    if project is None:
        return {"status": "error", "error": f"Project {project_id} not found"}

    # Build character emotion map
    characters = {}
    for cid, char in project.characters.items():
        emotions = {}
        for emotion, asset_id in char.asset_ids.items():
            if asset_id in project.asset_resources:
                emotions[str(emotion)] = project.asset_resources[asset_id].url
        characters[cid] = {
            "name": char.name,
            "emotions": emotions,
        }

    # Build background map
    backgrounds = {}
    for sid, scene in project.scenes.items():
        asset_url = ""
        if scene.background_id and scene.background_id in project.asset_resources:
            asset_url = project.asset_resources[scene.background_id].url
        backgrounds[sid] = {
            "name": scene.title or sid,
            "asset_url": asset_url,
            "description": scene.description or "",
        }

    export_id = f"export_{project_id}_web_{uuid4().hex[:8]}"
    zip_path = create_web_zip(export_id, project.title, characters, backgrounds)
    file_size = zip_path.stat().st_size if zip_path.exists() else 0

    # Record in exports table
    db_path = DATA_DIR / "galgame.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """INSERT OR REPLACE INTO exports (id, project_id, format, file_path, file_size_bytes, created_at, metadata_json)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            export_id, project_id, "web", str(zip_path), file_size,
            datetime.utcnow().isoformat() + "Z",
            json.dumps({"scenes_count": len(backgrounds), "characters_count": len(characters)}),
        ),
    )
    conn.commit()
    conn.close()

    return {
        "status": "ok",
        "export_id": export_id,
        "format": "web",
        "file_path": str(zip_path),
        "file_size_bytes": file_size,
        "scenes_count": len(backgrounds),
        "characters_count": len(characters),
    }


TASK_HANDLERS = {
    "parse_draft": handle_parse_draft,
    "generate_asset": handle_generate_asset,
    "export_renpy": handle_export_renpy,
    "export_web": handle_export_web,
}
