import json
import re
from pathlib import Path

INDEX = Path("index.html")
GROUPS = Path("groups.json")
MARKER = "/* GROUP_PICKER_NATIVE */"
END_MARKER = "/* END_GROUP_PICKER_NATIVE */"

CSS = r'''/* GROUP_PICKER_NATIVE */
.group-picker-wrap{position:relative;margin-top:7px;width:min(360px,78vw)}
.group-picker{width:100%;min-height:38px;appearance:auto;-webkit-appearance:auto;border:1px solid rgba(255,255,255,.10);border-radius:12px;padding:7px 34px 7px 10px;background:rgba(255,255,255,.045);color:#cbd1dd;font-size:13px;font-weight:750;cursor:pointer;touch-action:manipulation}
.group-picker:focus{outline:2px solid rgba(66,217,255,.35);outline-offset:2px}
.group-picker-wrap::after{content:"⌄";position:absolute;right:11px;top:50%;transform:translateY(-52%);color:#8e96a8;pointer-events:none}
@media(max-width:640px){.group-picker-wrap{width:min(330px,82vw)}.group-picker{min-height:42px;font-size:14px}}
/* END_GROUP_PICKER_NATIVE */
'''

JS = r'''/* GROUP_PICKER_NATIVE */
(function(){
  "use strict";

  const TARGET_GROUP_ID = "164606";
  const STORAGE_KEY = "ruz.selectedGroupId";
  const SNAPSHOT_KEY = "ruz.scheduleSnapshot";
  const FETCH_TIMEOUT_MS = 9000;
  const SW_VERSION = "11";
  const select = document.getElementById("groupPickerButton");

  if (!select || select.tagName !== "SELECT") return;

  function validGroupId(id){
    return Array.from(select.options).some(option => String(option.value) === String(id));
  }

  function selectedGroupId(){
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved && validGroupId(saved) ? String(saved) : TARGET_GROUP_ID;
  }

  function setHeader(name){
    const label = document.querySelector(".group");
    if (label && name) label.textContent = name + " · РУЗ";
  }

  function setSelectedHeader(id){
    select.value = String(id);
    const option = select.options[select.selectedIndex];
    if (option) setHeader(option.textContent);
  }

  function writeSnapshot(id, lessons){
    try{
      localStorage.setItem(SNAPSHOT_KEY, JSON.stringify({
        id:String(id),
        savedAt:Date.now(),
        lessons:Array.isArray(lessons) ? lessons : []
      }));
    }catch(_){
      // Snapshot is an extra fallback; failure must never break the app.
    }
  }

  function readSnapshot(id){
    try{
      const raw = localStorage.getItem(SNAPSHOT_KEY);
      if (!raw) return null;
      const data = JSON.parse(raw);
      if (String(data.id) !== String(id) || !Array.isArray(data.lessons)) return null;
      return data.lessons;
    }catch(_){
      return null;
    }
  }

  async function readCacheSnapshot(id){
    try{
      if (!window.caches) return null;
      const key = "./group_schedules/" + encodeURIComponent(String(id)) + ".json";
      const response = await caches.match(key, {ignoreSearch:true});
      if (!response || !response.ok) return null;
      const payload = await response.json();
      return payload && Array.isArray(payload.lessons) ? payload.lessons : null;
    }catch(_){
      return null;
    }
  }

  async function fetchGroupLessons(id){
    const url = "./group_schedules/" + encodeURIComponent(String(id)) + ".json?t=" + Date.now();
    let networkError = null;

    try{
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
      try{
        const response = await fetch(url, {
          cache:"no-store",
          credentials:"same-origin",
          headers:{Accept:"application/json"},
          signal:controller.signal
        });
        if (!response.ok) throw new Error("Не удалось загрузить расписание выбранной группы");
        const payload = await response.json();
        if (!payload || !Array.isArray(payload.lessons)) throw new Error("Некорректный файл расписания группы");
        writeSnapshot(id, payload.lessons);
        return payload.lessons;
      }finally{
        clearTimeout(timer);
      }
    }catch(error){
      networkError = error;
    }

    const cached = await readCacheSnapshot(id);
    if (cached) {
      writeSnapshot(id, cached);
      return cached;
    }

    const snapshot = readSnapshot(id);
    if (snapshot) return snapshot;

    throw networkError || new Error("Не удалось загрузить расписание выбранной группы");
  }

  function applyLessons(lessons){
    schedule = typeof sort === "function" ? sort(lessons || []) : (lessons || []);
    archive = [];
    renderSchedule();
    if (typeof renderStats === "function") renderStats();
    if (typeof updateHero === "function") updateHero();
  }

  // One and only one initial boot path: the existing loadAll() below calls
  // this overridden loadSchedule(). We deliberately do not call loadGroup()
  // on DOMContentLoaded, which used to race loadAll() and leave iOS PWAs in
  // a permanent loading state.
  loadSchedule = async function(){
    const id = selectedGroupId();
    const button = $("refreshButton");
    button.classList.add("loading");
    button.textContent = "↻ Обновление...";
    try{
      const lessons = await fetchGroupLessons(id);
      applyLessons(lessons);
      $("updated").textContent = "Обновлено в " + new Date().toLocaleTimeString("ru-RU",{hour:"2-digit",minute:"2-digit"});
    }catch(error){
      if(currentView !== "archive" && currentView !== "exams") {
        $("schedule").innerHTML = `<div class="error"><strong>Не удалось загрузить расписание</strong> ${esc(error.message || "Ошибка загрузки")}</div>`;
      }
      throw error;
    }finally{
      button.classList.remove("loading");
      button.textContent = "↻ Обновить";
    }
  };

  window.__ruzApp = window.__ruzApp || {};
  window.__ruzApp.loadGroup = async function(id){
    const selectedId = String(id);
    if(!validGroupId(selectedId)) return;

    localStorage.setItem(STORAGE_KEY, selectedId);
    setSelectedHeader(selectedId);
    select.disabled = true;
    select.setAttribute("aria-busy","true");

    try{
      const lessons = await fetchGroupLessons(selectedId);
      applyLessons(lessons);
      const status = $("updated");
      if (status) status.textContent = "Обновлено в " + new Date().toLocaleTimeString("ru-RU",{hour:"2-digit",minute:"2-digit"});
    }catch(error){
      const status = $("updated");
      if (status) status.textContent = error.message || "Ошибка загрузки группы";
      throw error;
    }finally{
      select.disabled = false;
      select.setAttribute("aria-busy","false");
    }
  };

  select.addEventListener("change", function(){
    window.__ruzApp.loadGroup(this.value).catch(() => {
      const fallback = selectedGroupId();
      setSelectedHeader(fallback);
      localStorage.setItem(STORAGE_KEY, fallback);
    });
  });

  // Restore only the UI state here. Data is loaded exactly once by loadAll().
  const initialId = selectedGroupId();
  localStorage.setItem(STORAGE_KEY, initialId);
  setSelectedHeader(initialId);

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("./sw.js?v=" + SW_VERSION, {updateViaCache:"none"})
      .then(registration => registration.update().catch(() => {}))
      .catch(() => {});
  }

  if (navigator.storage && navigator.storage.persist) {
    navigator.storage.persist().catch(() => {});
  }
})();
/* END_GROUP_PICKER_NATIVE */
'''


def remove_generated(text):
    # Remove every generated marker-delimited block, not just the first one.
    # The previous implementation left a second JS block behind after repeated
    # CI repairs, which caused multiple loadAll/loadGroup races on iOS PWA.
    text = re.sub(
        re.escape(MARKER) + r".*?" + re.escape(END_MARKER),
        "",
        text,
        flags=re.S,
    )

    # Remove older generator formats as well.
    text = re.sub(r"\n?/\* GROUP_PICKER_VIEW \*/.*?(?=\n\s*</style>)", "", text, flags=re.S)
    text = re.sub(r"\n?/\* GROUP_PICKER_VIEW \*/.*?(?=\n\s*</script>)", "", text, flags=re.S)
    while "<!-- GROUP_PICKER_VIEW -->" in text:
        start = text.rfind("<!-- GROUP_PICKER_VIEW -->")
        end = text.find("</body>", start)
        if end < 0:
            break
        text = text[:start] + text[end:]
    return text


def build_options(groups):
    out=[]
    for group in groups:
        gid=str(group["id"])
        name=str(group["name"])
        safe=(name.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;"))
        selected=" selected" if gid=="164606" else ""
        out.append(f'        <option value="{gid}"{selected}>{safe}</option>')
    return "\n".join(out)


text=remove_generated(INDEX.read_text(encoding="utf-8"))
groups=json.loads(GROUPS.read_text(encoding="utf-8"))
if not isinstance(groups,list) or not groups:
    raise SystemExit("groups.json must contain a non-empty array")

options=build_options(groups)
new_control=(
    '<div class="group-picker-wrap">\n'
    '      <select class="group-picker" id="groupPickerButton" aria-label="Выбор учебной группы">\n'
    + options + '\n'
    '      </select>\n'
    '</div>'
)

old_button=re.compile(r'<button class="group-picker" id="groupPickerButton" type="button">.*?</button>',re.S)
old_select=re.compile(r'<select class="group-picker" id="groupPickerButton".*?</select>',re.S)
if old_button.search(text):
    text=old_button.sub(new_control,text,count=1)
elif old_select.search(text):
    text=old_select.sub(new_control,text,count=1)
elif 'id="groupPickerButton"' not in text:
    needle='      <div class="group">\n        МеждОт25-2 · РУЗ\n      </div>'
    if needle not in text:
        raise SystemExit("group header markup not found")
    text=text.replace(needle,needle+"\n\n"+new_control,1)

style_pos=text.find("</style>")
if style_pos<0:
    raise SystemExit("</style> not found")
text=text[:style_pos]+"\n"+CSS+text[style_pos:]

boot=re.search(r'loadAll\(\)\.then\(\(\) => \{',text)
if not boot:
    raise SystemExit("real loadAll().then(...) boot call not found")
text=text[:boot.start()]+JS+"\n\n"+text[boot.start():]

INDEX.write_text(text,encoding="utf-8")
print(f"Installed exactly one native group picker for {len(groups)} groups")
