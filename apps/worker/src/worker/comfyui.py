"""
ComfyUI API client for Galgame asset generation.

Uses Animagine XL V3.1 as default checkpoint with Danbooru-style prompts.
Supports Face Detailer, Rembg (alpha PNG), LoRA, async WebSocket monitoring,
image post-processing (WebP, resize), and webhook callbacks.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import shutil
import struct
import threading
import time
import uuid
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

import httpx
from PIL import Image
from project_model.schema import (
    AdaptationProject,
    AssetResource,
    BranchNode,
    ChoiceNode,
    DialogueNode,
    Emotion,
    EndingNode,
    NarrationNode,
    Scene,
    SceneTransitionNode,
)

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Configuration — overridable via environment variables
# ---------------------------------------------------------------------------

COMFYUI_BASE = os.environ.get("COMFYUI_BASE", "http://127.0.0.1:8188")
COMFYUI_WS = os.environ.get("COMFYUI_WS", "ws://127.0.0.1:8188/ws")
COMFYUI_CHECKPOINT = os.environ.get(
    "COMFYUI_CHECKPOINT", "animagine-xl-3.1.safetensors"
)
COMFYUI_CONCURRENCY = int(os.environ.get("COMFYUI_CONCURRENCY", "1"))
_semaphore = threading.BoundedSemaphore(COMFYUI_CONCURRENCY)

# Feature flags
ENABLE_FACE_DETAILER = os.environ.get("ENABLE_FACE_DETAILER", "true").lower() == "true"
ENABLE_REMBG = os.environ.get("ENABLE_REMBG", "true").lower() == "true"
GENERATE_WEBP = os.environ.get("GENERATE_WEBP", "true").lower() == "true"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

# SDXL resolution presets for Animagine XL
RESOLUTION_CHARACTER = (896, 1344)     # 3:4 portrait
RESOLUTION_CHARACTER_WIDE = (1024, 1536)  # 2:3 tall
RESOLUTION_CHARACTER_TALL = (832, 1216)   # common alternative
RESOLUTION_BACKGROUND = (1344, 768)    # 16:9 landscape
RESOLUTION_BACKGROUND_WIDE = (1536, 864)  # 16:10
RESOLUTION_BACKGROUND_PORTRAIT = (1216, 832)  # 3:2 portrait

# Sampling defaults for Animagine XL
SAMPLER_STEPS = 30
SAMPLER_CFG = 7
SAMPLER_NAME = "euler_ancestral"
SAMPLER_SCHEDULER = "normal"

# LoRA
LORA_DIR = os.environ.get("LORA_DIR", "")

# Incremental inpainting denoise -- emotion to denoise strength mapping
_INPAINT_DENOISE_MAP: dict[str, float] = {
    "neutral": 0.35,
    "happy": 0.35,
    "shy": 0.35,
    "sad": 0.38,
    "thinking": 0.38,
    "angry": 0.40,
    "surprised": 0.40,
    "crying": 0.42,
    "embarrassed": 0.42,
}
_INPAINT_DENOISE_DEFAULT = 0.35

# Base image cache subdirectory name
_BASE_CACHE_DIRNAME = "bases"

# Timeouts (seconds)
PROMPT_TIMEOUT = 300
QUEUE_TIMEOUT = 30

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _generated_dir() -> Path:
    return Path(
        os.environ.get(
            "GENERATED_DIR",
            str(Path(__file__).resolve().parent.parent.parent.parent / "api" / "data" / "generated"),
        )
    )


def _export_dir() -> Path:
    """Return the organized export directory (for Ren'Py packaging)."""
    return _generated_dir().parent / "export"


def _base_cache_dir() -> Path:
    """Directory for cached base images (FaceDetailer pre-Rembg outputs)."""
    return _generated_dir() / _BASE_CACHE_DIRNAME


def _base_cache_path(idempotency_key: str) -> Path:
    """Determine the on-disk cache path for a given idempotency key."""
    safe = idempotency_key.replace(":", "_").replace("/", "_")
    return _base_cache_dir() / f"{safe}.png"


def _cache_base_image(img_data: bytes, idempotency_key: str) -> Path:
    """Persist a FaceDetailer output as a cached base image for later incremental use."""
    dest = _base_cache_path(idempotency_key)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(img_data)
    return dest


def _asset_url_to_path(asset_url: str) -> Path | None:
    """Convert /api/assets/xxx.png to a local Path, or None if unresolvable."""
    if not asset_url:
        return None
    filename = asset_url.replace("/api/assets/", "").lstrip("/")
    if not filename:
        return None
    path = _generated_dir() / filename
    return path if path.exists() else None


def check_asset_exists(
    project_asset_resources: dict[str, AssetResource],
    idempotency_key: str,
) -> AssetResource | None:
    """Check if an asset with the given idempotency key exists (DB + disk double-check).

    Args:
        project_asset_resources: ``project.asset_resources`` dict.
        idempotency_key: The deterministic fingerprint to look up.

    Returns:
        The AssetResource if found *and* the file exists on disk, else None.
    """
    for resource in project_asset_resources.values():
        if resource.idempotency_key == idempotency_key:
            local_path = _asset_url_to_path(resource.url)
            if local_path is not None and local_path.exists():
                return resource
    return None


# ---------------------------------------------------------------------------
# Workflow loading
# ---------------------------------------------------------------------------


def _load_workflow(path: str) -> dict[str, Any]:
    """Load a workflow API JSON from the workflows directory."""
    wf_path = Path(__file__).parent / "workflows" / path
    return json.loads(wf_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# HTTP submission
# ---------------------------------------------------------------------------


def _queue_prompt(workflow: dict[str, Any], retries: int = 3) -> str:
    """Send a workflow to ComfyUI and return the prompt_id. Retries on transient errors."""
    last_err = None
    for attempt in range(retries):
        try:
            resp = httpx.post(
                f"{COMFYUI_BASE}/prompt",
                json={"prompt": workflow},
                timeout=QUEUE_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()["prompt_id"]
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
    raise last_err  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Image fetching (from history API)
# ---------------------------------------------------------------------------


def _fetch_image_from_history(
    prompt_id: str,
    node_ids: set[str] | None = None,
) -> tuple[bytes, str] | None:
    """Fetch generated image from the ComfyUI history API."""
    try:
        resp = httpx.get(f"{COMFYUI_BASE}/history/{prompt_id}", timeout=10)
        if resp.status_code != 200:
            return None
        history = resp.json()
        if prompt_id not in history:
            return None
        outputs = history[prompt_id].get("outputs", {})
        for node_id, node_out in outputs.items():
            if node_ids is not None and node_id not in node_ids:
                continue
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
        return None
    return None


def _poll_image(
    prompt_id: str,
    timeout: int = PROMPT_TIMEOUT,
    node_ids: set[str] | None = None,
) -> tuple[bytes, str] | None:
    """Poll ComfyUI history until the image is ready.

    Args:
        prompt_id: The ComfyUI prompt ID.
        timeout: Max time to wait in seconds.
        node_ids: If set, only return images from these output node IDs.
    """
    start = time.time()
    while time.time() - start < timeout:
        result = _fetch_image_from_history(prompt_id, node_ids=node_ids)
        if result is not None:
            return result
        time.sleep(2)
    return None


# ---------------------------------------------------------------------------
# WebSocket monitoring (async)
# ---------------------------------------------------------------------------


async def _ws_wait_for_execution(
    prompt_id: str,
    client_id: str,
    on_progress: Callable[[float], None] | None = None,
    timeout: int = PROMPT_TIMEOUT,
) -> bool:
    """Monitor ComfyUI WebSocket until a prompt finishes executing.

    Returns True if execution completed, False on timeout.
    Calls ``on_progress(progress_float)`` each time a progress update arrives.
    """
    if websockets is None:
        # Fall back to polling when websockets isn't installed
        return _poll_image(prompt_id, timeout) is not None

    uri = f"{COMFYUI_WS}?clientId={client_id}"
    try:
        async with websockets.connect(uri, max_size=2**23, ping_interval=30) as ws:
            start = time.time()
            while time.time() - start < timeout:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Send a ping to keep connection alive, then retry
                    continue

                if isinstance(msg, bytes):
                    # ComfyUI binary WS format: [4B type][4B unused][8B? payload...]
                    msg_type = struct.unpack(">I", msg[:4])[0]
                    if msg_type == 1:
                        # Status message
                        data = json.loads(msg[8:].decode("utf-8"))
                        evt_type = data.get("type", "")
                        evt_data = data.get("data", {})

                        if evt_type == "executing" and evt_data.get("node") is None:
                            # Execution complete (node=None signals done)
                            return True

                    elif msg_type == 2 and on_progress is not None:
                        # Progress message
                        data = json.loads(msg[8:].decode("utf-8"))
                        step = data.get("step", 0)
                        max_step = data.get("max_step", 1) or 1
                        on_progress(min(step / max_step, 1.0))
            return False  # Timeout
    except Exception:
        # Fallback: poll if WS fails
        return _poll_image(prompt_id, timeout) is not None


# ---------------------------------------------------------------------------
# Workflow node helpers
# ---------------------------------------------------------------------------


def _set_node_text(workflow: dict[str, Any], node_id: str, text: str) -> None:
    node = workflow.get(node_id)
    if node and "inputs" in node:
        node["inputs"]["text"] = text


def _set_node_size(workflow: dict[str, Any], node_id: str, width: int, height: int) -> None:
    node = workflow.get(node_id)
    if node and "inputs" in node:
        node["inputs"]["width"] = width
        node["inputs"]["height"] = height


def _set_node_int(workflow: dict[str, Any], node_id: str, key: str, value: int) -> None:
    node = workflow.get(node_id)
    if node and "inputs" in node:
        node["inputs"][key] = value


def _set_node_float(workflow: dict[str, Any], node_id: str, key: str, value: float) -> None:
    node = workflow.get(node_id)
    if node and "inputs" in node:
        node["inputs"][key] = value


def _set_node_str(workflow: dict[str, Any], node_id: str, key: str, value: str) -> None:
    node = workflow.get(node_id)
    if node and "inputs" in node:
        node["inputs"][key] = value


# ---------------------------------------------------------------------------
# Seed derivation (Steps 17-20)
# ---------------------------------------------------------------------------


def _character_seed(
    character_name: str,
    emotion: str = "neutral",
    scene_index: int = 0,
    shot_index: int = 0,
    variation_index: int = 0,
) -> int:
    """Derive a deterministic seed from identity + emotion + scene + variation.

    Seed hierarchy (which params control what)::

        character + emotion  →  IDENTITY BASELINE
            These two define "who" the character is. Keep them fixed across
            expressions of the same character to maintain consistent appearance
            (hair, eyes, uniform, body type).

        scene + shot + variation  →  PER-SHOT PERTURBATION
            These add controlled variation for different in-game contexts.
            - scene_index       →  different story scenes (classroom, street)
            - shot_index        →  different camera angles in the same scene
            - variation_index   →  subtle alternative of the same shot

    Use cases::

        # Neutral expression, scene 0, first shot
        seed = _character_seed("Sakura", "neutral", scene_index=0, shot_index=0)

        # Same expression, scene 0, second shot (slightly different framing)
        seed = _character_seed("Sakura", "neutral", scene_index=0, shot_index=1)

        # Happy expression, scene 1, first shot, second variation
        seed = _character_seed("Sakura", "happy", scene_index=1, shot_index=0, variation_index=1)
    """
    raw = f"{character_name}:{emotion}:s{scene_index}:sh{shot_index}:v{variation_index}"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16) & 0x7FFFFFFF


def _compute_idempotency_key(
    target_type: str,
    project_id: str,
    character_id: str | None = None,
    emotion: str | None = None,
    scene_id: str | None = None,
    description: str | None = None,
) -> str:
    """Compute a deterministic idempotency key for an asset.

    Used for pre-generation dedup checks. Must produce identical output to
    the API-side version in ``routers/projects.py``.
    """
    if target_type == "character_sprite":
        raw = f"{project_id}:char:{character_id}:emotion:{emotion}"
    elif target_type == "background":
        raw = f"{project_id}:bg:{scene_id}"
    else:
        raw = f"{project_id}:{target_type}:{description or 'unknown'}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Dynamic workflow node injection
# ---------------------------------------------------------------------------


def _next_node_id(workflow: dict[str, Any]) -> str:
    """Return the next available integer node ID as a string."""
    existing = [int(k) for k in workflow.keys()]
    return str(max(existing) + 1 if existing else 1)


def _inject_lora(
    workflow: dict[str, Any], lora_name: str, lora_weight: float = 0.8
) -> dict[str, Any]:
    """Inject a LoraLoader node between the checkpoint and CLIP encoders.

    Node structure:
        LoraLoader(
            model ← CheckpointLoaderSimple.model,
            clip  ← CheckpointLoaderSimple.clip,
            lora_name,
            strength_model,
            strength_clip
        ) → (model, clip)

    All downstream nodes that consumed (model, clip) from the checkpoint
    are rewired to consume from the LoraLoader instead.
    """
    lora_node_id = _next_node_id(workflow)
    workflow[lora_node_id] = {
        "class_type": "LoraLoader",
        "inputs": {
            "lora_name": lora_name,
            "strength_model": lora_weight,
            "strength_clip": lora_weight,
            "model": ["4", 0],
            "clip": ["4", 1],
        },
    }

    # Re-wire all nodes that previously read from checkpoint (node 4) outputs 0/1
    for nid, node in workflow.items():
        if nid == lora_node_id:
            continue
        for key, val in node.get("inputs", {}).items():
            if isinstance(val, list) and len(val) == 2:
                if val == ["4", 0]:
                    node["inputs"][key] = [lora_node_id, 0]
                elif val == ["4", 1]:
                    node["inputs"][key] = [lora_node_id, 1]

    return workflow


def _select_character_workflow() -> dict[str, Any]:
    """Load the character workflow (with FaceDetailer + Rembg) or fall back to base.

    If custom nodes are unavailable, ComfyUI will return an error at submission
    time rather than crashing here — the caller should handle that gracefully.
    """
    return _load_workflow("txt2img_character.json")


def _select_background_workflow() -> dict[str, Any]:
    """Load the base txt2img workflow for background generation."""
    return _load_workflow("txt2img.json")


def _select_inpaint_workflow() -> dict[str, Any]:
    """Load the incremental inpaint workflow (LoadImage to FaceDetailer to Rembg)."""
    return _load_workflow("txt2img_inpaint.json")


def _upload_image_to_comfyui(image_path: str | Path) -> str:
    """Upload a cached base image to ComfyUI's input directory.

    Returns the filename (basename) to use in LoadImage node.
    Raises httpx.HTTPError on failure.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Base image not found: {path}")
    with open(path, "rb") as f:
        resp = httpx.post(
            f"{COMFYUI_BASE}/upload/image",
            files={"image": (path.name, f, "image/png")},
            data={"subfolder": _BASE_CACHE_DIRNAME, "type": "input"},
            timeout=30,
        )
    resp.raise_for_status()
    return resp.json().get("name", path.name)


# ---------------------------------------------------------------------------
# Danbooru-Style Prompt Builders (Animagine XL V3.1)
# ---------------------------------------------------------------------------


def _build_background_prompts(description: str) -> tuple[str, str]:
    """Build Danbooru-style positive/negative prompts for a background scene."""
    pos = (
        "masterpiece, best quality, very aesthetic, absurdres, "
        "galgame background, visual novel background, anime scenery, game cg, "
        f"{description}, "
        "wide angle, eye-level view, vanishing point, detailed background, "
        "soft lighting, soft colors, cinematic lighting"
    )
    neg = (
        "lowres, worst quality, low quality, normal quality, blurry, "
        "people, person, character, humans, crowd, "
        "bad perspective, distorted architecture, warped furniture, "
        "text, watermark, username, signature, "
        "realistic, photorealistic, 3d, 3d render"
    )
    return pos, neg


def _build_sprite_prompts(
    character_name: str,
    character_desc: str,
    emotion: str,
) -> tuple[str, str]:
    """Build Danbooru-style positive/negative prompts for a character sprite."""
    emotion_tags = {
        "neutral": "neutral expression, calm, looking at viewer",
        "happy": "smiling, happy, bright eyes, open mouth",
        "sad": "sad, teary eyes, downturned mouth",
        "shy": "embarrassed, blush, looking away",
        "angry": "angry, furrowed brows, glare",
        "surprised": "surprised, wide eyes, open mouth",
        "crying": "crying, tears, teary eyes, crying, sad",
        "embarrassed": "embarrassed, deep blush, nervous, looking away",
    }
    emotion_text = emotion_tags.get(emotion, f"{emotion}, looking at viewer")

    pos = (
        "masterpiece, best quality, very aesthetic, absurdres, "
        "galgame style, visual novel art, anime illustration, game cg, "
        "clean lineart, smooth shading, vibrant colors, "
        f"1girl, solo, {character_desc}, "
        f"{emotion_text}, "
        "cowboy shot, centered composition, "
        "simple background, pure white background, solid background"
    )
    neg = (
        "lowres, worst quality, low quality, normal quality, "
        "bad anatomy, bad hands, extra fingers, missing fingers, "
        "blurry, text, watermark, signature, username, "
        "realistic, photorealistic, 3d, 3d render, "
        "cluttered background, scenery, noise, "
        "multiple girls, multiple views, bad proportions"
    )
    return pos, neg


# ---------------------------------------------------------------------------
# Image post-processing (Steps 36-42)
# ---------------------------------------------------------------------------


def _img_from_bytes(data: bytes) -> Image.Image:
    """Load a PIL Image from raw bytes."""
    return Image.open(BytesIO(data))


def _save_png_alpha(data: bytes, dest: Path) -> None:
    """Save image as RGBA PNG (ensures alpha channel even if source is RGB)."""
    img = _img_from_bytes(data)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    img.save(dest, "PNG")


def _save_webp(data: bytes, dest: Path, quality: int = 85) -> None:
    """Save image as WebP with the given quality."""
    img = _img_from_bytes(data)
    # RGBA → RGB for WebP (lossy) or keep RGBA for lossless
    if img.mode == "RGBA":
        img = img.convert("RGBA")
    img.save(dest, "WEBP", quality=quality, lossless=False)


def _resize_image(
    data: bytes, target_height: int | None = None, target_width: int | None = None
) -> bytes:
    """Resize image to target dimensions, preserving aspect ratio.

    Only one of target_height/target_width needs to be set; the other
    is computed to preserve aspect ratio.
    """
    img = _img_from_bytes(data)
    w, h = img.size

    if target_height and not target_width:
        ratio = target_height / h
        new_size = (int(w * ratio), target_height)
    elif target_width and not target_height:
        ratio = target_width / w
        new_size = (target_width, int(h * ratio))
    elif target_height and target_width:
        new_size = (target_width, target_height)
    else:
        return data  # no resize requested

    img = img.resize(new_size, Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG" if img.mode == "RGBA" else "JPEG", quality=95)
    return buf.getvalue()


def _process_sprite_output(
    img_data: bytes,
    source_filename: str,
    character_name: str,
    emotion: str,
    target_height: int | None = None,
) -> dict[str, str | None]:
    """Post-process a generated character sprite.

    Returns paths/URLs for the alpha PNG and WebP preview.
    """
    generated_dir = _generated_dir()
    generated_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(source_filename).suffix or ".png"
    base = f"{character_name}_{emotion}_{uuid.uuid4().hex[:8]}"

    # 1. Save PNG with alpha
    png_name = f"{base}.png"
    png_dest = generated_dir / png_name
    _save_png_alpha(img_data, png_dest)
    png_url = f"/api/assets/{png_name}"

    # 2. Save WebP preview
    webp_url = None
    if GENERATE_WEBP:
        webp_name = f"{base}.webp"
        webp_dest = generated_dir / webp_name
        _save_webp(img_data, webp_dest)
        webp_url = f"/api/assets/{webp_name}"

    # 3. Optionally resize for game engine
    if target_height:
        resized_data = _resize_image(img_data, target_height=target_height)
        resized_name = f"{base}_game.png"
        resized_dest = generated_dir / resized_name
        _save_png_alpha(resized_data, resized_dest)

    return {"png_url": png_url, "webp_url": webp_url}


def _process_background_output(
    img_data: bytes,
    source_filename: str,
    scene_desc: str,
    target_width: int | None = None,
    target_height: int | None = None,
) -> dict[str, str | None]:
    """Post-process a generated background.

    Returns paths/URLs for the full-res image and WebP preview.
    """
    generated_dir = _generated_dir()
    generated_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(source_filename).suffix or ".png"
    desc_tag = scene_desc.replace(" ", "_")[:20] if scene_desc else "bg"
    base = f"bg_{desc_tag}_{uuid.uuid4().hex[:8]}"

    # 1. Save original
    orig_name = f"{base}{ext}"
    orig_dest = generated_dir / orig_name
    orig_dest.write_bytes(img_data)
    orig_url = f"/api/assets/{orig_name}"

    # 2. WebP preview
    webp_url = None
    if GENERATE_WEBP:
        webp_name = f"{base}.webp"
        webp_dest = generated_dir / webp_name
        _save_webp(img_data, webp_dest)
        webp_url = f"/api/assets/{webp_name}"

    # 3. Resize for game engine
    if target_width or target_height:
        resized_data = _resize_image(
            img_data, target_width=target_width, target_height=target_height
        )
        resized_name = f"{base}_game.png"
        resized_dest = generated_dir / resized_name
        resized_dest.write_bytes(resized_data)

    return {"original_url": orig_url, "webp_url": webp_url}


# ---------------------------------------------------------------------------
# Webhook callback
# ---------------------------------------------------------------------------


def _trigger_webhook(event: str, payload: dict[str, Any]) -> None:
    """Fire a webhook callback after asset generation completes."""
    if not WEBHOOK_URL:
        return
    try:
        httpx.post(
            WEBHOOK_URL,
            json={"event": event, "timestamp": datetime.now(timezone.utc).isoformat(), **payload},
            timeout=10,
        )
    except Exception:
        pass  # fire-and-forget


# ---------------------------------------------------------------------------
# Background Generation
# ---------------------------------------------------------------------------


def generate_background(
    description: str,
    width: int = 1344,
    height: int = 768,
    style_preset: str = "anime_visual_novel",
    lora_name: str = "",
    lora_weight: float = 0.8,
    scene_index: int = 0,
    job_id: str = "",
) -> dict[str, Any]:
    """Generate a background image using Animagine XL with Danbooru-style tags.

    Returns a dict with keys: status, asset_url, webp_url, prompt_id, error.
    """
    with _semaphore:
        try:
            pos_prompt, neg_prompt = _build_background_prompts(description)
            workflow = _select_background_workflow()

            # Inject LoRA if specified
            if lora_name:
                workflow = _inject_lora(workflow, lora_name, lora_weight)

            _set_node_text(workflow, "6", pos_prompt)
            _set_node_text(workflow, "7", neg_prompt)
            _set_node_size(workflow, "5", width, height)
            _set_node_int(workflow, "3", "seed", random.randint(0, 2_147_483_647))
            _set_node_int(workflow, "3", "steps", SAMPLER_STEPS)
            _set_node_float(workflow, "3", "cfg", SAMPLER_CFG)
            _set_node_str(workflow, "3", "sampler_name", SAMPLER_NAME)
            _set_node_str(workflow, "3", "scheduler", SAMPLER_SCHEDULER)
            _set_node_str(workflow, "4", "ckpt_name", COMFYUI_CHECKPOINT)

            prompt_id = _queue_prompt(workflow)
            result = _poll_image(prompt_id, timeout=PROMPT_TIMEOUT)
            if result is None:
                return {"status": "error", "error": "Image generation timed out"}

            img_data, filename = result
            processed = _process_background_output(img_data, filename, description)

            # Webhook callback
            _trigger_webhook("background_generated", {
                "job_id": job_id,
                "description": description,
                "asset_url": processed.get("original_url", ""),
                "webp_url": processed.get("webp_url", ""),
            })

            return {
                "status": "ok",
                "asset_url": processed.get("original_url", ""),
                "webp_url": processed.get("webp_url", ""),
                "prompt_id": prompt_id,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Character Sprite Generation
# ---------------------------------------------------------------------------


def generate_character_sprite(
    character_name: str,
    character_desc: str,
    emotion: str = "neutral",
    style_preset: str = "anime_visual_novel",
    lora_name: str = "",
    lora_weight: float = 0.8,
    scene_index: int = 0,
    shot_index: int = 0,
    variation_index: int = 0,
    target_height: int | None = None,
    job_id: str = "",
    # --- Incremental mode parameters ---
    base_asset_id: str | None = None,
    base_image_path: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Generate a character sprite with a specific emotion using Animagine XL.

    Seed is derived from character_name + emotion + scene_index to ensure
    consistent character appearance across expression/pose variations.

    Returns a dict with keys: status, asset_url, webp_url, prompt_id, error.
    """
    with _semaphore:
        try:
            pos_prompt, neg_prompt = _build_sprite_prompts(
                character_name, character_desc, emotion
            )

            if base_asset_id and base_image_path:
                # ── Incremental mode: load cached base + FaceDetailer only ──
                workflow = _select_inpaint_workflow()
                if lora_name:
                    workflow = _inject_lora(workflow, lora_name, lora_weight)

                # Upload cached base image to ComfyUI
                try:
                    base_img_filename = _upload_image_to_comfyui(base_image_path)
                except (httpx.HTTPError, FileNotFoundError) as e:
                    print(f"[comfyui] Base image upload failed, falling back to full gen: {e}")
                    base_asset_id = None  # trigger fallback below

                if base_asset_id is not None:
                    _set_node_str(workflow, "13", "image", base_img_filename)
                    # Emotion-adaptive denoise
                    denoise = _INPAINT_DENOISE_MAP.get(emotion, _INPAINT_DENOISE_DEFAULT)
                    _set_node_float(workflow, "10", "denoise", denoise)
                    _set_node_str(workflow, "4", "ckpt_name", COMFYUI_CHECKPOINT)

            if base_asset_id is None:
                # ── Full generation mode (existing behavior) ──
                workflow = _select_character_workflow()
                if lora_name:
                    workflow = _inject_lora(workflow, lora_name, lora_weight)

                _set_node_size(workflow, "5", RESOLUTION_CHARACTER[0], RESOLUTION_CHARACTER[1])
                _set_node_int(
                    workflow, "3", "seed",
                    _character_seed(character_name, emotion, scene_index, shot_index, variation_index),
                )
                _set_node_int(workflow, "3", "steps", SAMPLER_STEPS)
                _set_node_float(workflow, "3", "cfg", SAMPLER_CFG)
                _set_node_str(workflow, "3", "sampler_name", SAMPLER_NAME)
                _set_node_str(workflow, "3", "scheduler", SAMPLER_SCHEDULER)
                _set_node_str(workflow, "4", "ckpt_name", COMFYUI_CHECKPOINT)

            # Common: inject prompts
            _set_node_text(workflow, "6", pos_prompt)
            _set_node_text(workflow, "7", neg_prompt)

            prompt_id = _queue_prompt(workflow)
            # Only fetch from node 12 (Rembg output) — node 14 is also a SaveImage
            # but outputs the pre-Rembg FaceDetailer result (with background).
            result = _poll_image(prompt_id, timeout=PROMPT_TIMEOUT, node_ids={"12"})
            if result is None:
                return {"status": "error", "error": "Image generation timed out"}

            img_data, filename = result
            processed = _process_sprite_output(
                img_data, filename, character_name, emotion,
                target_height=target_height,
            )

            # ── Cache base image (full gen only) ──
            cached_base_id: str | None = None
            if base_asset_id is None and idempotency_key:
                base_img_data = _fetch_image_from_history(prompt_id, node_ids={"14"})
                if base_img_data is not None:
                    _cache_base_image(base_img_data[0], idempotency_key)
                    cached_base_id = idempotency_key

            # Webhook callback
            _trigger_webhook("sprite_generated", {
                "job_id": job_id,
                "character_name": character_name,
                "emotion": emotion,
                "asset_url": processed.get("png_url", ""),
                "webp_url": processed.get("webp_url", ""),
            })

            return {
                "status": "ok",
                "asset_url": processed.get("png_url", ""),
                "webp_url": processed.get("webp_url", ""),
                "prompt_id": prompt_id,
                "base_asset_id": cached_base_id or base_asset_id,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Async generation (WebSocket monitoring) — Steps 21-28
# ---------------------------------------------------------------------------


async def generate_background_async(
    description: str,
    width: int = 1344,
    height: int = 768,
    style_preset: str = "anime_visual_novel",
    lora_name: str = "",
    lora_weight: float = 0.8,
    scene_index: int = 0,
    on_progress: Callable[[float], None] | None = None,
    job_id: str = "",
) -> dict[str, Any]:
    """Async background generation with WebSocket progress monitoring."""
    try:
        pos_prompt, neg_prompt = _build_background_prompts(description)
        workflow = _select_background_workflow()
        if lora_name:
            workflow = _inject_lora(workflow, lora_name, lora_weight)

        _set_node_text(workflow, "6", pos_prompt)
        _set_node_text(workflow, "7", neg_prompt)
        _set_node_size(workflow, "5", width, height)
        _set_node_int(workflow, "3", "seed", random.randint(0, 2_147_483_647))
        _set_node_int(workflow, "3", "steps", SAMPLER_STEPS)
        _set_node_float(workflow, "3", "cfg", SAMPLER_CFG)
        _set_node_str(workflow, "3", "sampler_name", SAMPLER_NAME)
        _set_node_str(workflow, "3", "scheduler", SAMPLER_SCHEDULER)
        _set_node_str(workflow, "4", "ckpt_name", COMFYUI_CHECKPOINT)

        prompt_id = _queue_prompt(workflow)
        client_id = uuid.uuid4().hex[:12]

        done = await _ws_wait_for_execution(prompt_id, client_id, on_progress)
        if not done:
            return {"status": "error", "error": "Image generation timed out"}

        result = _fetch_image_from_history(prompt_id)
        if result is None:
            return {"status": "error", "error": "Failed to fetch image after execution"}

        img_data, filename = result
        processed = _process_background_output(img_data, filename, description)

        _trigger_webhook("background_generated", {
            "job_id": job_id,
            "description": description,
            "asset_url": processed.get("original_url", ""),
        })

        return {
            "status": "ok",
            "asset_url": processed.get("original_url", ""),
            "webp_url": processed.get("webp_url", ""),
            "prompt_id": prompt_id,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def generate_character_sprite_async(
    character_name: str,
    character_desc: str,
    emotion: str = "neutral",
    style_preset: str = "anime_visual_novel",
    lora_name: str = "",
    lora_weight: float = 0.8,
    scene_index: int = 0,
    shot_index: int = 0,
    variation_index: int = 0,
    target_height: int | None = None,
    on_progress: Callable[[float], None] | None = None,
    job_id: str = "",
    # --- Incremental mode parameters ---
    base_asset_id: str | None = None,
    base_image_path: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Async character sprite generation with WebSocket progress monitoring."""
    try:
        pos_prompt, neg_prompt = _build_sprite_prompts(
            character_name, character_desc, emotion
        )

        if base_asset_id and base_image_path:
            # ── Incremental mode: load cached base + FaceDetailer only ──
            workflow = _select_inpaint_workflow()
            if lora_name:
                workflow = _inject_lora(workflow, lora_name, lora_weight)

            # Upload cached base image to ComfyUI
            try:
                base_img_filename = _upload_image_to_comfyui(base_image_path)
            except (httpx.HTTPError, FileNotFoundError) as e:
                print(f"[comfyui] Base image upload failed, falling back to full gen: {e}")
                base_asset_id = None  # trigger fallback below

            if base_asset_id is not None:
                _set_node_str(workflow, "13", "image", base_img_filename)
                # Emotion-adaptive denoise
                denoise = _INPAINT_DENOISE_MAP.get(emotion, _INPAINT_DENOISE_DEFAULT)
                _set_node_float(workflow, "10", "denoise", denoise)
                _set_node_str(workflow, "4", "ckpt_name", COMFYUI_CHECKPOINT)

        if base_asset_id is None:
            # ── Full generation mode (existing behavior) ──
            workflow = _select_character_workflow()
            if lora_name:
                workflow = _inject_lora(workflow, lora_name, lora_weight)

            _set_node_size(workflow, "5", RESOLUTION_CHARACTER[0], RESOLUTION_CHARACTER[1])
            _set_node_int(
                workflow, "3", "seed",
                _character_seed(character_name, emotion, scene_index, shot_index, variation_index),
            )
            _set_node_int(workflow, "3", "steps", SAMPLER_STEPS)
            _set_node_float(workflow, "3", "cfg", SAMPLER_CFG)
            _set_node_str(workflow, "3", "sampler_name", SAMPLER_NAME)
            _set_node_str(workflow, "3", "scheduler", SAMPLER_SCHEDULER)
            _set_node_str(workflow, "4", "ckpt_name", COMFYUI_CHECKPOINT)

        # Common: inject prompts
        _set_node_text(workflow, "6", pos_prompt)
        _set_node_text(workflow, "7", neg_prompt)

        prompt_id = _queue_prompt(workflow)
        client_id = uuid.uuid4().hex[:12]

        done = await _ws_wait_for_execution(prompt_id, client_id, on_progress)
        if not done:
            return {"status": "error", "error": "Image generation timed out"}

        # Only fetch from node 12 (Rembg output) — node 14 is also a SaveImage
        # but outputs the pre-Rembg FaceDetailer result (with background).
        result = _fetch_image_from_history(prompt_id, node_ids={"12"})
        if result is None:
            return {"status": "error", "error": "Failed to fetch image after execution"}

        img_data, filename = result
        processed = _process_sprite_output(
            img_data, filename, character_name, emotion,
            target_height=target_height,
        )

        # ── Cache base image (full gen only) ──
        cached_base_id: str | None = None
        if base_asset_id is None and idempotency_key:
            base_img_data = _fetch_image_from_history(prompt_id, node_ids={"14"})
            if base_img_data is not None:
                _cache_base_image(base_img_data[0], idempotency_key)
                cached_base_id = idempotency_key

        _trigger_webhook("sprite_generated", {
            "job_id": job_id,
            "character_name": character_name,
            "emotion": emotion,
            "asset_url": processed.get("png_url", ""),
            "webp_url": processed.get("webp_url", ""),
        })

        return {
            "status": "ok",
            "asset_url": processed.get("png_url", ""),
            "webp_url": processed.get("webp_url", ""),
            "prompt_id": prompt_id,
            "base_asset_id": cached_base_id or base_asset_id,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Ren'Py export helpers (Steps 32-35)
# ---------------------------------------------------------------------------


def build_renpy_asset_declarations(
    project: AdaptationProject,
) -> str:
    """Generate a ``generated_assets.rpy`` script with image declarations.

    Uses project.characters → asset_ids and project.scenes → background_id
    to build Ren'Py ``image`` statements for sprites and backgrounds.
    """
    lines = [
        "# This file is auto-generated — do not edit manually.",
        f"# Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "init python:",
        "    import renpy",
        "",
    ]

    # Character image declarations
    for cid, char in project.characters.items():
        for emotion, asset_id in char.asset_ids.items():
            if asset_id in project.asset_resources:
                url = project.asset_resources[asset_id].url
                tag = f"{_sanitize_label(char.name)}_{emotion.value}"
                lines.append(f"image {tag} = \"{url}\"")
        lines.append("")

    # Background declarations
    for sid, scene in project.scenes.items():
        if scene.background_id and scene.background_id in project.asset_resources:
            url = project.asset_resources[scene.background_id].url
            bg_filename = url.rsplit("/", 1)[-1].rsplit(".", 1)[0] if url else ""
            if bg_filename:
                lines.append(f"image bg {bg_filename} = \"{url}\"")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Health check — ComfyUI node dependency verification
# ---------------------------------------------------------------------------

_REQUIRED_NODE_TYPES = {
    "FaceDetailer": "ComfyUI-Impact-Pack",
    "ImageRembg": "ComfyUI-rmbg (or WAS Node Suite)",
}

_OPTIONAL_NODE_TYPES = {
    "LoraLoader": "built-in ComfyUI (often needs separate models)",
}


def check_comfyui_health() -> dict[str, Any]:
    """Verify ComfyUI is reachable and all required custom nodes are installed.

    Checks in order:
        1. Server reachability (GET /system_stats)
        2. Default checkpoint exists
        3. Required custom node types (FaceDetailer, Rembg) registered
        4. WebSocket connectivity
        5. Optional node types (LoraLoader)
        6. LoRA directory (if configured)

    Returns a dict with ``status`` ("ok" | "degraded" | "error") and a
    ``checks`` list describing each check result.
    """
    checks: list[dict[str, Any]] = []
    all_ok = True

    # --- 1. Server reachability ---
    server_ok = False
    try:
        resp = httpx.get(f"{COMFYUI_BASE}/system_stats", timeout=10)
        if resp.status_code == 200:
            server_ok = True
            system_info = resp.json()
            checks.append({
                "name": "server_reachable",
                "status": "ok",
                "detail": f"ComfyUI {system_info.get('system', {}).get('comfyui_version', 'unknown')}",
            })
        else:
            checks.append({
                "name": "server_reachable",
                "status": "error",
                "detail": f"HTTP {resp.status_code}",
            })
            all_ok = False
    except Exception as e:
        checks.append({
            "name": "server_reachable",
            "status": "error",
            "detail": f"Connection failed: {e}",
        })
        all_ok = False

    # --- 2. Default checkpoint ---
    if server_ok:
        try:
            ckpt_resp = httpx.get(
                f"{COMFYUI_BASE}/object_info/CheckpointLoaderSimple",
                timeout=10,
            )
            checkpoint_found = False
            if ckpt_resp.status_code == 200:
                ckpt_info = ckpt_resp.json()
                available = (
                    ckpt_info.get("CheckpointLoaderSimple", {})
                    .get("input", {}).get("required", {})
                    .get("ckpt_name", [None])[0]
                )
                if isinstance(available, list):
                    checkpoint_found = COMFYUI_CHECKPOINT in available
            checks.append({
                "name": "checkpoint_exists",
                "status": "ok" if checkpoint_found else "warning",
                "detail": (
                    f"{COMFYUI_CHECKPOINT} {'found' if checkpoint_found else 'not found in available checkpoints'}"
                ),
            })
            if not checkpoint_found:
                all_ok = False
        except Exception as e:
            checks.append({
                "name": "checkpoint_exists",
                "status": "warning",
                "detail": f"Could not list checkpoints: {e}",
            })

    # --- 3. Required custom nodes ---
    for node_type, source in _REQUIRED_NODE_TYPES.items():
        if not server_ok:
            checks.append({
                "name": f"node_{node_type}",
                "status": "skipped",
                "detail": "Server unreachable, cannot verify",
            })
            continue
        try:
            resp = httpx.get(f"{COMFYUI_BASE}/object_info/{node_type}", timeout=10)
            if resp.status_code == 200:
                checks.append({
                    "name": f"node_{node_type}",
                    "status": "ok",
                    "detail": f"Registered (from {source})",
                })
            else:
                checks.append({
                    "name": f"node_{node_type}",
                    "status": "error",
                    "detail": f"NOT registered — install {source}",
                })
                all_ok = False
        except Exception as e:
            checks.append({
                "name": f"node_{node_type}",
                "status": "error",
                "detail": f"Check failed: {e}",
            })
            all_ok = False

    # --- 4. WebSocket connectivity ---
    if websockets is not None and server_ok:
        try:
            import asyncio

            async def _ws_ping() -> bool:
                try:
                    async with websockets.connect(
                        COMFYUI_WS, max_size=2**23, ping_interval=10, close_timeout=5
                    ):
                        return True
                except Exception:
                    return False

            ws_ok = asyncio.run(_ws_ping())
            checks.append({
                "name": "websocket_connect",
                "status": "ok" if ws_ok else "error",
                "detail": "WebSocket connected" if ws_ok else f"Could not connect to {COMFYUI_WS}",
            })
            if not ws_ok:
                all_ok = False
        except Exception as e:
            checks.append({
                "name": "websocket_connect",
                "status": "error",
                "detail": f"WebSocket check failed: {e}",
            })
            all_ok = False
    else:
        checks.append({
            "name": "websocket_connect",
            "status": "ok" if not server_ok else "warning",
            "detail": "websockets library not installed; will fall back to polling",
        })

    # --- 5. Optional nodes (LoRA) ---
    if server_ok:
        try:
            resp = httpx.get(f"{COMFYUI_BASE}/object_info/LoraLoader", timeout=10)
            lora_ok = resp.status_code == 200
            checks.append({
                "name": "node_LoraLoader",
                "status": "ok" if lora_ok else "warning",
                "detail": "Registered" if lora_ok else "Not registered (LoRA disabled)",
            })
        except Exception:
            checks.append({
                "name": "node_LoraLoader",
                "status": "warning",
                "detail": "Could not verify LoraLoader node",
            })

    # --- 6. LoRA directory ---
    if LORA_DIR:
        lora_path = Path(LORA_DIR)
        if lora_path.is_dir():
            lora_files = list(lora_path.glob("*.safetensors"))
            checks.append({
                "name": "lora_directory",
                "status": "ok",
                "detail": f"{len(lora_files)} LoRA file(s) found in {LORA_DIR}",
            })
        else:
            checks.append({
                "name": "lora_directory",
                "status": "warning",
                "detail": f"LORA_DIR={LORA_DIR} does not exist or is not a directory",
            })

    # --- Summary ---
    if all_ok:
        status = "ok"
    elif any(c["status"] == "error" for c in checks):
        status = "error"
    else:
        status = "degraded"

    return {"status": status, "checks": checks}


# ---------------------------------------------------------------------------
# Ren'Py export (Steps 32-35)
# ---------------------------------------------------------------------------


def export_renpy_assets(
    export_path: str | Path,
    project: AdaptationProject,
) -> str | None:
    """Write generated asset declarations to an organized Ren'Py export directory.

    Directory structure::

        export_path/
          images/
            backgrounds/
            sprites/
            webp/
          scripts/
            generated_assets.rpy
    """
    base = Path(export_path)
    bg_dir = base / "images" / "backgrounds"
    sprite_dir = base / "images" / "sprites"
    webp_dir = base / "images" / "webp"
    scripts_dir = base / "scripts"

    for d in [bg_dir, sprite_dir, webp_dir, scripts_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Write asset declarations script
    script = build_renpy_asset_declarations(project)
    script_path = scripts_dir / "generated_assets.rpy"
    script_path.write_text(script, encoding="utf-8")

    return str(script_path)


# ---------------------------------------------------------------------------
# Export packaging — Phase 6: Ren'Py & Web zip generation
# ---------------------------------------------------------------------------


def _copy_image_asset(asset_url: str, dest_dir: Path) -> Path | None:
    """Resolve an asset URL to a local file and copy it to dest_dir.

    Asset URLs are typically ``/api/assets/foo.png`` — the local file lives
    under ``_generated_dir()``. Returns the destination path on success, or
    *None* if the source doesn't exist.
    """
    if not asset_url:
        return None
    filename = asset_url.replace("/api/assets/", "").lstrip("/")
    if not filename:
        return None
    src = _generated_dir() / filename
    if not src.exists():
        return None
    dest = dest_dir / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


# ── Ren'Py skeleton files ──────────────────────────────────────────────────


def _build_renpy_skeleton(export_dir: Path, project_title: str) -> None:
    """Write minimal but runnable Ren'Py project files (*options.rpy*,
    *screens.rpy*, *gui.rpy*) into *export_dir/game/*."""
    game_dir = export_dir / "game"

    # options.rpy
    safe_name = project_title.replace('"', "'")
    (game_dir / "options.rpy").write_text(
        f'''# Minimal Ren'Py configuration -- auto-generated
define config.name = "{safe_name}"
define config.version = "1.0"
define gui.show_name = True
define config.save_directory = "{safe_name.lower().replace(" ", "_")}_saves"
define config.has_voice = False
define config.has_music = True
define config.has_sound = True
define config.main_menu_music = None
''', encoding="utf-8")

    # screens.rpy
    (game_dir / "screens.rpy").write_text(
        '''# Minimal Ren'Py screens -- auto-generated
screen say(who, what):
    style_prefix "say"
    window:
        id "window"
        if who is not None:
            window:
                id "namebox"
                style "namebox"
                text who id "who"
        text what id "what"
''', encoding="utf-8")

    # gui.rpy
    (game_dir / "gui.rpy").write_text(
        '''# Minimal GUI settings -- auto-generated
define gui.text_color = "#ffffff"
define gui.name_text_color = "#ffcccc"
define gui.text_size = 22
define gui.name_text_size = 18
define gui.dialogue_xpos = 0.5
define gui.dialogue_ypos = 0.75
define gui.dialogue_width = 0.8
define gui.name_xpos = 0.5
define gui.name_ypos = 0.73
define gui.namebox_width = 0.25
define gui.choice_button_width = 0.6
define gui.choice_button_height = 36
''', encoding="utf-8")


def _sanitize_label(name: str) -> str:
    """Convert arbitrary text to a valid ASCII Ren'Py label."""
    safe = "".join(c if c.isalnum() else "_" for c in name).strip("_")
    return safe if safe else "scene"


def _renpy_escape(text: str) -> str:
    """Escape Ren'Py string content: double any embedded quotes."""
    return text.replace('"', '""')


def _build_node_graph(
    project: AdaptationProject,
    scene: Scene,
) -> list[str]:
    """Generate Ren'Py label blocks for every node in a scene.

    Each node becomes a unique ``label`` so branching/jumps target correctly.
    Returns a list of Ren'Py source lines.
    """
    lines: list[str] = []
    lab = _sanitize_label
    esc = _renpy_escape

    first_nid = scene.first_node_id()
    if not first_nid:
        return lines

    # Walk the node chain, emitting labels in play order
    visited: set[str] = set()
    nid: str | None = first_nid
    while nid and nid not in visited:
        visited.add(nid)
        node = scene.nodes.get(nid)
        if node is None:
            break

        scene_label = f"scene_{scene.scene_id}_{nid}"
        nid = None  # will be set by each branch below

        match node:
            case DialogueNode():
                char = project.characters.get(node.character_id)
                color = f' color="{char.color}"' if char and char.color else ""
                char_name = char.name if char else node.character_id
                emotion_tag = f" (emotion: {node.emotion.value})" if node.emotion != Emotion.neutral else ""
                lines.append(f"")
                lines.append(f"label {scene_label}:")
                lines.append(f"    # {char_name} — {node.emotion.value}")
                lines.append(f'    {lab(char_name)}{emotion_tag} "{esc(node.text)}"')
                nid = node.next_node_id

            case NarrationNode():
                lines.append(f"")
                lines.append(f"label {scene_label}:")
                lines.append(f'    "{esc(node.text)}"')
                nid = node.next_node_id

            case ChoiceNode() as cn:
                lines.append(f"")
                lines.append(f"label {scene_label}:")
                if cn.text:
                    lines.append(f'    "{esc(cn.text)}"')
                lines.append("    menu:")
                for opt in cn.options:
                    opt_lab = f"{scene_label}_opt_{opt.option_id}"
                    cond = f" if {esc(opt.condition)}" if opt.condition else ""
                    lines.append(f'        "{esc(opt.text)}"{cond}:')
                    lines.append(f"            jump {_sanitize_label(f'scene_{scene.scene_id}_{opt.next_node_id}')}")
                # After choices, fall through to return
                lines.append("    pass")

            case SceneTransitionNode() as stn:
                target_lab = _sanitize_label(f"scene_{stn.target_scene_id}")
                lines.append(f"")
                lines.append(f"label {scene_label}:")
                lines.append(f"    # Transition to scene: {stn.target_scene_id}")
                lines.append(f"    jump {target_lab}")

            case BranchNode() as bn:
                lines.append(f"")
                lines.append(f"label {scene_label}:")
                lines.append(f"    if {esc(bn.condition)}:")
                lines.append(f"        jump {lab(f'scene_{scene.scene_id}_{bn.true_next}')}")
                lines.append("    else:")
                lines.append(f"        jump {lab(f'scene_{scene.scene_id}_{bn.false_next}')}")

            case EndingNode() as en:
                lines.append(f"")
                lines.append(f"label {scene_label}:")
                if en.epilogue:
                    lines.append(f'    "{esc(en.epilogue)}"')
                lines.append(f"    # {en.ending_type} ending")
                lines.append("    return")

    return lines


def _build_renpy_script(project: AdaptationProject) -> str:
    """Generate a *script.rpy* with complete story flow from AdaptationProject.

    Produces real character definitions, scene backgrounds, labelled nodes
    for dialogue/narration/choice/branch/transition/ending, and proper
    ``menu`` blocks for player choices.
    """
    lines: list[str] = [
        "# Auto-generated story script — do not edit manually",
        f'# {datetime.now(timezone.utc).isoformat()}',
        "",
    ]

    # Character definitions
    for cid, char in project.characters.items():
        color = f', color="{char.color}"' if char.color else ""
        lines.append(f'define {_sanitize_label(char.name)} = Character("{_renpy_escape(char.name)}"{color})')
    if project.characters:
        lines.append("")
    lines.append("define narrator = Character(None, kind=nvl)")
    lines.append("")

    # Entry point
    lines.append(f"label start:")
    first_scene_lab = _sanitize_label(f"scene_{project.start_scene_id}")
    lines.append(f"    jump {first_scene_lab}")
    lines.append("")

    # Scene-by-scene node graphs
    for sid, scene in project.scenes.items():
        scene_lab = _sanitize_label(f"scene_{sid}")
        lines.append("#" + "=" * 70)
        lines.append(f"# Scene: {scene.title} ({sid})")
        lines.append("#" + "=" * 70)
        lines.append(f"")
        lines.append(f"label {scene_lab}:")
        if scene.background_id and scene.background_id in project.asset_resources:
            bg_res = project.asset_resources[scene.background_id]
            bg_filename = bg_res.url.rsplit("/", 1)[-1] if bg_res.url else ""
            if bg_filename:
                lines.append(f"    scene bg {bg_filename.rsplit('.', 1)[0]}")
        lines.append(f"    # Scene description: {_renpy_escape(scene.description)}")
        lines.append("")
        # Jump to first node label (generated in _build_node_graph)
        first_nid = scene.first_node_id()
        if first_nid:
            lines.append(f"    jump {_sanitize_label(f'scene_{sid}_{first_nid}')}")

        lines.append("")
        # Emit node blocks
        node_lines = _build_node_graph(project, scene)
        lines.extend(node_lines)
        lines.append("")

    lines.append("")
    lines.append("# === End === ")
    lines.append("return")
    return "\n".join(lines)


# ── Ren'Py zip orchestrator ────────────────────────────────────────────────


def create_renpy_zip(
    export_id: str,
    project: AdaptationProject,
) -> Path:
    """Create a complete, runnable Ren'Py project zip file from project data.

    Returns the path to the generated *<title>_renpy.zip*.
    """
    export_dir = _export_dir()
    export_dir.mkdir(parents=True, exist_ok=True)

    staging = export_dir / f"staging_{export_id}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    game_dir = staging / "game"
    game_dir.mkdir()

    bg_img_dir = game_dir / "images" / "backgrounds"
    sprite_img_dir = game_dir / "images" / "sprites"
    audio_dir = game_dir / "audio"
    for d in [bg_img_dir, sprite_img_dir, audio_dir]:
        d.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Write Ren'Py skeleton files
        _build_renpy_skeleton(staging, project.title)

        # 2. Write generated_assets.rpy (image declarations)
        asset_script = build_renpy_asset_declarations(project)
        (game_dir / "generated_assets.rpy").write_text(asset_script, encoding="utf-8")

        # 3. Write script.rpy (story flow)
        story_script = _build_renpy_script(project)
        (game_dir / "script.rpy").write_text(story_script, encoding="utf-8")

        # 4. Copy background images
        for scene in project.scenes.values():
            if scene.background_id and scene.background_id in project.asset_resources:
                url = project.asset_resources[scene.background_id].url
                if url:
                    _copy_image_asset(url, bg_img_dir)

        # 5. Copy sprite images
        for char in project.characters.values():
            for asset_id in char.asset_ids.values():
                if asset_id in project.asset_resources:
                    url = project.asset_resources[asset_id].url
                    if url:
                        _copy_image_asset(url, sprite_img_dir)

        # 6. Create the zip
        safe_title = project.title.replace(" ", "_").replace("/", "_") or "project"
        zip_name = f"{safe_title}_renpy.zip"
        zip_path = export_dir / zip_name
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in staging.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(staging)
                    zf.write(file, arcname)

        return zip_path
    finally:
        if staging.exists():
            shutil.rmtree(staging)


# ── Web player generators ──────────────────────────────────────────────────


def _build_web_index_html(project: AdaptationProject) -> str:
    """Generate a self-contained *index.html* for the standalone web player.

    Story data is embedded inline as JSON in a ``<script id="story-data">``
    tag so the player works from ``file://`` protocol without fetch().
    """
    story_json = json.dumps(project.model_dump(), ensure_ascii=False)
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_renpy_escape(project.title)}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#000;color:#fff;font-family:"Microsoft YaHei","Noto Sans SC",sans-serif;overflow:hidden}}
#game{{position:relative;width:100vw;height:100vh}}
#bg{{position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover}}
#sprite{{position:absolute;bottom:0;left:50%;transform:translateX(-50%);max-height:70vh}}
#dialogue{{position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(0,0,0,0.9) 30%);padding:120px 80px 40px}}
#namebox{{display:inline-block;background:rgba(255,180,200,0.9);color:#333;padding:4px 20px;border-radius:4px 4px 0 0;font-weight:bold;margin-bottom:0}}
#text{{background:rgba(20,20,40,0.95);padding:16px 24px;border-radius:0 8px 8px 8px;min-height:60px;line-height:1.6;font-size:18px}}
#choices{{display:flex;flex-direction:column;gap:8px;margin-top:12px}}
.choice-btn{{background:rgba(255,180,200,0.15);border:1px solid rgba(255,180,200,0.4);color:#fff;padding:10px 20px;border-radius:6px;cursor:pointer;font-size:16px;text-align:left;transition:all 0.2s}}
.choice-btn:hover{{background:rgba(255,180,200,0.3);border-color:rgba(255,180,200,0.8)}}
.controls{{position:absolute;top:12px;right:16px;display:flex;gap:8px}}
.ctrl-btn{{background:rgba(255,255,255,0.1);border:none;color:#aaa;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:14px}}
.ctrl-btn:hover{{background:rgba(255,255,255,0.2);color:#fff}}
</style>
</head>
<body>
<script id="story-data" type="application/json">{story_json}</script>
<div id="game">
  <img id="bg" src="" alt="">
  <img id="sprite" src="" alt="" style="display:none">
  <div id="dialogue">
    <div id="namebox" style="display:none"></div>
    <div id="text"></div>
    <div id="choices"></div>
  </div>
  <div class="controls">
    <button class="ctrl-btn" onclick="restartScene()">重来</button>
  </div>
</div>
<script src="player.js"></script>
</body>
</html>'''


def _build_web_player_js() -> str:
    """Generate a standalone *player.js* that renders the game.

    Reads story data from ``document.getElementById("story-data").textContent``
    (embedded inline in index.html) instead of fetch(), so it works offline
    under ``file://`` protocol.
    """
    return '''// Standalone visual novel player (offline-capable)
(function(){
  var story, currentScene, currentNode, state = {};

  function init() {
    var el = document.getElementById("story-data");
    if (!el) { document.getElementById("text").textContent = "story-data not found"; return; }
    try {
      story = JSON.parse(el.textContent);
    } catch(e) {
      document.getElementById("text").textContent = "Invalid story data: " + e.message;
      return;
    }
    startScene(story.start_scene_id);
  }

  function startScene(sceneId) {
    currentScene = story.scenes[sceneId];
    if (!currentScene) { document.getElementById("text").textContent = "\\u573a\\u666f\\u672a\\u627e\\u5230"; return; }
    var targets = new Set();
    for (var k in currentScene.nodes) {
      var n = currentScene.nodes[k];
      if (n.next_node_id) targets.add(n.next_node_id);
      if (n.type === "choice" && n.options) n.options.forEach(function(o){ targets.add(o.next_node_id); });
      if (n.type === "branch") { targets.add(n.true_next); targets.add(n.false_next); }
    }
    var keys = Object.keys(currentScene.nodes);
    for (var i = 0; i < keys.length; i++) { if (!targets.has(keys[i])) { showNode(keys[i]); return; } }
  }

  function showNode(nodeId) {
    currentNode = currentScene.nodes[nodeId];
    if (!currentNode) return;
    var namebox = document.getElementById("namebox");
    var text = document.getElementById("text");
    var sprite = document.getElementById("sprite");
    var choices = document.getElementById("choices");
    var bg = document.getElementById("bg");
    choices.innerHTML = "";
    sprite.style.display = "none";
    if (currentScene.background_id && story.asset_resources[currentScene.background_id]) {
      var bgRes = story.asset_resources[currentScene.background_id];
      bg.src = "assets/backgrounds/" + bgRes.url.split("/").pop();
    }
    switch (currentNode.type) {
      case "dialogue":
        var ch = story.characters[currentNode.character_id];
        namebox.style.display = "block";
        namebox.textContent = ch ? ch.name : "???";
        text.textContent = currentNode.text;
        var emotion = currentNode.emotion || "neutral";
        if (ch && ch.emotions[emotion]) {
          var aid = ch.emotions[emotion];
          var res = story.asset_resources[aid];
          if (res) { sprite.src = "assets/sprites/" + res.url.split("/").pop(); sprite.style.display = "block"; }
        }
        break;
      case "narration":
        namebox.style.display = "none";
        text.textContent = currentNode.text;
        break;
      case "choice":
        namebox.style.display = "none";
        text.textContent = currentNode.text || "";
        if (currentNode.options) currentNode.options.forEach(function(opt){
          var btn = document.createElement("button");
          btn.className = "choice-btn";
          btn.textContent = opt.text;
          btn.onclick = function(){ showNode(opt.next_node_id); };
          choices.appendChild(btn);
        });
        return;
      case "scene_transition":
        startScene(currentNode.target_scene_id);
        return;
      case "branch":
        var result = false;
        try { result = eval(currentNode.condition); } catch(e) {}
        showNode(result ? currentNode.true_next : currentNode.false_next);
        return;
      case "ending":
        namebox.style.display = "none";
        text.textContent = currentNode.epilogue || "\\u2014 \\u5b8c \\u2014";
        break;
    }
  }

  document.getElementById("game").addEventListener("click", function(e){
    if (e.target.classList.contains("choice-btn") || e.target.closest(".controls")) return;
    if (currentNode && (currentNode.type === "dialogue" || currentNode.type === "narration")) {
      if (currentNode.next_node_id) showNode(currentNode.next_node_id);
    }
  });

  window.restartScene = function(){ state = {}; if (currentScene) startScene(Object.keys(story.scenes).find(function(k){ return story.scenes[k] === currentScene; })); };

  init();
})();
'''


def create_web_zip(export_id: str, project: AdaptationProject) -> Path:
    """Create a standalone Web player zip file.

    Contains *index.html* (with inline story JSON), *player.js*, and WebP/PNG
    assets in *assets/backgrounds/* and *assets/sprites/*.

    Returns the path to the generated *<title>_web.zip*.
    """
    export_dir = _export_dir()
    export_dir.mkdir(parents=True, exist_ok=True)

    staging = export_dir / f"staging_{export_id}"
    if staging.exists():
        shutil.rmtree(staging)

    assets_bg = staging / "assets" / "backgrounds"
    assets_sprites = staging / "assets" / "sprites"
    for d in [assets_bg, assets_sprites]:
        d.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Copy background images (WebP preferred, fallback PNG)
        for scene in project.scenes.values():
            if not scene.background_id or scene.background_id not in project.asset_resources:
                continue
            url = project.asset_resources[scene.background_id].url
            if not url:
                continue
            webp_url = url.rsplit(".", 1)[0] + ".webp" if "." in url else url + ".webp"
            webp_src = _generated_dir() / webp_url.replace("/api/assets/", "")
            if webp_src.exists():
                shutil.copy2(webp_src, assets_bg)
            else:
                _copy_image_asset(url, assets_bg)

        # 2. Copy sprite images
        for char in project.characters.values():
            for asset_id in char.asset_ids.values():
                if asset_id not in project.asset_resources:
                    continue
                url = project.asset_resources[asset_id].url
                if not url:
                    continue
                webp_url = url.rsplit(".", 1)[0] + ".webp" if "." in url else url + ".webp"
                webp_src = _generated_dir() / webp_url.replace("/api/assets/", "")
                if webp_src.exists():
                    shutil.copy2(webp_src, assets_sprites)
                else:
                    _copy_image_asset(url, assets_sprites)

        # 3. Write index.html (story data embedded inline)
        (staging / "index.html").write_text(
            _build_web_index_html(project), encoding="utf-8")

        # 4. Write player.js
        (staging / "player.js").write_text(
            _build_web_player_js(), encoding="utf-8")

        # 5. Create zip
        safe_title = project.title.replace(" ", "_").replace("/", "_") or "project"
        zip_name = f"{safe_title}_web.zip"
        zip_path = export_dir / zip_name
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in staging.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(staging)
                    zf.write(file, arcname)

        return zip_path
    finally:
        if staging.exists():
            shutil.rmtree(staging)
