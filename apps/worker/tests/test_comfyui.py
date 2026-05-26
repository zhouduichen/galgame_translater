from worker.comfyui import _load_workflow


def test_txt2img_workflow_uses_validated_checkpoint() -> None:
    workflow = _load_workflow("txt2img.json")

    assert workflow["4"]["inputs"]["ckpt_name"] == "v1-5-pruned-emaonly.safetensors"
