import requests
import json
from datetime import date, timedelta


BASE_URL = "https://ruz.fa.ru"
GROUP_NAME = "МеждОт25-2"


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
    # Берём расписание на ближайшие 21 день,
    # чтобы захватить конец августа и начало сентября.
    start = date.today()
    finish = start + timedelta(days=21)

    url = f"{BASE_URL}/api/schedule/group/{group_id}"

    params = {
        "start": start.strftime("%Y.%m.%d"),
        "finish": finish.strftime("%Y.%m.%d"),
        "lng": 1,
    }

    response = requests.get(
        url,
        params=params,
        timeout=20,
    )

    response.raise_for_status()

    return response.json()


def is_regular_lesson(lesson):
    """
    Оставляем обычные учебные занятия.
    Убираем повторную промежуточную аттестацию
    (пересдачи / дополнительные зачёты / экзамены).
    """

    kind_of_work = lesson.get("kindOfWork", "") or ""

    if kind_of_work.startswith(
        "Повторная промежуточная аттестация"
    ):
        return False

    # Не показываем удалённые записи.
    if lesson.get("deletion_mark", 0) != 0:
        return False

    return True


if __name__ == "__main__":

    groups = get_group()

    print("Найденные группы:")
    print(groups)

    if not groups:
        raise RuntimeError(
            f"Группа '{GROUP_NAME}' не найдена в РУЗ."
        )

    group = groups[0]
    group_id = group["id"]

    print("\nВыбрана группа:")
    print(group)

    print("\nПолучаем расписание из РУЗ...")

    raw_schedule = get_schedule(group_id)

    print(
        f"Всего записей получено: "
        f"{len(raw_schedule)}"
    )

    schedule = [
        lesson
        for lesson in raw_schedule
        if is_regular_lesson(lesson)
    ]

    print(
        f"Обычных занятий после фильтра: "
        f"{len(schedule)}"
    )

    print("\nРасписание обычных занятий:")

    for lesson in schedule:
        print(
            f'{lesson.get("date")} '
            f'{lesson.get("beginLesson")}-'
            f'{lesson.get("endLesson")} — '
            f'{lesson.get("discipline")} — '
            f'{lesson.get("lecturer")}'
        )

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

    print(
        "\nГотово: schedule.json обновлён."
    )
