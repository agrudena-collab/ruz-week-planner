import requests
from datetime import date, timedelta
from urllib.parse import quote


BASE_URL = "https://ruz.fa.ru"
GROUP_NAME = "МеждОт25-2"


def get_group():
    url = f"{BASE_URL}/api/search"
    params = {
        "term": GROUP_NAME,
        "type": "group",
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()

    return response.json()


def get_schedule(group_id):
    start = date.today()
    finish = start + timedelta(days=7)

    url = f"{BASE_URL}/api/schedule/group/{group_id}"
    params = {
        "start": start.strftime("%Y.%m.%d"),
        "finish": finish.strftime("%Y.%m.%d"),
        "lng": 1,
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()

    return response.json()


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

    print("\nРасписание на ближайшие 7 дней:")
    schedule = get_schedule(group_id)
    print(schedule)
