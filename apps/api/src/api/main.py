import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from project_model.schema_version import check_schema_version

from .database import DATABASE_URL, DEFAULT_GENERATED_DIR, init_db
from .routers import projects

# Existing SQLite databases must be migrated explicitly before API startup.
if DATABASE_URL.startswith("sqlite:///"):
    check_schema_version(DATABASE_URL.removeprefix("sqlite:///"))

app = FastAPI(title="Galgame 转译器 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated assets (configurable via GENERATED_DIR env var)
_generated_dir = Path(os.environ.get(
    "GENERATED_DIR",
    str(DEFAULT_GENERATED_DIR),
))
_generated_dir.mkdir(parents=True, exist_ok=True)
app.mount("/api/assets", StaticFiles(directory=str(_generated_dir)), name="assets")

app.include_router(projects.router, prefix="/api/projects", tags=["projects"])


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
