# Foundation Player Editor Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the current MVP foundation so the shared ProjectModel, mock demo, Web player, single-scene editor, and API persistence have tests and clear boundaries.

**Architecture:** The repository already contains a partial implementation under `apps/api`, `apps/web`, `apps/worker`, and `packages/project-model`. This plan keeps the current FastAPI + Next.js + SQLite + worker-loop direction, then adds tests, fixes schema defaults, removes corrupted mock fixture text, and moves runtime branching logic into pure functions before adding more LLM or export work.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, Pydantic v2, pytest, Next.js 15, React 19, TypeScript, Zustand, Vitest.

---

## Current State

The workspace already has these important files:

- `README.md`: MVP architecture notes and dev commands.
- `pyproject.toml`: root Python tooling configuration.
- `packages/project-model/src/project_model/schema.py`: Pydantic model definitions.
- `packages/project-model/src/project_model/mock_data.py`: mock `ParseDraft` and `AdaptationProject` fixture, currently with unreadable mojibake text.
- `apps/api/src/api/main.py`: FastAPI application.
- `apps/api/src/api/database.py`: SQLite-backed persistence, currently hard-coded to `sqlite:///data/galgame.db`.
- `apps/api/src/api/routers/projects.py`: project CRUD, draft, parse job, and export stub routes.
- `apps/web/src/lib/types.ts`: hand-written TypeScript mirror of the project model.
- `apps/web/src/stores/playerStore.ts`: Zustand player store.
- `apps/web/src/stores/editorStore.ts`: Zustand editor store.
- `apps/web/src/components/player/*`: Web player components.
- `apps/web/src/components/editor/*`: single-scene editor components.

Baseline verification observed before writing this plan:

- `python -m pytest -q` runs but reports `no tests ran`.
- `npm run build` fails in PowerShell because `npm.ps1` is blocked by execution policy.
- `npm.cmd run build` succeeds from `apps/web`.
- The directory is not a git repository, so commits require `git init` first.

## File Structure To Create Or Modify

### Repository And Docs

- Modify: `.gitignore`
- Modify: `README.md`
- Create: `docs/architecture/current-state.md`

### Project Model

- Modify: `packages/project-model/src/project_model/schema.py`
- Replace fixture text in: `packages/project-model/src/project_model/mock_data.py`
- Create: `packages/project-model/tests/test_schema.py`
- Create: `packages/project-model/tests/test_mock_data.py`

### API

- Modify: `apps/api/src/api/database.py`
- Modify: `apps/api/src/api/routers/projects.py`
- Create: `apps/api/tests/test_projects_api.py`

### Web

- Modify: `apps/web/package.json`
- Modify: `apps/web/src/lib/types.ts`
- Create: `apps/web/src/lib/storyRuntime.ts`
- Create: `apps/web/src/lib/storyRuntime.test.ts`
- Modify: `apps/web/src/stores/playerStore.ts`
- Modify: `apps/web/src/stores/editorStore.ts`
- Create: `apps/web/src/stores/editorStore.test.ts`

## Commit Policy

Because the workspace is not currently a git repository, Task 1 initializes git and makes the first baseline commit. Each later task ends with one small commit. Do not add `apps/web/node_modules`, `apps/web/.next`, `apps/api/data`, or `apps/api/uploads`.

---

### Task 1: Repository Baseline And Documentation

**Files:**

- Modify: `.gitignore`
- Modify: `README.md`
- Create: `docs/architecture/current-state.md`

- [ ] **Step 1: Confirm generated paths are ignored**

Run:

```powershell
Get-Content .gitignore
```

Expected: it contains these entries:

```gitignore
node_modules/
.next/
*.db
apps/api/data/
apps/api/uploads/
```

If any entry is missing, add it to `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/
env/
.coverage
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Node
node_modules/
.next/
out/
*.tsbuildinfo

# Database
*.db
*.sqlite

# Environment
.env
.env.local
.env.*.local

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Generated runtime data
apps/api/data/
apps/api/uploads/
```

- [ ] **Step 2: Add current-state architecture note**

Create `docs/architecture/current-state.md` with this content:

```markdown
# Current State

This repository contains a partial MVP implementation for converting uploaded novel text into a playable visual novel demo.

## Verified Baseline

- Frontend production build passes on Windows with `npm.cmd run build` from `apps/web`.
- Python test discovery works from the root with `python -m pytest -q`, but there are no tests yet.
- The workspace is not initialized as a git repository before Task 1.

## Existing Modules

- `packages/project-model`: Pydantic schemas and mock data.
- `apps/api`: FastAPI API, SQLite persistence, project and job routes.
- `apps/web`: Next.js player and editor.
- `apps/worker`: background worker and staged parser entry points.

## Known Gaps

- The mock data file contains mojibake text and should be replaced with a clean ASCII fixture.
- Pydantic models use mutable defaults in several fields.
- `AdaptationProject` does not explicitly define `start_scene_id`.
- Frontend story runtime logic is embedded in Zustand store actions.
- The backend database URL is hard-coded.
- API and frontend runtime tests are missing.
```

- [ ] **Step 3: Update README Windows command note**

In `README.md`, replace the frontend command block with:

```markdown
# Frontend
cd apps/web
npm install
npm.cmd run dev

# Frontend production build on Windows PowerShell
npm.cmd run build
```

Keep the rest of the README architecture content intact.

- [ ] **Step 4: Verify current build baseline**

Run:

```powershell
python -m pytest -q
```

Expected:

```text
no tests ran
```

Run:

```powershell
npm.cmd run build
```

from `apps/web`.

Expected: Next.js build completes successfully.

- [ ] **Step 5: Initialize git and commit baseline**

Run from repository root:

```powershell
git init
git status --short
git add .gitignore README.md docs/superpowers/specs/2026-05-24-novel-to-galgame-mvp-design.md docs/superpowers/plans/2026-05-25-foundation-player-editor-stabilization.md docs/architecture/current-state.md pyproject.toml apps/api apps/worker apps/web/src apps/web/package.json apps/web/package-lock.json apps/web/next.config.ts apps/web/postcss.config.js apps/web/tsconfig.json apps/web/next-env.d.ts packages test_pipeline.py
git commit -m "chore: capture current mvp foundation"
```

Expected: a first commit is created without `node_modules`, `.next`, database files, or uploads.

---

### Task 2: Add ProjectModel Tests Before Schema Changes

**Files:**

- Create: `packages/project-model/tests/test_schema.py`
- Create: `packages/project-model/tests/test_mock_data.py`

- [ ] **Step 1: Create schema tests**

Create `packages/project-model/tests/test_schema.py`:

```python
from project_model.schema import (
    AdaptationProject,
    Character,
    CharacterCue,
    ChoiceNode,
    ChoiceOption,
    DialogueNode,
    Emotion,
    NarrationNode,
    Scene,
)


def test_character_default_lists_are_independent() -> None:
    first = CharacterCue(character_id="a", name="A", description="First")
    second = CharacterCue(character_id="b", name="B", description="Second")

    first.traits.append("quiet")

    assert first.traits == ["quiet"]
    assert second.traits == []


def test_character_asset_maps_are_independent() -> None:
    first = Character(character_id="a", name="A", description="First")
    second = Character(character_id="b", name="B", description="Second")

    first.asset_ids[Emotion.neutral] = "sprite_a_neutral"

    assert first.asset_ids == {Emotion.neutral: "sprite_a_neutral"}
    assert second.asset_ids == {}


def test_scene_first_node_id_uses_incoming_edges() -> None:
    scene = Scene(
        scene_id="scene_opening",
        title="Opening",
        nodes={
            "n2": DialogueNode(
                node_id="n2",
                character_id="heroine",
                text="Good morning.",
            ),
            "n1": NarrationNode(
                node_id="n1",
                text="The first bell rang.",
                next_node_id="n2",
            ),
        },
    )

    assert scene.first_node_id() == "n1"


def test_choice_node_requires_at_least_one_option() -> None:
    node = ChoiceNode(
        node_id="choice_1",
        text="What will you do?",
        options=[
            ChoiceOption(
                option_id="opt_1",
                text="Answer",
                next_node_id="n2",
            )
        ],
    )

    assert node.options[0].text == "Answer"


def test_project_requires_start_scene_id_after_schema_update() -> None:
    project = AdaptationProject(
        project_id="proj_test",
        title="Test",
        characters={},
        scenes={
            "scene_opening": Scene(
                scene_id="scene_opening",
                title="Opening",
                nodes={
                    "n1": NarrationNode(node_id="n1", text="Start"),
                },
            )
        },
        start_scene_id="scene_opening",
    )

    assert project.start_scene_id == "scene_opening"
```

- [ ] **Step 2: Create mock data tests**

Create `packages/project-model/tests/test_mock_data.py`:

```python
from project_model.mock_data import MOCK_PARSE_DRAFT, MOCK_PROJECT


def test_mock_project_has_start_scene() -> None:
    assert MOCK_PROJECT.start_scene_id in MOCK_PROJECT.scenes


def test_mock_project_has_readable_ascii_fixture_text() -> None:
    assert MOCK_PROJECT.title == "Spring Rail - Chapter One"
    assert MOCK_PROJECT.characters["heroine"].name == "Haku Ame"
    assert "school gate" in MOCK_PROJECT.scenes["scene_gate"].description.lower()


def test_mock_project_first_scene_can_start() -> None:
    scene = MOCK_PROJECT.scenes[MOCK_PROJECT.start_scene_id]

    first_node_id = scene.first_node_id()

    assert first_node_id == "s1_narr_start"
    assert first_node_id in scene.nodes


def test_mock_parse_draft_matches_project_id() -> None:
    assert MOCK_PARSE_DRAFT.project_id == MOCK_PROJECT.project_id
    assert MOCK_PARSE_DRAFT.scenes[0].scene_id == MOCK_PROJECT.start_scene_id
```

- [ ] **Step 3: Run tests and confirm expected failures**

Run:

```powershell
python -m pytest packages/project-model/tests -q
```

Expected: tests fail because `AdaptationProject` has no `start_scene_id`, mutable defaults are still present, and mock fixture text is not readable.

- [ ] **Step 4: Commit failing tests**

Run:

```powershell
git add packages/project-model/tests
git commit -m "test(project-model): capture schema and fixture expectations"
```

Expected: commit records tests that describe the desired model behavior.

---

### Task 3: Stabilize Pydantic Schema Defaults And Start Scene

**Files:**

- Modify: `packages/project-model/src/project_model/schema.py`

- [ ] **Step 1: Replace mutable defaults with factories**

In `packages/project-model/src/project_model/schema.py`, update list and dict defaults to `Field(default_factory=...)`.

Use these exact field definitions in the relevant models:

```python
class CharacterCue(BaseModel):
    """Draft-level character info from LLM parsing."""

    character_id: str
    name: str
    role: str = "supporting"
    description: str
    traits: list[str] = Field(default_factory=list)
    color: str | None = None


class Character(CharacterCue):
    """Full character definition in an AdaptationProject."""

    asset_ids: dict[Emotion, str] = Field(default_factory=dict)
```

Update `ChoiceOption.effects`, `ParseDraft.characters`, `ParseDraft.locations`, `ParseDraft.scenes`, `ParseDraft.asset_cues`, `ParseDraft.variables`, `ParseDraft.warnings`, `AdaptationProject.variables`, `AdaptationProject.asset_resources`, `ExportArtifact.metadata`, `GenerationJob.payload`, and `GenerationJob.result` the same way:

```python
effects: dict[str, Any] = Field(default_factory=dict)
characters: list[CharacterCue] = Field(default_factory=list)
locations: list[str] = Field(default_factory=list)
scenes: list[Scene] = Field(default_factory=list)
asset_cues: list[AssetCue] = Field(default_factory=list)
variables: list[dict[str, Any]] = Field(default_factory=list)
warnings: list[str] = Field(default_factory=list)
asset_resources: dict[str, AssetResource] = Field(default_factory=dict)
metadata: dict[str, Any] = Field(default_factory=dict)
payload: dict[str, Any] = Field(default_factory=dict)
result: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 2: Add `start_scene_id` to `AdaptationProject`**

Replace the `AdaptationProject` class header and fields with:

```python
class AdaptationProject(BaseModel):
    """The canonical, edited project model used by the player and editor."""

    project_id: str
    title: str
    author: str = ""
    characters: dict[str, Character] = Field(default_factory=dict)
    scenes: dict[str, Scene] = Field(default_factory=dict)
    start_scene_id: str
    variables: list[dict[str, Any]] = Field(default_factory=list)
    asset_resources: dict[str, AssetResource] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    version: int = 1

    def model_post_init(self, __context: Any) -> None:
        now = datetime.utcnow().isoformat() + "Z"
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
```

- [ ] **Step 3: Update project creation route for `start_scene_id`**

In `apps/api/src/api/routers/projects.py`, update `create_project` to pass an empty start scene ID:

```python
project = AdaptationProject(
    project_id=f"proj_{int(datetime.utcnow().timestamp())}",
    title=body.title,
    author=body.author,
    characters={},
    scenes={},
    start_scene_id="",
    created_at=now,
    updated_at=now,
)
```

This keeps empty projects valid before the parser creates their first scene.

- [ ] **Step 4: Run model tests**

Run:

```powershell
python -m pytest packages/project-model/tests/test_schema.py -q
```

Expected: schema tests pass except mock data tests, which still fail until Task 4.

- [ ] **Step 5: Commit schema stabilization**

Run:

```powershell
git add packages/project-model/src/project_model/schema.py apps/api/src/api/routers/projects.py
git commit -m "fix(project-model): stabilize schema defaults and start scene"
```

---

### Task 4: Replace Corrupted Mock Fixture With Clean Demo Data

**Files:**

- Modify: `packages/project-model/src/project_model/mock_data.py`

- [ ] **Step 1: Replace human-readable fixture values**

Edit `packages/project-model/src/project_model/mock_data.py` so the mock project uses readable ASCII text. Keep the same IDs already used by the player and editor.

The top-level project must end with:

```python
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
```

The character names must be:

```python
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
```

Scene titles and descriptions must be:

```python
Scene(
    scene_id="scene_gate",
    title="Sakura School Gate",
    description="A first-morning encounter at the school gate.",
    background_id="bg_sakura_path",
    nodes=SCENE1_NODES,
)

Scene(
    scene_id="scene_classroom",
    title="Empty Classroom",
    description="A direct conversation with the student council president.",
    background_id="bg_classroom",
    nodes=SCENE2_NODES,
)
```

Use English dialogue for all nodes. Preserve the node IDs, choice IDs, scene IDs, and asset IDs currently present in the file so the frontend keeps working.

- [ ] **Step 2: Update mock `ParseDraft`**

Set `MOCK_PARSE_DRAFT` to:

```python
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
            asset_id="bg_sakura_path",
            target_type=AssetType.background,
            description="Spring school gate with drifting sakura petals.",
            style_preset="anime_visual_novel",
        ),
        AssetCue(
            asset_id="bg_classroom",
            target_type=AssetType.background,
            description="Empty classroom lit by afternoon sun.",
            style_preset="anime_visual_novel",
        ),
    ],
)
```

- [ ] **Step 3: Run mock data tests**

Run:

```powershell
python -m pytest packages/project-model/tests -q
```

Expected: all project model tests pass.

- [ ] **Step 4: Commit mock fixture cleanup**

Run:

```powershell
git add packages/project-model/src/project_model/mock_data.py packages/project-model/tests
git commit -m "test(project-model): use readable mock adaptation fixture"
```

---

### Task 5: Add Frontend Test Harness And Story Runtime

**Files:**

- Modify: `apps/web/package.json`
- Create: `apps/web/src/lib/storyRuntime.ts`
- Create: `apps/web/src/lib/storyRuntime.test.ts`
- Modify: `apps/web/src/lib/types.ts`

- [ ] **Step 1: Install Vitest**

Run from `apps/web`:

```powershell
npm.cmd install -D vitest
```

Expected: `package.json` and `package-lock.json` update with `vitest`.

- [ ] **Step 2: Add test script**

In `apps/web/package.json`, add:

```json
"test": "vitest run"
```

The scripts block should become:

```json
"scripts": {
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "next lint",
  "test": "vitest run"
}
```

- [ ] **Step 3: Add `start_scene_id` to TypeScript project type**

In `apps/web/src/lib/types.ts`, update `Project`:

```ts
export type Project = {
  project_id: string;
  title: string;
  author: string;
  characters: Record<string, Character>;
  scenes: Record<string, Scene>;
  start_scene_id: string;
  asset_resources: Record<string, AssetResource>;
  variables: { name: string; type: string; default: string | number | boolean }[];
  created_at: string;
  updated_at: string;
  version: number;
};
```

- [ ] **Step 4: Create failing runtime tests**

Create `apps/web/src/lib/storyRuntime.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import {
  applyChoiceEffects,
  getInitialStoryState,
  getNodeAfterChoice,
  getNextLinearNode,
} from "./storyRuntime";
import type { Project } from "./types";

const project: Project = {
  project_id: "proj_test",
  title: "Test",
  author: "",
  characters: {},
  asset_resources: {},
  variables: [
    { name: "confidence", type: "int", default: 0 },
    { name: "has_key", type: "bool", default: false },
  ],
  start_scene_id: "scene_start",
  created_at: "",
  updated_at: "",
  version: 1,
  scenes: {
    scene_start: {
      scene_id: "scene_start",
      title: "Start",
      description: "",
      nodes: {
        n1: { type: "narration", node_id: "n1", text: "Start", next_node_id: "choice" },
        choice: {
          type: "choice",
          node_id: "choice",
          text: "Choose",
          options: [
            {
              option_id: "take",
              text: "Take the key",
              next_node_id: "n2",
              effects: { confidence: 1, has_key: true },
            },
          ],
        },
        n2: { type: "narration", node_id: "n2", text: "Done" },
      },
    },
  },
};

describe("storyRuntime", () => {
  it("starts from the explicit start scene", () => {
    const state = getInitialStoryState(project);

    expect(state.currentSceneId).toBe("scene_start");
    expect(state.currentNodeId).toBe("n1");
    expect(state.variables).toEqual({ confidence: 0, has_key: false });
  });

  it("finds the next linear node", () => {
    const scene = project.scenes.scene_start;
    const next = getNextLinearNode(scene, scene.nodes.n1);

    expect(next?.node_id).toBe("choice");
  });

  it("applies choice effects without mutating previous variables", () => {
    const next = applyChoiceEffects({ confidence: 0, has_key: false }, { confidence: 1, has_key: true });

    expect(next).toEqual({ confidence: 1, has_key: true });
  });

  it("resolves a choice target node", () => {
    const scene = project.scenes.scene_start;
    const node = scene.nodes.choice;
    if (node.type !== "choice") throw new Error("expected choice node");

    const target = getNodeAfterChoice(scene, node.options[0]);

    expect(target?.node_id).toBe("n2");
  });
});
```

- [ ] **Step 5: Run frontend tests and confirm expected failure**

Run from `apps/web`:

```powershell
npm.cmd run test
```

Expected: test fails because `storyRuntime.ts` does not exist.

- [ ] **Step 6: Implement story runtime**

Create `apps/web/src/lib/storyRuntime.ts`:

```ts
import type { ChoiceOption, Project, Scene, StoryNode } from "./types";
import { getFirstNodeId } from "./types";

export type StoryVariables = Record<string, string | number | boolean>;

export type StoryState = {
  currentSceneId: string;
  currentNodeId: string | null;
  variables: StoryVariables;
  visitedNodeIds: string[];
  history: { sceneId: string; nodeId: string }[];
};

function defaultVariableValue(type: string): string | number | boolean {
  if (type === "int" || type === "number") return 0;
  if (type === "bool" || type === "boolean") return false;
  return "";
}

export function getInitialVariables(project: Project): StoryVariables {
  return Object.fromEntries(
    project.variables.map((variable) => [
      variable.name,
      variable.default ?? defaultVariableValue(variable.type),
    ]),
  );
}

export function getInitialStoryState(project: Project): StoryState {
  const sceneId = project.start_scene_id || Object.keys(project.scenes)[0] || "";
  const scene = project.scenes[sceneId];
  const firstNodeId = scene ? getFirstNodeId(scene) : null;

  return {
    currentSceneId: sceneId,
    currentNodeId: firstNodeId,
    variables: getInitialVariables(project),
    visitedNodeIds: firstNodeId ? [firstNodeId] : [],
    history: [],
  };
}

export function getNode(scene: Scene | undefined, nodeId: string | null): StoryNode | null {
  if (!scene || !nodeId) return null;
  return scene.nodes[nodeId] ?? null;
}

export function getNextLinearNode(scene: Scene, node: StoryNode): StoryNode | null {
  if (!("next_node_id" in node) || !node.next_node_id) return null;
  return scene.nodes[node.next_node_id] ?? null;
}

export function getNodeAfterChoice(scene: Scene, option: ChoiceOption): StoryNode | null {
  return scene.nodes[option.next_node_id] ?? null;
}

export function applyChoiceEffects(
  variables: StoryVariables,
  effects: Record<string, string | number | boolean> = {},
): StoryVariables {
  return {
    ...variables,
    ...effects,
  };
}
```

- [ ] **Step 7: Run frontend tests and build**

Run:

```powershell
npm.cmd run test
npm.cmd run build
```

from `apps/web`.

Expected: tests and production build pass.

- [ ] **Step 8: Commit frontend runtime foundation**

Run:

```powershell
git add apps/web/package.json apps/web/package-lock.json apps/web/src/lib/types.ts apps/web/src/lib/storyRuntime.ts apps/web/src/lib/storyRuntime.test.ts
git commit -m "test(web): add story runtime coverage"
```

---

### Task 6: Wire Player Store To Story Runtime

**Files:**

- Modify: `apps/web/src/stores/playerStore.ts`

- [ ] **Step 1: Update player store state fields**

In `apps/web/src/stores/playerStore.ts`, import runtime helpers:

```ts
import {
  applyChoiceEffects,
  getInitialStoryState,
  getNode,
  getNodeAfterChoice,
  getNextLinearNode,
  type StoryState,
} from "@/lib/storyRuntime";
```

Add `storyState` to `PlayerState`:

```ts
storyState: StoryState | null;
chooseOption: (optionId: string) => void;
advance: () => void;
```

Initialize it:

```ts
storyState: null,
```

- [ ] **Step 2: Use `start_scene_id` in `loadProject`**

Replace the current `loadProject` action with:

```ts
loadProject: (project) => {
  const storyState = getInitialStoryState(project);
  const scene = project.scenes[storyState.currentSceneId] ?? null;
  const node = getNode(scene ?? undefined, storyState.currentNodeId);

  set({
    project,
    storyState,
    scene,
    node,
    history: [],
    status: node ? (node.type === "choice" ? "waiting_choice" : "playing") : "error",
  });
},
```

- [ ] **Step 3: Add `advance` action**

Add this action:

```ts
advance: () => {
  const { scene, node, goTo } = get();
  if (!scene || !node) return;
  const next = getNextLinearNode(scene, node);
  if (next) goTo(next);
},
```

- [ ] **Step 4: Add `chooseOption` action**

Add this action:

```ts
chooseOption: (optionId) => {
  const { scene, node, storyState, goTo } = get();
  if (!scene || !node || node.type !== "choice" || !storyState) return;
  const option = node.options.find((item) => item.option_id === optionId);
  if (!option) return;

  const target = getNodeAfterChoice(scene, option);
  if (!target) return;

  set({
    storyState: {
      ...storyState,
      variables: applyChoiceEffects(storyState.variables, option.effects),
    },
  });
  goTo(target);
},
```

- [ ] **Step 5: Update `goTo` to maintain story state**

Inside `goTo`, update `storyState` when moving nodes:

```ts
goTo: (node) => {
  const { node: current, scene, storyState } = get();
  if (!scene) return;
  const nextStoryState = storyState
    ? {
        ...storyState,
        currentSceneId: scene.scene_id,
        currentNodeId: node.node_id,
        visitedNodeIds: [...storyState.visitedNodeIds, node.node_id],
        history: current
          ? [...storyState.history, { sceneId: scene.scene_id, nodeId: current.node_id }]
          : storyState.history,
      }
    : null;

  set((s) => ({
    storyState: nextStoryState,
    history: current ? [...s.history, current] : s.history,
    node,
    status:
      node.type === "choice"
        ? "waiting_choice"
        : node.type === "ending"
          ? "ended"
          : node.type === "scene_transition"
            ? "transitioning"
            : "playing",
  }));

  if (node.type === "scene_transition" && node.target_scene_id) {
    setTimeout(() => get().changeScene(node.target_scene_id), 600);
  }
},
```

- [ ] **Step 6: Use player actions in `PlayerContainer`**

In `apps/web/src/components/player/PlayerContainer.tsx`, replace direct next-node click handlers with `advance()` and choice option IDs with `chooseOption()`.

For dialogue and narration:

```tsx
const { scene, history, advance, chooseOption, goBack, restartScene, toggleAutoMode, setTextSpeed } = store;
```

Use:

```tsx
onClick={advance}
```

For choices:

```tsx
onChoose={(opt) => chooseOption(opt.option_id)}
```

Update auto-advance to call `store.advance()` instead of manually resolving `next_node_id`.

- [ ] **Step 7: Verify player wiring**

Run:

```powershell
npm.cmd run test
npm.cmd run build
```

from `apps/web`.

Expected: tests and build pass.

- [ ] **Step 8: Commit player runtime wiring**

Run:

```powershell
git add apps/web/src/stores/playerStore.ts apps/web/src/components/player/PlayerContainer.tsx
git commit -m "feat(web): route player transitions through story runtime"
```

---

### Task 7: Stabilize Editor Store Persistence And Node Ordering

**Files:**

- Modify: `apps/web/src/stores/editorStore.ts`
- Create: `apps/web/src/stores/editorStore.test.ts`

- [ ] **Step 1: Add editor store tests**

Create `apps/web/src/stores/editorStore.test.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useEditorStore } from "./editorStore";
import type { Project } from "@/lib/types";

const project: Project = {
  project_id: "proj_editor",
  title: "Editor Test",
  author: "",
  characters: {},
  asset_resources: {},
  variables: [],
  start_scene_id: "scene_1",
  created_at: "",
  updated_at: "",
  version: 1,
  scenes: {
    scene_1: {
      scene_id: "scene_1",
      title: "Scene",
      description: "",
      nodes: {
        n1: { type: "narration", node_id: "n1", text: "One", next_node_id: "n2" },
        n2: { type: "narration", node_id: "n2", text: "Two" },
      },
    },
  },
};

describe("editorStore", () => {
  beforeEach(() => {
    useEditorStore.setState({
      project: null,
      currentSceneId: null,
      selectedNodeId: null,
      dirty: false,
    });
    vi.restoreAllMocks();
  });

  it("loads the explicit start scene", () => {
    useEditorStore.getState().loadProject(project);

    expect(useEditorStore.getState().currentSceneId).toBe("scene_1");
  });

  it("marks project dirty after editing a node", () => {
    useEditorStore.getState().loadProject(project);
    useEditorStore.getState().updateNode("n1", { text: "Changed" });

    const updated = useEditorStore.getState().project;
    expect(updated?.scenes.scene_1.nodes.n1).toMatchObject({ text: "Changed" });
    expect(useEditorStore.getState().dirty).toBe(true);
  });

  it("persists through the shared API helper", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    useEditorStore.getState().loadProject(project);
    await useEditorStore.getState().saveProject();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/proj_editor",
      expect.objectContaining({ method: "PUT" }),
    );
    expect(useEditorStore.getState().dirty).toBe(false);
  });
});
```

- [ ] **Step 2: Update editor load to use `start_scene_id`**

In `apps/web/src/stores/editorStore.ts`, replace `loadProject` with:

```ts
loadProject: (project) => {
  const sceneId = project.start_scene_id || Object.keys(project.scenes)[0] || null;
  set({
    project,
    currentSceneId: sceneId,
    selectedNodeId: null,
    dirty: false,
  });
},
```

- [ ] **Step 3: Replace raw fetch save with the API helper**

Import the API helper:

```ts
import { api } from "@/lib/api";
```

Replace `saveProject` with:

```ts
saveProject: async () => {
  const { project } = get();
  if (!project) return;
  await api.updateProject(project);
  set({ dirty: false });
},
```

- [ ] **Step 4: Run editor tests and build**

Run:

```powershell
npm.cmd run test
npm.cmd run build
```

from `apps/web`.

Expected: tests and build pass.

- [ ] **Step 5: Commit editor stabilization**

Run:

```powershell
git add apps/web/src/stores/editorStore.ts apps/web/src/stores/editorStore.test.ts
git commit -m "test(web): cover editor store persistence"
```

---

### Task 8: Add API Test Isolation And Route Coverage

**Files:**

- Modify: `apps/api/src/api/database.py`
- Modify: `apps/api/src/api/main.py`
- Create: `apps/api/tests/test_projects_api.py`

- [ ] **Step 1: Make database URL configurable**

In `apps/api/src/api/database.py`, add:

```python
import os
```

Replace:

```python
SQLITE_URL = "sqlite:///data/galgame.db"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
```

with:

```python
DATABASE_URL = os.getenv("GALGAME_DATABASE_URL", "sqlite:///data/galgame.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine)
```

- [ ] **Step 2: Move DB initialization to FastAPI startup**

In `apps/api/src/api/main.py`, import `init_db`:

```python
from .database import init_db
```

Add:

```python
@app.on_event("startup")
def startup() -> None:
    init_db()
```

Remove the router-level `@router.on_event("startup")` block from `apps/api/src/api/routers/projects.py`.

- [ ] **Step 3: Add API tests**

Create `apps/api/tests/test_projects_api.py`:

```python
import os

os.environ["GALGAME_DATABASE_URL"] = "sqlite:///./test_galgame_api.db"

from fastapi.testclient import TestClient

from api.database import Base, engine, init_db
from api.main import app


def reset_database() -> None:
    Base.metadata.drop_all(engine)
    init_db()


def test_health() -> None:
    reset_database()
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_and_load_project() -> None:
    reset_database()
    client = TestClient(app)

    create_response = client.post("/api/projects/", json={"title": "API Test", "author": "tester"})

    assert create_response.status_code == 200
    project_id = create_response.json()["id"]

    load_response = client.get(f"/api/projects/{project_id}")

    assert load_response.status_code == 200
    body = load_response.json()
    assert body["title"] == "API Test"
    assert body["author"] == "tester"
    assert body["start_scene_id"] == ""


def test_parse_request_creates_job() -> None:
    reset_database()
    client = TestClient(app)

    project_id = client.post("/api/projects/", json={"title": "Parse Test"}).json()["id"]
    response = client.post(
        f"/api/projects/{project_id}/parse",
        json={"novel_text": "The bell rang. She looked up.", "target_length": "10min_demo"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project_id
    assert body["job_type"] == "parse_draft"
    assert body["status"] == "pending"
```

- [ ] **Step 4: Run API tests**

Run from repository root:

```powershell
python -m pytest apps/api/tests -q
```

Expected: API tests pass.

- [ ] **Step 5: Commit API test coverage**

Run:

```powershell
git add apps/api/src/api/database.py apps/api/src/api/main.py apps/api/src/api/routers/projects.py apps/api/tests/test_projects_api.py
git commit -m "test(api): cover project routes with isolated database"
```

---

### Task 9: Final Foundation Verification

**Files:**

- Modify: `README.md`

- [ ] **Step 1: Add verification commands to README**

Add this section to `README.md`:

````markdown
## Verification

```bash
python -m pytest -q
cd apps/web
npm.cmd run test
npm.cmd run build
```

Use `npm.cmd` on Windows PowerShell to avoid the local script execution policy blocking `npm.ps1`.
````

- [ ] **Step 2: Run full Python tests**

Run from repository root:

```powershell
python -m pytest -q
```

Expected: project model and API tests pass.

- [ ] **Step 3: Run frontend tests and build**

Run from `apps/web`:

```powershell
npm.cmd run test
npm.cmd run build
```

Expected: Vitest and Next.js production build pass.

- [ ] **Step 4: Check git status**

Run:

```powershell
git status --short
```

Expected: only intentional README changes are unstaged before the final commit.

- [ ] **Step 5: Commit verification docs**

Run:

```powershell
git add README.md
git commit -m "docs: add foundation verification commands"
```

## Handoff Criteria

This plan is complete when:

- The repository is initialized with git.
- `python -m pytest -q` passes.
- `npm.cmd run test` passes from `apps/web`.
- `npm.cmd run build` passes from `apps/web`.
- The mock project fixture is readable.
- `AdaptationProject` has `start_scene_id`.
- ProjectModel mutable defaults are removed.
- The player uses pure runtime functions for initial state, linear advance, and choice effects.
- The editor saves through the shared API helper.
- API tests cover health, project creation, project loading, and parse job creation.

## Next Plan After This

After this foundation plan passes, write a separate implementation plan for:

```text
ParseDraft -> AdaptationProject converter
upload endpoint
worker job execution
staged parser with mock LLM responses
```

Do not start Ren'Py export or ComfyUI integration until the converter and upload flow are tested.
