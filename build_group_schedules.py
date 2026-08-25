import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

import requests


BASE_URL = "https://ruz.fa.ru"
GROUPS_PATH = Path("groups.json")
OUTPUT_PATH = Path("group_schedules.json")
GROUP_DIR = Path("group_schedules")
START = date.today()
FINISH = START + timedelta(days=70)
MAX_WORKERS = 5


def extract_list(data):
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("data", "schedule", "lessons", "items", "results", "result", "list"):
            value = data.get(key)
            if isinstance(value, list):
                return value

        for value in data.values():
            if isinstance(value, (dict, list)):
                found = extract_list(value)
                if found is not None:
                    return found

    return None


def is_regular_lesson(lesson):
    kind = lesson.get("kindOfWork", "") or ""
    if kind.startswith("Повторная промежуточная аттестация"):
        return False
    return lesson.get("deletion_mark", 0) == 0


def fetch_group(group):
    group_id = group["id"]
    url = f"{BASE_URL}/api/schedule/group/{group_id}"
    params = {
        "start": START.strftime("%Y.%m.%d"),
        "finish": FINISH.strftime("%Y.%m.%d"),
        "lng": 1,
    }

    with requests.Session() as session:
        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()
        raw = response.json()

    data = extract_list(raw)
    if data is None:
        raise RuntimeError("unexpected RUZ response shape")

    lessons = [item for item in data if isinstance(item, dict) and is_regular_lesson(item)]
    return {
        "id": group_id,
        "name": group["name"],
        "lessons": lessons,
    }


def write_group_file(item):
    GROUP_DIR.mkdir(parents=True, exist_ok=True)
    path = GROUP_DIR / f"{item['id']}.json"
    path.write_text(
        json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def main():
    groups = json.loads(GROUPS_PATH.read_text(encoding="utf-8"))
    if not isinstance(groups, list) or not groups:
        raise SystemExit("groups.json must contain a non-empty array")

    GROUP_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in GROUP_DIR.glob("*.json"):
        old_file.unlink()

    result = {}
    failures = []

    print(f"Building schedules for {len(groups)} groups")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_group, group): group for group in groups}
        for index, future in enumerate(as_completed(futures), 1):
            group = futures[future]
            try:
                item = future.result()
                result[str(item["id"])] = item
                write_group_file(item)
                print(f"[{index}/{len(groups)}] {item['name']}: {len(item['lessons'])} lessons")
            except Exception as exc:
                failures.append((group["id"], group["name"], str(exc)))
                print(f"[{index}/{len(groups)}] {group['name']}: FAILED - {exc}")

    if not result:
        raise SystemExit("No group schedules were fetched")

    payload = {
        "generatedAt": START.isoformat(),
        "start": START.isoformat(),
        "finish": FINISH.isoformat(),
        "groups": result,
        "failed": [
            {"id": group_id, "name": name, "error": error}
            for group_id, name, error in failures
        ],
    }

    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Saved {len(result)} group schedules to {OUTPUT_PATH}")
    print(f"Saved {len(result)} lazy-load files to {GROUP_DIR}/")
    print(f"Failed groups: {len(failures)}")


if __name__ == "__main__":
    main()
