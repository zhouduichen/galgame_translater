from prompt_templates.parse_draft import (
    STEP_CHARACTERS,
    STEP_SCENES,
    STEP_SUMMARIZE,
    STEP_VN_ADAPT,
    build_parse_draft_prompt,
)


def test_parse_draft_prompts_require_chinese_user_facing_text() -> None:
    prompts = [
        build_parse_draft_prompt(STEP_SUMMARIZE, novel_text="第一天上学。", target_length="10min_demo"),
        build_parse_draft_prompt(
            STEP_CHARACTERS,
            novel_text="第一天上学。",
            summary_json='{"title":"开学日"}',
        ),
        build_parse_draft_prompt(
            STEP_SCENES,
            novel_text="第一天上学。",
            characters_json='{"characters":[]}',
        ),
        build_parse_draft_prompt(
            STEP_VN_ADAPT,
            scene_id="scene_001",
            scene_title="校门",
            scene_description="开学第一天的相遇。",
            scene_info="校门口，樱花飘落。",
            characters_json='{"characters":[]}',
            locations_json='["校门"]',
            location_id="school_gate",
        ),
    ]

    assert all("所有面向用户的文本必须使用简体中文" in prompt for prompt in prompts)
