import argparse
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

from backend.app import DB_PATH, GROUPS_FILE, init_db
from backend.ruz_client import RUZClient, RUZClientError

DEFAULT_DAYS = 70
MAX_WORKERS = 5
FETCH_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2


def load_groups():
    groups = json.loads(GROUPS_FILE.read_text(encoding="utf-8"))
    if not isinstance(groups, list) or not groups:
        raise RuntimeError("groups.json must contain a non-empty array")
    return [
        item for item in groups
        if isinstance(item, dict) and item.get("id") is not None
    ]


def fetch_with_retry(client, group, start, finish):
    last_error = None
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        try:
            lessons = client.fetch_group_schedule(group["id"], start, finish)
            return {
                "id": str(group["id"]),
                "name": str(group.get("name", "")),
                "lessons": lessons,
            }
        except RUZClientError as exc:
            last_error = exc
            if attempt < FETCH_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS * attempt)
    raise RuntimeError(str(last_error))


def apply_results(results):
    with sqlite3.connect(DB_PATH) as db:
        current_ids = {item["id"] for item in results}
        for item in results:
            db.execute(
                "INSERT OR REPLACE INTO groups (id, name) VALUES (?, ?)",
                (item["id"], item["name"]),
            )
            db.execute(
                "INSERT OR REPLACE INTO schedules (group_id, payload) VALUES (?, ?)",
                (item["id"], json.dumps(item, ensure_ascii=False)),
            )

        if current_ids:
            placeholders = ",".join("?" for _ in current_ids)
            db.execute(
                f"DELETE FROM schedules WHERE group_id NOT IN ({placeholders})",
                tuple(current_ids),
            )
            db.execute(
                f"DELETE FROM groups WHERE id NOT IN ({placeholders})",
                tuple(current_ids),
            )


def sync_groups(days=DEFAULT_DAYS, group_id=None):
    init_db()
    groups = load_groups()
    if group_id is not None:
        groups = [group for group in groups if str(group["id"]) == str(group_id)]
        if not groups:
            raise RuntimeError(f"Group {group_id} not found in groups.json")

    start = date.today()
    finish = start + timedelta(days=days)
    client = RUZClient()
    results = []
    failures = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_with_retry, client, group, start, finish): group
            for group in groups
        }
        for future in as_completed(futures):
            group = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                failures.append({
                    "id": str(group["id"]),
                    "name": str(group.get("name", "")),
                    "error": str(exc),
                })

    if results:
        apply_results(results)

    return {
        "requested": len(groups),
        "updated": len(results),
        "failed": failures,
        "start": start.isoformat(),
        "finish": finish.isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Synchronize schedules from RUZ into SQLite")
    parser.add_argument("--group-id", help="Synchronize only one group")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    args = parser.parse_args()

    if args.days < 1:
        parser.error("--days must be >= 1")

    result = sync_groups(days=args.days, group_id=args.group_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
