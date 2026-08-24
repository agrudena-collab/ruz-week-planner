import json
from pathlib import Path
from datetime import datetime

OLD_FILE = Path("schedule_previous.json")
NEW_FILE = Path("schedule.json")
CHANGES_FILE = Path("changes.json")

COMPARE_FIELDS = {
    "beginLesson": "Время начала",
    "endLesson": "Время окончания",
    "discipline": "Предмет",
    "lecturer": "Преподаватель",
    "auditorium": "Аудитория",
    "building": "Корпус",
    "kindOfWork": "Тип занятия",
}


def load(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def identity(lesson):
    """
    Stable lesson identity that does not depend on fields we want to detect
    as changes. This lets us detect time/subject/teacher/room changes.
    """
    return (
        lesson.get("date", ""),
        lesson.get("lessonNumberStart", ""),
        lesson.get("lessonNumberEnd", ""),
        lesson.get("group", ""),
        lesson.get("subGroup", ""),
        lesson.get("stream", ""),
        lesson.get("contentTableOfLessonsOid", ""),
    )


def make_change(previous, current, now, status=None):
    source = current or previous
    fields = []

    if status == "added":
        fields.append({
            "field": "status",
            "label": "Статус",
            "old": "Не было",
            "new": "Добавлено",
        })
    elif status == "removed":
        fields.append({
            "field": "status",
            "label": "Статус",
            "old": "Было в расписании",
            "new": "Удалено",
        })
    else:
        for field, label in COMPARE_FIELDS.items():
            before = previous.get(field, "")
            after = current.get(field, "")
            if before != after:
                fields.append({
                    "field": field,
                    "label": label,
                    "old": before,
                    "new": after,
                })

    if not fields:
        return None

    return {
        "date": source.get("date", ""),
        "beginLesson": source.get("beginLesson", ""),
        "endLesson": source.get("endLesson", ""),
        "discipline": source.get("discipline", ""),
        "lecturer": source.get("lecturer", ""),
        "auditorium": source.get("auditorium", ""),
        "building": source.get("building", ""),
        "detectedAt": now,
        "fields": fields,
    }


old = load(OLD_FILE)
new = load(NEW_FILE)

old_by_id = {
    identity(x): x
    for x in old
    if identity(x) != ("", "", "", "", "", "", "")
}
new_by_id = {
    identity(x): x
    for x in new
    if identity(x) != ("", "", "", "", "", "", "")
}

changes = []
now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

# Existing lessons: detect changed fields.
for lesson_id in sorted(old_by_id.keys() | new_by_id.keys()):
    previous = old_by_id.get(lesson_id)
    current = new_by_id.get(lesson_id)

    if previous is None:
        change = make_change(None, current, now, "added")
    elif current is None:
        change = make_change(previous, None, now, "removed")
    else:
        change = make_change(previous, current, now)

    if change:
        changes.append(change)

changes.sort(key=lambda x: (x.get("date", ""), x.get("beginLesson", "")))

with CHANGES_FILE.open("w", encoding="utf-8") as f:
    json.dump(changes, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"Previous lessons: {len(old)}")
print(f"Current lessons: {len(new)}")
print(f"Detected changes: {len(changes)}")
