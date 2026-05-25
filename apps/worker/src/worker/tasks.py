"""Task handlers for the background worker.

Each handler receives a payload dict and returns a result dict.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from project_model.schema import AdaptationProject

from .parser import parse_novel
from .promoter import promote

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "api" / "data"


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

    if not novel_text.strip():
        return {"status": "error", "error": "Empty novel text"}

    # Step 1: LLM parse
    draft = parse_novel(novel_text, target_length)

    # Step 2: Promote to validated AdaptationProject
    project = promote(draft, project_id or None)

    # Step 3: Persist to DB
    _save_project_to_db(project)

    return {
        "status": "ok",
        "project_id": project.project_id,
        "draft": draft,
        "characters_count": len(draft.get("characters", [])),
        "scenes_count": len(draft.get("scenes", [])),
    }


def handle_generate_asset(payload: dict[str, Any]) -> dict[str, Any]:
    """Generate an asset (background, sprite) via ComfyUI/SD.

    Placeholder: returns a mock result. Will be wired in Phase 6.
    """
    return {
        "status": "ok",
        "message": "Asset generation not yet wired.",
        "asset_url": None,
    }


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
