import json
import sqlite3

from fastapi.testclient import TestClient

import backend.app as app_module
from backend.app import CHANGES_DIR, DB_PATH, GROUPS_FILE, SCHEDULE_DIR, app

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


def test_sqlite_groups_match_source_groups():
    source = json.loads(GROUPS_FILE.read_text(encoding="utf-8"))
    expected = {
        (str(item["id"]), str(item.get("name", "")))
        for item in source
        if isinstance(item, dict) and item.get("id") is not None
    }

    with sqlite3.connect(DB_PATH) as db:
        actual = set(db.execute("SELECT id, name FROM groups").fetchall())

    assert actual == expected


def test_sqlite_schedule_ids_match_source_files():
    expected = {path.stem for path in SCHEDULE_DIR.glob("*.json")}

    with sqlite3.connect(DB_PATH) as db:
        actual = {row[0] for row in db.execute("SELECT group_id FROM schedules")}

    assert actual == expected


def test_sqlite_change_ids_match_source_files():
    expected = {path.stem for path in CHANGES_DIR.glob("*.json")}

    with sqlite3.connect(DB_PATH) as db:
        actual = {row[0] for row in db.execute("SELECT group_id FROM changes")}

    assert actual == expected


def test_init_db_preserves_runtime_state(tmp_path, monkeypatch):
    runtime_db = tmp_path / "runtime.sqlite"
    monkeypatch.setattr(app_module, "DB_PATH", runtime_db)

    app_module.init_db()
    with sqlite3.connect(runtime_db) as db:
        db.execute("INSERT INTO groups (id, name) VALUES (?, ?)", ("runtime-1", "Runtime group"))
        db.execute(
            "INSERT INTO schedules (group_id, payload) VALUES (?, ?)",
            ("runtime-1", json.dumps({"id": "runtime-1", "lessons": []})),
        )
        db.commit()

    app_module.init_db()

    with sqlite3.connect(runtime_db) as db:
        group = db.execute("SELECT id, name FROM groups WHERE id = ?", ("runtime-1",)).fetchone()
        schedule = db.execute(
            "SELECT payload FROM schedules WHERE group_id = ?", ("runtime-1",)
        ).fetchone()

    assert group == ("runtime-1", "Runtime group")
    assert json.loads(schedule[0])["id"] == "runtime-1"
