import json
import os
from pathlib import Path

import requests


BASE_URL = "https://ruz.fa.ru"
SEARCH_URL = f"{BASE_URL}/api/search"
OUTPUT_PATH = Path("groups.json")

# RUZ rejects an empty search string, so use the current configured group
# as the safe default. Set RUZ_GROUP_SEARCH to another term when testing.
SEARCH_TERM = os.getenv("RUZ_GROUP_SEARCH", "МеждОт25-2")


def extract_items(data):
    """Normalize the different container shapes returned by RUZ search."""
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("data", "results", "items", "groups", "list"):
            value = data.get(key)
            if isinstance(value, list):
                return value

        # Some APIs wrap the result one level deeper.
        for value in data.values():
            if isinstance(value, dict):
                nested = extract_items(value)
                if nested is not None:
                    return nested

    return None


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
    items = extract_items(data)

    if items is None:
        if isinstance(data, dict):
            keys = ", ".join(map(str, data.keys()))
            preview = json.dumps(data, ensure_ascii=False)[:500]
            raise RuntimeError(
                f"РУЗ вернул неожиданный формат. Ключи: {keys}. Ответ: {preview}"
            )
        raise RuntimeError(
            f"РУЗ вернул неожиданный формат: {type(data).__name__}"
        )

    groups = []
    seen_ids = set()

    for item in items:
        if not isinstance(item, dict):
            continue

        group_id = item.get("id") or item.get("groupId") or item.get("group_id")
        name = (
            item.get("label")
            or item.get("name")
            or item.get("title")
            or item.get("groupName")
            or ""
        )
        name = str(name).strip()

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
    print(f"Получаем список групп из РУЗ по запросу: {SEARCH_TERM}")
    groups = fetch_groups()
    save_groups(groups)

    print(f"Получено групп: {len(groups)}")
    print(f"Сохранено: {OUTPUT_PATH}")

    for group in groups[:20]:
        print(f"  {group['id']} | {group['name']}")

    if len(groups) > 20:
        print(f"  ... ещё {len(groups) - 20}")
