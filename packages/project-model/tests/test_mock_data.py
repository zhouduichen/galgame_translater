from project_model.mock_data import MOCK_PARSE_DRAFT, MOCK_PROJECT


def test_mock_project_has_start_scene() -> None:
    assert MOCK_PROJECT.start_scene_id in MOCK_PROJECT.scenes


def test_mock_project_has_readable_ascii_fixture_text() -> None:
    assert MOCK_PROJECT.title == "Spring Rail - Chapter One"
    assert MOCK_PROJECT.characters["heroine"].name == "Haku Ame"
    assert "school gate" in MOCK_PROJECT.scenes["scene_gate"].description.lower()


def test_mock_project_first_scene_can_start() -> None:
    scene = MOCK_PROJECT.scenes[MOCK_PROJECT.start_scene_id]

    first_node_id = scene.first_node_id()

    assert first_node_id == "s1_narr_start"
    assert first_node_id in scene.nodes


def test_mock_parse_draft_matches_project_id() -> None:
    assert MOCK_PARSE_DRAFT.project_id == MOCK_PROJECT.project_id
    assert MOCK_PARSE_DRAFT.scenes[0].scene_id == MOCK_PROJECT.start_scene_id
