# Galgame Translater

Upload novels → Generate playable visual novel demo → Edit online → Export Ren'Py project.

## Architecture

```
apps/
  web/       Next.js frontend (player + editor)
  api/       FastAPI backend
  worker/    Background job processor
packages/
  project-model/    Shared Pydantic schemas
  renpy-exporter/   Ren'Py .rpy generator
  prompt-templates/ LLM prompt definitions
```

## Core Data Flow

```
Upload (.txt/.md)
  → ParseDraft (LLM-generated draft)
    → AdaptationProject (validated, editable model)
      → Web Player (preview)
      → Ren'Py Export (.rpy + assets)
```

## Development

```bash
# Backend
cd apps/api && pip install -e . && uvicorn api.main:app --reload

# Worker
cd apps/worker && pip install -e . && python -m worker.main

# Frontend
cd apps/web && npm install
npm.cmd run dev

# Frontend production build on Windows PowerShell
npm.cmd run build
```

## MVP Scope

- Upload `.txt`/`.md` novels
- AI parses into scenes, characters, dialogue, choices
- Web-based player and single-scene editor
- Export to Ren'Py project zip
- Asset generation (ComfyUI/SD) — Phase 2

## Verification

```bash
python -m pytest -q
cd apps/web
npm.cmd run test
npm.cmd run build
```

Use `npm.cmd` on Windows PowerShell to avoid the local script execution policy blocking `npm.ps1`.
