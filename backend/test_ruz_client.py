import json
from datetime import date
from urllib.parse import parse_qs, urlparse

import pytest

import backend.ruz_client as ruz_client
from backend.ruz_client import RUZClient, RUZClientError


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_fetch_group_schedule_builds_expected_request(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        return FakeResponse({
            "data": [
                {"id": 1, "kindOfWork": "Лекция", "deletion_mark": 0},
                {"id": 2, "kindOfWork": "Повторная промежуточная аттестация", "deletion_mark": 0},
                {"id": 3, "kindOfWork": "Семинар", "deletion_mark": 1},
            ]
        })

    monkeypatch.setattr(ruz_client, "urlopen", fake_urlopen)

    client = RUZClient(base_url="https://example.test", timeout=12)
    lessons = client.fetch_group_schedule(164606, date(2026, 8, 25), date(2026, 11, 3))

    parsed = urlparse(seen["url"])
    params = parse_qs(parsed.query)
    assert parsed.path == "/api/schedule/group/164606"
    assert params == {"start": ["2026.08.25"], "finish": ["2026.11.03"], "lng": ["1"]}
    assert seen["timeout"] == 12
    assert [item["id"] for item in lessons] == [1]


def test_unexpected_response_shape_is_rejected(monkeypatch):
    monkeypatch.setattr(ruz_client, "urlopen", lambda request, timeout: FakeResponse({"status": "ok"}))

    client = RUZClient(base_url="https://example.test")
    with pytest.raises(RUZClientError, match="Unexpected RUZ response shape"):
        client.fetch_group_schedule(164606, date(2026, 8, 25), date(2026, 8, 26))
