# Data Flow Architecture

## Overview

The pipeline converts a novel text into a playable visual novel through three canonical data stages:

```
Upload (.txt/.md)
    │
    ▼
┌──────────────┐     LLM      ┌──────────────┐
│  ParseDraft  │ ◄─────────── │  Novel Text  │
│  (draft)     │              │  (raw)       │
└──────┬───────┘
       │ validate & edit
       ▼
┌──────────────────┐
│ AdaptationProject│  ◄── Web Player consumes this
│  (canonical)     │  ◄── Editor modifies this
└──────┬───────────┘
       │ export
       ▼
┌──────────────────┐
│ ExportArtifact   │  ──► .rpy / zip
│  (snapshot)      │
└──────────────────┘
```

## Stage 1: ParseDraft

**Source:** LLM output from novel text parsing.

**Schema:** `project_model.schema.ParseDraft`

**Characteristics:**
- Contains `CharacterCue` (lightweight, draft-quality)
- Contains `Scene` objects with full node graphs
- Contains `AssetCue` declarations (what's needed)
- May have warnings or inconsistencies
- NOT directly playable without validation

**Validation rules applied before Promotion:**
- All `next_node_id` references resolve within the scene
- Choice option targets exist
- Character references in dialogue nodes exist
- No dangling branches

## Stage 2: AdaptationProject

**Source:** Validated and edited ParseDraft, or manual creation.

**Schema:** `project_model.schema.AdaptationProject`

**Characteristics:**
- Characters stored as `dict[str, Character]` (keyed by ID)
- Scenes stored as `dict[str, Scene]` (keyed by ID)
- Full `Character` objects with emotion→asset mappings
- `AssetResource` records for all generated/uploaded assets
- `variables` define the story state model
- MUST pass schema validation
- IS the source of truth for player and editor

**Persistence:** Serialized as JSON in SQLite `projects` table.

## Stage 3: ExportArtifact

**Source:** Snapshot of an AdaptationProject at export time.

**Schema:** `project_model.schema.ExportArtifact`

**Characteristics:**
- One-directional reference to project_id
- Does NOT back-link to project (project is source of truth)
- Records file path, format, size, timestamp
- NOT involved in editing or playback

---

## Module Responsibilities

### packages/project-model/
- Pydantic schemas for all three stages
- No external dependencies beyond Pydantic
- No SQL, no I/O
- Single source of truth for data shape

### apps/api/
- FastAPI HTTP layer
- CRUD for projects, drafts, jobs
- SQLite persistence via SQLAlchemy
- File upload and storage
- Proxy for worker job submission

### apps/worker/
- Polls `generation_jobs` table
- Routes to handler by `job_type`
- Three handler types: `parse_draft`, `generate_asset`, `export_renpy`
- Each handler is a callable: `(payload: dict) -> result: dict`

### apps/web/
- Next.js with App Router
- Consumes API via `/api/*` (rewritten to backend in dev)
- Zustand stores for editor and player state
- DOM/CSS-based visual novel player

---

## Asset Model

```
AssetCue          │    AssetResource
──────────────────┼─────────────────────
"What I need"     │    "What I have"
demand side       │    supply side
                  │
- type            │    - id
- character_id    │    - url
- emotion         │    - generator
- description     │    - seed
- style_preset    │    - width/height
```

- `AssetCue` lives in `ParseDraft` — declares what assets the draft needs
- `AssetResource` lives in `AdaptationProject` — records what's actually available
- Player falls back to placeholder when a referenced `AssetResource` is missing

## Variable & Branch Model

Variables are defined in `AdaptationProject.variables`:

```json
{
  "name": "affection_heroine",
  "type": "int",
  "default": 0
}
```

Branching uses:
- `BranchNode.condition`: expression string like `"affection_heroine >= 3"`
- `ChoiceOption.condition`: optional gate on the option
- `ChoiceOption.effects`: variable mutations on selection

Condition expressions are intentionally simple strings — evaluated by a minimal expression engine (not a full DSL).
