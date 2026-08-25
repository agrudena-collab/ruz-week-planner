from datetime import date
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://ruz.fa.ru"
DEFAULT_TIMEOUT_SECONDS = 30


class RUZClientError(RuntimeError):
    """Raised when the RUZ API cannot provide a usable schedule."""


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


class RUZClient:
    def __init__(self, base_url=BASE_URL, timeout=DEFAULT_TIMEOUT_SECONDS):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def fetch_group_schedule(self, group_id, start: date, finish: date, lng=1):
        params = urlencode(
            {
                "start": start.strftime("%Y.%m.%d"),
                "finish": finish.strftime("%Y.%m.%d"),
                "lng": lng,
            }
        )
        url = f"{self.base_url}/api/schedule/group/{group_id}?{params}"
        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "ScheduleBackend/1.0"},
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise RUZClientError(f"RUZ request failed for group {group_id}: {exc}") from exc

        data = extract_list(raw)
        if data is None:
            raise RUZClientError(f"Unexpected RUZ response shape for group {group_id}")

        lessons = [
            item for item in data
            if isinstance(item, dict) and is_regular_lesson(item)
        ]
        return lessons
