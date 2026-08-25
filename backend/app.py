from pathlib import Path
import json
from fastapi import FastAPI, HTTPException

ROOT = Path(__file__).resolve().parent.parent
GROUPS_FILE = ROOT / "groups.json"
SCHEDULE_DIR = ROOT / "group_schedules"
CHANGES_DIR = ROOT / "changes_by_group"

app = FastAPI(title="Schedule API", version="1.0.0")


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def groups():
    data = read_json(GROUPS_FILE, [])
    return data if isinstance(data, list) else []


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/v1/groups")
def list_groups():
    return {"groups": groups()}


@app.get("/api/v1/groups/{group_id}/schedule")
def group_schedule(group_id: int):
    path = SCHEDULE_DIR / f"{group_id}.json"
    data = read_json(path, None)
    if data is None:
        raise HTTPException(status_code=404, detail="Group schedule not found")
    return data


@app.get("/api/v1/groups/{group_id}/changes")
def group_changes(group_id: int):
    path = CHANGES_DIR / f"{group_id}.json"
    data = read_json(path, None)
    if data is None:
        raise HTTPException(status_code=404, detail="Group changes not found")
    return {"group_id": group_id, "changes": data}
