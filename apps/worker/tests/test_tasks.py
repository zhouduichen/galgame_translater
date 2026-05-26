import json
import sqlite3

from project_model.schema import AdaptationProject
from worker import tasks


def test_handle_parse_draft_saves_draft_and_project(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(tasks, "DATA_DIR", tmp_path)
    db_path = tmp_path / "galgame.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE projects (id TEXT PRIMARY KEY, title TEXT NOT NULL, author TEXT, data TEXT NOT NULL, created_at TEXT, updated_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE parse_drafts (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT)"
    )
    conn.commit()
    conn.close()

    draft = {
        "draft_id": "",
        "project_id": "",
        "novel_title": "测试标题",
        "novel_excerpt": "测试正文",
        "synopsis": "简介",
        "characters": [],
        "locations": [],
        "scenes": [],
        "asset_cues": [],
        "warnings": [],
    }

    def fake_parse_novel(novel_text: str, target_length: str):
        return dict(draft)

    def fake_promote(parsed_draft, project_id):
        return AdaptationProject(
            project_id=project_id,
            title=parsed_draft["novel_title"],
            characters={},
            scenes={},
            start_scene_id="",
        )

    monkeypatch.setattr(tasks, "parse_novel", fake_parse_novel)
    monkeypatch.setattr(tasks, "promote", fake_promote)

    result = tasks.handle_parse_draft(
        {"project_id": "proj_test", "novel_text": "正文", "target_length": "10min_demo"}
    )

    assert result["status"] == "ok"
    conn = sqlite3.connect(str(db_path))
    saved_draft = conn.execute("SELECT id, project_id, data FROM parse_drafts").fetchone()
    saved_project = conn.execute("SELECT id, data FROM projects").fetchone()
    conn.close()

    assert saved_draft[0].startswith("draft_proj_test_")
    assert saved_draft[1] == "proj_test"
    assert json.loads(saved_draft[2])["project_id"] == "proj_test"
    assert saved_project[0] == "proj_test"
