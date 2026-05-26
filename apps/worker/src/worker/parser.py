"""Multi-step novel parsing pipeline.

Runs 4 steps sequentially, each building on the previous:
  Step 1 (summarize) → Step 2 (characters) → Step 3 (scenes) → Step 4 (vn_adapt per scene)
"""

from __future__ import annotations

import json
from typing import Any

from prompt_templates import build_parse_draft_prompt
from prompt_templates.parse_draft import STEP_SUMMARIZE, STEP_CHARACTERS, STEP_SCENES, STEP_VN_ADAPT

from .llm import call_llm_json

SYSTEM_PROMPT = (
    "You are a precise JSON generator for a visual novel adaptation pipeline. "
    "Output ONLY valid JSON, no explanations, no markdown fences. "
    "All user-facing story text must be Simplified Chinese."
)


def parse_novel(novel_text: str, target_length: str = "10min_demo") -> dict[str, Any]:
    """Run the full parsing pipeline and return a ParseDraft-compatible dict."""
    # Step 1: Summarize
    print("[parser] Step 1/4: Summarizing novel...")
    summary = call_llm_json(
        SYSTEM_PROMPT,
        build_parse_draft_prompt("summarize", novel_text=novel_text, target_length=target_length),
    )

    # Step 2: Characters
    print("[parser] Step 2/4: Extracting characters...")
    char_result = call_llm_json(
        SYSTEM_PROMPT,
        build_parse_draft_prompt(
            "characters",
            novel_text=novel_text,
            summary_json=json.dumps(summary, ensure_ascii=False),
        ),
    )
    characters = char_result.get("characters", [])

    # Step 3: Scenes
    print("[parser] Step 3/4: Segmenting scenes...")
    scenes_result = call_llm_json(
        SYSTEM_PROMPT,
        build_parse_draft_prompt(
            "scenes",
            novel_text=novel_text,
            characters_json=json.dumps(characters, ensure_ascii=False),
        ),
    )
    scenes_meta = scenes_result.get("scenes", [])

    # Step 4: VN adaptation for each scene
    print(f"[parser] Step 4/4: Adapting {len(scenes_meta)} scenes to VN nodes...")
    adapted_scenes = []
    all_asset_cues = []

    for i, scene_meta in enumerate(scenes_meta):
        scene_id = scene_meta.get("scene_id", f"scene_{i + 1:03d}")
        print(f"  Adapting scene {i + 1}/{len(scenes_meta)}: {scene_meta.get('title', scene_id)}")

        scene_info = (
            f"Title: {scene_meta.get('title', '')}\n"
            f"Description: {scene_meta.get('description', '')}\n"
            f"Location: {scene_meta.get('location', '')}\n"
            f"Characters present: {', '.join(scene_meta.get('characters_present', []))}"
        )

        scene_chars = [
            c for c in characters if c.get("character_id") in scene_meta.get("characters_present", [])
        ]

        scene_result = call_llm_json(
            SYSTEM_PROMPT,
            build_parse_draft_prompt(
                "vn_adapt",
                scene_id=scene_id,
                scene_title=scene_meta.get("title", ""),
                scene_description=scene_meta.get("description", ""),
                scene_info=scene_info,
                characters_json=json.dumps(scene_chars, ensure_ascii=False),
                locations_json=json.dumps(summary.get("locations", []), ensure_ascii=False),
                location_id=scene_meta.get("location", "").lower().replace(" ", "_"),
            ),
        )

        adapted_scenes.append(scene_result)

        # Extract background cue
        bg_cue = scene_result.get("background_cue")
        if bg_cue:
            all_asset_cues.append(bg_cue)

    # Assemble final result
    characters_simple = []
    for c in characters:
        characters_simple.append({
            "character_id": c.get("character_id"),
            "name": c.get("name"),
            "role": c.get("role", "supporting"),
            "description": c.get("description", ""),
            "traits": c.get("traits", []),
            "color": c.get("color"),
        })

    result = {
        "draft_id": "",
        "project_id": "",
        "novel_title": summary.get("title", "未命名作品"),
        "novel_excerpt": novel_text[:500],
        "synopsis": summary.get("synopsis", ""),
        "characters": characters_simple,
        "locations": summary.get("locations", []),
        "scenes": adapted_scenes,
        "asset_cues": all_asset_cues,
        "warnings": [],
    }

    return result
