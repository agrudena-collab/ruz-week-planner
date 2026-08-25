import os
import requests
import json
from datetime import date, timedelta


BASE_URL = "https://ruz.fa.ru"
GROUP_NAME = os.getenv("GROUP_NAME", "МеждОт25-2").strip()


def extract_list(data):
    """Find a list of schedule records in the different RUZ response shapes."""
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        preferred_keys = (
            "data",
            "schedule",
            "lessons",
            "items",
            "results",
            "result",
            "list",
        )

        for key in preferred_keys:
            value = data.get(key)
            if isinstance(value, list):
                return value

        for value in data.values():
            if isinstance(value, (dict, list)):
                found = extract_list(value)
                if found is not None:
                    return found

    return None


def get_group():
    url = f"{BASE_URL}/api/search"
    params = {
        "term": GROUP_NAME,
        "type": "group",
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    groups = extract_list(data)
    if groups is None:
        raise RuntimeError(
            "РУЗ вернул неожиданный формат поиска групп: "
            + json.dumps(data, ensure_ascii=False)[:1000]
        )

    return groups


def get_schedule(group_id):
    start = date.today()
    finish = start + timedelta(days=70)

    url = f"{BASE_URL}/api/schedule/group/{group_id}"
    params = {
        "start": start.strftime("%Y.%m.%d"),
        "finish": finish.strftime("%Y.%m.%d"),
        "lng": 1,
    }

    print("=" * 70)
    print("ДИАГНОСТИКА ЗАПРОСА К РУЗ")
    print("=" * 70)
    print(f"Группа:         {GROUP_NAME}")
    print(f"Group ID:       {group_id}")
    print(f"Запрашиваем с:  {start}")
    print(f"Запрашиваем до: {finish}")
    print(f"URL:            {url}")
    print(f"Параметры:      {params}")

    response = requests.get(url, params=params, timeout=30)
    print(f"HTTP статус:    {response.status_code}")
    response.raise_for_status()

    raw_data = response.json()
    data = extract_list(raw_data)

    if data is None:
        raise RuntimeError(
            "РУЗ вернул неожиданный формат расписания. "
            f"Тип ответа: {type(raw_data).__name__}. "
            f"Ответ: {json.dumps(raw_data, ensure_ascii=False)[:2000]}"
        )

    print(f"Всего записей после разбора ответа: {len(data)}")

    if not data:
        raise RuntimeError(
            "РУЗ вернул пустое расписание. "
            "schedule.json специально НЕ будет перезаписан пустым массивом."
        )

    valid_lessons = [item for item in data if isinstance(item, dict)]
    if not valid_lessons:
        raise RuntimeError("РУЗ вернул список без объектов занятий.")

    dates = sorted(
        {
            lesson.get("date")
            for lesson in valid_lessons
            if lesson.get("date")
        }
    )

    if dates:
        print(f"Самая ранняя дата: {dates[0]}")
        print(f"Самая поздняя дата: {dates[-1]}")

    print("=" * 70)
    return valid_lessons


def is_regular_lesson(lesson):
    kind_of_work = lesson.get("kindOfWork", "") or ""

    if kind_of_work.startswith("Повторная промежуточная аттестация"):
        return False

    if lesson.get("deletion_mark", 0) != 0:
        return False

    return True


if __name__ == "__main__":
    print("=" * 70)
    print("ПОИСК ГРУППЫ")
    print("=" * 70)

    groups = get_group()

    print(f"Найдено результатов: {len(groups)}")

    exact_group = None
    for group in groups:
        if not isinstance(group, dict):
            continue

        name = (
            group.get("label")
            or group.get("name")
            or group.get("title")
            or group.get("groupName")
            or ""
        )

        if str(name).strip() == GROUP_NAME:
            exact_group = group
            break

    if exact_group is None:
        raise RuntimeError(
            f"Точное совпадение группы '{GROUP_NAME}' не найдено. "
            f"Результаты: {json.dumps(groups, ensure_ascii=False)[:2000]}"
        )

    group_id = (
        exact_group.get("id")
        or exact_group.get("groupId")
        or exact_group.get("group_id")
    )

    if group_id is None:
        raise RuntimeError(
            f"У группы '{GROUP_NAME}' не найден ID: "
            f"{json.dumps(exact_group, ensure_ascii=False)}"
        )

    print(f"Выбрана группа: {GROUP_NAME}")
    print(f"ID группы:       {group_id}")

    raw_schedule = get_schedule(group_id)

    schedule = [
        lesson for lesson in raw_schedule
        if is_regular_lesson(lesson)
    ]

    print(f"До фильтра:      {len(raw_schedule)}")
    print(f"После фильтра:   {len(schedule)}")

    if not schedule:
        raise RuntimeError(
            "После фильтра расписание стало пустым. "
            "schedule.json не будет очищен."
        )

    with open("schedule.json", "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"schedule.json обновлён: {len(schedule)} занятий")
