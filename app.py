from __future__ import annotations

import json
import os
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from groups_loader import fetch_groups
from ruz_client import get_group, get_schedule, is_regular_lesson


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_GROUP_ID = os.getenv("DEFAULT_GROUP_ID", "164606")
CACHE_TTL_SECONDS = int(os.getenv("RUZ_CACHE_TTL", "300"))
GROUPS_CACHE_TTL_SECONDS = int(os.getenv("GROUPS_CACHE_TTL", "3600"))

app = FastAPI(
    title="Расписание API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache_lock = threading.Lock()
_schedule_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_groups_cache: tuple[float, list[dict[str, Any]]] | None = None


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return fallback


def _load_cached_groups() -> list[dict[str, Any]]:
    global _groups_cache
    now = time.monotonic()
    with _cache_lock:
        if _groups_cache and now - _groups_cache[0] < GROUPS_CACHE_TTL_SECONDS:
            return _groups_cache[1]

    groups_file = _read_json(BASE_DIR / "groups.json", None)
    if isinstance(groups_file, list) and groups_file:
        groups = [g for g in groups_file if isinstance(g, dict) and g.get("id") and g.get("name")]
    else:
        groups = fetch_groups()

    with _cache_lock:
        _groups_cache = (now, groups)
    return groups


def _fetch_live_schedule(group_id: str) -> list[dict[str, Any]]:
    now = time.monotonic()
    with _cache_lock:
        cached = _schedule_cache.get(group_id)
        if cached and now - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]

    data = [item for item in get_schedule(group_id) if is_regular_lesson(item)]
    if not data:
        raise RuntimeError("РУЗ вернул пустое расписание")

    with _cache_lock:
        _schedule_cache[group_id] = (now, data)
    return data


def _group_name(group_id: str) -> str:
    for group in _load_cached_groups():
        if str(group.get("id")) == str(group_id):
            return str(group.get("name"))
    return str(group_id)


def _normalize_schedule(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(item: dict[str, Any]):
        return (
            str(item.get("date") or ""),
            str(item.get("beginLesson") or item.get("startLesson") or ""),
            str(item.get("discipline") or item.get("subject") or ""),
        )

    return sorted(items, key=key)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "ruz-schedule-api",
        "default_group_id": DEFAULT_GROUP_ID,
        "time": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/groups")
def groups() -> dict[str, Any]:
    items = _load_cached_groups()
    return {"groups": items, "count": len(items), "default_group_id": DEFAULT_GROUP_ID}


@app.get("/api/schedule")
def schedule(
    group_id: str = Query(DEFAULT_GROUP_ID, min_length=1),
) -> dict[str, Any]:
    try:
        items = _normalize_schedule(_fetch_live_schedule(group_id))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось получить расписание из РУЗ: {exc}") from exc

    return {
        "group_id": str(group_id),
        "group_name": _group_name(group_id),
        "source": "ruz",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "lessons": items,
    }


@app.get("/api/changes")
def changes(group_id: str = Query(DEFAULT_GROUP_ID, min_length=1)) -> dict[str, Any]:
    current_path = BASE_DIR / "group_schedules" / f"{group_id}.json"
    previous_path = BASE_DIR / "group_schedules_previous" / f"{group_id}.json"

    current = _read_json(current_path, {})
    previous = _read_json(previous_path, {})
    current_lessons = current.get("lessons", []) if isinstance(current, dict) else []
    previous_lessons = previous.get("lessons", []) if isinstance(previous, dict) else []

    previous_map = {json.dumps(x, ensure_ascii=False, sort_keys=True): x for x in previous_lessons if isinstance(x, dict)}
    current_map = {json.dumps(x, ensure_ascii=False, sort_keys=True): x for x in current_lessons if isinstance(x, dict)}

    added = [current_map[key] for key in current_map.keys() - previous_map.keys()]
    removed = [previous_map[key] for key in previous_map.keys() - current_map.keys()]

    return {
        "group_id": str(group_id),
        "group_name": _group_name(group_id),
        "added": added,
        "removed": removed,
        "count": len(added) + len(removed),
        "source": "schedule-snapshots",
    }


@app.get("/api/now")
def now() -> dict[str, Any]:
    today = date.today()
    return {
        "date": today.isoformat(),
        "weekday": today.strftime("%A"),
        "server_time": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


@app.get("/{path:path}", include_in_schema=False)
def static_file(path: str) -> FileResponse:
    candidate = (BASE_DIR / path).resolve()
    if BASE_DIR not in candidate.parents or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(candidate)
