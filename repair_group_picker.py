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
  const select = document.getElementById("groupPickerButton");
  if (!select || select.tagName !== "SELECT") return;
  function validGroupId(id){ return Array.from(select.options).some(option => String(option.value) === String(id)); }
  function selectedGroupId(){ const saved = localStorage.getItem(STORAGE_KEY); return saved && validGroupId(saved) ? String(saved) : TARGET_GROUP_ID; }
  function setHeader(name){ const label = document.querySelector(".group"); if (label && name) label.textContent = name + " · РУЗ"; }
  async function fetchGroupLessons(id){
    const response = await fetch("./group_schedules/" + encodeURIComponent(String(id)) + ".json?t=" + Date.now(), {cache:"no-store",headers:{Accept:"application/json"}});
    if (!response.ok) throw new Error("Не удалось загрузить расписание выбранной группы");
    const payload = await response.json();
    if (!payload || !Array.isArray(payload.lessons)) throw new Error("Некорректный файл расписания группы");
    return payload.lessons;
  }
  const originalLoadSchedule = loadSchedule;
  loadSchedule = async function(){
    const id = selectedGroupId();
    const button = $("refreshButton");
    button.classList.add("loading");
    button.textContent = "↻ Обновление...";
    try{
      const lessons = await fetchGroupLessons(id);
      schedule = typeof sort === "function" ? sort(lessons) : lessons;
      archive = [];
      $("updated").textContent = "Обновлено в " + new Date().toLocaleTimeString("ru-RU",{hour:"2-digit",minute:"2-digit"});
      renderSchedule();
    }catch(error){
      if(id === TARGET_GROUP_ID){ await originalLoadSchedule(); return; }
      if(currentView !== "archive" && currentView !== "exams") $("schedule").innerHTML = `<div class="error"><strong>Не удалось загрузить расписание</strong> ${esc(error.message)}</div>`;
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
    localStorage.setItem(STORAGE_KEY,selectedId);
    select.value = selectedId;
    const option = select.options[select.selectedIndex];
    if(option) setHeader(option.textContent);
    select.disabled = true;
    select.setAttribute("aria-busy","true");
    try{
      const lessons = await fetchGroupLessons(selectedId);
      schedule = typeof sort === "function" ? sort(lessons) : lessons;
      archive = [];
      renderSchedule();
      if(typeof renderStats === "function") renderStats();
      if(typeof updateHero === "function") updateHero();
    }finally{
      select.disabled = false;
      select.setAttribute("aria-busy","false");
    }
  };
  select.addEventListener("change",function(){
    window.__ruzApp.loadGroup(this.value).catch(()=>{
      select.value = TARGET_GROUP_ID;
      localStorage.setItem(STORAGE_KEY,TARGET_GROUP_ID);
      const option = select.options[select.selectedIndex];
      if(option) setHeader(option.textContent);
      window.__ruzApp.loadGroup(TARGET_GROUP_ID).catch(()=>{});
    });
  });
  function restoreSelected(){
    const id = selectedGroupId();
    select.value = id;
    const option = select.options[select.selectedIndex];
    if(option) setHeader(option.textContent);
    localStorage.setItem(STORAGE_KEY,id);
    return window.__ruzApp.loadGroup(id);
  }
  if(document.readyState === "loading") document.addEventListener("DOMContentLoaded",()=>restoreSelected().catch(()=>{}),{once:true});
  else restoreSelected().catch(()=>{});
})();
/* END_GROUP_PICKER_NATIVE */
'''


def remove_generated(text):
    # Remove current marker-delimited injections and legacy injections that were
    # created before END_GROUP_PICKER_NATIVE was present.
    text = re.sub(r"\n?/\* GROUP_PICKER_NATIVE \*/.*?(?=\n\s*</style>)", "", text, flags=re.S)
    text = re.sub(r"\n?/\* GROUP_PICKER_NATIVE \*/.*?(?=\n\s*loadAll\(\)\.then\(\(\) => \{)", "", text, flags=re.S)
    text = re.sub(r"\n?/\* GROUP_PICKER_VIEW \*/.*?(?=\n\s*</style>)", "", text, flags=re.S)
    text = re.sub(r"\n?/\* GROUP_PICKER_VIEW \*/.*?(?=\n\s*</script>)", "", text, flags=re.S)
    while "<!-- GROUP_PICKER_VIEW -->" in text:
        start = text.rfind("<!-- GROUP_PICKER_VIEW -->")
        end = text.find("</body>", start)
        if end < 0: break
        text = text[:start] + text[end:]
    return text


def build_options(groups):
    out=[]
    for group in groups:
        gid=str(group["id"]); name=str(group["name"])
        safe=(name.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;"))
        selected=" selected" if gid=="164606" else ""
        out.append(f'        <option value="{gid}"{selected}>{safe}</option>')
    return "\n".join(out)

text=remove_generated(INDEX.read_text(encoding="utf-8"))
groups=json.loads(GROUPS.read_text(encoding="utf-8"))
if not isinstance(groups,list) or not groups: raise SystemExit("groups.json must contain a non-empty array")
options=build_options(groups)
new_control=('<div class="group-picker-wrap">\n'
              '      <select class="group-picker" id="groupPickerButton" aria-label="Выбор учебной группы">\n'
              + options + '\n'
              '      </select>\n'
              '</div>')
old_button=re.compile(r'<button class="group-picker" id="groupPickerButton" type="button">.*?</button>',re.S)
old_select=re.compile(r'<select class="group-picker" id="groupPickerButton".*?</select>',re.S)
if old_button.search(text): text=old_button.sub(new_control,text,count=1)
elif old_select.search(text): text=old_select.sub(new_control,text,count=1)
elif 'id="groupPickerButton"' not in text:
    needle='      <div class="group">\n        МеждОт25-2 · РУЗ\n      </div>'
    if needle not in text: raise SystemExit("group header markup not found")
    text=text.replace(needle,needle+"\n\n"+new_control,1)
style_pos=text.find("</style>")
if style_pos<0: raise SystemExit("</style> not found")
text=text[:style_pos]+"\n"+CSS+text[style_pos:]
boot=re.search(r'loadAll\(\)\.then\(\(\) => \{',text)
if not boot: raise SystemExit("real loadAll().then(...) boot call not found")
text=text[:boot.start()]+JS+"\n\n"+text[boot.start():]
INDEX.write_text(text,encoding="utf-8")
print(f"Installed exactly one native group picker for {len(groups)} groups")
