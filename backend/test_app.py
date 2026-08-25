from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["storage"] == "sqlite"


def test_groups():
    response = client.get("/api/v1/groups")
    assert response.status_code == 200
    assert isinstance(response.json()["groups"], list)


def test_known_group_schedule():
    response = client.get("/api/v1/groups/164606/schedule")
    assert response.status_code == 200
    assert response.json()["id"] == "164606"


def test_known_group_changes():
    response = client.get("/api/v1/groups/164606/changes")
    assert response.status_code == 200
    assert response.json()["group_id"] == 164606
    assert isinstance(response.json()["changes"], list)


def test_unknown_group_schedule_is_404():
    response = client.get("/api/v1/groups/999999999/schedule")
    assert response.status_code == 404


def test_unknown_group_changes_is_404():
    response = client.get("/api/v1/groups/999999999/changes")
    assert response.status_code == 404
