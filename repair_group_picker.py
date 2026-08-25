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

  // Bridge into the main non-module script. The closure can access its lexical
  // schedule variable; assigning window.schedule would create a different value.
  window.__ruzApp = window.__ruzApp || {};
  window.__ruzApp.ready = false;
  window.__ruzApp.setSchedule = function(lessons){
    schedule = typeof sort === "function" ? sort(lessons || []) : (lessons || []);
    archive = [];
    if (typeof renderSchedule === "function") renderSchedule();
    if (typeof renderStats === "function") renderStats();
    if (typeof updateHero === "function") updateHero();
  };
  window.__ruzApp.restoreDefault = function(){
    if (typeof loadAll === "function") loadAll();
  };

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("./sw.js", {
      scope: "./",
      updateViaCache: "none"
    }).catch(() => {});
  }

  if (!select || select.tagName !== "SELECT") return;

  let loading = false;

  function setHeader(name){
    const label = document.querySelector(".group");
    if (label && name) label.textContent = name + " · РУЗ";
  }

  async function loadGroup(id){
    if (loading) return;
    const option = Array.from(select.options).find(item => String(item.value) === String(id));
    if (!option) return;

    const selectedId = String(id);
    localStorage.setItem(STORAGE_KEY, selectedId);
    select.value = selectedId;
    setHeader(option.textContent);

    if (selectedId === TARGET_GROUP_ID) {
      window.__ruzApp.restoreDefault();
      return;
    }

    loading = true;
    select.disabled = true;
    select.setAttribute("aria-busy", "true");

    try {
      const response = await fetch(
        "./group_schedules/" + encodeURIComponent(selectedId) + ".json?t=" + Date.now(),
        { cache: "no-store", headers: { Accept: "application/json" } }
      );
      if (!response.ok) throw new Error("Не удалось загрузить расписание выбранной группы");
      const payload = await response.json();
      if (!payload || !Array.isArray(payload.lessons)) {
        throw new Error("Некорректный файл расписания группы");
      }
      window.__ruzApp.setSchedule(payload.lessons);
    } catch (error) {
      const status = document.getElementById("updated");
      if (status) status.textContent = error.message || "Ошибка загрузки группы";
      select.value = localStorage.getItem(STORAGE_KEY) || TARGET_GROUP_ID;
    } finally {
      loading = false;
      select.disabled = false;
      select.setAttribute("aria-busy", "false");
    }
  }

  select.addEventListener("change", function(){
    loadGroup(this.value);
  });

  function restoreSaved(){
    const saved = localStorage.getItem(STORAGE_KEY) || TARGET_GROUP_ID;
    if (!Array.from(select.options).some(option => String(option.value) === String(saved))) {
      localStorage.removeItem(STORAGE_KEY);
      select.value = TARGET_GROUP_ID;
      return;
    }
    select.value = String(saved);
    const option = select.options[select.selectedIndex];
    if (option) setHeader(option.textContent);
    if (String(saved) !== TARGET_GROUP_ID) loadGroup(saved);
  }

  document.addEventListener("ruz:schedule-ready", function(){
    window.__ruzApp.ready = true;
    restoreSaved();
  }, { once: true });

  // Defensive fallback for a very slow network/device where the ready event
  // has not arrived yet.
  setTimeout(() => {
    if (!window.__ruzApp.ready) {
      window.__ruzApp.ready = true;
      restoreSaved();
    }
  }, 3000);
})();
'''


def remove_marked_css(text):
    return re.sub(r"\n?/\* GROUP_PICKER_VIEW \*/.*?(?=\n\s*</style>)", "", text, flags=re.S)


def remove_marked_js(text):
    return re.sub(r"\n?/\* GROUP_PICKER_VIEW \*/.*?(?=\n\s*</script>)", "", text, flags=re.S)


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

# Remove every old picker implementation first. This makes the migration idempotent.
text = remove_marked_css(text)
text = remove_marked_js(text)
text = remove_marked_html(text)

# Replace the old custom button with a real native <select>.
old_button = re.compile(r'<button class="group-picker" id="groupPickerButton" type="button">.*?</button>', flags=re.S)
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
    text = re.sub(
        r'<select class="group-picker" id="groupPickerButton".*?</select>',
        '<select class="group-picker" id="groupPickerButton" aria-label="Выбор учебной группы">\n'
        + build_options(groups, selected_id)
        + '\n      </select>',
        text,
        count=1,
        flags=re.S,
    )

# Expose the main app bridge before its first loadAll() call and emit a readiness event.
bridge_anchor = 'window.__ruzApp = window.__ruzApp || {};'
if bridge_anchor not in text:
    last_load = text.rfind("loadAll();")
    if last_load < 0:
        raise SystemExit("initial loadAll(); call not found")
    readiness = '''window.__ruzApp = window.__ruzApp || {};\nwindow.__ruzApp.ready = false;\nwindow.__ruzApp.setSchedule = function(lessons){\n  schedule = typeof sort === "function" ? sort(lessons || []) : (lessons || []);\n  archive = [];\n  if (typeof renderSchedule === "function") renderSchedule();\n  if (typeof renderStats === "function") renderStats();\n  if (typeof updateHero === "function") updateHero();\n};\nwindow.__ruzApp.restoreDefault = function(){\n  if (typeof loadAll === "function") loadAll();\n};\n\n'''
    text = text[:last_load] + readiness + text[last_load:]

# Replace the initial call with a readiness-aware call. This only changes the first boot call.
first_load = text.find("loadAll();")
if first_load >= 0:
    text = text[:first_load] + 'loadAll().then(() => {\n  window.__ruzApp.ready = true;\n  document.dispatchEvent(new Event("ruz:schedule-ready"));\n}).catch(() => {\n  window.__ruzApp.ready = true;\n  document.dispatchEvent(new Event("ruz:schedule-ready"));\n});' + text[first_load + len("loadAll();"):]

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
