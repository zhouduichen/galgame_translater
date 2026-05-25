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
        character_id="heroine", name="白雨", role="protagonist",
        description="沉默寡言但内心细腻的少女，喜欢在教室窗边看书。",
        traits=["安静", "善于观察", "倔强"],
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
        character_id="rival", name="朱雀院 椿", role="supporting",
        description="学生会会长，气质凛然的优等生，对主角抱有复杂的竞争心。",
        traits=["严格", "优秀", "外冷内热"],
        color="#ff6688",
        asset_ids={
            Emotion.neutral: "sprite_rival_neutral",
            Emotion.angry: "sprite_rival_angry",
        },
    ),
    "friend": Character(
        character_id="friend", name="朝日 奏", role="supporting",
        description="主角的同班好友，元气满满的吐槽役。",
        traits=["开朗", "话多", "热心"],
        color="#ffcc44",
        asset_ids={
            Emotion.neutral: "sprite_friend_neutral",
            Emotion.happy: "sprite_friend_happy",
        },
    ),
}

# ─── Scenes ──────────────────────────────────────────────────────────────────

# Scene 1: 校门口偶遇
SCENE1_NODES: dict = {
    "s1_narr_start": NarrationNode(
        node_id="s1_narr_start",
        text="春天清晨，樱花纷飞的校门口。新学期第一天，空气中弥漫着花粉和新鲜感的气味。",
        background_id="bg_sakura_path",
        next_node_id="s1_dialogue_friend",
    ),
    "s1_dialogue_friend": DialogueNode(
        node_id="s1_dialogue_friend",
        character_id="friend", text="早啊白雨！新学期第一天就这么没精神，昨晚又熬夜看书了？",
        emotion=Emotion.happy, side=Side.right,
        next_node_id="s1_dialogue_heroine_1",
    ),
    "s1_dialogue_heroine_1": DialogueNode(
        node_id="s1_dialogue_heroine_1",
        character_id="heroine", text="……嗯。小说看完了最后一章，没控制住时间。",
        emotion=Emotion.neutral, side=Side.left,
        next_node_id="s1_dialogue_friend_2",
    ),
    "s1_dialogue_friend_2": DialogueNode(
        node_id="s1_dialogue_friend_2",
        character_id="friend", text="哈哈哈，果然是你！对了，听说今天转学生会会长要来找你，你知道吗？",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s1_dialogue_heroine_2",
    ),
    "s1_dialogue_heroine_2": DialogueNode(
        node_id="s1_dialogue_heroine_2",
        character_id="heroine", text="……找我？我好像没做什么会被记过的事。",
        emotion=Emotion.neutral, side=Side.left,
        next_node_id="s1_choice",
    ),
    "s1_choice": ChoiceNode(
        node_id="s1_choice",
        text="听到这个消息，你心想：",
        options=[
            ChoiceOption(
                option_id="s1_opt_worry", text="有点不安……我最近没惹事吧？",
                next_node_id="s1_dialogue_heroine_worry",
                effects={"anxiety": 1},
            ),
            ChoiceOption(
                option_id="s1_opt_curious", text="会长找我？有意思。",
                next_node_id="s1_dialogue_heroine_curious",
                effects={"anxiety": -1, "confidence": 1},
            ),
        ],
    ),
    "s1_dialogue_heroine_worry": DialogueNode(
        node_id="s1_dialogue_heroine_worry",
        character_id="heroine", text="……奏，你知不知道是什么事？给我点心理准备。",
        emotion=Emotion.shy, side=Side.left,
        next_node_id="s1_dialogue_friend_3",
    ),
    "s1_dialogue_heroine_curious": DialogueNode(
        node_id="s1_dialogue_heroine_curious",
        character_id="heroine", text="那就让她来找我好啦，反正我也没什么好躲的。",
        emotion=Emotion.neutral, side=Side.left,
        next_node_id="s1_dialogue_friend_3",
    ),
    "s1_dialogue_friend_3": DialogueNode(
        node_id="s1_dialogue_friend_3",
        character_id="friend", text="我也不清楚详情——不过看她的表情，不像是坏事哦！我先去教室了，你加油～",
        emotion=Emotion.happy, side=Side.right,
        next_node_id="s1_narr_rival_enters",
    ),
    "s1_narr_rival_enters": NarrationNode(
        node_id="s1_narr_rival_enters",
        text="奏挥挥手跑开了。你正要迈步，身后传来清冽的声音。",
        background_id="bg_sakura_path",
        next_node_id="s1_dialogue_rival",
    ),
    "s1_dialogue_rival": DialogueNode(
        node_id="s1_dialogue_rival",
        character_id="rival", text="你就是白雨同学吧。我是学生会会长，朱雀院椿。占用你五分钟。",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s1_end",
    ),
    "s1_end": SceneTransitionNode(
        node_id="s1_end",
        target_scene_id="scene_classroom",
        effect="fade",
    ),
}

# Scene 2: 教室谈判
SCENE2_NODES: dict = {
    "s2_narr_classroom": NarrationNode(
        node_id="s2_narr_classroom",
        text="空无一人的教室里，两人隔着一张课桌相对而坐。窗外传来运动部的吆喝声。",
        background_id="bg_classroom",
        next_node_id="s2_dialogue_rival_1",
    ),
    "s2_dialogue_rival_1": DialogueNode(
        node_id="s2_dialogue_rival_1",
        character_id="rival", text="开门见山地说——我希望你加入学生会。",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s2_dialogue_heroine_1",
    ),
    "s2_dialogue_heroine_1": DialogueNode(
        node_id="s2_dialogue_heroine_1",
        character_id="heroine", text="……哈？",
        emotion=Emotion.surprised, side=Side.left,
        next_node_id="s2_dialogue_rival_2",
    ),
    "s2_dialogue_rival_2": DialogueNode(
        node_id="s2_dialogue_rival_2",
        character_id="rival", text="我调查过你的履历。成绩优秀，文笔出色，去年校刊的获奖作品我读过了。",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s2_dialogue_rival_3",
    ),
    "s2_dialogue_rival_3": DialogueNode(
        node_id="s2_dialogue_rival_3",
        character_id="rival", text="学生会现在缺一个书记。与其从那些只想在简历里添一笔的家伙里挑，不如找真正有能力的人。",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s2_dialogue_heroine_2",
    ),
    "s2_dialogue_heroine_2": DialogueNode(
        node_id="s2_dialogue_heroine_2",
        character_id="heroine", text="……被你看过底牌的感觉真不好。不过我确实没理由拒绝。",
        emotion=Emotion.shy, side=Side.left,
        next_node_id="s2_dialogue_rival_4",
    ),
    "s2_dialogue_rival_4": DialogueNode(
        node_id="s2_dialogue_rival_4",
        character_id="rival", text="那就这么定了。明天放学后到学生会室报到。别迟到。",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s2_narr_end",
    ),
    "s2_narr_end": NarrationNode(
        node_id="s2_narr_end",
        text="朱雀院椿站起身，校服裙摆划出一道利落的弧线。她走到门口时停顿了一下。",
        background_id="bg_classroom",
        next_node_id="s2_dialogue_rival_final",
    ),
    "s2_dialogue_rival_final": DialogueNode(
        node_id="s2_dialogue_rival_final",
        character_id="rival", text="——期待你的表现。",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s2_choice",
    ),
    "s2_choice": ChoiceNode(
        node_id="s2_choice",
        text="她的背影消失在门后，你心想：",
        options=[
            ChoiceOption(
                option_id="s2_opt_positive", text="……好像也不坏。新学期有个新开始。",
                next_node_id="s2_ending_positive",
                effects={"confidence": 1, "rival_relation": 1},
            ),
            ChoiceOption(
                option_id="s2_opt_negative", text="麻烦……希望别占用太多看书的时间。",
                next_node_id="s2_ending_neutral",
                effects={"anxiety": 1},
            ),
        ],
    ),
    "s2_ending_positive": EndingNode(
        node_id="s2_ending_positive",
        ending_type="neutral",
        epilogue="就这样，你成为了学生会书记。未来的校园生活，似乎不会太无聊了。",
    ),
    "s2_ending_neutral": EndingNode(
        node_id="s2_ending_neutral",
        ending_type="neutral",
        epilogue="你叹了口气，收拾好书包走出教室。图书馆今天还开着，至少今晚能把那本小说读完。",
    ),
}

SCENES: list[Scene] = [
    Scene(
        scene_id="scene_gate",
        title="樱花校门",
        description="新学期第一天，校门口的偶遇。",
        background_id="bg_sakura_path",
        nodes=SCENE1_NODES,
    ),
    Scene(
        scene_id="scene_classroom",
        title="空教室的对话",
        description="与学生会长的第一次正面交锋。",
        background_id="bg_classroom",
        nodes=SCENE2_NODES,
    ),
]

# ─── Mock ParseDraft ─────────────────────────────────────────────────────────

MOCK_PARSE_DRAFT = ParseDraft(
    draft_id="draft_001",
    project_id="proj_001",
    novel_title="春日の軌跡",
    novel_excerpt="春天清晨，樱花纷飞的校门口...",
    synopsis="内向少女白雨在高中新学期被学生会会长看中，被迫（？）加入学生会，"
             "在与个性鲜明的成员们相处的过程中逐渐打开心扉的故事。",
    characters=[
        CharacterCue(
            character_id="heroine", name="白雨", role="protagonist",
            description="沉默寡言但内心细腻的少女，喜欢看书。",
            traits=["安静", "善于观察", "倔强"],
        ),
        CharacterCue(
            character_id="rival", name="朱雀院 椿", role="supporting",
            description="学生会会长，气质凛然。",
            traits=["严格", "优秀", "外冷内热"],
        ),
        CharacterCue(
            character_id="friend", name="朝日 奏", role="supporting",
            description="主角的同班好友。",
            traits=["开朗", "话多", "热心"],
        ),
    ],
    locations=["校门口", "教室", "学生会室", " rooftop"],
    scenes=SCENES,
    asset_cues=[
        AssetCue(
            asset_id="bg_sakura_path", target_type=AssetType.background,
            description="春天的樱花校门，花瓣纷飞", style_preset="anime_visual_novel",
        ),
        AssetCue(
            asset_id="bg_classroom", target_type=AssetType.background,
            description="午后阳光充足的教室", style_preset="anime_visual_novel",
        ),
        AssetCue(
            asset_id="bg_rooftop", target_type=AssetType.background,
            description="黄昏的天台，铁丝网围栏", style_preset="anime_visual_novel",
        ),
    ],
)

# ─── Mock AdaptationProject ──────────────────────────────────────────────────

MOCK_PROJECT = AdaptationProject(
    project_id="proj_001",
    title="春日の軌跡 - 第一章",
    author="demo",
    characters=CHARACTERS,
    scenes={s.scene_id: s for s in SCENES},
    variables=[
        {"name": "anxiety", "type": "int", "default": 0, "description": "主角的不安值"},
        {"name": "confidence", "type": "int", "default": 0, "description": "主角的自信值"},
        {"name": "rival_relation", "type": "int", "default": 0, "description": "与朱雀院椿的关系"},
    ],
    asset_resources=ASSETS,
)
