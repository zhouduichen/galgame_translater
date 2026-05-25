from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import projects

app = FastAPI(title="Galgame Translater API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/projects", tags=["projects"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
