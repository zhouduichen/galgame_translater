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
        name="Haku Ame",
        role="protagonist",
        description="A quiet but observant student who reads novels by the classroom window.",
        traits=["quiet", "observant", "stubborn"],
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
        name="Akane Suzume",
        role="supporting",
        description="The strict student council president, admired for her precision and poise.",
        traits=["strict", "talented", "secretly kind"],
        color="#ff6688",
        asset_ids={
            Emotion.neutral: "sprite_rival_neutral",
            Emotion.angry: "sprite_rival_angry",
        },
    ),
    "friend": Character(
        character_id="friend",
        name="Nana Asahi",
        role="supporting",
        description="The heroine's energetic classmate and informal emotional support.",
        traits=["bright", "talkative", "helpful"],
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
        text="Spring morning at the school gate, cherry blossoms drifting in the air. The first day of a new semester, carrying the scent of pollen and fresh beginnings.",
        background_id="bg_sakura_path",
        next_node_id="s1_dialogue_friend",
    ),
    "s1_dialogue_friend": DialogueNode(
        node_id="s1_dialogue_friend",
        character_id="friend", text="Morning, Ame! You look half asleep again — stayed up reading last night?",
        emotion=Emotion.happy, side=Side.right,
        next_node_id="s1_dialogue_heroine_1",
    ),
    "s1_dialogue_heroine_1": DialogueNode(
        node_id="s1_dialogue_heroine_1",
        character_id="heroine", text="...Yeah. Finished the last chapter of my novel. Lost track of time.",
        emotion=Emotion.neutral, side=Side.left,
        next_node_id="s1_dialogue_friend_2",
    ),
    "s1_dialogue_friend_2": DialogueNode(
        node_id="s1_dialogue_friend_2",
        character_id="friend", text="Haha, that's so you! Oh hey, did you know the student council president is looking for you today?",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s1_dialogue_heroine_2",
    ),
    "s1_dialogue_heroine_2": DialogueNode(
        node_id="s1_dialogue_heroine_2",
        character_id="heroine", text="...Looking for me? I don't think I've done anything worth a reprimand.",
        emotion=Emotion.neutral, side=Side.left,
        next_node_id="s1_choice",
    ),
    "s1_choice": ChoiceNode(
        node_id="s1_choice",
        text="Hearing this, you think:",
        options=[
            ChoiceOption(
                option_id="s1_opt_worry", text="A bit uneasy... I haven't been in trouble lately, have I?",
                next_node_id="s1_dialogue_heroine_worry",
                effects={"anxiety": 1},
            ),
            ChoiceOption(
                option_id="s1_opt_curious", text="The president wants to see me? Interesting.",
                next_node_id="s1_dialogue_heroine_curious",
                effects={"anxiety": -1, "confidence": 1},
            ),
        ],
    ),
    "s1_dialogue_heroine_worry": DialogueNode(
        node_id="s1_dialogue_heroine_worry",
        character_id="heroine", text="...Nana, do you know what it's about? Give me a heads-up at least.",
        emotion=Emotion.shy, side=Side.left,
        next_node_id="s1_dialogue_friend_3",
    ),
    "s1_dialogue_heroine_curious": DialogueNode(
        node_id="s1_dialogue_heroine_curious",
        character_id="heroine", text="Let her come find me, then. It's not like I have anything to hide.",
        emotion=Emotion.neutral, side=Side.left,
        next_node_id="s1_dialogue_friend_3",
    ),
    "s1_dialogue_friend_3": DialogueNode(
        node_id="s1_dialogue_friend_3",
        character_id="friend", text="I don't know the details — but from the look on her face, it didn't seem bad! I'll head to class first. Good luck~",
        emotion=Emotion.happy, side=Side.right,
        next_node_id="s1_narr_rival_enters",
    ),
    "s1_narr_rival_enters": NarrationNode(
        node_id="s1_narr_rival_enters",
        text="Nana waves and runs off. Just as you're about to step forward, a clear voice calls out from behind you.",
        background_id="bg_sakura_path",
        next_node_id="s1_dialogue_rival",
    ),
    "s1_dialogue_rival": DialogueNode(
        node_id="s1_dialogue_rival",
        character_id="rival", text="You must be Haku Ame. I'm Akane Suzume, student council president. I need five minutes of your time.",
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
        text="In the empty classroom, the two of you sit across from each other at a desk. The sounds of sports clubs drift in through the window.",
        background_id="bg_classroom",
        next_node_id="s2_dialogue_rival_1",
    ),
    "s2_dialogue_rival_1": DialogueNode(
        node_id="s2_dialogue_rival_1",
        character_id="rival", text="I'll be direct — I'd like you to join the student council.",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s2_dialogue_heroine_1",
    ),
    "s2_dialogue_heroine_1": DialogueNode(
        node_id="s2_dialogue_heroine_1",
        character_id="heroine", text="...Huh?",
        emotion=Emotion.surprised, side=Side.left,
        next_node_id="s2_dialogue_rival_2",
    ),
    "s2_dialogue_rival_2": DialogueNode(
        node_id="s2_dialogue_rival_2",
        character_id="rival", text="I checked your records. Excellent grades, strong writing skills — I read your award-winning piece in last year's school paper.",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s2_dialogue_rival_3",
    ),
    "s2_dialogue_rival_3": DialogueNode(
        node_id="s2_dialogue_rival_3",
        character_id="rival", text="The council needs a secretary. I'd rather pick someone capable than someone just padding their resume.",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s2_dialogue_heroine_2",
    ),
    "s2_dialogue_heroine_2": DialogueNode(
        node_id="s2_dialogue_heroine_2",
        character_id="heroine", text="...It's uncomfortable knowing you've read my file. But I don't really have a reason to refuse.",
        emotion=Emotion.shy, side=Side.left,
        next_node_id="s2_dialogue_rival_4",
    ),
    "s2_dialogue_rival_4": DialogueNode(
        node_id="s2_dialogue_rival_4",
        character_id="rival", text="Then it's settled. Report to the council room after school tomorrow. Don't be late.",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s2_narr_end",
    ),
    "s2_narr_end": NarrationNode(
        node_id="s2_narr_end",
        text="Akane Suzume stands up, her uniform skirt tracing a sharp arc. She pauses at the door.",
        background_id="bg_classroom",
        next_node_id="s2_dialogue_rival_final",
    ),
    "s2_dialogue_rival_final": DialogueNode(
        node_id="s2_dialogue_rival_final",
        character_id="rival", text="— I look forward to seeing what you can do.",
        emotion=Emotion.neutral, side=Side.right,
        next_node_id="s2_choice",
    ),
    "s2_choice": ChoiceNode(
        node_id="s2_choice",
        text="Her silhouette disappears beyond the door. You think:",
        options=[
            ChoiceOption(
                option_id="s2_opt_positive", text="...Doesn't seem so bad. A new start for the new semester.",
                next_node_id="s2_ending_positive",
                effects={"confidence": 1, "rival_relation": 1},
            ),
            ChoiceOption(
                option_id="s2_opt_negative", text="What a hassle... hope it doesn't cut into my reading time.",
                next_node_id="s2_ending_neutral",
                effects={"anxiety": 1},
            ),
        ],
    ),
    "s2_ending_positive": EndingNode(
        node_id="s2_ending_positive",
        ending_type="neutral",
        epilogue="And so, you became the student council secretary. It seems like campus life won't be boring after all.",
    ),
    "s2_ending_neutral": EndingNode(
        node_id="s2_ending_neutral",
        ending_type="neutral",
        epilogue="You sigh, pack your bag, and leave the classroom. The library is still open — at least you can finish that novel tonight.",
    ),
}

SCENES: list[Scene] = [
    Scene(
        scene_id="scene_gate",
        title="Sakura School Gate",
        description="A first-morning encounter at the school gate.",
        background_id="bg_sakura_path",
        nodes=SCENE1_NODES,
    ),
    Scene(
        scene_id="scene_classroom",
        title="Empty Classroom",
        description="A direct conversation with the student council president.",
        background_id="bg_classroom",
        nodes=SCENE2_NODES,
    ),
]

# ─── Mock ParseDraft ─────────────────────────────────────────────────────────

MOCK_PARSE_DRAFT = ParseDraft(
    draft_id="draft_001",
    project_id="proj_001",
    novel_title="Spring Rail",
    novel_excerpt="The school gate glimmered under drifting petals on the first morning of spring.",
    synopsis=(
        "Haku Ame is invited into the student council by Akane Suzume, a strict president "
        "who has already read Haku's writing. The demo follows their first meeting and "
        "Haku's choice to treat the new semester as a chance or a burden."
    ),
    characters=[
        CharacterCue(
            character_id="heroine",
            name="Haku Ame",
            role="protagonist",
            description="A quiet student who notices more than she says.",
            traits=["quiet", "observant", "stubborn"],
        ),
        CharacterCue(
            character_id="rival",
            name="Akane Suzume",
            role="supporting",
            description="Student council president with a precise way of speaking.",
            traits=["strict", "talented", "secretly kind"],
        ),
        CharacterCue(
            character_id="friend",
            name="Nana Asahi",
            role="supporting",
            description="Haku's cheerful classmate.",
            traits=["bright", "talkative", "helpful"],
        ),
    ],
    locations=["school gate", "classroom", "student council room"],
    scenes=SCENES,
    asset_cues=[
        AssetCue(
            asset_id="bg_sakura_path", target_type=AssetType.background,
            description="Spring school gate with drifting sakura petals.",
            style_preset="anime_visual_novel",
        ),
        AssetCue(
            asset_id="bg_classroom", target_type=AssetType.background,
            description="Empty classroom lit by afternoon sun.",
            style_preset="anime_visual_novel",
        ),
    ],
)

# ─── Mock AdaptationProject ──────────────────────────────────────────────────

MOCK_PROJECT = AdaptationProject(
    project_id="proj_001",
    title="Spring Rail - Chapter One",
    author="demo",
    characters=CHARACTERS,
    scenes={s.scene_id: s for s in SCENES},
    start_scene_id="scene_gate",
    variables=[
        {"name": "anxiety", "type": "int", "default": 0, "description": "Heroine unease"},
        {"name": "confidence", "type": "int", "default": 0, "description": "Heroine confidence"},
        {"name": "rival_relation", "type": "int", "default": 0, "description": "Relationship with the council president"},
    ],
    asset_resources=ASSETS,
)
