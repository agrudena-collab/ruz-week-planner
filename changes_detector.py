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


def key(lesson):
    return (
        lesson.get("date", ""),
        lesson.get("beginLesson", ""),
        lesson.get("endLesson", ""),
        lesson.get("discipline", ""),
        lesson.get("lecturer", ""),
        lesson.get("auditorium", ""),
        lesson.get("building", ""),
        lesson.get("kindOfWork", ""),
    )


def identity(lesson):
    # A lesson is identified by date, start time and subject.
    return (
        lesson.get("date", ""),
        lesson.get("beginLesson", ""),
        lesson.get("discipline", ""),
    )


old = load(OLD_FILE)
new = load(NEW_FILE)

old_by_id = {identity(x): x for x in old if identity(x) != ("", "", "")}
new_by_id = {identity(x): x for x in new if identity(x) != ("", "", "")}

changes = []
now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

for lesson_id, current in new_by_id.items():
    previous = old_by_id.get(lesson_id)
    if previous is None:
        continue

    fields = []
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

    if fields:
        changes.append({
            "date": current.get("date", ""),
            "beginLesson": current.get("beginLesson", ""),
            "endLesson": current.get("endLesson", ""),
            "discipline": current.get("discipline", ""),
            "lecturer": current.get("lecturer", ""),
            "auditorium": current.get("auditorium", ""),
            "building": current.get("building", ""),
            "detectedAt": now,
            "fields": fields,
        })

changes.sort(key=lambda x: (x.get("date", ""), x.get("beginLesson", "")))

with CHANGES_FILE.open("w", encoding="utf-8") as f:
    json.dump(changes, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"Previous lessons: {len(old)}")
print(f"Current lessons: {len(new)}")
print(f"Detected changed lessons: {len(changes)}")
