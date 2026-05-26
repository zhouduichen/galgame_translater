from project_model.schema import (
    AdaptationProject,
    AssetResource,
    AssetType,
    Character,
    CharacterCue,
    ChoiceNode,
    ChoiceOption,
    DialogueNode,
    Emotion,
    NarrationNode,
    Scene,
)


def test_character_default_lists_are_independent() -> None:
    first = CharacterCue(character_id="a", name="A", description="First")
    second = CharacterCue(character_id="b", name="B", description="Second")

    first.traits.append("quiet")

    assert first.traits == ["quiet"]
    assert second.traits == []


def test_character_asset_maps_are_independent() -> None:
    first = Character(character_id="a", name="A", description="First")
    second = Character(character_id="b", name="B", description="Second")

    first.asset_ids[Emotion.neutral] = "sprite_a_neutral"

    assert first.asset_ids == {Emotion.neutral: "sprite_a_neutral"}
    assert second.asset_ids == {}


def test_scene_first_node_id_uses_incoming_edges() -> None:
    scene = Scene(
        scene_id="scene_opening",
        title="Opening",
        nodes={
            "n2": DialogueNode(
                node_id="n2",
                character_id="heroine",
                text="Good morning.",
            ),
            "n1": NarrationNode(
                node_id="n1",
                text="The first bell rang.",
                next_node_id="n2",
            ),
        },
    )

    assert scene.first_node_id() == "n1"


def test_choice_node_requires_at_least_one_option() -> None:
    node = ChoiceNode(
        node_id="choice_1",
        text="What will you do?",
        options=[
            ChoiceOption(
                option_id="opt_1",
                text="Answer",
                next_node_id="n2",
            )
        ],
    )

    assert node.options[0].text == "Answer"


def test_asset_references_are_resolvable() -> None:
    """All non-null background_id and asset_ids must exist in asset_resources."""
    project = AdaptationProject(
        project_id="proj_test",
        title="Test",
        characters={
            "chara": Character(
                character_id="chara",
                name="Chara",
                description="",
                asset_ids={Emotion.neutral: "ast_sprite_neutral"},
            ),
        },
        scenes={
            "scene_1": Scene(
                scene_id="scene_1",
                title="Scene",
                background_id="ast_bg_01",
                nodes={
                    "n1": NarrationNode(node_id="n1", text="Test"),
                },
            ),
        },
        start_scene_id="scene_1",
        asset_resources={
            "ast_bg_01": AssetResource(id="ast_bg_01", url="/api/assets/bg.png", asset_type=AssetType.background),
            "ast_sprite_neutral": AssetResource(id="ast_sprite_neutral", url="/api/assets/sprite.png", asset_type=AssetType.character_sprite),
        },
    )

    for sid, scene in project.scenes.items():
        if scene.background_id:
            assert scene.background_id in project.asset_resources, (
                f"Scene {sid} background_id '{scene.background_id}' not in asset_resources"
            )

    for cid, char in project.characters.items():
        for emotion, asset_id in char.asset_ids.items():
            assert asset_id in project.asset_resources, (
                f"Character {cid} asset_ids[{emotion}] = '{asset_id}' not in asset_resources"
            )


def test_project_requires_start_scene_id_after_schema_update() -> None:
    project = AdaptationProject(
        project_id="proj_test",
        title="Test",
        characters={},
        scenes={
            "scene_opening": Scene(
                scene_id="scene_opening",
                title="Opening",
                nodes={
                    "n1": NarrationNode(node_id="n1", text="Start"),
                },
            )
        },
        start_scene_id="scene_opening",
    )

    assert project.start_scene_id == "scene_opening"
