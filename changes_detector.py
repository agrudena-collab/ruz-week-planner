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
    """Stable lesson identity independent of fields we detect as changes."""
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

# The schedule is a rolling window. Its first/last dates naturally move
# between runs, so lessons that disappear from the old window or appear at
# the new far edge must not be reported as real removals/additions.
old_dates = {x.get("date", "") for x in old if x.get("date", "")}
new_dates = {x.get("date", "") for x in new if x.get("date", "")}
shared_dates = old_dates & new_dates

changes = []
now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

for lesson_id in sorted(old_by_id.keys() | new_by_id.keys()):
    previous = old_by_id.get(lesson_id)
    current = new_by_id.get(lesson_id)

    if previous is None:
        # Ignore additions that exist only because the rolling window moved.
        if current.get("date", "") not in shared_dates:
            continue
        change = make_change(None, current, now, "added")
    elif current is None:
        # Ignore removals that exist only because the rolling window moved.
        if previous.get("date", "") not in shared_dates:
            continue
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
print(f"Shared dates: {len(shared_dates)}")
print(f"Detected changes: {len(changes)}")
