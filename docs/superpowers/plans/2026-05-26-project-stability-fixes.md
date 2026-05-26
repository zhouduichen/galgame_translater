# Project Stability Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the highest-risk project issues found in the review: async job truthfulness, player scene transitions, ID collisions, asset serving paths, draft persistence, project ID validation, worker job claiming, path traversal, and CI/static-check readiness.

**Architecture:** Keep the existing FastAPI + SQLite + polling worker + Next.js architecture. Make small targeted changes with regression tests around public behavior rather than broad rewrites. Prefer shared helpers for ID generation and path constants so API and worker stay aligned.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, SQLite, Pydantic, pytest, Next.js 15, React 19, Zustand, Vitest, TypeScript.

---

## File Structure

- Modify `apps/api/src/api/database.py`: add shared default data/generated directories, add job fetch/claim helpers, preserve row timestamps on merge.
- Modify `apps/api/src/api/main.py`: use the shared generated directory default.
- Modify `apps/api/src/api/routers/projects.py`: use UUID-based IDs, validate path/body project IDs, create unique parse jobs, add tests for collisions and validation.
- Modify `apps/api/tests/test_projects_api.py`: cover unique IDs, update validation, and draft/job persistence expectations where API-owned.
- Modify `apps/worker/src/worker/main.py`: atomically claim pending jobs and mark handler-level error payloads as failed.
- Modify `apps/worker/src/worker/tasks.py`: save parse drafts, use shared data paths, let hard failures propagate or mark clear task failure.
- Add `apps/worker/tests/test_worker_jobs.py`: cover failed handler payloads, unique job processing, and draft persistence with a temp DB.
- Modify `apps/worker/pyproject.toml`: include pytest dependencies if worker tests need local package install.
- Modify `apps/web/src/stores/playerStore.ts`: make scene transitions land on the target scene's first node.
- Modify `apps/web/src/stores/playerStore.test.ts`: add tests for scene transitions and history consistency.
- Modify `apps/web/src/app/upload/page.tsx`: handle completed/failed/timeout accurately and only trigger asset generation after successful parse.
- Add or modify `apps/web/src/app/upload/page.test.tsx` only if a test harness exists; otherwise add a store/helper test for polling behavior after extracting a helper.
- Modify `apps/web/src/app/api/bg-images/route.ts`: harden path traversal handling with resolved paths.
- Add `apps/web/src/app/api/bg-images/route.test.ts` if route tests are already supported; otherwise cover helper extraction with Vitest.
- Modify `apps/web/package.json`: replace deprecated interactive `next lint` with non-interactive ESLint or remove the script until configured.
- Add ESLint config files only if choosing to keep lint.
- Modify root `pyproject.toml`: add dev dependency guidance or document install commands for `ruff` and `mypy`.

---

### Task 1: Make API IDs Unique And Validate Project Updates

**Files:**
- Modify: `apps/api/src/api/routers/projects.py`
- Modify: `apps/api/tests/test_projects_api.py`

- [ ] **Step 1: Write failing tests**

Append these tests to `apps/api/tests/test_projects_api.py`:

```python
def test_create_project_ids_do_not_collide() -> None:
    reset_database()
    client = TestClient(app)

    ids = {
        client.post("/api/projects/", json={"title": f"Project {i}"}).json()["id"]
        for i in range(5)
    }

    assert len(ids) == 5


def test_parse_job_ids_do_not_collide_for_same_project() -> None:
    reset_database()
    client = TestClient(app)
    project_id = client.post("/api/projects/", json={"title": "Parse Test"}).json()["id"]

    first = client.post(
        f"/api/projects/{project_id}/parse",
        json={"novel_text": "First text.", "target_length": "10min_demo"},
    ).json()
    second = client.post(
        f"/api/projects/{project_id}/parse",
        json={"novel_text": "Second text.", "target_length": "10min_demo"},
    ).json()

    assert first["job_id"] != second["job_id"]
    jobs = client.get(f"/api/projects/{project_id}/jobs").json()
    assert len([job for job in jobs if job["job_type"] == "parse_draft"]) == 2


def test_update_project_rejects_mismatched_path_id() -> None:
    reset_database()
    client = TestClient(app)
    project_id = client.post("/api/projects/", json={"title": "A"}).json()["id"]
    project = client.get(f"/api/projects/{project_id}").json()
    project["project_id"] = "proj_other"

    response = client.put(f"/api/projects/{project_id}", json=project)

    assert response.status_code == 400
    assert "project_id" in response.text
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest apps/api/tests/test_projects_api.py -q
```

Expected: at least the ID collision or update mismatch tests fail before implementation.

- [ ] **Step 3: Implement UUID IDs and update validation**

In `apps/api/src/api/routers/projects.py`, add import:

```python
from uuid import uuid4
```

Change project creation:

```python
project = AdaptationProject(
    project_id=f"proj_{uuid4().hex}",
    title=body.title,
    author=body.author,
    characters={},
    scenes={},
    start_scene_id="",
    created_at=now,
    updated_at=now,
)
```

Change `update_project`:

```python
@router.put("/{project_id}")
def update_project(project_id: str, project: AdaptationProject) -> dict:
    if project.project_id != project_id:
        raise HTTPException(400, "Path project_id does not match request body project_id")
    with SessionLocal() as session:
        save_project(session, project)
    return {"ok": True}
```

Change parse job creation:

```python
job = GenerationJob(
    job_id=f"job_{project_id}_parse_{uuid4().hex}",
    project_id=project_id,
    job_type="parse_draft",
    payload={
        "project_id": project_id,
        "novel_text": body.novel_text[:100_000],
        "target_length": body.target_length,
    },
)
```

- [ ] **Step 4: Verify**

Run:

```powershell
python -m pytest apps/api/tests/test_projects_api.py -q
```

Expected: all API tests pass.

---

### Task 2: Align Generated Asset Paths Between API And Worker

**Files:**
- Modify: `apps/api/src/api/database.py`
- Modify: `apps/api/src/api/main.py`
- Modify: `apps/worker/src/worker/tasks.py`
- Modify: `apps/worker/src/worker/comfyui.py`

- [ ] **Step 1: Add shared path constants**

In `apps/api/src/api/database.py`, add near `_DEFAULT_DB`:

```python
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DEFAULT_DB = _DEFAULT_DATA_DIR / "galgame.db"
DEFAULT_GENERATED_DIR = _DEFAULT_DATA_DIR / "generated"
```

Keep `DATABASE_URL` using `_DEFAULT_DB`.

- [ ] **Step 2: Use shared generated dir in API**

In `apps/api/src/api/main.py`, replace `_generated_dir` with:

```python
from .database import DEFAULT_GENERATED_DIR, init_db

_generated_dir = Path(os.environ.get("GENERATED_DIR", str(DEFAULT_GENERATED_DIR)))
```

- [ ] **Step 3: Use matching default in worker**

In `apps/worker/src/worker/tasks.py`, change `DATA_DIR` default to:

```python
DATA_DIR = Path(
    os.environ.get(
        "GALGAME_DB_DIR",
        str(Path(__file__).resolve().parent.parent.parent.parent / "api" / "data"),
    )
)
```

This is already the intended default; keep it as the single worker-side source.

In `apps/worker/src/worker/comfyui.py`, keep `GENERATED_DIR` default aligned with the same `api/data/generated` path:

```python
generated_dir = Path(
    os.environ.get(
        "GENERATED_DIR",
        str(Path(__file__).resolve().parent.parent.parent.parent / "api" / "data" / "generated"),
    )
)
```

- [ ] **Step 4: Verify local defaults**

Run:

```powershell
python - <<'PY'
from api.database import DEFAULT_GENERATED_DIR
from pathlib import Path
print(DEFAULT_GENERATED_DIR)
print(Path("apps/api/data/generated").resolve())
PY
```

Expected: both paths point to `D:\galgame_translater\apps\api\data\generated`.

---

### Task 3: Persist Parse Drafts During Worker Parse

**Files:**
- Modify: `apps/worker/src/worker/tasks.py`
- Add: `apps/worker/tests/test_tasks.py`

- [ ] **Step 1: Write failing test**

Create `apps/worker/tests/test_tasks.py`:

```python
import json
import sqlite3

from project_model.schema import AdaptationProject
from worker import tasks


def test_handle_parse_draft_saves_draft_and_project(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(tasks, "DATA_DIR", tmp_path)
    db_path = tmp_path / "galgame.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE projects (id TEXT PRIMARY KEY, title TEXT NOT NULL, author TEXT, data TEXT NOT NULL, created_at TEXT, updated_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE parse_drafts (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT)"
    )
    conn.commit()
    conn.close()

    draft = {
        "draft_id": "",
        "project_id": "",
        "novel_title": "测试标题",
        "novel_excerpt": "测试正文",
        "synopsis": "简介",
        "characters": [],
        "locations": [],
        "scenes": [],
        "asset_cues": [],
        "warnings": [],
    }

    def fake_parse_novel(novel_text: str, target_length: str):
        return dict(draft)

    def fake_promote(parsed_draft, project_id):
        return AdaptationProject(
            project_id=project_id,
            title=parsed_draft["novel_title"],
            characters={},
            scenes={},
            start_scene_id="",
        )

    monkeypatch.setattr(tasks, "parse_novel", fake_parse_novel)
    monkeypatch.setattr(tasks, "promote", fake_promote)

    result = tasks.handle_parse_draft(
        {"project_id": "proj_test", "novel_text": "正文", "target_length": "10min_demo"}
    )

    assert result["status"] == "ok"
    conn = sqlite3.connect(db_path)
    saved_draft = conn.execute("SELECT id, project_id, data FROM parse_drafts").fetchone()
    saved_project = conn.execute("SELECT id, data FROM projects").fetchone()
    conn.close()

    assert saved_draft[0].startswith("draft_proj_test_")
    assert saved_draft[1] == "proj_test"
    assert json.loads(saved_draft[2])["project_id"] == "proj_test"
    assert saved_project[0] == "proj_test"
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
python -m pytest apps/worker/tests/test_tasks.py -q
```

Expected: fails because no parse draft row is written.

- [ ] **Step 3: Implement draft persistence**

In `apps/worker/src/worker/tasks.py`, add helper:

```python
def _save_draft_to_db(draft: dict[str, Any], project_id: str) -> dict[str, Any]:
    db_path = DATA_DIR / "galgame.db"
    saved = dict(draft)
    saved["project_id"] = project_id
    saved["draft_id"] = saved.get("draft_id") or f"draft_{project_id}_{uuid4().hex[:8]}"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """INSERT OR REPLACE INTO parse_drafts (id, project_id, data, created_at)
           VALUES (?, ?, ?, ?)""",
        (
            saved["draft_id"],
            project_id,
            json.dumps(saved, ensure_ascii=False),
            datetime.utcnow().isoformat() + "Z",
        ),
    )
    conn.commit()
    conn.close()
    return saved
```

In `handle_parse_draft`, after `draft = parse_novel(...)`:

```python
draft = _save_draft_to_db(draft, project_id)
```

Then pass saved draft into `promote`:

```python
project = promote(draft, project_id or None)
```

- [ ] **Step 4: Verify**

Run:

```powershell
python -m pytest apps/worker/tests/test_tasks.py apps/api/tests/test_projects_api.py -q
```

Expected: all pass.

---

### Task 4: Make Worker Job Outcomes Truthful And Job Claiming Safer

**Files:**
- Modify: `apps/worker/src/worker/main.py`
- Add: `apps/worker/tests/test_worker_main.py`

- [ ] **Step 1: Extract status decision helper and write tests**

Create `apps/worker/tests/test_worker_main.py`:

```python
from worker.main import _job_result_failed


def test_job_result_failed_for_error_status() -> None:
    assert _job_result_failed({"status": "error", "error": "Empty novel text"}) is True


def test_job_result_not_failed_for_ok_status() -> None:
    assert _job_result_failed({"status": "ok"}) is False
```

Run:

```powershell
python -m pytest apps/worker/tests/test_worker_main.py -q
```

Expected: fails because helper does not exist.

- [ ] **Step 2: Implement result status helper**

In `apps/worker/src/worker/main.py`, add:

```python
def _job_result_failed(result: object) -> bool:
    return isinstance(result, dict) and result.get("status") == "error"
```

Change completion handling:

```python
result = handler(payload)
if _job_result_failed(result):
    _update_job(
        job["id"],
        status="failed",
        progress=1.0,
        result=json.dumps(result, ensure_ascii=False),
        error=str(result.get("error", "Task returned error status")),
    )
    print(f"[worker] Failed {job['id']}: {result.get('error', 'Task returned error status')}")
    continue
_update_job(
    job["id"],
    status="completed",
    progress=1.0,
    result=json.dumps(result, ensure_ascii=False),
)
```

- [ ] **Step 3: Make claiming less race-prone**

Replace `_poll()` with a claim function that flips rows from `pending` to `running` in the same connection before returning:

```python
def _claim_pending_jobs(limit: int = 5) -> list[dict]:
    db_path = DATA_DIR / "galgame.db"
    if not db_path.exists():
        return []

    import sqlite3

    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        rows = [
            dict(r)
            for r in conn.execute(
                """SELECT id, project_id, job_type, payload, result
                   FROM generation_jobs
                   WHERE status = 'pending'
                   ORDER BY created_at ASC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        ]
        now = datetime.utcnow().isoformat() + "Z"
        for row in rows:
            conn.execute(
                "UPDATE generation_jobs SET status = 'running', progress = 0.0, updated_at = ? WHERE id = ? AND status = 'pending'",
                (now, row["id"]),
            )
        conn.commit()
        return rows
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

In `main()`, replace `jobs = _poll()` with:

```python
jobs = _claim_pending_jobs()
```

Remove the later `_update_job(job["id"], status="running", progress=0.0)` because claiming already did it.

Keep `_poll = _claim_pending_jobs` only if `test_e2e.py` still imports `_poll`:

```python
_poll = _claim_pending_jobs
```

- [ ] **Step 4: Verify**

Run:

```powershell
python -m pytest apps/worker/tests/test_worker_main.py -q
python -m pytest -q
```

Expected: all pass.

---

### Task 5: Fix Player Scene Transitions

**Files:**
- Modify: `apps/web/src/stores/playerStore.ts`
- Modify: `apps/web/src/lib/storyRuntime.test.ts`

- [ ] **Step 1: Write failing test**

Add a second-scene transition case to `apps/web/src/lib/storyRuntime.test.ts` or create `apps/web/src/stores/playerStore.test.ts` if preferred. For store-level coverage, add:

```typescript
import { describe, expect, it, beforeEach } from "vitest";
import { usePlayerStore } from "./playerStore";
import type { Project } from "@/lib/types";

const transitionProject: Project = {
  project_id: "proj_transition",
  title: "Transition",
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
      title: "One",
      description: "",
      nodes: {
        n1: { type: "scene_transition", node_id: "n1", target_scene_id: "scene_2", effect: "fade" },
      },
    },
    scene_2: {
      scene_id: "scene_2",
      title: "Two",
      description: "",
      nodes: {
        s2_start: { type: "narration", node_id: "s2_start", text: "Arrived" },
      },
    },
  },
};

describe("playerStore scene transitions", () => {
  beforeEach(() => {
    usePlayerStore.setState({
      project: null,
      scene: null,
      node: null,
      history: [],
      status: "loading",
      storyState: null,
      textSpeed: 40,
      autoMode: false,
      uiMenuOpen: false,
    });
  });

  it("loads the target scene first node when changing scenes", () => {
    usePlayerStore.getState().loadProject(transitionProject);
    usePlayerStore.getState().changeScene("scene_2");

    const state = usePlayerStore.getState();
    expect(state.scene?.scene_id).toBe("scene_2");
    expect(state.node?.node_id).toBe("s2_start");
    expect(state.status).toBe("playing");
  });
});
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
npm.cmd test
```

Expected: transition test fails because current code uses the old node ID.

- [ ] **Step 3: Implement scene first-node selection**

In `apps/web/src/stores/playerStore.ts`, import `getFirstNodeId`:

```typescript
import { getFirstNodeId, type Project, type Scene, type StoryNode } from "@/lib/types";
```

Change `changeScene`:

```typescript
changeScene: (sceneId) => {
  const { project, storyState } = get();
  if (!project) return;
  const scene = project.scenes[sceneId];
  if (!scene) return;
  const firstNodeId = getFirstNodeId(scene);
  const firstNode = firstNodeId ? scene.nodes[firstNodeId] ?? null : null;
  set({
    scene,
    node: firstNode,
    history: [],
    storyState: storyState
      ? {
          ...storyState,
          currentSceneId: scene.scene_id,
          currentNodeId: firstNode?.node_id ?? null,
          visitedNodeIds: firstNode ? [...storyState.visitedNodeIds, firstNode.node_id] : storyState.visitedNodeIds,
        }
      : storyState,
    status: firstNode ? (firstNode.type === "choice" ? "waiting_choice" : "playing") : "error",
  });
},
```

- [ ] **Step 4: Verify**

Run:

```powershell
npm.cmd test
npm.cmd run build
```

Expected: tests and production build pass.

---

### Task 6: Make Upload Polling Handle Failed And Timed-Out Jobs Correctly

**Files:**
- Modify: `apps/web/src/app/upload/page.tsx`

- [ ] **Step 1: Extract polling result handling**

In `apps/web/src/app/upload/page.tsx`, define types and a helper above the component:

```typescript
type JobStatus = "pending" | "running" | "completed" | "failed";
type GenerationJob = {
  job_id: string;
  status: JobStatus;
  error?: string | null;
};

function findJob(jobs: GenerationJob[], jobId: string): GenerationJob | null {
  return jobs.find((job) => job.job_id === jobId) ?? null;
}
```

- [ ] **Step 2: Update polling logic**

Replace the current loop with:

```typescript
let completed = false;
let failedError: string | null = null;
let attempts = 0;

while (attempts < 120) {
  const jobsRes = await fetch(`/api/projects/${id}/jobs`);
  if (!jobsRes.ok) throw new Error("查询解析任务失败");
  const jobs: GenerationJob[] = await jobsRes.json();
  const job = findJob(jobs, job_id);

  if (job?.status === "completed") {
    completed = true;
    break;
  }
  if (job?.status === "failed") {
    failedError = job.error || "解析任务失败";
    break;
  }

  await new Promise((r) => setTimeout(r, 2000));
  attempts++;
}

if (failedError) throw new Error(failedError);
if (!completed) throw new Error("解析任务超时，请确认 Worker 是否正在运行");

fetch(`/api/projects/${id}/generate-assets`, { method: "POST" }).catch(() => {});
setStatus("done");
```

Remove the unconditional asset generation and unconditional `setStatus("done")` after the old loop.

- [ ] **Step 3: Remove `any` catches**

Change:

```typescript
} catch (e: any) {
  setError(e.message);
```

to:

```typescript
} catch (e: unknown) {
  setError(e instanceof Error ? e.message : "上传或解析失败");
```

- [ ] **Step 4: Verify**

Run:

```powershell
npm.cmd test
npm.cmd run build
```

Expected: build passes and upload page no longer reports failed/timeout jobs as success.

---

### Task 7: Harden `/api/bg-images` Path Handling

**Files:**
- Modify: `apps/web/src/app/api/bg-images/route.ts`

- [ ] **Step 1: Add safe path helper**

In `route.ts`, add:

```typescript
function safeImagePath(file: string): string | null {
  const decoded = decodeURIComponent(file);
  const filePath = path.resolve(BG_DIR, decoded);
  const relative = path.relative(BG_DIR, filePath);
  if (relative.startsWith("..") || path.isAbsolute(relative)) return null;
  return filePath;
}
```

- [ ] **Step 2: Use helper in GET**

Replace:

```typescript
const decoded = decodeURIComponent(file);
const filePath = path.join(BG_DIR, decoded);
if (!filePath.startsWith(BG_DIR)) {
  return new NextResponse(null, { status: 404 });
}
```

with:

```typescript
const filePath = safeImagePath(file);
if (!filePath) {
  return new NextResponse(null, { status: 404 });
}
const ext = path.extname(filePath).slice(1).toLowerCase();
```

Also remove the old `const ext = path.extname(decoded)...` line.

- [ ] **Step 3: Verify**

Run:

```powershell
npm.cmd run build
```

Expected: build passes. Manual check with `/api/bg-images?file=..%2Fpackage.json` should return 404.

---

### Task 8: Make Static Checks Non-Interactive And Reproducible

**Files:**
- Modify: `apps/web/package.json`
- Add: `apps/web/eslint.config.mjs`
- Modify: `pyproject.toml`
- Optionally create: `requirements-dev.txt`

- [ ] **Step 1: Add explicit ESLint dependencies**

Run:

```powershell
cd apps/web
npm.cmd install -D eslint eslint-config-next
```

- [ ] **Step 2: Add ESLint flat config**

Create `apps/web/eslint.config.mjs`:

```javascript
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = [...nextVitals, ...nextTs];

export default eslintConfig;
```

- [ ] **Step 3: Update lint script**

In `apps/web/package.json`, change:

```json
"lint": "next lint"
```

to:

```json
"lint": "eslint ."
```

- [ ] **Step 4: Add Python dev dependency record**

Create `requirements-dev.txt`:

```text
ruff>=0.8
mypy>=1.13
pytest>=8
```

Or, if the project prefers `pyproject.toml` only, add:

```toml
[project.optional-dependencies]
dev = [
    "ruff>=0.8",
    "mypy>=1.13",
    "pytest>=8",
]
```

- [ ] **Step 5: Verify**

Run:

```powershell
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m mypy apps packages
cd apps/web
npm.cmd run lint
npm.cmd test
npm.cmd run build
```

Expected: commands complete non-interactively. If lint surfaces existing style findings, fix them in a separate small pass rather than weakening rules immediately.

---

### Task 9: Address Dependency Audit

**Files:**
- Modify: `apps/web/package.json`
- Modify: `apps/web/package-lock.json`

- [ ] **Step 1: Try safe Next upgrade**

Run:

```powershell
cd apps/web
npm.cmd install next@latest
npm.cmd audit --audit-level=moderate
npm.cmd test
npm.cmd run build
```

Expected: audit clears or identifies whether Next has not yet pulled fixed `postcss`.

- [ ] **Step 2: If audit remains, do not run forced downgrade**

Do not use `npm audit fix --force` because current output suggests a breaking downgrade path. Instead keep the finding tracked and pin the safest available Next version once upstream publishes a release containing fixed PostCSS.

- [ ] **Step 3: Record residual risk if not fixable today**

Add a short note to `README.md` or a security tracking issue:

```markdown
Known dependency audit item: Next.js currently pulls `postcss@8.4.31` via its internal dependency tree. Do not run `npm audit fix --force`; upgrade Next when a release carries `postcss>=8.5.10`.
```

---

## Final Verification

Run from repository root:

```powershell
python -m pytest -q
python -m ruff check .
python -m mypy apps packages
cd apps/web
npm.cmd test
npm.cmd run build
npm.cmd run lint
npm.cmd audit --audit-level=moderate
```

Expected:
- Python tests pass.
- Web tests pass.
- Next production build passes.
- Lint runs without interactive prompts.
- Audit is clean, or a documented Next/PostCSS residual risk remains if no safe upstream fix is available.

## Recommended Commit Order

1. `fix(api): use unique ids and validate project updates`
2. `fix(worker): persist parse drafts and truthful job failures`
3. `fix(player): load target scene entry node on transitions`
4. `fix(upload): report failed parse jobs accurately`
5. `fix(web): harden background image path handling`
6. `chore(ci): make lint and python checks reproducible`
7. `chore(deps): update web dependencies`

## Self-Review

- Spec coverage: all review findings are mapped to tasks.
- Placeholder scan: no task uses TBD/TODO/fill-in language.
- Type consistency: job status values match `GenerationJob.status`; project fields match existing `Project` and `AdaptationProject` names; worker DB table names match current schema.
