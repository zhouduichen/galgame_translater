"""ComfyUI API client for generating backgrounds and character sprites."""

from __future__ import annotations

import json
import os
import random
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

COMFYUI_BASE = os.environ.get("COMFYUI_BASE", "http://127.0.0.1:8188")
COMFYUI_CHECKPOINT = os.environ.get(
    "COMFYUI_CHECKPOINT", "v1-5-pruned-emaonly.safetensors"
)


def _generated_dir() -> Path:
    return Path(
        os.environ.get(
            "GENERATED_DIR",
            str(Path(__file__).resolve().parent.parent.parent.parent / "api" / "data" / "generated"),
        )
    )


def _load_workflow(path: str) -> dict[str, Any]:
    """Load a workflow API JSON from the workflows directory."""
    wf_path = Path(__file__).parent / "workflows" / path
    return json.loads(wf_path.read_text(encoding="utf-8"))


def _queue_prompt(workflow: dict[str, Any], retries: int = 3) -> str:
    """Send a workflow to ComfyUI and return the prompt_id. Retries on transient errors."""
    last_err = None
    for attempt in range(retries):
        try:
            resp = httpx.post(
                f"{COMFYUI_BASE}/prompt",
                json={"prompt": workflow},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["prompt_id"]
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
    raise last_err  # type: ignore[misc]


def _wait_for_image(prompt_id: str, timeout: int = 180) -> tuple[bytes, str] | None:
    """Poll ComfyUI until the image is generated, download and return (image_bytes, filename)."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = httpx.get(
                f"{COMFYUI_BASE}/history/{prompt_id}",
                timeout=10,
            )
            if resp.status_code != 200:
                time.sleep(2)
                continue
            history = resp.json()
            if prompt_id not in history:
                time.sleep(2)
                continue
            outputs = history[prompt_id].get("outputs", {})
            for node_id, node_out in outputs.items():
                for img_data in node_out.get("images", []):
                    filename = img_data["filename"]
                    view_resp = httpx.get(
                        f"{COMFYUI_BASE}/view",
                        params={
                            "filename": filename,
                            "subfolder": img_data.get("subfolder", ""),
                            "type": img_data.get("type", "output"),
                        },
                        timeout=30,
                    )
                    if view_resp.status_code == 200:
                        return (view_resp.content, filename)
        except Exception:
            time.sleep(2)
        time.sleep(2)
    return None


# --- Background Generation ----------------------------------------------------


def generate_background(
    description: str,
    width: int = 1280,
    height: int = 720,
    style_preset: str = "anime_visual_novel",
) -> str | None:
    """Generate a background image from a scene description."""
    prompt = _build_background_prompt(description, style_preset)
    workflow = _load_workflow("txt2img.json")

    _set_node_text(workflow, "6", prompt)
    _set_node_text(workflow, "7", "nsfw, lowres, text, watermark, worst quality, bad anatomy")
    _set_node_size(workflow, "5", width, height)
    _set_node_int(workflow, "3", "seed", random.randint(0, 2_147_483_647))
    _set_node_int(workflow, "3", "steps", 20)
    _set_node_str(workflow, "4", "ckpt_name", COMFYUI_CHECKPOINT)

    prompt_id = _queue_prompt(workflow)
    result = _wait_for_image(prompt_id)
    if result is None:
        return None
    img_data, filename = result
    return _save_and_serve(img_data, source_filename=filename)


# --- Character Sprite Generation ----------------------------------------------


def generate_character_sprite(
    character_name: str,
    character_desc: str,
    emotion: str = "neutral",
    style_preset: str = "anime_visual_novel",
) -> str | None:
    """Generate a character sprite with a specific emotion."""
    prompt = _build_sprite_prompt(character_name, character_desc, emotion, style_preset)
    workflow = _load_workflow("txt2img.json")

    _set_node_text(workflow, "6", prompt)
    _set_node_text(workflow, "7", "nsfw, lowres, text, watermark, bad anatomy, extra limbs, bad hands")
    _set_node_size(workflow, "5", 512, 768)
    _set_node_int(workflow, "3", "seed", random.randint(0, 2_147_483_647))
    _set_node_str(workflow, "4", "ckpt_name", COMFYUI_CHECKPOINT)

    prompt_id = _queue_prompt(workflow)
    result = _wait_for_image(prompt_id)
    if result is None:
        return None
    img_data, filename = result
    return _save_and_serve(img_data, source_filename=filename)


# --- Prompt Builders ----------------------------------------------------------


def _build_background_prompt(description: str, style: str) -> str:
    return (
        f"masterpiece, best quality, anime visual novel background, {description}, "
        f"detailed environment, atmospheric lighting, no characters, empty scene"
    )


def _build_sprite_prompt(name: str, desc: str, emotion: str, style: str) -> str:
    emotion_map = {
        "neutral": "neutral expression, calm, looking at viewer",
        "happy": "happy expression, smiling, bright eyes",
        "sad": "sad expression, teary eyes, downturned mouth",
        "shy": "shy expression, blushing, looking away, embarrassed",
        "angry": "angry expression, furrowed brows, tense posture",
        "surprised": "surprised expression, wide eyes, open mouth",
    }
    emotion_text = emotion_map.get(emotion, emotion_map["neutral"])
    return (
        f"masterpiece, best quality, anime character sprite, {name}, {desc}, {emotion_text}, "
        f"full body, standing, plain white background, "
        f"clean lineart, cel shading, solo"
    )


# --- Workflow Helpers ---------------------------------------------------------


def _set_node_text(workflow: dict[str, Any], node_id: str, text: str) -> None:
    """Set the text input of a CLIPTextEncode node."""
    node = workflow.get(node_id)
    if node and "inputs" in node:
        node["inputs"]["text"] = text


def _set_node_size(workflow: dict[str, Any], node_id: str, width: int, height: int) -> None:
    """Set the dimensions of an EmptyLatentImage node."""
    node = workflow.get(node_id)
    if node and "inputs" in node:
        node["inputs"]["width"] = width
        node["inputs"]["height"] = height


def _set_node_int(workflow: dict[str, Any], node_id: str, key: str, value: int) -> None:
    """Set an integer input on any node."""
    node = workflow.get(node_id)
    if node and "inputs" in node:
        node["inputs"][key] = value


def _set_node_str(workflow: dict[str, Any], node_id: str, key: str, value: str) -> None:
    """Set a string input on any node."""
    node = workflow.get(node_id)
    if node and "inputs" in node:
        node["inputs"][key] = value


def _save_and_serve(img_data: bytes, source_filename: str) -> str:
    """Save image bytes to GENERATED_DIR and return a URL path for the API to serve."""
    generated_dir = _generated_dir()
    generated_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(source_filename).suffix or ".png"
    unique = f"gen_{uuid.uuid4().hex[:12]}{ext}"
    dest = generated_dir / unique
    dest.write_bytes(img_data)
    return f"/api/assets/{unique}"
