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
