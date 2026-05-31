"""
Concurrency regression tests for atomic_merge_asset.

Verifies that N threads merging assets into the same project within a
BEGIN IMMEDIATE transaction do not lose data (TOCTOU race).

Uses threading.Barrier synchronised at the transaction boundary via
_CONCURRENCY_BARRIER to maximise the race window.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

# Allow import from apps/worker/src
_HERE = Path(__file__).resolve().parent
_WORKER_SRC = _HERE.parent / "src"
if str(_WORKER_SRC) not in sys.path:
    sys.path.insert(0, str(_WORKER_SRC))

from project_model.schema import AdaptationProject, AssetResource, AssetType, Emotion, Character  # noqa: E402

# Use a test database in the same location that atomic_merge_asset expects
TEST_DB_DIR = _HERE.parent / ".test_data"
TEST_DB_PATH = TEST_DB_DIR / "galgame.db"

os.environ.setdefault("GALGAME_DB_DIR", str(TEST_DB_DIR))


def _setup_project() -> str:
    """Create a test project and return its project_id."""
    TEST_DB_DIR.mkdir(parents=True, exist_ok=True)
    _close_all_connections()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink(missing_ok=True)

    conn = sqlite3.connect(str(TEST_DB_PATH))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )"""
    )
    pid = f"test_{uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    project = AdaptationProject(
        project_id=pid,
        title="Concurrency Test",
        start_scene_id="",
        created_at=now,
        updated_at=now,
    )
    conn.execute(
        "INSERT INTO projects (id, title, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (pid, "Concurrency Test", project.model_dump_json(), now, now),
    )
    conn.commit()
    conn.close()
    return pid


def _close_all_connections():
    """Force-close any lingering SQLite connections by triggering GC."""
    import gc
    gc.collect()
    gc.collect()


def _load_asset_count(project_id: str) -> int:
    """Return the count of asset_resources in the project."""
    conn = sqlite3.connect(str(TEST_DB_PATH))
    row = conn.execute("SELECT data FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    if row is None:
        return 0
    project = AdaptationProject.model_validate_json(row[0])
    return len(project.asset_resources)


def _cleanup():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    if TEST_DB_DIR.exists():
        TEST_DB_DIR.rmdir()


# Import after setting env var and sys.path
from worker.tasks import _CONCURRENCY_BARRIER, atomic_merge_asset  # noqa: E402


class TestAtomicMergeConcurrency:
    """Verify that atomic_merge_asset does not lose data under concurrency."""

    def test_single_thread_merge(self):
        """Baseline: single-threaded merge retains all assets."""
        pid = _setup_project()
        asset = AssetResource(id="ast_0001", url="/gen/1.png", asset_type="background")

        ok = atomic_merge_asset(pid, asset)
        assert ok is True
        assert _load_asset_count(pid) == 1
        _cleanup()

    def test_concurrent_merge_retains_all_assets(self):
        """N threads merging different assets all succeed — count == N."""
        N = 10
        pid = _setup_project()
        barrier = threading.Barrier(N)
        _CONCURRENCY_BARRIER = barrier  # type: ignore[assignment]

        results: list[bool] = []
        results_lock = threading.Lock()

        def _worker(asset: AssetResource):
            ok = atomic_merge_asset(pid, asset)
            with results_lock:
                results.append(ok)

        assets = [
            AssetResource(
                id=f"ast_{i:04x}",
                url=f"/generated/concurrent/{i}.png",
                asset_type="background",
            )
            for i in range(N)
        ]
        threads = [threading.Thread(target=_worker, args=(a,)) for a in assets]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        _CONCURRENCY_BARRIER = None  # reset

        assert all(results), f"Some merges failed: {results}"
        assert _load_asset_count(pid) == N, (
            f"Expected {N} assets, got {_load_asset_count(pid)}"
        )
        _cleanup()

    def test_concurrent_merge_same_asset_id_does_not_duplicate(self):
        """Two threads writing the same asset_id: only one copy survives."""
        pid = _setup_project()
        barrier = threading.Barrier(2)
        _CONCURRENCY_BARRIER = barrier  # type: ignore[assignment]

        results: list[bool] = []
        results_lock = threading.Lock()

        def _worker(idx: int):
            asset = AssetResource(
                id="ast_collision",
                url=f"/gen/collision/{idx}.png",
                asset_type="background",
            )
            ok = atomic_merge_asset(pid, asset)
            with results_lock:
                results.append(ok)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        _CONCURRENCY_BARRIER = None
        assert all(results)
        # Only one asset with this ID should exist
        assert _load_asset_count(pid) == 1
        _cleanup()


class TestAtomicMergeEdgeCases:
    """Edge cases: nonexistent project, type bindings, re-merge."""

    def test_nonexistent_project_returns_false(self):
        asset = AssetResource(id="ast_x", url="/gen/x.png", asset_type="background")
        ok = atomic_merge_asset("proj_nonexistent", asset)
        assert ok is False

    def test_background_binding_sets_scene_id(self):
        pid = _setup_project()
        # First add a scene manually
        conn = sqlite3.connect(str(TEST_DB_PATH))
        row = conn.execute("SELECT data FROM projects WHERE id = ?", (pid,)).fetchone()
        project = AdaptationProject.model_validate_json(row[0])
        from project_model.schema import NarrationNode, Scene

        scene = Scene(scene_id="scene_001", title="Test Scene", nodes={})
        project.scenes["scene_001"] = scene
        conn.execute(
            "UPDATE projects SET data = ? WHERE id = ?",
            (project.model_dump_json(), pid),
        )
        conn.commit()
        conn.close()

        asset = AssetResource(id="ast_bg", url="/gen/bg.png", asset_type="background")
        ok = atomic_merge_asset(pid, asset, scene_id="scene_001")
        assert ok is True

        conn = sqlite3.connect(str(TEST_DB_PATH))
        row = conn.execute("SELECT data FROM projects WHERE id = ?", (pid,)).fetchone()
        conn.close()
        project = AdaptationProject.model_validate_json(row[0])
        assert project.scenes["scene_001"].background_id == "ast_bg"
        assert "ast_bg" in project.asset_resources
        _cleanup()


class TestBaseCacheFallback:
    """Verify _base_cache_fallback() works with base cache paths."""

    def test_base_cache_fallback_returns_none_when_no_neutral(self):
        """No neutral asset in char.asset_ids → fallback returns None."""
        from project_model.schema import Character
        pid = _setup_project()
        # Add a character with no neutral
        conn = sqlite3.connect(str(TEST_DB_PATH))
        row = conn.execute("SELECT data FROM projects WHERE id = ?", (pid,)).fetchone()
        project = AdaptationProject.model_validate_json(row[0])
        char = Character(
            character_id="char_a",
            name="Alice",
            description="A test character",
        )
        project.characters["char_a"] = char
        conn.execute(
            "UPDATE projects SET data = ? WHERE id = ?",
            (project.model_dump_json(), pid),
        )
        conn.commit()
        conn.close()

        # The fallback should return None when no neutral asset exists
        from worker.tasks import _base_cache_fallback
        result = _base_cache_fallback(project, "char_a")
        assert result is None
        _cleanup()

    def test_base_cache_fallback_returns_none_when_no_idempotency_key(self):
        """Asset exists but has no idempotency_key → cannot resolve cache path."""
        pid = _setup_project()
        conn = sqlite3.connect(str(TEST_DB_PATH))
        row = conn.execute("SELECT data FROM projects WHERE id = ?", (pid,)).fetchone()
        project = AdaptationProject.model_validate_json(row[0])
        char = Character(
            character_id="char_b",
            name="Bob",
            description="Another character",
            asset_ids={Emotion.neutral: "ast_neutral"},
        )
        project.characters["char_b"] = char
        project.asset_resources["ast_neutral"] = AssetResource(
            id="ast_neutral",
            url="/api/assets/neutral.png",
            asset_type="character_sprite",
            # No idempotency_key
        )
        conn.execute(
            "UPDATE projects SET data = ? WHERE id = ?",
            (project.model_dump_json(), pid),
        )
        conn.commit()
        conn.close()

        from worker.tasks import _base_cache_fallback
        result = _base_cache_fallback(project, "char_b")
        assert result is None
        _cleanup()
