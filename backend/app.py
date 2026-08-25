from pathlib import Path
import json
import os
import sqlite3

from fastapi import FastAPI, HTTPException

ROOT = Path(__file__).resolve().parent.parent
GROUPS_FILE = ROOT / "groups.json"
SCHEDULE_DIR = ROOT / "group_schedules"
CHANGES_DIR = ROOT / "changes_by_group"
# The default is CI/local-safe. Production Docker sets SCHEDULE_DB_PATH=/data/ruz_schedule.db.
DB_PATH = Path(os.getenv("SCHEDULE_DB_PATH", "/tmp/ruz_schedule.db"))

app = FastAPI(title="Schedule API", version="1.2.0")


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def seed_table_from_files(db, table: str, paths):
    for path in paths:
        data = read_json(path, None)
        if data is not None:
            db.execute(
                f"INSERT OR REPLACE INTO {table} (group_id, payload) VALUES (?, ?)",
                (path.stem, json.dumps(data, ensure_ascii=False)),
            )


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS groups (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS schedules (
                group_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS changes (
                group_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            """
        )

        # JSON files are bootstrap data only. Once SQLite has been populated,
        # runtime updates are kept in SQLite and are not overwritten on restart.
        groups_count = db.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
        if groups_count == 0:
            group_data = read_json(GROUPS_FILE, [])
            if isinstance(group_data, list):
                for item in group_data:
                    if isinstance(item, dict) and item.get("id") is not None:
                        db.execute(
                            "INSERT OR REPLACE INTO groups (id, name) VALUES (?, ?)",
                            (str(item["id"]), str(item.get("name", ""))),
                        )

        schedules_count = db.execute("SELECT COUNT(*) FROM schedules").fetchone()[0]
        if schedules_count == 0:
            seed_table_from_files(db, "schedules", SCHEDULE_DIR.glob("*.json"))

        changes_count = db.execute("SELECT COUNT(*) FROM changes").fetchone()[0]
        if changes_count == 0:
            seed_table_from_files(db, "changes", CHANGES_DIR.glob("*.json"))


def db_query_one(query: str, params=()):
    with sqlite3.connect(DB_PATH) as db:
        return db.execute(query, params).fetchone()


def db_query_all(query: str, params=()):
    with sqlite3.connect(DB_PATH) as db:
        return db.execute(query, params).fetchall()


init_db()


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": "1.2.0", "storage": "sqlite"}


@app.get("/api/v1/groups")
def list_groups():
    rows = db_query_all("SELECT id, name FROM groups ORDER BY name, id")
    return {"groups": [{"id": row[0], "name": row[1]} for row in rows]}


@app.get("/api/v1/groups/{group_id}/schedule")
def group_schedule(group_id: int):
    row = db_query_one(
        "SELECT payload FROM schedules WHERE group_id = ?", (str(group_id),)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Group schedule not found")
    return json.loads(row[0])


@app.get("/api/v1/groups/{group_id}/changes")
def group_changes(group_id: int):
    row = db_query_one(
        "SELECT payload FROM changes WHERE group_id = ?", (str(group_id),)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Group changes not found")
    return {"group_id": group_id, "changes": json.loads(row[0])}
