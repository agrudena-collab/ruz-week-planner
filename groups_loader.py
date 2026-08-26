import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests


BASE_URL = "https://ruz.fa.ru"
SEARCH_URL = f"{BASE_URL}/api/search"
OUTPUT_PATH = Path("groups.json")

EXPLICIT_TERM = os.getenv("RUZ_GROUP_SEARCH", "").strip()
SEMANTIC_TERMS = [
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
    "Дизайн",
    "Психолог",
    "Аудит",
    "Инвест",
    "Ресторан",
    "Управ",
    "Полит",
    "Юрид",
    "Бух",
    "Налог",
    "Тамож",
    "Статист",
    "Социолог",
    "Лингв",
    "Иностран",
    "Технолог",
    "Програм",
    "Кибер",
    "Данные",
    "Гуманит",
]

# The current RUZ group names contain six-digit programme codes such as
# 002877 and 003757. A search for just "00" is not a catalogue endpoint: it
# returns only the first slice of matching groups. Querying the four-digit
# prefixes partitions that catalogue much more safely (0000..0099).
NUMERIC_PREFIX_TERMS = [f"00{number:02d}" for number in range(100)]

# RUZ's search endpoint does not expose pagination in this API contract. Some
# prefixes can therefore be saturated at a fixed result count. When a numeric
# prefix returns one of these common cap sizes, recursively split it by one
# more digit. This turns a broad search into a deterministic prefix crawl.
SATURATION_COUNTS = {10, 20, 50, 100}
MAX_NUMERIC_PREFIX_DEPTH = 6
MAX_NUMERIC_QUERIES = 5000

SEARCH_TERMS = (
    [EXPLICIT_TERM]
    if EXPLICIT_TERM
    else list(dict.fromkeys(NUMERIC_PREFIX_TERMS + SEMANTIC_TERMS))
)
MAX_WORKERS = 10


def extract_items(data):
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
        raise RuntimeError(f"unexpected RUZ response shape for '{term}'")

    groups = []
    for item in items:
        group = normalize_group(item)
        if group is not None:
            groups.append(group)
    return groups


def numeric_children(term):
    if not term.isdigit() or len(term) >= MAX_NUMERIC_PREFIX_DEPTH:
        return []
    return [term + str(digit) for digit in range(10)]


def should_expand_numeric_term(term, groups):
    return (
        term.isdigit()
        and len(term) < MAX_NUMERIC_PREFIX_DEPTH
        and len(groups) in SATURATION_COUNTS
    )


def fetch_groups():
    unique_groups = {}
    failed_terms = []
    pending_terms = list(SEARCH_TERMS)
    seen_terms = set()
    numeric_queries = 0

    print(f"Поиск расширенного каталога групп РУЗ. Начальных запросов: {len(SEARCH_TERMS)}")

    while pending_terms:
        batch = []
        for term in pending_terms:
            if term in seen_terms:
                continue
            seen_terms.add(term)
            batch.append(term)
        pending_terms = []

        if not batch:
            break

        numeric_queries += sum(term.isdigit() for term in batch)
        if numeric_queries > MAX_NUMERIC_QUERIES:
            raise RuntimeError(
                "Слишком много числовых запросов к РУЗ; каталог не записан, "
                "чтобы не публиковать потенциально неполный результат."
            )

        def worker(term):
            with requests.Session() as session:
                return term, fetch_groups_for_term(session, term)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(worker, term): term for term in batch}
            completed = 0
            for future in as_completed(futures):
                term = futures[future]
                completed += 1
                try:
                    _, groups = future.result()
                    before = len(unique_groups)
                    for group in groups:
                        unique_groups[str(group["id"])] = group
                    added = len(unique_groups) - before
                    print(
                        f"[{completed}/{len(batch)}] '{term}': "
                        f"найдено {len(groups)}, новых {added}, всего {len(unique_groups)}"
                    )

                    if should_expand_numeric_term(term, groups):
                        children = numeric_children(term)
                        pending_terms.extend(children)
                        print(
                            f"  -> префикс '{term}' выглядит насыщенным; "
                            f"добавляем {len(children)} дочерних префиксов"
                        )
                except (requests.RequestException, ValueError, RuntimeError) as exc:
                    failed_terms.append((term, str(exc)))
                    print(f"[{completed}/{len(batch)}] '{term}': ошибка, пропускаем")

    # Never destroy a known-good catalogue because RUZ temporarily rejects
    # some search prefixes. Merge the previous catalogue as a safety net; the
    # next successful run can only add/update groups, not silently erase them.
    previous = []
    try:
        raw_previous = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        if isinstance(raw_previous, list):
            previous = [g for g in raw_previous if normalize_group(g)]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    for group in previous:
        normalized = normalize_group(group)
        if normalized is not None:
            unique_groups.setdefault(str(normalized["id"]), normalized)

    if not unique_groups:
        details = "; ".join(f"{term}: {error}" for term, error in failed_terms[:10])
        raise RuntimeError(
            "РУЗ не вернул ни одной группы. groups.json не будет записан пустым."
            + (f" Ошибки: {details}" if details else "")
        )

    groups = sorted(unique_groups.values(), key=lambda group: group["name"].casefold())
    print(
        f"Каталог готов: {len(groups)} уникальных групп; "
        f"ошибок запросов: {len(failed_terms)}; "
        f"числовых запросов: {numeric_queries}"
    )
    return groups


def save_groups(groups):
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(groups, file, ensure_ascii=False, indent=2)
        file.write("\n")


if __name__ == "__main__":
    groups = fetch_groups()
    save_groups(groups)
    print(f"Получено групп: {len(groups)}")
    print(f"Сохранено: {OUTPUT_PATH}")
