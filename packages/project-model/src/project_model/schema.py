from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


# ─── Enums ───────────────────────────────────────────────────────────────────

class NodeType(str, Enum):
    dialogue = "dialogue"
    narration = "narration"
    choice = "choice"
    scene_transition = "scene_transition"
    branch = "branch"
    ending = "ending"


class Emotion(str, Enum):
    neutral = "neutral"
    happy = "happy"
    sad = "sad"
    angry = "angry"
    surprised = "surprised"
    shy = "shy"
    thinking = "thinking"
    crying = "crying"
    laughing = "laughing"


class AssetType(str, Enum):
    character_sprite = "character_sprite"
    background = "background"
    cg = "cg"
    icon = "icon"
    bgm = "bgm"
    sfx = "sfx"


class ExportFormat(str, Enum):
    renpy = "renpy"
    web = "web"


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    permanently_failed = "permanently_failed"
    cancelled = "cancelled"


class Side(str, Enum):
    left = "left"
    right = "right"
    center = "center"


# ─── Asset Layer ─────────────────────────────────────────────────────────────

class AssetCue(BaseModel):
    """What resource is needed. Exists at the 'demand' layer — before generation."""
    asset_id: str
    target_type: AssetType
    character_id: str | None = None
    emotion: Emotion | None = None
    description: str
    style_preset: str = "anime_visual_novel"
    width: int = 1920
    height: int = 1080


class AssetResource(BaseModel):
    """What resource is actually available. Exists at the 'supply' layer — after generation or manual upload."""
    id: str
    url: str
    asset_type: AssetType
    character_id: str | None = None
    emotion: Emotion | None = None
    generator: str | None = None  # "comfyui", "manual_upload", "placeholder"
    seed: int | None = None
    width: int = 1920
    height: int = 1080
    idempotency_key: str | None = None
    """Deterministic hash(project_id:type:params) for dedup — see check_asset_exists()."""
    base_asset_id: str | None = None
    """If this asset was generated incrementally from a base, points to the base AssetResource.id."""


# ─── Character Layer ─────────────────────────────────────────────────────────

class CharacterCue(BaseModel):
    """Draft-level character info from LLM parsing."""
    character_id: str
    name: str
    role: str = "supporting"  # protagonist, supporting, antagonist
    description: str
    appearance: str = ""  # visual appearance for image generation
    traits: list[str] = Field(default_factory=list)
    color: str | None = None  # nameplate / text color hint


class Character(CharacterCue):
    """Full character definition in an AdaptationProject — includes assigned assets."""
    asset_ids: dict[Emotion, str] = Field(default_factory=dict)
    """Maps emotion → asset_resource_id for sprite rendering."""


# ─── Node Layer ──────────────────────────────────────────────────────────────

class ChoiceOption(BaseModel):
    option_id: str
    text: str
    next_node_id: str
    condition: str | None = None
    """Optional variable expression string. Empty = always available."""
    effects: dict[str, Any] = Field(default_factory=dict)
    """Variables to set when this option is chosen, e.g. {"affection_heroine": 3}."""


class DialogueNode(BaseModel):
    type: Literal[NodeType.dialogue] = NodeType.dialogue
    node_id: str
    character_id: str
    text: str
    emotion: Emotion = Emotion.neutral
    side: Side = Side.center
    next_node_id: str | None = None


class NarrationNode(BaseModel):
    type: Literal[NodeType.narration] = NodeType.narration
    node_id: str
    text: str
    next_node_id: str | None = None
    background_id: str | None = None


class ChoiceNode(BaseModel):
    type: Literal[NodeType.choice] = NodeType.choice
    node_id: str
    text: str = ""
    """Narration text shown above the choice list, if any."""
    options: list[ChoiceOption] = Field(min_length=1)


class SceneTransitionNode(BaseModel):
    type: Literal[NodeType.scene_transition] = NodeType.scene_transition
    node_id: str
    target_scene_id: str
    effect: str = "fade"
    next_node_id: str | None = None


class BranchNode(BaseModel):
    type: Literal[NodeType.branch] = NodeType.branch
    node_id: str
    condition: str
    """Variable expression to evaluate, e.g. "affection_heroine >= 3"."""
    true_next: str
    false_next: str


class EndingNode(BaseModel):
    type: Literal[NodeType.ending] = NodeType.ending
    node_id: str
    ending_type: Literal["good", "bad", "true", "neutral"] = "neutral"
    epilogue: str = ""


Node = Annotated[
    DialogueNode
    | NarrationNode
    | ChoiceNode
    | SceneTransitionNode
    | BranchNode
    | EndingNode,
    Field(discriminator="type"),
]


# ─── Scene Layer ─────────────────────────────────────────────────────────────

class Scene(BaseModel):
    scene_id: str
    title: str
    description: str = ""
    visual_description: str = ""  # visual details for image generation prompt
    background_id: str | None = None
    """References an asset_resource_id. Falls back to placeholder if unset."""
    nodes: dict[str, Node]
    """Keyed by node_id. Order is maintained by the 'next_node_id' chain."""

    def first_node_id(self) -> str | None:
        """Return the entry-point node ID (the one no other node points to)."""
        targets = set()
        for node in self.nodes.values():
            match node:
                case DialogueNode(next_node_id=nid) if nid:
                    targets.add(nid)
                case NarrationNode(next_node_id=nid) if nid:
                    targets.add(nid)
                case SceneTransitionNode(next_node_id=nid) if nid:
                    targets.add(nid)
                case ChoiceNode():
                    for opt in node.options:
                        targets.add(opt.next_node_id)
                case BranchNode():
                    targets.add(node.true_next)
                    targets.add(node.false_next)
        for nid in self.nodes:
            if nid not in targets:
                return nid
        return None


# ─── Top-Level Models ────────────────────────────────────────────────────────

class ParseDraft(BaseModel):
    """LLM-parsed output from novel text. May not be fully playable — needs validation."""
    draft_id: str
    project_id: str
    novel_title: str
    novel_excerpt: str
    synopsis: str = ""
    characters: list[CharacterCue] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    scenes: list[Scene] = Field(default_factory=list)
    asset_cues: list[AssetCue] = Field(default_factory=list)
    variables: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AdaptationProject(BaseModel):
    """The canonical, edited project model used by the player and editor."""
    project_id: str
    title: str
    author: str = ""
    characters: dict[str, Character] = Field(default_factory=dict)
    scenes: dict[str, Scene] = Field(default_factory=dict)
    start_scene_id: str
    variables: list[dict[str, Any]] = Field(default_factory=list)
    asset_resources: dict[str, AssetResource] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    version: int = 1

    def model_post_init(self, __context: Any) -> None:
        now = datetime.utcnow().isoformat() + "Z"
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


class ExportArtifact(BaseModel):
    """Record of a completed export — does NOT bi-directionally link to the project."""
    export_id: str
    project_id: str
    format: ExportFormat
    file_path: str
    file_size_bytes: int | None = None
    created_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class GenerationJob(BaseModel):
    """Background job for LLM parsing or asset generation."""
    job_id: str
    project_id: str
    job_type: Literal["parse_draft", "generate_asset", "export_renpy", "export_web"]
    status: JobStatus = JobStatus.pending
    progress: float = 0.0
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    retry_count: int = 0
    created_at: str = ""
    updated_at: str = ""

    def model_post_init(self, __context: Any) -> None:
        now = datetime.utcnow().isoformat() + "Z"
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
