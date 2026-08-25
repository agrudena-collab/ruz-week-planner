import json
import re
from pathlib import Path

INDEX = Path("index.html")
GROUPS = Path("groups.json")

CSS = r'''/* GROUP_PICKER_NATIVE */
.group-picker-wrap{
  position:relative;
  margin-top:7px;
  width:min(360px,78vw);
}
.group-picker{
  width:100%;
  min-height:38px;
  appearance:auto;
  -webkit-appearance:auto;
  border:1px solid rgba(255,255,255,.10);
  border-radius:12px;
  padding:7px 34px 7px 10px;
  background:rgba(255,255,255,.045);
  color:#cbd1dd;
  font-size:13px;
  font-weight:750;
  cursor:pointer;
  touch-action:manipulation;
}
.group-picker:focus{
  outline:2px solid rgba(66,217,255,.35);
  outline-offset:2px;
}
.group-picker-wrap::after{
  content:"⌄";
  position:absolute;
  right:11px;
  top:50%;
  transform:translateY(-52%);
  color:#8e96a8;
  pointer-events:none;
}
@media(max-width:640px){
  .group-picker-wrap{width:min(330px,82vw)}
  .group-picker{min-height:42px;font-size:14px}
}
'''

JS = r'''/* GROUP_PICKER_NATIVE */
(function(){
  "use strict";

  const TARGET_GROUP_ID = "164606";
  const STORAGE_KEY = "ruz.selectedGroupId";
  const select = document.getElementById("groupPickerButton");
  if (!select || select.tagName !== "SELECT") return;

  let currentId = localStorage.getItem(STORAGE_KEY) || TARGET_GROUP_ID;
  let loading = false;

  function setHeader(group){
    const label = document.querySelector(".group");
    if (label && group) label.textContent = group.name + " · РУЗ";
  }

  function setBusy(value){
    loading = value;
    select.disabled = value;
    select.setAttribute("aria-busy", value ? "true" : "false");
  }

  async function loadGroup(id, closeNativePicker){
    if (loading) return;
    const group = Array.from(select.options).find(option => String(option.value) === String(id));
    if (!group) return;

    currentId = String(id);
    localStorage.setItem(STORAGE_KEY, currentId);
    setHeader({name: group.textContent});

    if (currentId === TARGET_GROUP_ID) {
      // The default group is already loaded by the main application.
      if (window.__ruzApp && typeof window.__ruzApp.restoreDefault === "function") {
        window.__ruzApp.restoreDefault();
      }
      return;
    }

    setBusy(true);
    try {
      const response = await fetch("./group_schedules/" + encodeURIComponent(currentId) + ".json?t=" + Date.now(), {
        cache: "no-store",
        headers: { "Accept": "application/json" }
      });
      if (!response.ok) throw new Error("Не удалось загрузить расписание выбранной группы");
      const payload = await response.json();
      if (!payload || !Array.isArray(payload.lessons)) throw new Error("Некорректный файл расписания группы");

      if (window.__ruzApp && typeof window.__ruzApp.setSchedule === "function") {
        window.__ruzApp.setSchedule(payload.lessons);
      } else {
        throw new Error("Основное приложение ещё не готово");
      }
    } catch (error) {
      // Revert to the previously working selection instead of leaving the UI in a broken state.
      select.value = currentId === TARGET_GROUP_ID ? TARGET_GROUP_ID : (localStorage.getItem(STORAGE_KEY) || TARGET_GROUP_ID);
      const status = document.getElementById("updated");
      if (status) status.textContent = error.message || "Ошибка загрузки группы";
    } finally {
      setBusy(false);
    }
  }

  select.addEventListener("change", function(){
    loadGroup(this.value, true);
  });

  // Restore the saved group only after the main schedule has had a chance to load.
  function restoreSaved(){
    const saved = localStorage.getItem(STORAGE_KEY) || TARGET_GROUP_ID;
    select.value = String(saved);
    const option = select.options[select.selectedIndex];
    if (option) setHeader({name: option.textContent});
    if (String(saved) !== TARGET_GROUP_ID) loadGroup(saved, false);
  }

  // Main application exposes a readiness event after its initial schedule fetch.
  document.addEventListener("ruz:schedule-ready", restoreSaved, { once: true });
  setTimeout(() => {
    if (!window.__ruzApp || !window.__ruzApp.ready) restoreSaved();
  }, 1500);
})();
'''


def remove_marked_css(text):
    return re.sub(
        r"\n?/\* GROUP_PICKER_VIEW \*/.*?(?=\n\s*</style>)",
        "",
        text,
        flags=re.S,
    )


def remove_marked_js(text):
    return re.sub(
        r"\n?/\* GROUP_PICKER_VIEW \*/.*?(?=\n\s*</script>)",
        "",
        text,
        flags=re.S,
    )


def remove_marked_html(text):
    while "<!-- GROUP_PICKER_VIEW -->" in text:
        start = text.rfind("<!-- GROUP_PICKER_VIEW -->")
        end = text.find("</body>", start)
        if end < 0:
            break
        text = text[:start] + text[end:]
    return text


def build_options(groups, selected_id):
    options = []
    for group in groups:
        gid = str(group["id"])
        name = str(group["name"])
        selected = " selected" if gid == selected_id else ""
        safe_name = (
            name.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        options.append(f'        <option value="{gid}"{selected}>{safe_name}</option>')
    return "\n".join(options)


text = INDEX.read_text(encoding="utf-8")
groups = json.loads(GROUPS.read_text(encoding="utf-8"))
if not isinstance(groups, list) or not groups:
    raise SystemExit("groups.json must contain a non-empty array")

selected_id = str(next((g["id"] for g in groups if str(g["id"]) == "164606"), groups[0]["id"]))

# Remove every old picker implementation first. This makes the migration idempotent
# and prevents duplicate IDs/listeners from accumulating in index.html.
text = remove_marked_css(text)
text = remove_marked_js(text)
text = remove_marked_html(text)

# Replace the old custom button with a real HTML <select>. Native form controls are
# deliberately used as the primary interaction on iOS/iPadOS; the JS only reacts to change.
old_button = re.compile(
    r'<button class="group-picker" id="groupPickerButton" type="button">.*?</button>',
    flags=re.S,
)
new_control = (
    '<div class="group-picker-wrap">\n'
    '      <select class="group-picker" id="groupPickerButton" aria-label="Выбор учебной группы">\n'
    + build_options(groups, selected_id)
    + '\n      </select>\n'
    '</div>'
)

if old_button.search(text):
    text = old_button.sub(new_control, text, count=1)
elif 'id="groupPickerButton"' not in text:
    needle = '      <div class="group">\n        МеждОт25-2 · РУЗ\n      </div>'
    if needle not in text:
        raise SystemExit("group header markup not found")
    text = text.replace(needle, needle + "\n\n" + new_control, 1)
else:
    # A previous run may already have produced the native select. Refresh its options.
    text = re.sub(
        r'<select class="group-picker" id="groupPickerButton".*?</select>',
        '<select class="group-picker" id="groupPickerButton" aria-label="Выбор учебной группы">\n'
        + build_options(groups, selected_id)
        + '\n      </select>',
        text,
        count=1,
        flags=re.S,
    )

style_pos = text.rfind("</style>")
if style_pos < 0:
    raise SystemExit("</style> not found")
text = text[:style_pos] + "\n" + CSS + "\n" + text[style_pos:]

script_pos = text.rfind("</script>")
if script_pos < 0:
    raise SystemExit("</script> not found")
text = text[:script_pos] + "\n" + JS + "\n" + text[script_pos:]

INDEX.write_text(text, encoding="utf-8")
print(f"Installed native group selector for {len(groups)} groups")
