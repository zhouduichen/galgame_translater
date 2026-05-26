"""Comprehensive mock data for frontend and backend development without LLM."""

from .schema import (
    AdaptationProject,
    AssetCue,
    AssetResource,
    AssetType,
    Character,
    CharacterCue,
    ChoiceNode,
    ChoiceOption,
    DialogueNode,
    Emotion,
    EndingNode,
    NarrationNode,
    NodeType,
    ParseDraft,
    Scene,
    SceneTransitionNode,
    Side,
)

# ─── Asset Resources (pretend they exist) ────────────────────────────────────

ASSETS: dict[str, AssetResource] = {
    "bg_school_gate": AssetResource(
        id="bg_school_gate", url="/assets/bg_school_gate.png",
        asset_type=AssetType.background, width=1920, height=1080,
        generator="placeholder",
    ),
    "bg_classroom": AssetResource(
        id="bg_classroom", url="/assets/bg_classroom.png",
        asset_type=AssetType.background, width=1920, height=1080,
        generator="placeholder",
    ),
    "bg_rooftop": AssetResource(
        id="bg_rooftop", url="/assets/bg_rooftop.png",
        asset_type=AssetType.background, width=1920, height=1080,
        generator="placeholder",
    ),
    "bg_sakura_path": AssetResource(
        id="bg_sakura_path", url="/assets/bg_sakura_path.png",
        asset_type=AssetType.background, width=1920, height=1080,
        generator="placeholder",
    ),
    "sprite_heroine_neutral": AssetResource(
        id="sprite_heroine_neutral", url="/assets/heroine_neutral.png",
        asset_type=AssetType.character_sprite, character_id="heroine",
        emotion=Emotion.neutral, generator="placeholder",
    ),
    "sprite_heroine_happy": AssetResource(
        id="sprite_heroine_happy", url="/assets/heroine_happy.png",
        asset_type=AssetType.character_sprite, character_id="heroine",
        emotion=Emotion.happy, generator="placeholder",
    ),
    "sprite_heroine_sad": AssetResource(
        id="sprite_heroine_sad", url="/assets/heroine_sad.png",
        asset_type=AssetType.character_sprite, character_id="heroine",
        emotion=Emotion.sad, generator="placeholder",
    ),
    "sprite_heroine_shy": AssetResource(
        id="sprite_heroine_shy", url="/assets/heroine_shy.png",
        asset_type=AssetType.character_sprite, character_id="heroine",
        emotion=Emotion.shy, generator="placeholder",
    ),
    "sprite_heroine_surprised": AssetResource(
        id="sprite_heroine_surprised", url="/assets/heroine_surprised.png",
        asset_type=AssetType.character_sprite, character_id="heroine",
        emotion=Emotion.surprised, generator="placeholder",
    ),
    "sprite_rival_neutral": AssetResource(
        id="sprite_rival_neutral", url="/assets/rival_neutral.png",
        asset_type=AssetType.character_sprite, character_id="rival",
        emotion=Emotion.neutral, generator="placeholder",
    ),
    "sprite_rival_angry": AssetResource(
        id="sprite_rival_angry", url="/assets/rival_angry.png",
        asset_type=AssetType.character_sprite, character_id="rival",
        emotion=Emotion.angry, generator="placeholder",
    ),
    "sprite_friend_neutral": AssetResource(
        id="sprite_friend_neutral", url="/assets/friend_neutral.png",
        asset_type=AssetType.character_sprite, character_id="friend",
        emotion=Emotion.neutral, generator="placeholder",
    ),
    "sprite_friend_happy": AssetResource(
        id="sprite_friend_happy", url="/assets/friend_happy.png",
        asset_type=AssetType.character_sprite, character_id="friend",
        emotion=Emotion.happy, generator="placeholder",
    ),
}

# ─── Characters ──────────────────────────────────────────────────────────────

CHARACTERS: dict[str, Character] = {
    "heroine": Character(
        character_id="heroine",
        name="雨宫白",
        role="protagonist",
        description="一个安静但敏锐的学生，习惯坐在教室窗边读小说。",
        traits=["安静", "敏锐", "有点固执"],
        color="#88ccff",
        asset_ids={
            Emotion.neutral: "sprite_heroine_neutral",
            Emotion.happy: "sprite_heroine_happy",
            Emotion.sad: "sprite_heroine_sad",
            Emotion.shy: "sprite_heroine_shy",
            Emotion.surprised: "sprite_heroine_surprised",
        },
    ),
    "rival": Character(
        character_id="rival",
        name="朱雀茜",
        role="supporting",
        description="严谨的学生会长，说话做事都很利落，其实比外表温柔。",
        traits=["严格", "能干", "不太坦率"],
        color="#ff6688",
        asset_ids={
            Emotion.neutral: "sprite_rival_neutral",
            Emotion.angry: "sprite_rival_angry",
        },
    ),
    "friend": Character(
        character_id="friend",
        name="朝日奈奈",
        role="supporting",
        description="女主角开朗的同班同学，总是在不经意间替她打气。",
        traits=["开朗", "话多", "热心"],
        color="#ffcc44",
        asset_ids={
            Emotion.neutral: "sprite_friend_neutral",
            Emotion.happy: "sprite_friend_happy",
        },
    ),
}

# ─── Scenes ──────────────────────────────────────────────────────────────────

# Scene 1: School gate encounter
SCENE1_NODES: dict = {
    "s1_narr_start": NarrationNode(
        node_id="s1_narr_start",
        text="春天的清晨，校门口的樱花在风里缓缓飘落。新学期第一天，空气里有花粉和刚擦过黑板的味道，也有一点说不清的新鲜感。",
        background_id="bg_sakura_path",
        next_node_id="s1_dialogue_friend",
    ),
    "s1_dialogue_friend": DialogueNode(
        node_id="s1_dialogue_friend",
        character_id="friend", text="早啊，小白！你看起来又没睡醒，昨晚是不是又熬夜看书了？",
        emotion=Emotion.happy, side=Side.right,
        next_node_id="s1_dialogue_heroine_1",
    ),
    "s1_dialogue_heroine_1": DialogueNode(
        node_id="s1_dialogue_heroine_1",
        character_id="heroine", text="……嗯。把小说最后一章看完了，一不小心就忘了时间。",
        emotion=Emotion.neutral, side=Side.left,
        next_node_id="s1_dialogue_friend_2",
    ),
    "s1_dialogue_friend_2": DialogueNode(
        node_id="s1_dialogue_friend_2",
        character_id="friend", text="哈哈，真像你。对了，你知道吗？学生会长今天好像在找你。",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s1_dialogue_heroine_2",
    ),
    "s1_dialogue_heroine_2": DialogueNode(
        node_id="s1_dialogue_heroine_2",
        character_id="heroine", text="……找我？我最近应该没做什么会被训的事吧。",
        emotion=Emotion.neutral, side=Side.left,
        next_node_id="s1_choice",
    ),
    "s1_choice": ChoiceNode(
        node_id="s1_choice",
        text="听到这句话，你想：",
        options=[
            ChoiceOption(
                option_id="s1_opt_worry", text="有点不安……我最近没惹什么麻烦吧？",
                next_node_id="s1_dialogue_heroine_worry",
                effects={"anxiety": 1},
            ),
            ChoiceOption(
                option_id="s1_opt_curious", text="学生会长找我？倒是有点意思。",
                next_node_id="s1_dialogue_heroine_curious",
                effects={"anxiety": -1, "confidence": 1},
            ),
        ],
    ),
    "s1_dialogue_heroine_worry": DialogueNode(
        node_id="s1_dialogue_heroine_worry",
        character_id="heroine", text="……奈奈，你知道是为了什么吗？至少给我一点心理准备。",
        emotion=Emotion.shy, side=Side.left,
        next_node_id="s1_dialogue_friend_3",
    ),
    "s1_dialogue_heroine_curious": DialogueNode(
        node_id="s1_dialogue_heroine_curious",
        character_id="heroine", text="那就让她来找我吧。反正我也没什么好躲的。",
        emotion=Emotion.neutral, side=Side.left,
        next_node_id="s1_dialogue_friend_3",
    ),
    "s1_dialogue_friend_3": DialogueNode(
        node_id="s1_dialogue_friend_3",
        character_id="friend", text="具体我也不知道啦。不过看她的表情，应该不是坏事！我先去教室了，祝你好运~",
        emotion=Emotion.happy, side=Side.right,
        next_node_id="s1_narr_rival_enters",
    ),
    "s1_narr_rival_enters": NarrationNode(
        node_id="s1_narr_rival_enters",
        text="奈奈挥挥手，快步跑远。你刚准备往前走，身后忽然传来一道清亮的声音。",
        background_id="bg_sakura_path",
        next_node_id="s1_dialogue_rival",
    ),
    "s1_dialogue_rival": DialogueNode(
        node_id="s1_dialogue_rival",
        character_id="rival", text="你就是雨宫白吧。我是学生会长朱雀茜。可以占用你五分钟吗？",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s1_end",
    ),
    "s1_end": SceneTransitionNode(
        node_id="s1_end",
        target_scene_id="scene_classroom",
        effect="fade",
    ),
}

# Scene 2: Classroom conversation
SCENE2_NODES: dict = {
    "s2_narr_classroom": NarrationNode(
        node_id="s2_narr_classroom",
        text="空教室里，你们隔着一张课桌面对面坐下。窗外传来运动社团的口号声，午后的光落在桌沿上。",
        background_id="bg_classroom",
        next_node_id="s2_dialogue_rival_1",
    ),
    "s2_dialogue_rival_1": DialogueNode(
        node_id="s2_dialogue_rival_1",
        character_id="rival", text="我就直说了。我希望你加入学生会。",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s2_dialogue_heroine_1",
    ),
    "s2_dialogue_heroine_1": DialogueNode(
        node_id="s2_dialogue_heroine_1",
        character_id="heroine", text="……欸？",
        emotion=Emotion.surprised, side=Side.left,
        next_node_id="s2_dialogue_rival_2",
    ),
    "s2_dialogue_rival_2": DialogueNode(
        node_id="s2_dialogue_rival_2",
        character_id="rival", text="我看过你的资料。成绩很好，文字能力也强。去年校报上那篇获奖文章，我也读过。",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s2_dialogue_rival_3",
    ),
    "s2_dialogue_rival_3": DialogueNode(
        node_id="s2_dialogue_rival_3",
        character_id="rival", text="学生会需要一名书记。与其找一个只想刷履历的人，我更想找真正能做事的人。",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s2_dialogue_heroine_2",
    ),
    "s2_dialogue_heroine_2": DialogueNode(
        node_id="s2_dialogue_heroine_2",
        character_id="heroine", text="……被你看过资料这件事有点微妙。不过，我好像也没有拒绝的理由。",
        emotion=Emotion.shy, side=Side.left,
        next_node_id="s2_dialogue_rival_4",
    ),
    "s2_dialogue_rival_4": DialogueNode(
        node_id="s2_dialogue_rival_4",
        character_id="rival", text="那就这么定了。明天放学后来学生会室报到，不要迟到。",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s2_narr_end",
    ),
    "s2_narr_end": NarrationNode(
        node_id="s2_narr_end",
        text="朱雀茜站起身，制服裙摆划出利落的弧线。她走到门口，又短暂停了一下。",
        background_id="bg_classroom",
        next_node_id="s2_dialogue_rival_final",
    ),
    "s2_dialogue_rival_final": DialogueNode(
        node_id="s2_dialogue_rival_final",
        character_id="rival", text="——我期待你的表现。",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s2_choice",
    ),
    "s2_choice": ChoiceNode(
        node_id="s2_choice",
        text="她的身影消失在门外。你想：",
        options=[
            ChoiceOption(
                option_id="s2_opt_positive", text="……好像也不坏。新学期就当作新的开始吧。",
                next_node_id="s2_ending_positive",
                effects={"confidence": 1, "rival_relation": 1},
            ),
            ChoiceOption(
                option_id="s2_opt_negative", text="真麻烦……希望不要占掉我看书的时间。",
                next_node_id="s2_ending_neutral",
                effects={"anxiety": 1},
            ),
        ],
    ),
    "s2_ending_positive": EndingNode(
        node_id="s2_ending_positive",
        ending_type="neutral",
        epilogue="就这样，你成了学生会书记。看来这个春天的校园生活，不会太无聊。",
    ),
    "s2_ending_neutral": EndingNode(
        node_id="s2_ending_neutral",
        ending_type="neutral",
        epilogue="你叹了口气，收拾书包离开教室。图书馆还开着，至少今晚还能把那本小说读完。",
    ),
}

SCENES: list[Scene] = [
    Scene(
        scene_id="scene_gate",
        title="樱花校门",
        description="新学期第一个早晨，校门口发生的一次相遇。",
        background_id="bg_sakura_path",
        nodes=SCENE1_NODES,
    ),
    Scene(
        scene_id="scene_classroom",
        title="空教室",
        description="与学生会长之间一场直接而意外的谈话。",
        background_id="bg_classroom",
        nodes=SCENE2_NODES,
    ),
]

# ─── Mock ParseDraft ─────────────────────────────────────────────────────────

MOCK_PARSE_DRAFT = ParseDraft(
    draft_id="draft_001",
    project_id="proj_001",
    novel_title="春日轨道",
    novel_excerpt="春天第一个早晨，校门在飘落的花瓣间泛着光。",
    synopsis=(
        "雨宫白在新学期第一天被学生会长朱雀茜邀请加入学生会。"
        "这个 demo 讲述她们第一次见面，以及白如何看待这个突如其来的新开始。"
    ),
    characters=[
        CharacterCue(
            character_id="heroine",
            name="雨宫白",
            role="protagonist",
            description="安静寡言，却总能注意到细节的学生。",
            traits=["安静", "敏锐", "有点固执"],
        ),
        CharacterCue(
            character_id="rival",
            name="朱雀茜",
            role="supporting",
            description="说话利落的学生会长，做事严格，但并不冷漠。",
            traits=["严格", "能干", "不太坦率"],
        ),
        CharacterCue(
            character_id="friend",
            name="朝日奈奈",
            role="supporting",
            description="白开朗的同班同学。",
            traits=["开朗", "话多", "热心"],
        ),
    ],
    locations=["校门", "教室", "学生会室"],
    scenes=SCENES,
    asset_cues=[
        AssetCue(
            asset_id="bg_sakura_path", target_type=AssetType.background,
            description="春天的校门口，樱花花瓣在风中飘落。",
            style_preset="anime_visual_novel",
        ),
        AssetCue(
            asset_id="bg_classroom", target_type=AssetType.background,
            description="午后阳光照进空教室。",
            style_preset="anime_visual_novel",
        ),
    ],
)

# ─── Mock AdaptationProject ──────────────────────────────────────────────────

MOCK_PROJECT = AdaptationProject(
    project_id="proj_001",
    title="春日轨道 第一章",
    author="演示",
    characters=CHARACTERS,
    scenes={s.scene_id: s for s in SCENES},
    start_scene_id="scene_gate",
    variables=[
        {"name": "anxiety", "type": "int", "default": 0, "description": "女主角的不安"},
        {"name": "confidence", "type": "int", "default": 0, "description": "女主角的自信"},
        {"name": "rival_relation", "type": "int", "default": 0, "description": "与学生会长的关系"},
    ],
    asset_resources=ASSETS,
)
