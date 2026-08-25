import json
import os
from pathlib import Path

import requests


BASE_URL = "https://ruz.fa.ru"
SEARCH_URL = f"{BASE_URL}/api/search"
OUTPUT_PATH = Path("groups.json")

# RUZ search is intentionally used instead of hard-coding group IDs.
# Set RUZ_GROUP_SEARCH to a narrower term when testing a subset of groups.
SEARCH_TERM = os.getenv("RUZ_GROUP_SEARCH", "")


def fetch_groups():
    params = {
        "term": SEARCH_TERM,
        "type": "group",
    }

    response = requests.get(
        SEARCH_URL,
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    if not isinstance(data, list):
        raise RuntimeError("РУЗ вернул неожиданный формат списка групп.")

    groups = []
    seen_ids = set()

    for item in data:
        if not isinstance(item, dict):
            continue

        group_id = item.get("id")
        name = (item.get("label") or item.get("name") or "").strip()

        if group_id is None or not name or group_id in seen_ids:
            continue

        seen_ids.add(group_id)
        groups.append({
            "id": group_id,
            "name": name,
        })

    groups.sort(key=lambda group: group["name"].casefold())
    return groups


def save_groups(groups):
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(groups, file, ensure_ascii=False, indent=2)
        file.write("\n")


if __name__ == "__main__":
    print("Получаем список групп из РУЗ...")
    groups = fetch_groups()
    save_groups(groups)

    print(f"Получено групп: {len(groups)}")
    print(f"Сохранено: {OUTPUT_PATH}")

    for group in groups[:20]:
        print(f"  {group['id']} | {group['name']}")

    if len(groups) > 20:
        print(f"  ... ещё {len(groups) - 20}")
