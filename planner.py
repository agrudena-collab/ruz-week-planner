import json
from datetime import datetime

with open("schedule.json", "r", encoding="utf-8") as f:
    schedule = json.load(f)

print("РАСПИСАНИЕ МЕЖДОТ25-2")
print("=" * 60)

if not schedule:
    print("Расписание не найдено.")
    raise SystemExit

schedule = sorted(
    schedule,
    key=lambda x: (
        x.get("date", ""),
        x.get("beginLesson", "")
    )
)

current_date = None

for lesson in schedule:
    lesson_date = lesson.get("date", "Дата неизвестна")

    if lesson_date != current_date:
        current_date = lesson_date

        try:
            date_obj = datetime.strptime(lesson_date, "%Y-%m-%d")
            date_text = date_obj.strftime("%d.%m.%Y")
        except ValueError:
            date_text = lesson_date

        print()
        print(f"📅 {date_text}")
        print("-" * 60)

    begin = lesson.get("beginLesson", "?")
    end = lesson.get("endLesson", "?")
    discipline = lesson.get("discipline", "Предмет неизвестен")
    lecturer = lesson.get("lecturer", "Преподаватель неизвестен")
    auditorium = lesson.get("auditorium", "Аудитория неизвестна")
    building = lesson.get("building", "")

    print(f"🕐 {begin}–{end}")
    print(f"📚 {discipline}")
    print(f"👨‍🏫 {lecturer}")

    if auditorium:
        print(f"🏫 {auditorium}")

    if building:
        print(f"📍 {building}")

    print()
