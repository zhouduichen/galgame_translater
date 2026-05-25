"""Multi-step LLM prompt pipeline for novel → ParseDraft conversion.

Pipeline:
  1. STEP_SUMMARIZE — Extract title, synopsis, key locations, themes
  2. STEP_CHARACTERS — Identify and describe characters
  3. STEP_SCENES — Segment novel into scenes with descriptions
  4. STEP_VN_ADAPT — Convert each scene into a VN node graph
"""

STEP_SUMMARIZE = "summarize"
STEP_CHARACTERS = "characters"
STEP_SCENES = "scenes"
STEP_VN_ADAPT = "vn_adapt"

# ─── Step 1: Summarize ───────────────────────────────────────────────────────

PROMPT_SUMMARIZE = """You are a visual novel adaptation assistant. Your task is to analyze a novel excerpt and produce a structured summary.

Novel text:
```
{novel_text}
```

Output ONLY valid JSON with this exact structure (no markdown fences, no extra text):
{{
  "title": "original novel title or generated title",
  "synopsis": "2-4 sentence synopsis of the excerpt",
  "themes": ["list of themes"],
  "locations": ["list of distinct locations mentioned"],
  "target_length": "{target_length}",
  "tone": "overall tone (e.g., romantic, suspenseful, comedic)"
}}"""

# ─── Step 2: Characters ──────────────────────────────────────────────────────

PROMPT_CHARACTERS = """Based on this novel excerpt, identify all characters and their attributes.

Novel text:
```
{novel_text}
```

Context summary:
{summary_json}

Output ONLY valid JSON with this exact structure (no markdown, no extra text):
{{
  "characters": [
    {{
      "character_id": "unique_id (e.g., char_001)",
      "name": "character name",
      "role": "protagonist | supporting | antagonist",
      "description": "2-3 sentence description",
      "traits": ["3-5 personality traits"],
      "color": "hex color for name display (e.g., #88ccff)",
      "key_dialogue": "a notable line of dialogue that captures their voice"
    }}
  ]
}}

Rules:
- protagonist role for the main POV character (max 1-2)
- Include all named characters with speaking roles
- character_id must be lowercase letters and underscores only"""

# ─── Step 3: Scenes ──────────────────────────────────────────────────────────

PROMPT_SCENES = """Segment the novel excerpt into distinct scenes. A scene is a continuous sequence at one location with a consistent set of characters.

Novel text:
```
{novel_text}
```

Characters:
{characters_json}

Output ONLY valid JSON with this exact structure (no markdown):
{{
  "scenes": [
    {{
      "scene_id": "scene_001",
      "title": "short scene title",
      "description": "1-2 sentence scene summary",
      "location": "location name",
      "characters_present": ["character_id list"],
      "narrative_focus": "what happens / what changes",
      "estimated_nodes": number (5-15),
      "has_choice": true/false (whether a meaningful player choice can exist here)
    }}
  ]
}}

Rules:
- First scene should establish setting and protagonist
- Each scene should have 5-15 VN nodes worth of content
- Mark has_choice=true only if there's a natural branching point
- Scenes should be in chronological order"""

# ─── Step 4: VN Adaptation ──────────────────────────────────────────────────

PROMPT_VN_ADAPT = """Convert the following scene into a visual novel node graph. Each node is one "frame" of the visual novel.

Scene info:
{scene_info}

Characters in scene:
{characters_json}

Available locations:
{locations_json}

Output ONLY valid JSON with this exact structure (no markdown):
{{
  "scene_id": "{scene_id}",
  "title": "{scene_title}",
  "description": "{scene_description}",
  "background_cue": {{
    "asset_id": "bg_{location_id}",
    "target_type": "background",
    "description": "description of the background image needed"
  }},
  "nodes": {{
    "node_001": {{
      "type": "narration",
      "node_id": "node_001",
      "text": "narration text setting the scene",
      "next_node_id": "node_002"
    }},
    "node_002": {{
      "type": "dialogue",
      "node_id": "node_002",
      "character_id": "char_id",
      "text": "dialogue line",
      "emotion": "neutral|happy|sad|angry|surprised|shy|thinking",
      "side": "left|right|center",
      "next_node_id": "node_003"
    }}
  }}
}}

RULES:
1. node_id format: "node_001", "node_002", etc.
2. Dialogue nodes MUST have character_id matching a character in the scene
3. Narration nodes set the scene mood and describe actions
4. Add a ChoiceNode at the branching point if the scene has a choice
5. ChoiceNode options must point to existing node_ids
6. SceneTransitionNode as the last node if another scene follows
7. EndingNode if this is the final scene
8. Every next_node_id must reference an existing node_id in this scene
9. Total 8-12 nodes per scene for a 10-minute demo density
10. Include varied emotions in dialogue nodes, not all neutral

If this scene should have a choice, structure it like:
{{
  "type": "choice",
  "node_id": "node_00X",
  "text": "narration before choice",
  "options": [
    {{"option_id": "opt_1", "text": "choice text", "next_node_id": "node_00Y", "effects": {{"variable_name": value}}}},
    {{"option_id": "opt_2", "text": "alternative", "next_node_id": "node_00Z", "effects": {{"variable_name": value}}}}
  ]
}}
"""


# ─── Pipeline builder ────────────────────────────────────────────────────────

def build_parse_draft_prompt(step: str, **kwargs) -> str:
    """Build the prompt for a given pipeline step."""
    match step:
        case "summarize":
            return PROMPT_SUMMARIZE.format(
                novel_text=kwargs["novel_text"],
                target_length=kwargs.get("target_length", "10min_demo"),
            )
        case "characters":
            return PROMPT_CHARACTERS.format(
                novel_text=kwargs["novel_text"],
                summary_json=kwargs["summary_json"],
            )
        case "scenes":
            return PROMPT_SCENES.format(
                novel_text=kwargs["novel_text"],
                characters_json=kwargs["characters_json"],
            )
        case "vn_adapt":
            return PROMPT_VN_ADAPT.format(
                scene_id=kwargs["scene_id"],
                scene_title=kwargs["scene_title"],
                scene_description=kwargs["scene_description"],
                scene_info=kwargs.get("scene_info", ""),
                characters_json=kwargs["characters_json"],
                locations_json=kwargs["locations_json"],
                location_id=kwargs.get("location_id", "unknown"),
            )
        case _:
            raise ValueError(f"Unknown step: {step}")
