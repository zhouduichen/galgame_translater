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
