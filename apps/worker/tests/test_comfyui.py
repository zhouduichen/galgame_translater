"""Tests for the ComfyUI client — Animagine XL V3.1 + Danbooru pipeline."""

import json
import os
import tempfile
from pathlib import Path

import pytest
from worker.comfyui import (
    _build_background_prompts,
    _build_sprite_prompts,
    _base_cache_path,
    _cache_base_image,
    _character_seed,
    _compute_idempotency_key,
    _copy_image_asset,
    _INPAINT_DENOISE_MAP,
    _inject_lora,
    _load_workflow,
    _next_node_id,
    _process_background_output,
    _process_sprite_output,
    _resize_image,
    _save_png_alpha,
    _save_webp,
    _select_inpaint_workflow,
    _build_renpy_skeleton,
    _build_renpy_script,
    build_renpy_asset_declarations,
    check_asset_exists,
    check_comfyui_health,
    create_renpy_zip,
    create_web_zip,
    export_renpy_assets,
    _REQUIRED_NODE_TYPES,
)

# =========================================================================
# Workflow sanity
# =========================================================================


def test_txt2img_workflow_uses_animagine_checkpoint() -> None:
    workflow = _load_workflow("txt2img.json")
    assert workflow["4"]["inputs"]["ckpt_name"] == "animagine-xl-3.1.safetensors"


def test_txt2img_workflow_has_animagine_sampling_defaults() -> None:
    workflow = _load_workflow("txt2img.json")
    assert workflow["3"]["inputs"]["sampler_name"] == "euler_ancestral"
    assert workflow["3"]["inputs"]["steps"] == 30
    assert workflow["3"]["inputs"]["cfg"] == 7


def test_txt2img_workflow_has_sdxl_landscape_resolution() -> None:
    workflow = _load_workflow("txt2img.json")
    w = workflow["5"]["inputs"]["width"]
    h = workflow["5"]["inputs"]["height"]
    # Base workflow defaults to landscape (backgrounds)
    assert w > h, f"Expected landscape SDXL, got {w}x{h}"
    assert w * h >= 1_000_000  # SDXL minimum area


def test_character_workflow_includes_face_detailer() -> None:
    workflow = _load_workflow("txt2img_character.json")
    class_types = {k: v["class_type"] for k, v in workflow.items()}
    assert "FaceDetailer" in class_types.values()


def test_character_workflow_includes_rembg() -> None:
    workflow = _load_workflow("txt2img_character.json")
    class_types = {k: v["class_type"] for k, v in workflow.items()}
    assert any("rembg" in ct.lower() for ct in class_types.values())


def test_character_workflow_saves_image() -> None:
    workflow = _load_workflow("txt2img_character.json")
    class_types = {k: v["class_type"] for k, v in workflow.items()}
    assert "SaveImage" in class_types.values()


# =========================================================================
# Seed derivation (Steps 17-20)
# =========================================================================


def test_character_seed_is_stable() -> None:
    assert _character_seed("Sakura", "neutral") == _character_seed("Sakura", "neutral")


def test_character_seed_changes_with_emotion() -> None:
    assert _character_seed("Sakura", "neutral") != _character_seed("Sakura", "happy")


def test_character_seed_changes_with_name() -> None:
    assert _character_seed("Sakura", "neutral") != _character_seed("Aoi", "neutral")


def test_character_seed_in_range() -> None:
    assert 0 <= _character_seed("Test", "angry") <= 2_147_483_647


def test_character_seed_changes_with_scene_index() -> None:
    s1 = _character_seed("Sakura", "neutral", scene_index=0)
    s2 = _character_seed("Sakura", "neutral", scene_index=1)
    assert s1 != s2


def test_character_seed_changes_with_shot_index() -> None:
    s1 = _character_seed("Sakura", "neutral", shot_index=0)
    s2 = _character_seed("Sakura", "neutral", shot_index=1)
    assert s1 != s2


def test_character_seed_changes_with_variation_index() -> None:
    s1 = _character_seed("Sakura", "neutral", variation_index=0)
    s2 = _character_seed("Sakura", "neutral", variation_index=1)
    assert s1 != s2


# =========================================================================
# Danbooru prompt builders
# =========================================================================


def test_background_prompts_include_description() -> None:
    pos, neg = _build_background_prompts("empty classroom, afternoon sunlight")
    assert "empty classroom" in pos
    assert "people" in neg


def test_background_prompts_no_characters_in_negative() -> None:
    _, neg = _build_background_prompts("test")
    assert "people" in neg or "person" in neg


def test_background_prompts_have_quality_tags() -> None:
    pos, _ = _build_background_prompts("test")
    assert "masterpiece, best quality, very aesthetic, absurdres" in pos


def test_background_prompts_have_galgame_prefix() -> None:
    pos, _ = _build_background_prompts("test")
    assert "galgame background" in pos


def test_background_prompts_reject_realism() -> None:
    _, neg = _build_background_prompts("test")
    assert "realistic" in neg


def test_sprite_prompts_include_character() -> None:
    pos, neg = _build_sprite_prompts("Sakura", "long black hair, brown eyes", "neutral")
    assert "long black hair" in pos
    assert "pure white background" in pos


def test_sprite_prompts_have_emotion_tags() -> None:
    pos, _ = _build_sprite_prompts("Sakura", "short hair", "happy")
    assert "smiling" in pos or "happy" in pos


def test_sprite_prompts_have_galgame_style_tags() -> None:
    pos, _ = _build_sprite_prompts("Sakura", "short hair", "neutral")
    assert "galgame style" in pos or "visual novel art" in pos


def test_sprite_negative_prevents_realism() -> None:
    _, neg = _build_sprite_prompts("Sakura", "short hair", "neutral")
    assert "realistic" in neg


def test_all_emotion_tags_defined() -> None:
    emotions = ["neutral", "happy", "sad", "shy", "angry", "surprised", "crying", "embarrassed"]
    for emo in emotions:
        pos, _ = _build_sprite_prompts("Sakura", "short hair", emo)
        assert pos, f"Empty positive prompt for emotion '{emo}'"


def test_sprite_prompts_use_cowboy_shot() -> None:
    pos, _ = _build_sprite_prompts("Sakura", "short hair", "neutral")
    assert "cowboy shot" in pos


def test_sprite_prompts_have_quality_leader() -> None:
    pos, _ = _build_sprite_prompts("Sakura", "short hair", "neutral")
    assert pos.startswith("masterpiece, best quality, very aesthetic, absurdres")


# =========================================================================
# LoRA injection (Steps 14-16)
# =========================================================================


def test_inject_lora_adds_lora_loader_node() -> None:
    workflow = _load_workflow("txt2img.json")
    assert "4" in workflow  # checkpoint

    workflow = _inject_lora(workflow, "my_style.safetensors", 0.7)
    lora_nodes = {k: v for k, v in workflow.items() if v["class_type"] == "LoraLoader"}
    assert len(lora_nodes) == 1


def test_inject_lora_rewires_connections() -> None:
    workflow = _load_workflow("txt2img.json")
    workflow = _inject_lora(workflow, "my_style.safetensors", 0.7)

    lora_id = str(max(int(k) for k in workflow.keys() if workflow[k].get("class_type") == "LoraLoader"))
    for nid, node in workflow.items():
        if nid == lora_id:
            continue
        for key, val in node.get("inputs", {}).items():
            if isinstance(val, list) and len(val) == 2:
                assert val != ["4", 0], f"Node {nid} still points to checkpoint model"
                assert val != ["4", 1], f"Node {nid} still points to checkpoint clip"


def test_inject_lora_preserves_checkpoint() -> None:
    workflow = _load_workflow("txt2img.json")
    workflow = _inject_lora(workflow, "style.safetensors", 0.8)
    assert workflow["4"]["inputs"]["ckpt_name"] == "animagine-xl-3.1.safetensors"


def test_next_node_id() -> None:
    workflow = {"1": {}, "5": {}, "10": {}}
    assert _next_node_id(workflow) == "11"


# =========================================================================
# Image post-processing (Steps 36-42)
# =========================================================================


def _make_img_bytes(size, mode="RGB", color=(255, 0, 0)):
    """Helper: create a small PNG in memory."""
    from PIL import Image
    from io import BytesIO

    buf = BytesIO()
    Image.new(mode, (size, size), color=color).save(buf, "PNG")
    return buf.getvalue()


def test_save_png_alpha_creates_png(tmp_path: Path) -> None:
    data = _make_img_bytes(64, "RGB", (255, 0, 0))
    dest = tmp_path / "test.png"
    _save_png_alpha(data, dest)
    assert dest.exists()
    from PIL import Image
    loaded = Image.open(dest)
    assert loaded.mode == "RGBA"


def test_save_webp_creates_webp(tmp_path: Path) -> None:
    data = _make_img_bytes(64, "RGBA", (255, 0, 0, 255))
    dest = tmp_path / "test.webp"
    _save_webp(data, dest)
    assert dest.exists()
    from PIL import Image
    loaded = Image.open(dest)
    assert loaded.format == "WEBP"


def test_resize_image_by_height() -> None:
    from PIL import Image
    from io import BytesIO

    img = Image.new("RGB", (200, 100), color=(0, 255, 0))
    buf = BytesIO()
    img.save(buf, "PNG")
    data = buf.getvalue()

    resized = _resize_image(data, target_height=50)
    out_img = Image.open(BytesIO(resized))
    assert out_img.height == 50
    assert out_img.width == 100  # aspect ratio 2:1


def test_resize_image_by_width() -> None:
    from PIL import Image
    from io import BytesIO

    img = Image.new("RGB", (100, 200), color=(0, 255, 0))
    buf = BytesIO()
    img.save(buf, "PNG")
    data = buf.getvalue()

    resized = _resize_image(data, target_width=50)
    out_img = Image.open(BytesIO(resized))
    assert out_img.width == 50
    assert out_img.height == 100  # aspect ratio 1:2


def test_resize_no_op_when_no_dimensions_given() -> None:
    data = _make_img_bytes(64)
    assert _resize_image(data) == data


def test_process_sprite_output_returns_urls(tmp_path: Path) -> None:
    data = _make_img_bytes(64, "RGBA", (0, 128, 255, 255))
    old_val = os.environ.get("GENERATED_DIR")
    old_webp = os.environ.get("GENERATE_WEBP")
    os.environ["GENERATED_DIR"] = str(tmp_path)
    os.environ["GENERATE_WEBP"] = "true"
    try:
        result = _process_sprite_output(data, "test.png", "Sakura", "happy")
        assert result["png_url"] is not None
        assert "/api/assets/" in result["png_url"]
        assert result["png_url"].endswith(".png")
    finally:
        if old_val:
            os.environ["GENERATED_DIR"] = old_val
        else:
            del os.environ["GENERATED_DIR"]
        if old_webp:
            os.environ["GENERATE_WEBP"] = old_webp
        else:
            del os.environ["GENERATE_WEBP"]


# =========================================================================
# Ren'Py export (Steps 32-35)
# =========================================================================


def test_build_renpy_asset_declarations_generates_script() -> None:
    characters = {
        "char_1": {
            "name": "Sakura",
            "emotions": {
                "neutral": "/api/assets/sakura_neutral.png",
                "happy": "/api/assets/sakura_happy.png",
            },
        },
    }
    backgrounds = {
        "scene_1": {
            "name": "classroom",
            "asset_url": "/api/assets/classroom.png",
            "description": "Empty classroom",
        },
    }

    script = build_renpy_asset_declarations(characters, backgrounds)
    assert "image Sakura_neutral" in script
    assert "image Sakura_happy" in script
    assert "image bg classroom" in script
    assert "label generated_scene:" in script
    assert "show Sakura_neutral" in script
    assert "return" in script


def test_build_renpy_empty_data() -> None:
    script = build_renpy_asset_declarations({}, {})
    assert "label generated_scene:" in script
    assert "return" in script


def test_export_renpy_assets_creates_directory_structure(tmp_path: Path) -> None:
    characters = {
        "c1": {"name": "Aoi", "emotions": {"neutral": "/url/aoi.png"}},
    }
    backgrounds = {
        "s1": {"name": "street", "asset_url": "/url/street.png", "description": ""},
    }

    export_path = tmp_path / "renpy_export"
    script_path = export_renpy_assets(export_path, characters, backgrounds)

    assert script_path is not None
    assert Path(script_path).exists()
    assert (export_path / "images" / "sprites").is_dir()
    assert (export_path / "images" / "backgrounds").is_dir()
    assert (export_path / "images" / "webp").is_dir()
    assert (export_path / "scripts").is_dir()
    assert (export_path / "scripts" / "generated_assets.rpy").exists()


# =========================================================================
# Workflow selection
# =========================================================================


def test_character_workflow_has_sdxl_resolution() -> None:
    workflow = _load_workflow("txt2img_character.json")
    w = workflow["5"]["inputs"]["width"]
    h = workflow["5"]["inputs"]["height"]
    assert h > w
    assert w * h >= 1_000_000


def test_character_workflow_vaes_to_face_detailer() -> None:
    workflow = _load_workflow("txt2img_character.json")
    assert workflow["10"]["inputs"]["image"] == ["8", 0]
    assert workflow["11"]["inputs"]["images"] == ["10", 0]
    assert workflow["12"]["inputs"]["images"] == ["11", 0]


# =========================================================================
# Integration: full pipeline smoke test (Steps 43-49)
# =========================================================================


def test_integration_character_8_expressions() -> None:
    """Simulate 8 expressions for 1 character — validate seed + prompt consistency."""
    char_desc = "long black hair, brown eyes, japanese school uniform, sailor collar"
    emotions = ["neutral", "happy", "sad", "shy", "angry", "surprised", "crying", "embarrassed"]

    seeds = {}
    prompts = {}
    for emo in emotions:
        seeds[emo] = _character_seed("Sakura", emo, scene_index=0)
        pos, _ = _build_sprite_prompts("Sakura", char_desc, emo)
        prompts[emo] = pos

    # All emotions get unique seeds
    assert len(set(seeds.values())) == len(emotions)

    # Same character desc in all prompts
    for emo in emotions:
        assert "long black hair" in prompts[emo]
        assert "sailor collar" in prompts[emo]
        assert "galgame style" in prompts[emo]
        assert "pure white background" in prompts[emo]
        assert prompts[emo].startswith("masterpiece, best quality, very aesthetic, absurdres")

    # Different scene → different seed
    scene1_seed = _character_seed("Sakura", "neutral", scene_index=1)
    assert scene1_seed != seeds["neutral"]


def test_integration_2_backgrounds() -> None:
    """Simulate 2 backgrounds — validate prompts + quality."""
    scenes = [
        ("empty classroom, afternoon sunlight, rows of desks", 1344, 768),
        ("japanese suburban street, cherry blossoms, spring", 1536, 864),
    ]
    for desc, w, h in scenes:
        pos, neg = _build_background_prompts(desc)
        assert "galgame background" in pos
        assert pos.startswith("masterpiece, best quality, very aesthetic, absurdres")
        assert "people" in neg
        assert "realistic" in neg
        assert w * h >= 1_000_000


def test_integration_renpy_export_full() -> None:
    """Full Ren'Py export: 1 character (8 emotions) + 2 backgrounds."""
    characters = {
        "char_sakura": {
            "name": "Sakura",
            "emotions": {
                "neutral": "/a/s_neutral.png",
                "happy": "/a/s_happy.png",
                "sad": "/a/s_sad.png",
                "shy": "/a/s_shy.png",
                "angry": "/a/s_angry.png",
                "surprised": "/a/s_surprised.png",
                "crying": "/a/s_crying.png",
                "embarrassed": "/a/s_embarrassed.png",
            },
        },
    }
    backgrounds = {
        "sc1": {"name": "classroom", "asset_url": "/a/class.png", "description": ""},
        "sc2": {"name": "street", "asset_url": "/a/street.png", "description": ""},
    }

    script = build_renpy_asset_declarations(characters, backgrounds)
    for emo in characters["char_sakura"]["emotions"]:
        assert f"image Sakura_{emo}" in script
    assert "image bg classroom" in script
    assert "image bg street" in script
    assert "label generated_scene:" in script
    assert "return" in script


def test_integration_image_pipeline(tmp_path: Path) -> None:
    """Full image pipeline: alpha PNG → WebP → resize → save."""
    from PIL import Image
    from io import BytesIO

    # Non-square image (2:1 aspect ratio for clear resize testing)
    buf = BytesIO()
    Image.new("RGBA", (200, 100), color=(128, 64, 200, 255)).save(buf, "PNG")
    img_data = buf.getvalue()

    old_dir = os.environ.get("GENERATED_DIR")
    old_webp = os.environ.get("GENERATE_WEBP")
    os.environ["GENERATED_DIR"] = str(tmp_path)
    os.environ["GENERATE_WEBP"] = "true"

    try:
        # 1. Sprite output → PNG alpha
        spr = _process_sprite_output(img_data, "test.png", "Sakura", "happy", target_height=256)
        assert spr["png_url"].endswith(".png")
        png_path2 = tmp_path / Path(spr["png_url"]).name
        if png_path2.exists():
            loaded = Image.open(png_path2)
            assert loaded.mode == "RGBA"

        # 2. Background output → original + WebP
        bg = _process_background_output(img_data, "test.png", "empty classroom", target_width=800)
        assert bg["original_url"] is not None
        assert bg["webp_url"] is not None
        assert bg["webp_url"].endswith(".webp")

        # 3. Resize preserves aspect ratio (200x100 → target_height=50 → 100x50)
        resized = _resize_image(img_data, target_height=50)
        out = Image.open(BytesIO(resized))
        assert out.height == 50
        assert out.width == 100
    finally:
        if old_dir:
            os.environ["GENERATED_DIR"] = old_dir
        else:
            del os.environ["GENERATED_DIR"]
        if old_webp:
            os.environ["GENERATE_WEBP"] = old_webp
        else:
            del os.environ["GENERATE_WEBP"]


def test_integration_seed_consistency() -> None:
    """Steps 44-46: character consistency + sprite/background quality checks."""
    # Deterministic: same params → same seed
    a = _character_seed("Sakura", "neutral", scene_index=0, shot_index=0, variation_index=0)
    b = _character_seed("Sakura", "neutral", scene_index=0, shot_index=0, variation_index=0)
    assert a == b

    # Different emotions → different seeds
    assert len({_character_seed("Sakura", e) for e in ("neutral", "happy", "sad")}) == 3

    # Background: no realism, no people in pos
    pos, neg = _build_background_prompts("test")
    assert "realistic" not in pos
    assert "people" in neg

    # Sprite: has composition/style tags
    pos, neg = _build_sprite_prompts("Sakura", "short hair", "neutral")
    assert "absurdres" in pos
    assert "cowboy shot" in pos
    assert "pure white background" in pos
    assert "galgame style" in pos


# =========================================================================
# Health check tests
# =========================================================================


def test_check_comfyui_health_returns_dict() -> None:
    """check_comfyui_health always returns a dict with status + checks."""
    result = check_comfyui_health()
    assert isinstance(result, dict)
    assert "status" in result
    assert "checks" in result
    assert isinstance(result["checks"], list)


def test_check_comfyui_health_fails_when_server_down() -> None:
    """Without a running ComfyUI, the health check returns status 'error'."""
    result = check_comfyui_health()
    assert result["status"] in ("error", "degraded")


def test_check_comfyui_health_checks_have_expected_fields(monkeypatch) -> None:
    """Each check item has name, status, and detail."""

    class MockResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"system": {"comfyui_version": "test"}}

    monkeypatch.setattr("httpx.get", lambda url, **kw: MockResponse())

    result = check_comfyui_health()
    for check in result["checks"]:
        assert "name" in check
        assert "status" in check
        assert "detail" in check


def test_check_comfyui_health_requires_face_detailer(monkeypatch) -> None:
    """If FaceDetailer is not registered, health check returns error."""

    class MockOkResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"system": {"comfyui_version": "test"}}

    class MockNodeTypeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "CheckpointLoaderSimple": {
                    "input": {"required": {"ckpt_name": ["animagine-xl-3.1.safetensors"]}}
                }
            }

    class MockNotFoundResponse:
        status_code = 404

    responses = {
        "/system_stats": MockOkResponse(),
        "/object_info/CheckpointLoaderSimple": MockNodeTypeResponse(),
        "/object_info/FaceDetailer": MockNotFoundResponse(),
        "/object_info/ImageRembg": MockOkResponse(),
    }

    def mock_get(url: str, **kw) -> object:
        for path, resp in responses.items():
            if path in url:
                return resp
        return MockOkResponse()

    monkeypatch.setattr("httpx.get", mock_get)

    result = check_comfyui_health()
    assert result["status"] == "error"
    face_checks = [c for c in result["checks"] if "FaceDetailer" in c["name"]]
    assert len(face_checks) > 0
    assert face_checks[0]["status"] == "error"


# =========================================================================
# Export packaging tests
# =========================================================================


class TestCopyImageAsset:
    def test_success(self, tmp_path: Path) -> None:
        """Copy an existing asset file."""
        src_dir = tmp_path / "generated"
        src_dir.mkdir()
        src_file = src_dir / "test_sprite.png"
        src_file.write_bytes(b"fake_png_bytes")
        monkeypatch = __import__("pytest").MonkeyPatch()
        monkeypatch.setattr("worker.comfyui._generated_dir", lambda: src_dir)

        dest = tmp_path / "output"
        dest.mkdir()
        result = _copy_image_asset("/api/assets/test_sprite.png", dest)
        assert result is not None
        assert (dest / "test_sprite.png").exists()
        assert (dest / "test_sprite.png").read_bytes() == b"fake_png_bytes"

    def test_none_url(self, tmp_path: Path) -> None:
        """Empty URL returns None."""
        assert _copy_image_asset("", tmp_path) is None

    def test_missing_file(self, tmp_path: Path) -> None:
        """Non-existent source returns None."""
        src_dir = tmp_path / "generated"
        src_dir.mkdir()
        monkeypatch = __import__("pytest").MonkeyPatch()
        monkeypatch.setattr("worker.comfyui._generated_dir", lambda: src_dir)

        assert _copy_image_asset("/api/assets/nonexistent.png", tmp_path) is None

    def test_empty_url_after_strip(self, tmp_path: Path) -> None:
        """URL that resolves to empty filename returns None."""
        assert _copy_image_asset("/api/assets/", tmp_path) is None


class TestRenpyExport:
    def test_skeleton_creates_files(self, tmp_path: Path) -> None:
        """Skeleton writes options.rpy, screens.rpy, gui.rpy."""
        staging = tmp_path / "staging"
        game = staging / "game"
        game.mkdir(parents=True)
        _build_renpy_skeleton(staging, "Test Game")

        assert (game / "options.rpy").exists()
        assert (game / "screens.rpy").exists()
        assert (game / "gui.rpy").exists()
        content = (game / "options.rpy").read_text("utf-8")
        assert 'config.name = "Test Game"' in content

    def test_script_generation(self) -> None:
        """Generated script contains expected Ren'Py syntax."""
        characters = {
            "c1": {"name": "Sakura", "emotions": {"neutral": "/a/n.png", "happy": "/a/h.png"}},
            "c2": {"name": "Taro", "emotions": {"neutral": "/a/t.png"}},
        }
        backgrounds = {
            "s1": {"name": "classroom", "asset_url": "/a/bg.png", "description": "A classroom"},
        }
        script = _build_renpy_script("Test", characters, backgrounds)
        assert "label start:" in script
        assert "scene bg classroom" in script
        assert "show Sakura_neutral" in script
        assert "show Taro_neutral" in script
        assert 'config.name' not in script  # not in script.rpy

    def test_empty_backgrounds(self) -> None:
        """Empty backgrounds still produces valid script."""
        script = _build_renpy_script("Test", {}, {})
        assert "label start:" in script
        assert "return" in script

    def test_create_renpy_zip_structure(self, monkeypatch, tmp_path: Path) -> None:
        """Ren'Py zip contains expected directory structure."""
        export_dir = tmp_path / "export"
        gen_dir = tmp_path / "generated"
        gen_dir.mkdir()
        # Create a fake asset file
        (gen_dir / "sprite.png").write_bytes(b"png")
        (gen_dir / "bg.png").write_bytes(b"png")

        monkeypatch.setattr("worker.comfyui._export_dir", lambda: export_dir)
        monkeypatch.setattr("worker.comfyui._generated_dir", lambda: gen_dir)

        characters = {
            "c1": {"name": "Sakura", "emotions": {"neutral": "/api/assets/sprite.png"}},
        }
        backgrounds = {
            "s1": {"name": "classroom", "asset_url": "/api/assets/bg.png", "description": "教室"},
        }

        zip_path = create_renpy_zip("test_export", "Test Game", characters, backgrounds)
        assert zip_path.exists()
        assert zip_path.suffix == ".zip"

        # Unzip and verify structure
        import zipfile
        unzip_dir = tmp_path / "unzipped"
        unzip_dir.mkdir()
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(unzip_dir)

        assert (unzip_dir / "game" / "script.rpy").exists()
        assert (unzip_dir / "game" / "generated_assets.rpy").exists()
        assert (unzip_dir / "game" / "options.rpy").exists()
        assert (unzip_dir / "game" / "images" / "backgrounds" / "bg.png").exists()
        assert (unzip_dir / "game" / "images" / "sprites" / "sprite.png").exists()

    def test_create_renpy_zip_empty_assets(self, monkeypatch, tmp_path: Path) -> None:
        """Ren'Py zip works with no assets."""
        export_dir = tmp_path / "export"
        gen_dir = tmp_path / "generated"
        gen_dir.mkdir()
        monkeypatch.setattr("worker.comfyui._export_dir", lambda: export_dir)
        monkeypatch.setattr("worker.comfyui._generated_dir", lambda: gen_dir)

        zip_path = create_renpy_zip("empty_export", "Empty", {}, {})
        assert zip_path.exists()

        import zipfile
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
        assert "game/script.rpy" in names
        assert "game/options.rpy" in names
        assert "game/generated_assets.rpy" in names


class TestWebExport:
    def test_create_web_zip_structure(self, monkeypatch, tmp_path: Path) -> None:
        """Web zip contains expected files."""
        export_dir = tmp_path / "export"
        gen_dir = tmp_path / "generated"
        gen_dir.mkdir()
        (gen_dir / "bg.webp").write_bytes(b"webp")
        (gen_dir / "sprite.webp").write_bytes(b"webp")

        monkeypatch.setattr("worker.comfyui._export_dir", lambda: export_dir)
        monkeypatch.setattr("worker.comfyui._generated_dir", lambda: gen_dir)

        characters = {
            "c1": {"name": "Sakura", "emotions": {"neutral": "/api/assets/sprite.png"}},
        }
        backgrounds = {
            "s1": {"name": "classroom", "asset_url": "/api/assets/bg.png", "description": "教室"},
        }

        zip_path = create_web_zip("test_web", "Test Web", characters, backgrounds)
        assert zip_path.exists()

        import zipfile
        unzip_dir = tmp_path / "unzipped"
        unzip_dir.mkdir()
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(unzip_dir)

        assert (unzip_dir / "index.html").exists()
        assert (unzip_dir / "player.js").exists()
        assert (unzip_dir / "data" / "story.json").exists()
        # Assets
        assert (unzip_dir / "assets" / "backgrounds" / "bg.webp").exists()
        assert (unzip_dir / "assets" / "sprites" / "sprite.webp").exists()

        # Verify story.json content
        story = json.loads((unzip_dir / "data" / "story.json").read_text("utf-8"))
        assert story["title"] == "Test Web"
        assert "classroom" in str(story["scenes"])

    def test_web_fallback_to_png(self, monkeypatch, tmp_path: Path) -> None:
        """Web export falls back to PNG when WebP is not available."""
        export_dir = tmp_path / "export"
        gen_dir = tmp_path / "generated"
        gen_dir.mkdir()
        # Only PNG available, no WebP
        (gen_dir / "bg.png").write_bytes(b"png")

        monkeypatch.setattr("worker.comfyui._export_dir", lambda: export_dir)
        monkeypatch.setattr("worker.comfyui._generated_dir", lambda: gen_dir)

        characters = {}
        backgrounds = {
            "s1": {"name": "classroom", "asset_url": "/api/assets/bg.png", "description": ""},
        }

        zip_path = create_web_zip("fallback", "Fallback", characters, backgrounds)
        assert zip_path.exists()

        import zipfile
        unzip_dir = tmp_path / "unzipped"
        unzip_dir.mkdir()
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(unzip_dir)

        assert (unzip_dir / "assets" / "backgrounds" / "bg.png").exists()


# =========================================================================
# Idempotency key derivation (Task 4 Step 7)
# =========================================================================


def test_idempotency_key_is_deterministic() -> None:
    a = _compute_idempotency_key("character_sprite", "proj_1", character_id="c1", emotion="neutral")
    b = _compute_idempotency_key("character_sprite", "proj_1", character_id="c1", emotion="neutral")
    assert a == b
    assert len(a) == 16  # hexdigest[:16]


def test_idempotency_key_differs_by_emotion() -> None:
    neutral = _compute_idempotency_key("character_sprite", "proj_1", character_id="c1", emotion="neutral")
    happy = _compute_idempotency_key("character_sprite", "proj_1", character_id="c1", emotion="happy")
    assert neutral != happy


def test_idempotency_key_differs_by_character() -> None:
    c1 = _compute_idempotency_key("character_sprite", "proj_1", character_id="c1", emotion="neutral")
    c2 = _compute_idempotency_key("character_sprite", "proj_1", character_id="c2", emotion="neutral")
    assert c1 != c2


def test_idempotency_key_differs_by_project() -> None:
    p1 = _compute_idempotency_key("character_sprite", "proj_1", character_id="c1", emotion="neutral")
    p2 = _compute_idempotency_key("character_sprite", "proj_2", character_id="c1", emotion="neutral")
    assert p1 != p2


def test_idempotency_key_differs_by_type() -> None:
    sprite = _compute_idempotency_key("character_sprite", "proj_1", character_id="c1", emotion="neutral")
    bg = _compute_idempotency_key("background", "proj_1", scene_id="s1")
    assert sprite != bg


# =========================================================================
# check_asset_exists (Task 4 Step 5)
# =========================================================================


class TestCheckAssetExists:
    def test_hit(self, tmp_path: Path) -> None:
        """Asset with matching key and existing file returns the resource."""
        from project_model.schema import AssetResource, AssetType

        # Create a fake asset file
        asset_dir = tmp_path / "generated"
        asset_dir.mkdir()
        asset_file = asset_dir / "test_sprite.png"
        asset_file.write_bytes(b"fake_png")

        resource = AssetResource(
            id="ast_1",
            url="/api/assets/test_sprite.png",
            asset_type=AssetType.character_sprite,
            idempotency_key="key_abc123",
        )

        monkeypatch = __import__("pytest").MonkeyPatch()
        monkeypatch.setattr("worker.comfyui._generated_dir", lambda: asset_dir)

        try:
            result = check_asset_exists({"ast_1": resource}, "key_abc123")
            assert result is not None
            assert result.id == "ast_1"
        finally:
            monkeypatch.undo()

    def test_miss_no_match(self) -> None:
        """No asset with the given key returns None."""
        assert check_asset_exists({}, "nonexistent_key") is None

    def test_miss_file_deleted(self, tmp_path: Path) -> None:
        """DB has the key but file is missing -> returns None (disk double-check)."""
        from project_model.schema import AssetResource, AssetType

        asset_dir = tmp_path / "generated"
        asset_dir.mkdir()

        resource = AssetResource(
            id="ast_ghost",
            url="/api/assets/ghost.png",
            asset_type=AssetType.character_sprite,
            idempotency_key="ghost_key",
        )

        monkeypatch = __import__("pytest").MonkeyPatch()
        monkeypatch.setattr("worker.comfyui._generated_dir", lambda: asset_dir)

        try:
            # ghost.png does NOT exist on disk
            result = check_asset_exists({"ast_ghost": resource}, "ghost_key")
            assert result is None
        finally:
            monkeypatch.undo()

    def test_hit_when_key_match_and_file_exists(self, tmp_path: Path) -> None:
        """Multiple resources, only one matches -- returns the correct one."""
        from project_model.schema import AssetResource, AssetType

        asset_dir = tmp_path / "generated"
        asset_dir.mkdir()
        (asset_dir / "target.png").write_bytes(b"png")
        (asset_dir / "other.png").write_bytes(b"png")

        resources = {
            "ast_1": AssetResource(
                id="ast_1",
                url="/api/assets/other.png",
                asset_type=AssetType.character_sprite,
                idempotency_key="other_key",
            ),
            "ast_2": AssetResource(
                id="ast_2",
                url="/api/assets/target.png",
                asset_type=AssetType.character_sprite,
                idempotency_key="target_key",
            ),
        }

        monkeypatch = __import__("pytest").MonkeyPatch()
        monkeypatch.setattr("worker.comfyui._generated_dir", lambda: asset_dir)

        try:
            result = check_asset_exists(resources, "target_key")
            assert result is not None
            assert result.id == "ast_2"
        finally:
            monkeypatch.undo()


# =========================================================================
# Base cache helpers (Task 4 Step 4)
# =========================================================================


def test_base_cache_path_is_deterministic() -> None:
    p1 = _base_cache_path("abc123")
    p2 = _base_cache_path("abc123")
    assert p1 == p2
    assert p1.name == "abc123.png"


def test_base_cache_path_sanitizes_colons() -> None:
    path = _base_cache_path("proj:char:emo")
    # Colons replaced with underscores
    assert ":" not in path.name


def test_cache_base_image_creates_file(tmp_path: Path) -> None:
    monkeypatch = __import__("pytest").MonkeyPatch()
    monkeypatch.setattr("worker.comfyui._generated_dir", lambda: tmp_path)

    try:
        dest = _cache_base_image(b"fake_png_bytes", "test_key")
        assert dest.exists()
        assert dest.read_bytes() == b"fake_png_bytes"
    finally:
        monkeypatch.undo()


# =========================================================================
# Incremental inpaint workflow (Task 3)
# =========================================================================


def test_inpaint_workflow_uses_load_image() -> None:
    workflow = _load_workflow("txt2img_inpaint.json")
    assert "13" in workflow
    assert workflow["13"]["class_type"] == "LoadImage"
    # Has a placeholder that gets replaced at runtime
    assert workflow["13"]["inputs"]["image"] == "__BASE_PLACEHOLDER__"


def test_inpaint_workflow_has_face_detailer() -> None:
    workflow = _load_workflow("txt2img_inpaint.json")
    assert workflow["10"]["class_type"] == "FaceDetailer"
    # FaceDetailer reads from LoadImage (node 13)
    assert workflow["10"]["inputs"]["image"] == ["13", 0]


def test_inpaint_workflow_has_rembg() -> None:
    workflow = _load_workflow("txt2img_inpaint.json")
    assert workflow["11"]["class_type"] == "ImageRembg"
    assert workflow["11"]["inputs"]["images"] == ["10", 0]


def test_inpaint_workflow_saves_image() -> None:
    workflow = _load_workflow("txt2img_inpaint.json")
    assert workflow["12"]["class_type"] == "SaveImage"
    assert workflow["12"]["inputs"]["images"] == ["11", 0]


def test_inpaint_workflow_no_ksmapler() -> None:
    """Inpaint workflow should NOT have a KSampler node."""
    workflow = _load_workflow("txt2img_inpaint.json")
    class_types = {k: v["class_type"] for k, v in workflow.items()}
    assert "KSampler" not in class_types.values()


def test_inpaint_workflow_default_denoise() -> None:
    workflow = _load_workflow("txt2img_inpaint.json")
    assert workflow["10"]["inputs"]["denoise"] == 0.35


def test_select_inpaint_workflow() -> None:
    workflow = _select_inpaint_workflow()
    assert workflow["13"]["class_type"] == "LoadImage"


def test_inpaint_denoise_map_covers_all_emotions() -> None:
    expected = {"neutral", "happy", "sad", "shy", "angry", "surprised", "crying", "embarrassed", "thinking"}
    for emo in expected:
        assert emo in _INPAINT_DENOISE_MAP, f"Missing denoise mapping for {emo}"
        assert 0.3 <= _INPAINT_DENOISE_MAP[emo] <= 0.5


def test_character_workflow_now_has_base_cache_node() -> None:
    """Full-gen character workflow should have node 14 for base image caching."""
    workflow = _load_workflow("txt2img_character.json")
    assert "14" in workflow
    assert workflow["14"]["class_type"] == "SaveImage"
    # Node 14 reads from FaceDetailer output (node 10)
    assert workflow["14"]["inputs"]["images"] == ["10", 0]
