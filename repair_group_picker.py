from pathlib import Path

INDEX = Path("index.html")

JS = r'''/* GROUP_PICKER_VIEW */
(function(){
  "use strict";

  const TARGET_GROUP_ID = "164606";
  const TARGET_GROUP_NAME = "МеждОт25-2";
  const storageKey = "ruz.selectedGroupId";
  let catalog = [];
  let schedules = {};
  let selectedId = TARGET_GROUP_ID;

  const get = id => document.getElementById(id);

  function esc(value){
    return String(value ?? "").replace(/[&<>\"']/g, ch => ({
      "&":"&amp;", "<":"&lt;", ">":"&gt;", "\"":"&quot;", "'":"&#39;"
    }[ch]));
  }

  function readStored(){
    try { return localStorage.getItem(storageKey) || TARGET_GROUP_ID; }
    catch (_) { return TARGET_GROUP_ID; }
  }

  function writeStored(id){
    try { localStorage.setItem(storageKey, id); } catch (_) {}
  }

  function setHeader(name){
    const label = document.querySelector(".group");
    const button = get("groupPickerButton");
    const changes = get("scheduleChangesButton");
    const value = name || TARGET_GROUP_NAME;
    if(label) label.textContent = value + " · РУЗ";
    if(button){
      const span = button.querySelector("span:first-child");
      if(span) span.textContent = value;
    }
    if(changes) changes.style.display = String(selectedId) === TARGET_GROUP_ID ? "" : "none";
  }

  function openPicker(){
    const backdrop = get("groupPickerBackdrop");
    if(!backdrop) return;
    backdrop.classList.add("open");
    backdrop.setAttribute("aria-hidden", "false");
    backdrop.style.display = "flex";
    document.body.style.overflow = "hidden";
    renderList();
    const search = get("groupPickerSearch");
    if(search) setTimeout(() => search.focus(), 0);
  }

  function closePicker(){
    const backdrop = get("groupPickerBackdrop");
    if(!backdrop) return;
    backdrop.classList.remove("open");
    backdrop.setAttribute("aria-hidden", "true");
    backdrop.style.display = "none";
    document.body.style.overflow = "";
  }

  // Capture-phase delegation makes the control independent of script order and
  // survives any later DOM replacement by the schedule renderer.
  document.addEventListener("click", event => {
    const target = event.target && event.target.closest ? event.target.closest("#groupPickerButton") : null;
    if(target){
      event.preventDefault();
      event.stopPropagation();
      openPicker();
      return;
    }

    const close = event.target && event.target.closest ? event.target.closest("#groupPickerClose") : null;
    if(close){
      event.preventDefault();
      closePicker();
      return;
    }

    const item = event.target && event.target.closest ? event.target.closest("[data-group-id]") : null;
    if(item){
      event.preventDefault();
      selectGroup(item.getAttribute("data-group-id"));
      return;
    }

    if(event.target === get("groupPickerBackdrop")) closePicker();
  }, true);

  document.addEventListener("keydown", event => {
    if(event.key === "Escape") closePicker();
  });

  document.addEventListener("input", event => {
    if(event.target && event.target.id === "groupPickerSearch") renderList();
  });

  function renderList(){
    const list = get("groupPickerList");
    const status = get("groupPickerStatus");
    const search = get("groupPickerSearch");
    if(!list || !status) return;

    const query = search ? search.value.trim().toLowerCase() : "";
    const items = catalog.filter(group => !query || String(group.name || "").toLowerCase().includes(query));
    status.textContent = catalog.length ? `${items.length} из ${catalog.length} групп` : "Загрузка групп…";
    list.innerHTML = items.slice(0,250).map(group =>
      `<button class="group-picker-item ${String(group.id) === String(selectedId) ? "active" : ""}" data-group-id="${esc(group.id)}" type="button">${esc(group.name)}<span class="group-picker-id">ID ${esc(group.id)}</span></button>`
    ).join("");
    if(items.length > 250) status.textContent += " · показаны первые 250";
  }

  async function loadData(){
    try{
      const [groupsResponse, schedulesResponse] = await Promise.all([
        fetch("./groups.json?t=" + Date.now(), {cache:"no-store"}),
        fetch("./group_schedules.json?t=" + Date.now(), {cache:"no-store"})
      ]);
      if(!groupsResponse.ok) throw new Error("Не удалось загрузить groups.json");
      if(!schedulesResponse.ok) throw new Error("Не удалось загрузить group_schedules.json");

      const groups = await groupsResponse.json();
      const payload = await schedulesResponse.json();
      catalog = Array.isArray(groups) ? groups : [];
      schedules = payload && payload.groups && typeof payload.groups === "object" ? payload.groups : {};

      if(!catalog.some(group => String(group.id) === String(selectedId))){
        selectedId = TARGET_GROUP_ID;
        writeStored(selectedId);
      }

      const selected = catalog.find(group => String(group.id) === String(selectedId));
      setHeader(selected ? selected.name : TARGET_GROUP_NAME);
      renderList();
      if(String(selectedId) !== TARGET_GROUP_ID) applySelectedSchedule(false);
      const status = get("groupPickerStatus");
      if(status) status.textContent = `${catalog.length} групп доступно`;
    }catch(error){
      const status = get("groupPickerStatus");
      const list = get("groupPickerList");
      if(status) status.textContent = error.message || "Ошибка загрузки групп";
      if(list) list.innerHTML = "";
    }
  }

  function applySelectedSchedule(hideAfter){
    const item = schedules[String(selectedId)];
    if(!item || !Array.isArray(item.lessons) || !item.lessons.length){
      const status = get("groupPickerStatus");
      if(status) status.textContent = "Для этой группы расписание пока не загружено";
      return;
    }

    if(typeof window.sort === "function") window.schedule = window.sort(item.lessons);
    else window.schedule = item.lessons;
    window.archive = [];
    if(typeof window.renderSchedule === "function") window.renderSchedule();
    if(hideAfter) closePicker();
  }

  function selectGroup(id){
    const group = catalog.find(item => String(item.id) === String(id));
    if(!group) return;
    selectedId = String(id);
    writeStored(selectedId);
    setHeader(group.name);
    renderList();
    applySelectedSchedule(true);
  }

  selectedId = readStored();
  if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", loadData, {once:true});
  else loadData();

  setInterval(() => {
    if(String(selectedId) !== TARGET_GROUP_ID) applySelectedSchedule(false);
  }, 5 * 60 * 1000 + 1000);
})();'''

text = INDEX.read_text(encoding="utf-8")

# Replace only the picker JS block: use the last picker marker, which is the JS marker.
marker = "/* GROUP_PICKER_VIEW */"
script_end = text.rfind("</script>")
start = text.rfind(marker, 0, script_end)
if start < 0:
    raise SystemExit("GROUP_PICKER_VIEW JS marker not found")

text = text[:start] + JS + "\n\n" + text[script_end:]

# Make the button unambiguously above decorative/header layers and touchable on iOS.
text = text.replace(
    ".group-picker{\n",
    ".group-picker{\n  position:relative;\n  z-index:130;\n  pointer-events:auto;\n  touch-action:manipulation;\n  -webkit-tap-highlight-color:transparent;\n",
    1
)
text = text.replace(
    ".group-picker-backdrop{\n",
    ".group-picker-backdrop{\n  z-index:1000;\n",
    1
)

INDEX.write_text(text, encoding="utf-8")
print("Group picker JS repaired")
