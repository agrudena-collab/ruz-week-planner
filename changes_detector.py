import json
from datetime import datetime
from pathlib import Path

OLD_DIR = Path("group_schedules_previous")
NEW_DIR = Path("group_schedules")
OUTPUT_DIR = Path("changes_by_group")
LEGACY_FILE = Path("changes.json")

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
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def identity(lesson):
    return (
        lesson.get("date", ""),
        lesson.get("lessonNumberStart", ""),
        lesson.get("lessonNumberEnd", ""),
        lesson.get("group", ""),
        lesson.get("subGroup", ""),
        lesson.get("stream", ""),
    )


def make_change(previous, current, now, status=None):
    source = current or previous
    fields = []

    if status == "added":
        fields.append({"field": "status", "label": "Статус", "old": "Не было", "new": "Добавлено"})
    elif status == "removed":
        fields.append({"field": "status", "label": "Статус", "old": "Было в расписании", "new": "Удалено"})
    else:
        for field, label in COMPARE_FIELDS.items():
            before = previous.get(field, "")
            after = current.get(field, "")
            if before != after:
                fields.append({"field": field, "label": label, "old": before, "new": after})

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


def detect(previous, current, now):
    old_by_id = {identity(x): x for x in previous if identity(x) != ("", "", "", "", "", "")}
    new_by_id = {identity(x): x for x in current if identity(x) != ("", "", "", "", "", "")}
    old_dates = {x.get("date", "") for x in previous if x.get("date", "")}
    new_dates = {x.get("date", "") for x in current if x.get("date", "")}
    shared_dates = old_dates & new_dates
    changes = []

    for lesson_id in sorted(old_by_id.keys() | new_by_id.keys()):
        previous_lesson = old_by_id.get(lesson_id)
        current_lesson = new_by_id.get(lesson_id)

        if previous_lesson is None:
            if current_lesson.get("date", "") not in shared_dates:
                continue
            change = make_change(None, current_lesson, now, "added")
        elif current_lesson is None:
            if previous_lesson.get("date", "") not in shared_dates:
                continue
            change = make_change(previous_lesson, None, now, "removed")
        else:
            change = make_change(previous_lesson, current_lesson, now)

        if change:
            changes.append(change)

    changes.sort(key=lambda x: (x.get("date", ""), x.get("beginLesson", "")))
    return changes


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR_FILES = set()
now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

for new_path in sorted(NEW_DIR.glob("*.json")):
    group_id = new_path.stem
    current = load(new_path)
    previous = load(OLD_DIR / new_path.name)
    changes = detect(previous, current, now) if previous else []
    out = OUTPUT_DIR / new_path.name
    out.write_text(json.dumps(changes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_DIR_FILES.add(out.name)
    print(f"{group_id}: previous={len(previous)} current={len(current)} changes={len(changes)}")

for old_output in OUTPUT_DIR.glob("*.json"):
    if old_output.name not in OUTPUT_DIR_FILES:
        old_output.unlink()

# Keep the legacy file for the currently active/default group.
legacy = OUTPUT_DIR / "164606.json"
LEGACY_FILE.write_text(legacy.read_text(encoding="utf-8") if legacy.exists() else "[]\n", encoding="utf-8")
print(f"Wrote {len(OUTPUT_DIR_FILES)} per-group change files")
