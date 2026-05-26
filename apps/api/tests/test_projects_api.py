import os

os.environ["GALGAME_DATABASE_URL"] = "sqlite:///./test_galgame_api.db"

from fastapi.testclient import TestClient

from api.database import Base, SessionLocal, engine, init_db, save_project
from api.main import app
from project_model.mock_data import MOCK_PROJECT


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


def test_builtin_demo_uses_current_mock_data_even_if_database_has_stale_copy() -> None:
    reset_database()
    stale_demo = MOCK_PROJECT.model_copy(update={"title": "Old English Demo"})
    with SessionLocal() as session:
        save_project(session, stale_demo)
    client = TestClient(app)

    load_response = client.get(f"/api/projects/{MOCK_PROJECT.project_id}")
    list_response = client.get("/api/projects/")

    assert load_response.status_code == 200
    assert load_response.json()["title"] == MOCK_PROJECT.title
    assert list_response.status_code == 200
    listed_demo = next(p for p in list_response.json()["projects"] if p["id"] == MOCK_PROJECT.project_id)
    assert listed_demo["title"] == MOCK_PROJECT.title
