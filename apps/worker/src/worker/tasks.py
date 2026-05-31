"""Task handlers for the background worker.

Each handler receives a payload dict and returns a result dict.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from project_model.schema import AdaptationProject, AssetResource, AssetType, Emotion

from .parser import parse_novel
from .promoter import promote

DATA_DIR = Path(os.environ.get("GALGAME_DB_DIR", str(Path(__file__).resolve().parent.parent.parent.parent / "api" / "data")))

# ── Project-level concurrency lock ─────────────────────────────────────────
# Guards the read-merge-write cycle per project_id.
# Only effective within a single process; multi-worker deployments need
# the locked_until + BEGIN IMMEDIATE approach instead.
_project_locks: dict[str, Lock] = {}
_project_locks_lock = Lock()
_BASE_WAIT_TIMEOUT = 300.0        # seconds before degrading to full gen
_BASE_WAIT_POLL_INTERVAL = 2.0
_DEGRADED_MAX_RETRIES = 2         # max neutral failures before skipping base


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


def _get_project_lock(project_id: str) -> Lock:
    """Return a per-project reentrant lock for single-process safety."""
    with _project_locks_lock:
        if project_id not in _project_locks:
            _project_locks[project_id] = Lock()
        return _project_locks[project_id]


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
    """Save an AdaptationProject back to the SQLite DB (minimal columns).

    DEPRECATED: use atomic_merge_asset() instead to avoid TOCTOU races.
    Retained for call sites that do read-merge-write in a single-thread context.
    """
    db_path = DATA_DIR / "galgame.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "UPDATE projects SET data = ?, updated_at = ? WHERE id = ?",
        (project.model_dump_json(), datetime.utcnow().isoformat() + "Z", project.project_id),
    )
    conn.commit()
    conn.close()


# ── Atomic asset merge ─────────────────────────────────────────────────────


def atomic_merge_asset(
    project_id: str,
    asset_resource: AssetResource,
    *,
    scene_id: str | None = None,
    character_id: str | None = None,
    emotion: Emotion | None = None,
    base_asset_id: str | None = None,
) -> bool:
    """Merge one AssetResource into the project within a single BEGIN IMMEDIATE transaction.

    Reads the latest project JSON, merges in-memory, then writes back.
    The write-lock serialises concurrent writes per-project.

    Args:
        project_id: The project to update.
        asset_resource: The fully-constructed AssetResource to insert/overwrite.
        scene_id: If set AND asset type is background, bind to scene.background_id.
        character_id + emotion: If set AND asset type is character_sprite, bind
            char.asset_ids[emotion].
        base_asset_id: Optional id of the base asset used for incremental gen.

    Returns:
        True if the project was updated. False if the project does not exist.
    """
    db_path = DATA_DIR / "galgame.db"
    if not db_path.exists():
        return False

    conn = sqlite3.connect(str(db_path), timeout=10)
    try:
        # Test hook: align contenders immediately before lock acquisition.
        # Waiting after BEGIN IMMEDIATE would deadlock because only one
        # connection can hold SQLite's write lock at a time.
        barrier = _CONCURRENCY_BARRIER
        if barrier is not None:
            barrier.wait()

        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute(
            "SELECT data FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if row is None:
            conn.rollback()
            return False

        project = AdaptationProject.model_validate_json(row[0])

        # Merge the asset
        project.asset_resources[asset_resource.id] = asset_resource

        if base_asset_id and asset_resource.base_asset_id is None:
            asset_resource.base_asset_id = base_asset_id

        # Bind background
        if scene_id and asset_resource.asset_type == AssetType.background:
            if scene_id in project.scenes:
                project.scenes[scene_id].background_id = asset_resource.id

        # Bind character sprite
        if (
            character_id
            and emotion
            and asset_resource.asset_type == AssetType.character_sprite
        ):
            if character_id in project.characters:
                project.characters[character_id].asset_ids[emotion] = asset_resource.id

        now = datetime.now(timezone.utc).isoformat()
        project.updated_at = now
        conn.execute(
            "UPDATE projects SET data = ?, updated_at = ? WHERE id = ?",
            (project.model_dump_json(), now, project_id),
        )

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _re_enqueue_job(
    job_id: str,
    project_id: str,
    original_payload: dict[str, Any],
    *,
    degraded_base: bool = False,
    degraded_reason: str = "",
) -> None:
    """Cancel the current job and enqueue a deferred replacement.

    Used when a non-neutral character sprite needs to wait for a base image.
    The new job carries ``degraded_base`` + ``degraded_reason`` in its payload
    so the next handler invocation knows to skip further base-image detection.
    """
    db_path = DATA_DIR / "galgame.db"
    if not db_path.exists():
        return

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("BEGIN IMMEDIATE")

        now = datetime.now(timezone.utc).isoformat()
        # Cancel the current job
        conn.execute(
            "UPDATE generation_jobs SET status='cancelled', updated_at=? WHERE id=?",
            (now, job_id),
        )

        # Create replacement with degraded flag
        new_payload = dict(original_payload)
        if degraded_base:
            new_payload["degraded_base"] = True
            new_payload["degraded_reason"] = degraded_reason

        new_id = f"deferred_{uuid4().hex[:12]}"
        conn.execute(
            """INSERT INTO generation_jobs
               (id, project_id, job_type, status, payload, created_at, updated_at)
               VALUES (?, ?, 'generate_asset', 'pending', ?, ?, ?)""",
            (new_id, project_id, json.dumps(new_payload), now, now),
        )

        conn.commit()
        print(f"[worker] Re-enqueued {job_id} -> {new_id} (degraded={degraded_base})")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _count_pending_jobs(
    project_id: str,
    character_id: str | None = None,
    emotion: str | None = None,
) -> int:
    """Count pending/running generate_asset jobs matching optional filters."""
    db_path = DATA_DIR / "galgame.db"
    if not db_path.exists():
        return 0
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.execute(
            """SELECT COUNT(*) FROM generation_jobs
               WHERE project_id = ?
                 AND job_type = 'generate_asset'
                 AND status IN ('pending', 'running')""",
            (project_id,),
        )
        return cursor.fetchone()[0]
    finally:
        conn.close()


def _count_failed_jobs(
    project_id: str,
    character_id: str | None = None,
    emotion: str | None = None,
) -> int:
    """Count failed/permanently_failed generate_asset jobs matching filters."""
    db_path = DATA_DIR / "galgame.db"
    if not db_path.exists():
        return 0
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.execute(
            """SELECT COUNT(*) FROM generation_jobs
               WHERE project_id = ?
                 AND job_type = 'generate_asset'
                 AND status IN ('failed', 'permanently_failed')""",
            (project_id,),
        )
        return cursor.fetchone()[0]
    finally:
        conn.close()


# ── Concurrency test hook ──────────────────────────────────────────────────

_CONCURRENCY_BARRIER: Any = None


def _base_cache_fallback(
    project: AdaptationProject,
    character_id: str,
    emotion_target: Emotion = Emotion.neutral,
) -> Path | None:
    """Fallback: check the base cache directory if the primary asset is missing.

    Returns the cached base image path if found, None otherwise.
    """
    aid = project.characters.get(character_id, {}).asset_ids.get(emotion_target)  # type: ignore[union-attr]
    if not aid or aid not in project.asset_resources:
        return None
    res = project.asset_resources[aid]
    ikey = res.idempotency_key
    if not ikey:
        return None
    try:
        from .comfyui import _base_cache_path  # type: ignore[import-untyped]
        cached = _base_cache_path(ikey)
        return cached if cached.exists() else None
    except Exception:
        return None
"""Optional threading.Barrier injected by tests. Waits inside atomic_merge_asset
right after BEGIN IMMEDIATE to maximise the race window."""


# ── Asset handler ──────────────────────────────────────────────────────────


def _resolve_base_for_emotion(
    project: AdaptationProject,
    character_id: str,
    emotion: str,
    job_id: str,
    project_id: str,
    degraded_base: bool = False,
) -> tuple[str | None, str | None]:
    """Resolve a base image for incremental character sprite generation.

    Priority:
      1. Primary: char.asset_ids[neutral] → asset_resources → file on disk
      2. Fallback:  idempotency_key → _base_cache_path() (cached pre-Rembg output)
      3. If neutral job is pending, re-enqueue
      4. If neutral failed >= _DEGRADED_MAX_RETRIES, degrade to full gen

    Returns:
        (base_asset_id, base_image_path) for a ready base
        ("RE_ENQUEUE", None) if the caller should re-enqueue and return
        (None, None) if the caller should fall back to full generation
    """
    char = project.characters.get(character_id)
    if not char or emotion == "neutral":
        return None, None

    if degraded_base:
        return None, None

    # 1. Primary: check asset_resources + on-disk file
    aid = char.asset_ids.get(Emotion.neutral)
    if aid and aid in project.asset_resources:
        res = project.asset_resources[aid]
        img_path = _comfyui_asset_url_to_path(res.url)
        if img_path and img_path.exists():
            return aid, str(img_path)

    # 2. Fallback: check base cache directory
    if aid and aid in project.asset_resources:
        cached_path = _base_cache_fallback(project, character_id)
        if cached_path is not None:
            return aid, str(cached_path)

    # 3. Check if neutral job is in flight
    pending_neutral = _count_pending_jobs(project_id, character_id=character_id, emotion="neutral")
    if pending_neutral > 0:
        return "RE_ENQUEUE", None

    # 4. Check neutral failure history
    failed_neutral_count = _count_failed_jobs(project_id, character_id=character_id, emotion="neutral")
    if failed_neutral_count >= _DEGRADED_MAX_RETRIES:
        return None, None

    # 5. Neutral not yet scheduled
    return "RE_ENQUEUE", None


def handle_generate_asset(payload: dict[str, Any]) -> dict[str, Any]:
    """Generate an asset (background, sprite) via ComfyUI/SD.

    Performs pre-generation idempotency check (layer 2 interception):
    if the asset already exists with a matching idempotency_key AND the
    file exists on disk, returns the existing asset URL directly.

    For character sprites: routes to inpaint workflow when a base image
    exists.  If a non-neutral emotion has no ready base, the job is
    re-enqueued (not blocked inline).  On repeated base failures it
    degrades to full generation.

    The final asset is persisted via atomic_merge_asset() inside a
    BEGIN IMMEDIATE transaction to prevent concurrent-write TOCTOU.
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
    degraded_base: bool = payload.get("degraded_base", False)

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

        if target_type == "character_sprite" and character_id:
            base_result = _resolve_base_for_emotion(
                project, character_id, emotion, job_id, project_id,
                degraded_base=degraded_base,
            )
            if base_result[0] == "RE_ENQUEUE":
                _re_enqueue_job(job_id, project_id, payload)
                return {"status": "ok", "re_enqueued": True, "reason": "waiting_for_base"}
            base_asset_id = base_result[0]
            base_image_path = base_result[1]
            if base_asset_id:
                print(f"[worker] Incremental mode: using base {base_asset_id} -> {base_image_path}")

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

        # ── Persist base_asset_id from generate result ──
        from_generation = result.get("base_asset_id")
        if from_generation and base_asset_id is None:
            base_asset_id = from_generation
        cached_base = result.get("cached_base_id")
        if cached_base and base_asset_id is None:
            base_asset_id = cached_base

        # ── Atomic merge ──
        asset_id = f"ast_{uuid4().hex[:8]}"
        resource = AssetResource(
            id=asset_id,
            url=asset_url,
            asset_type=AssetType(target_type),
            generator="comfyui",
            idempotency_key=idempotency_key or None,
            base_asset_id=base_asset_id,
        )

        lock = _get_project_lock(project_id)
        with lock:
            ok = atomic_merge_asset(
                project_id, resource,
                scene_id=scene_id if target_type == "background" else None,
                character_id=character_id if target_type == "character_sprite" else None,
                emotion=Emotion(emotion) if target_type == "character_sprite" and emotion else None,
                base_asset_id=base_asset_id,
            )

        if not ok:
            return {"status": "error", "error": f"Project {project_id} not found during merge"}

        return {
            "status": "ok",
            "asset_url": asset_url,
            "webp_url": result.get("webp_url"),
            "asset_id": asset_id,
            "asset_type": target_type,
            "prompt_id": result.get("prompt_id"),
            "cached": False,
            "base_asset_id": base_asset_id,
            "degraded_base": degraded_base,
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
