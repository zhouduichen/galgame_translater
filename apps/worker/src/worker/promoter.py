"""Promote a ParseDraft to a validated AdaptationProject.

Validates and transforms the LLM-generated draft into a canonical project
that's playable in the Web player and editable in the editor.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from project_model.schema import (
    AdaptationProject,
    AssetCue,
    AssetResource,
    AssetType,
    BranchNode,
    Character,
    CharacterCue,
    ChoiceNode,
    ChoiceOption,
    DialogueNode,
    Emotion,
    EndingNode,
    NarrationNode,
    Node,
    Scene,
    SceneTransitionNode,
    Side,
)

logger = logging.getLogger(__name__)

VALID_EMOTIONS = {e.value for e in Emotion}
VALID_SIDES = {s.value for s in Side}
VALID_NODE_TYPES = {
    "dialogue", "narration", "choice",
    "scene_transition", "branch", "ending",
}


def promote(draft: dict[str, Any], project_id: str | None = None) -> AdaptationProject:
    """Convert a ParseDraft dict into a validated AdaptationProject.

    Args:
        draft: The raw ParseDraft output from the LLM pipeline.
        project_id: Optional project ID. Auto-generated if not provided.

    Returns:
        A validated AdaptationProject ready to save.

    Raises:
        ValueError: If the draft is structurally invalid beyond repair.
    """
    if not project_id:
        project_id = f"proj_{int(datetime.now(timezone.utc).timestamp())}"

    # 1. Normalize characters
    characters: dict[str, Character] = {}
    for c in draft.get("characters", []):
        cid = c.get("character_id", "")
        if not cid:
            continue
        characters[cid] = Character(
            character_id=cid,
            name=c.get("name", cid),
            role=c.get("role", "supporting"),
            description=c.get("description", ""),
            traits=c.get("traits", []),
            color=c.get("color"),
            asset_ids={},
        )

    # 2. Normalize scenes + nodes
    scenes: dict[str, Scene] = {}
    all_warnings: list[str] = []

    for raw_scene in draft.get("scenes", []):
        scene_id = raw_scene.get("scene_id", "")
        if not scene_id:
            continue

        raw_nodes = raw_scene.get("nodes", {})
        if not raw_nodes:
            all_warnings.append(f"Scene {scene_id} has no nodes, skipping")
            continue

        # Build validated nodes
        seen_ids: set[str] = set()
        nodes: dict[str, Node] = {}

        for nid, raw in raw_nodes.items():
            node = _normalize_node(nid, raw, characters, all_warnings)
            if node and nid not in seen_ids:
                nodes[nid] = node
                seen_ids.add(nid)

        # Validate references within the scene
        _validate_node_refs(nodes, scene_id, all_warnings)

        # Extract background_id from background_cue if present
        bg_cue = raw_scene.get("background_cue")
        bg_id = bg_cue.get("asset_id") if isinstance(bg_cue, dict) else None

        scenes[scene_id] = Scene(
            scene_id=scene_id,
            title=raw_scene.get("title", scene_id),
            description=raw_scene.get("description", ""),
            background_id=bg_id,
            nodes=nodes,
        )

    # 3. Extract asset cues
    asset_cues: list[AssetCue] = []
    for ac in draft.get("asset_cues", []):
        try:
            asset_cues.append(AssetCue(**ac))
        except Exception:
            pass

    # 4. Determine start scene
    start_scene_id = next(iter(scenes)) if scenes else ""

    # 5. Build the project (timestamps set by model_post_init)
    project = AdaptationProject(
        project_id=project_id,
        title=draft.get("novel_title", "Untitled"),
        author="",
        characters=characters,
        scenes=scenes,
        start_scene_id=start_scene_id,
        variables=draft.get("variables", []),
        asset_resources={},
        version=1,
    )

    return project


def _normalize_node(
    nid: str,
    raw: dict[str, Any],
    characters: dict[str, Character],
    warnings: list[str],
) -> Node | None:
    """Parse a raw node dict into a typed Node, with best-effort repairs."""
    ntype = raw.get("type", "")

    if ntype not in VALID_NODE_TYPES:
        warnings.append(f"Node {nid}: unknown type '{ntype}', treating as narration")
        ntype = "narration"

    try:
        match ntype:
            case "dialogue":
                cid = raw.get("character_id", "")
                if cid not in characters:
                    warnings.append(f"Node {nid}: unknown character '{cid}', dropping")
                    # Still create the node but note the issue
                emotion = raw.get("emotion", "neutral")
                if emotion not in VALID_EMOTIONS:
                    emotion = "neutral"
                side = raw.get("side", "center")
                if side not in VALID_SIDES:
                    side = "center"
                return DialogueNode(
                    node_id=nid,
                    character_id=cid,
                    text=raw.get("text", ""),
                    emotion=Emotion(emotion),
                    side=Side(side),
                    next_node_id=raw.get("next_node_id"),
                )

            case "narration":
                return NarrationNode(
                    node_id=nid,
                    text=raw.get("text", ""),
                    next_node_id=raw.get("next_node_id"),
                    background_id=raw.get("background_id"),
                )

            case "choice":
                options = []
                for opt in raw.get("options", []):
                    options.append(ChoiceOption(
                        option_id=opt.get("option_id", f"opt_{nid}_{len(options)}"),
                        text=opt.get("text", ""),
                        next_node_id=opt.get("next_node_id", ""),
                        condition=opt.get("condition"),
                        effects=opt.get("effects", {}),
                    ))
                return ChoiceNode(
                    node_id=nid,
                    text=raw.get("text", ""),
                    options=options,
                )

            case "scene_transition":
                return SceneTransitionNode(
                    node_id=nid,
                    target_scene_id=raw.get("target_scene_id", ""),
                    effect=raw.get("effect", "fade"),
                    next_node_id=raw.get("next_node_id"),
                )

            case "branch":
                return BranchNode(
                    node_id=nid,
                    condition=raw.get("condition", ""),
                    true_next=raw.get("true_next", ""),
                    false_next=raw.get("false_next", ""),
                )

            case "ending":
                return EndingNode(
                    node_id=nid,
                    ending_type=raw.get("ending_type", "neutral"),
                    epilogue=raw.get("epilogue", ""),
                )

    except Exception as e:
        warnings.append(f"Node {nid}: failed to parse ({e}), skipping")
        return None

    return None


def _validate_node_refs(
    nodes: dict[str, Node],
    scene_id: str,
    warnings: list[str],
) -> None:
    """Validate all inter-node references within a scene, repairing when possible."""
    for nid, node in nodes.items():
        match node:
            case DialogueNode(next_node_id=nxt) if nxt and nxt not in nodes:
                warnings.append(f"Scene {scene_id}: DialogueNode {nid} points to missing {nxt}")
                node.next_node_id = None
            case NarrationNode(next_node_id=nxt) if nxt and nxt not in nodes:
                warnings.append(f"Scene {scene_id}: NarrationNode {nid} points to missing {nxt}")
                node.next_node_id = None
            case ChoiceNode() as cn:
                for opt in cn.options:
                    if opt.next_node_id not in nodes:
                        warnings.append(f"Scene {scene_id}: ChoiceNode {nid} option {opt.option_id} points to missing {opt.next_node_id}")
            case BranchNode() as bn:
                if bn.true_next not in nodes:
                    warnings.append(f"Scene {scene_id}: BranchNode {nid} true_next points to missing {bn.true_next}")
                if bn.false_next not in nodes:
                    warnings.append(f"Scene {scene_id}: BranchNode {nid} false_next points to missing {bn.false_next}")
            case SceneTransitionNode(target_scene_id=tid) if not tid:
                warnings.append(f"Scene {scene_id}: SceneTransitionNode {nid} has no target_scene_id")


def validate_project(project: AdaptationProject) -> list[str]:
    """Run integrity checks on a promoted project. Returns list of issues."""
    issues: list[str] = []
    all_char_ids = set(project.characters.keys())
    all_scene_ids = set(project.scenes.keys())

    for sid, scene in project.scenes.items():
        for nid, node in scene.nodes.items():
            # Check character references
            if isinstance(node, DialogueNode):
                if node.character_id and node.character_id not in all_char_ids:
                    issues.append(f"Scene {sid}/{nid}: references missing character '{node.character_id}'")
        # Check scene transition targets
        for node in scene.nodes.values():
            if isinstance(node, SceneTransitionNode):
                if node.target_scene_id and node.target_scene_id not in all_scene_ids:
                    issues.append(f"Scene {sid}/{nid}: SceneTransitionNode target '{node.target_scene_id}' not found")

    return issues
