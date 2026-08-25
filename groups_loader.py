import json
import os
from pathlib import Path

import requests


BASE_URL = "https://ruz.fa.ru"
SEARCH_URL = f"{BASE_URL}/api/search"
OUTPUT_PATH = Path("groups.json")

# RUZ does not accept an empty/one-character group search reliably.  Keep the
# explicit term for diagnostics, but use a small set of meaningful prefixes
# when discovering the catalogue automatically.
EXPLICIT_TERM = os.getenv("RUZ_GROUP_SEARCH", "").strip()
SEARCH_TERMS = [
    "Межд",
    "Фин",
    "Эконом",
    "Менедж",
    "Бизнес",
    "Маркет",
    "Прав",
    "Государ",
    "Информац",
    "Компьют",
    "Матем",
    "Логист",
    "Торгов",
    "Международ",
]


def extract_items(data):
    """Normalize the different container shapes returned by RUZ search."""
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("data", "results", "items", "groups", "list"):
            value = data.get(key)
            if isinstance(value, list):
                return value

        for value in data.values():
            if isinstance(value, dict):
                nested = extract_items(value)
                if nested is not None:
                    return nested

    return None


def normalize_group(item):
    if not isinstance(item, dict):
        return None

    group_id = item.get("id") or item.get("groupId") or item.get("group_id")
    name = (
        item.get("label")
        or item.get("name")
        or item.get("title")
        or item.get("groupName")
        or ""
    )
    name = str(name).strip()

    if group_id is None or not name:
        return None

    return {"id": group_id, "name": name}


def fetch_groups_for_term(session, term):
    response = session.get(
        SEARCH_URL,
        params={"term": term, "type": "group"},
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
                f"РУЗ вернул неожиданный формат для запроса '{term}'. "
                f"Ключи: {keys}. Ответ: {preview}"
            )
        raise RuntimeError(
            f"РУЗ вернул неожиданный формат для запроса '{term}': "
            f"{type(data).__name__}"
        )

    groups = []
    for item in items:
        group = normalize_group(item)
        if group is not None:
            groups.append(group)

    return groups


def fetch_groups():
    terms = [EXPLICIT_TERM] if EXPLICIT_TERM else SEARCH_TERMS

    session = requests.Session()
    unique_groups = {}
    successful_terms = 0
    failed_terms = []

    print(f"Поиск каталога групп РУЗ. Запросов: {len(terms)}")

    for term in terms:
        try:
            groups = fetch_groups_for_term(session, term)
        except requests.RequestException as exc:
            failed_terms.append((term, f"HTTP: {exc}"))
            print(f"  '{term}': ошибка HTTP, пропускаем")
            continue
        except (ValueError, RuntimeError) as exc:
            failed_terms.append((term, str(exc)))
            print(f"  '{term}': ошибка формата, пропускаем")
            continue

        successful_terms += 1
        before = len(unique_groups)
        for group in groups:
            unique_groups[str(group["id"])] = group
        added = len(unique_groups) - before

        print(
            f"  '{term}': найдено {len(groups)}, новых {added}, "
            f"всего уникальных {len(unique_groups)}"
        )

    if not unique_groups:
        details = "; ".join(f"{term}: {error}" for term, error in failed_terms)
        raise RuntimeError(
            "РУЗ не вернул ни одной группы. groups.json не будет записан пустым. "
            + (f"Ошибки: {details}" if details else "")
        )

    print(
        f"Успешно обработано запросов: {successful_terms}/{len(terms)}; "
        f"уникальных групп: {len(unique_groups)}"
    )

    return sorted(
        unique_groups.values(),
        key=lambda group: group["name"].casefold(),
    )


def save_groups(groups):
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(groups, file, ensure_ascii=False, indent=2)
        file.write("\n")


if __name__ == "__main__":
    groups = fetch_groups()
    save_groups(groups)

    print(f"Получено групп: {len(groups)}")
    print(f"Сохранено: {OUTPUT_PATH}")

    for group in groups[:30]:
        print(f"  {group['id']} | {group['name']}")

    if len(groups) > 30:
        print(f"  ... ещё {len(groups) - 30}")
