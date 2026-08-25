import os
import requests
import json
from datetime import date, timedelta


BASE_URL = "https://ruz.fa.ru"
# Keep the current group as the safe default. Multi-group runs can provide
# GROUP_NAME through the environment without changing the source code.
GROUP_NAME = os.getenv("GROUP_NAME", "МеждОт25-2").strip()


def get_group():
    url = f"{BASE_URL}/api/search"

    params = {
        "term": GROUP_NAME,
        "type": "group",
    }

    response = requests.get(
        url,
        params=params,
        timeout=20,
    )

    response.raise_for_status()

    return response.json()


def get_schedule(group_id):

    start = date.today()
    finish = start + timedelta(days=70)

    url = f"{BASE_URL}/api/schedule/group/{group_id}"

    params = {
        "start": start.strftime("%Y.%m.%d"),
        "finish": finish.strftime("%Y.%m.%d"),
        "lng": 1,
    }

    print()
    print("=" * 70)
    print("ДИАГНОСТИКА ЗАПРОСА К РУЗ")
    print("=" * 70)

    print(f"Группа:         {GROUP_NAME}")
    print(f"Сегодня:        {start}")
    print(f"Запрашиваем с:  {start}")
    print(f"Запрашиваем до: {finish}")

    print()
    print("URL:")
    print(url)

    print()
    print("Параметры:")
    print(params)

    response = requests.get(
        url,
        params=params,
        timeout=20,
    )

    print()
    print(f"HTTP статус: {response.status_code}")

    response.raise_for_status()

    data = response.json()

    print()
    print(f"Всего записей от РУЗ: {len(data)}")

    if data:

        dates = sorted(
            set(
                lesson.get("date")
                for lesson in data
                if lesson.get("date")
            )
        )

        print()
        print("Даты, которые реально вернул РУЗ:")

        for item_date in dates:
            print(f"  {item_date}")

        print()
        print(f"Самая ранняя дата: {dates[0]}")
        print(f"Самая поздняя дата: {dates[-1]}")

    else:
        print()
        print("РУЗ вернул пустой список.")

    print("=" * 70)
    print()

    return data


def is_regular_lesson(lesson):

    kind_of_work = lesson.get(
        "kindOfWork",
        ""
    ) or ""

    if kind_of_work.startswith(
        "Повторная промежуточная аттестация"
    ):
        return False

    if lesson.get("deletion_mark", 0) != 0:
        return False

    return True


if __name__ == "__main__":

    print("=" * 70)
    print("ПОИСК ГРУППЫ")
    print("=" * 70)

    groups = get_group()

    print()
    print("Найденные группы:")

    for group in groups:
        print(
            f'ID: {group.get("id")} | '
            f'Название: {group.get("label") or group.get("name")}'
        )

    if not groups:
        raise RuntimeError(
            f"Группа '{GROUP_NAME}' не найдена в РУЗ."
        )

    # Ищем точное совпадение названия.
    exact_group = None

    for group in groups:

        name = (
            group.get("label")
            or group.get("name")
            or ""
        )

        if name.strip() == GROUP_NAME:
            exact_group = group
            break

    if exact_group is None:

        raise RuntimeError(
            f"Точное совпадение группы "
            f"'{GROUP_NAME}' не найдено."
        )

    group = exact_group
    group_id = group["id"]

    print()
    print("Выбрана точная группа:")

    print(group)

    print()
    print("Получаем расписание...")

    raw_schedule = get_schedule(group_id)

    print()
    print("=" * 70)
    print("АНАЛИЗ ФИЛЬТРА")
    print("=" * 70)

    if raw_schedule:

        raw_dates = sorted(
            set(
                lesson.get("date")
                for lesson in raw_schedule
                if lesson.get("date")
            )
        )

        print()
        print(
            f"До фильтра: "
            f"{len(raw_schedule)} записей"
        )

        print(
            f"Диапазон: "
            f"{raw_dates[0]} → {raw_dates[-1]}"
        )

    schedule = [
        lesson
        for lesson in raw_schedule
        if is_regular_lesson(lesson)
    ]

    print()
    print(
        f"После фильтра: "
        f"{len(schedule)} записей"
    )

    if schedule:

        filtered_dates = sorted(
            set(
                lesson.get("date")
                for lesson in schedule
                if lesson.get("date")
            )
        )

        print(
            f"Диапазон после фильтра: "
            f"{filtered_dates[0]} → "
            f"{filtered_dates[-1]}"
        )

    print()
    print("Последние даты после фильтра:")

    if schedule:

        for lesson_date in filtered_dates[-10:]:
            print(f"  {lesson_date}")

    print()
    print("=" * 70)

    with open(
        "schedule.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            schedule,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("schedule.json обновлён.")
