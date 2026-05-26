from pathlib import Path

from project_model.mock_data import MOCK_PARSE_DRAFT, MOCK_PROJECT


REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_PUBLIC = REPO_ROOT / "apps" / "web" / "public"


def has_chinese(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def test_mock_project_has_start_scene() -> None:
    assert MOCK_PROJECT.start_scene_id in MOCK_PROJECT.scenes


def test_mock_project_has_readable_chinese_fixture_text() -> None:
    assert MOCK_PROJECT.title == "春日轨道 第一章"
    assert MOCK_PROJECT.characters["heroine"].name == "雨宫白"
    assert "校门" in MOCK_PROJECT.scenes["scene_gate"].description


def test_mock_project_first_scene_can_start() -> None:
    scene = MOCK_PROJECT.scenes[MOCK_PROJECT.start_scene_id]

    first_node_id = scene.first_node_id()

    assert first_node_id == "s1_narr_start"
    assert first_node_id in scene.nodes


def test_mock_parse_draft_matches_project_id() -> None:
    assert MOCK_PARSE_DRAFT.project_id == MOCK_PROJECT.project_id
    assert MOCK_PARSE_DRAFT.scenes[0].scene_id == MOCK_PROJECT.start_scene_id


def test_mock_project_assets_exist_in_web_public() -> None:
    missing = []
    for resource in MOCK_PROJECT.asset_resources.values():
        if resource.url.startswith("/"):
            path = WEB_PUBLIC / resource.url.lstrip("/")
            if not path.is_file():
                missing.append(resource.url)

    assert missing == []


def test_mock_project_story_text_is_chinese() -> None:
    story_text = [
        MOCK_PROJECT.title,
        *[character.name for character in MOCK_PROJECT.characters.values()],
        *[character.description for character in MOCK_PROJECT.characters.values()],
        *[scene.title for scene in MOCK_PROJECT.scenes.values()],
        *[scene.description for scene in MOCK_PROJECT.scenes.values()],
    ]

    for scene in MOCK_PROJECT.scenes.values():
        for node in scene.nodes.values():
            if hasattr(node, "text"):
                story_text.append(node.text)
            if hasattr(node, "epilogue"):
                story_text.append(node.epilogue)
            if hasattr(node, "options"):
                story_text.extend(option.text for option in node.options)

    assert story_text
    assert all(has_chinese(text) for text in story_text if text)
