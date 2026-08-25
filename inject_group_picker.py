from pathlib import Path

INDEX = Path("index.html")
MARKER = "<!-- GROUP_PICKER_VIEW -->"

CSS = r"""
/* GROUP_PICKER_VIEW */
.group-picker{
  margin-top:7px;
  display:inline-flex;
  align-items:center;
  gap:8px;
  max-width:min(360px,78vw);
  border:1px solid rgba(255,255,255,.10);
  border-radius:12px;
  padding:7px 10px;
  background:rgba(255,255,255,.045);
  color:#cbd1dd;
  font-size:13px;
  font-weight:750;
  cursor:pointer;
}
.group-picker:hover{background:rgba(255,255,255,.07);color:#fff}
.group-picker span:first-child{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.group-picker-arrow{color:#8e96a8}
.group-picker-backdrop{
  position:fixed;
  inset:0;
  z-index:125;
  display:none;
  align-items:flex-end;
  justify-content:center;
  padding:14px;
  background:rgba(0,0,0,.62);
  backdrop-filter:blur(9px);
}
.group-picker-backdrop.open{display:flex}
.group-picker-panel{
  width:min(620px,100%);
  max-height:min(82vh,720px);
  overflow:hidden;
  border:1px solid rgba(255,255,255,.10);
  border-radius:26px;
  background:linear-gradient(160deg,#111624,#090b12);
  box-shadow:0 30px 90px rgba(0,0,0,.55);
}
.group-picker-head{padding:18px 18px 12px;border-bottom:1px solid rgba(255,255,255,.07)}
.group-picker-head-row{display:flex;justify-content:space-between;align-items:center;gap:12px}
.group-picker-title{font-size:22px;font-weight:900}
.group-picker-close{border:1px solid rgba(255,255,255,.10);border-radius:12px;background:rgba(255,255,255,.06);color:#fff;padding:8px 11px;cursor:pointer}
.group-picker-search{width:100%;margin-top:12px;border:1px solid rgba(255,255,255,.09);border-radius:13px;background:rgba(255,255,255,.045);color:#fff;padding:11px 12px;outline:none}
.group-picker-search::placeholder{color:#697184}
.group-picker-status{padding:10px 18px;color:#8e96a8;font-size:12px}
.group-picker-list{max-height:calc(min(82vh,720px) - 145px);overflow:auto;padding:0 10px 12px}
.group-picker-item{width:100%;display:block;text-align:left;border:1px solid transparent;border-radius:13px;background:transparent;color:#cbd1dd;padding:11px 12px;margin:3px 0;cursor:pointer}
.group-picker-item:hover{background:rgba(255,255,255,.055);color:#fff}
.group-picker-item.active{background:rgba(79,140,255,.12);border-color:rgba(79,140,255,.22);color:#fff}
.group-picker-id{display:block;color:#697184;font-size:10px;margin-top:3px}
@media (max-width:640px){
  .group-picker-backdrop{padding:0}
  .group-picker-panel{border-radius:24px 24px 0 0;max-height:88vh}
  .group-picker-list{max-height:calc(88vh - 145px)}
}
"""

HTML = r"""
<!-- GROUP_PICKER_VIEW -->
<div class="group-picker-backdrop" id="groupPickerBackdrop" aria-hidden="true">
  <section class="group-picker-panel" role="dialog" aria-modal="true" aria-labelledby="groupPickerTitle">
    <div class="group-picker-head">
      <div class="group-picker-head-row">
        <div class="group-picker-title" id="groupPickerTitle">Выбор группы</div>
        <button class="group-picker-close" id="groupPickerClose" type="button">Закрыть</button>
      </div>
      <input class="group-picker-search" id="groupPickerSearch" type="search" placeholder="Найти группу…" autocomplete="off">
    </div>
    <div class="group-picker-status" id="groupPickerStatus">Загрузка групп…</div>
    <div class="group-picker-list" id="groupPickerList"></div>
  </section>
</div>
"""

JS = r"""
/* GROUP_PICKER_VIEW */
document.addEventListener("DOMContentLoaded", function(){
(function(){
  const TARGET_GROUP_ID="164606";
  const TARGET_GROUP_NAME="МеждОт25-2";
  const storageKey="ruz.selectedGroupId";
  const button=document.getElementById("groupPickerButton");
  const backdrop=document.getElementById("groupPickerBackdrop");
  const close=document.getElementById("groupPickerClose");
  const search=document.getElementById("groupPickerSearch");
  const list=document.getElementById("groupPickerList");
  const status=document.getElementById("groupPickerStatus");
  const groupLabel=document.querySelector(".group");
  const changesButton=document.getElementById("scheduleChangesButton");
  if(!button||!backdrop||!close||!search||!list||!status||!groupLabel)return;

  let catalog=[];
  let schedules={};
  let selectedId=localStorage.getItem(storageKey)||TARGET_GROUP_ID;
  let selectedName=TARGET_GROUP_NAME;

  const esc=value=>String(value??"").replace(/[&<>\"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[ch]));
  const open=()=>{backdrop.classList.add("open");backdrop.setAttribute("aria-hidden","false");search.focus();};
  const hide=()=>{backdrop.classList.remove("open");backdrop.setAttribute("aria-hidden","true");};
  button.addEventListener("click",open);
  close.addEventListener("click",hide);
  backdrop.addEventListener("click",e=>{if(e.target===backdrop)hide();});
  document.addEventListener("keydown",e=>{if(e.key==="Escape")hide();});
  search.addEventListener("input",renderList);

  function setHeader(name){
    selectedName=name||TARGET_GROUP_NAME;
    groupLabel.textContent=selectedName+" · РУЗ";
    button.querySelector("span:first-child").textContent=selectedName;
    if(changesButton){
      changesButton.style.display=selectedId===TARGET_GROUP_ID?"":"none";
    }
  }

  function renderList(){
    const query=search.value.trim().toLowerCase();
    const items=catalog.filter(group=>!query||group.name.toLowerCase().includes(query));
    status.textContent=`${items.length} из ${catalog.length} групп`;
    list.innerHTML=items.slice(0,250).map(group=>`
      <button class="group-picker-item ${String(group.id)===String(selectedId)?"active":""}" data-group-id="${esc(group.id)}" type="button">
        ${esc(group.name)}
        <span class="group-picker-id">ID ${esc(group.id)}</span>
      </button>
    `).join("");
    list.querySelectorAll("[data-group-id]").forEach(item=>item.addEventListener("click",()=>selectGroup(item.dataset.groupId)));
    if(items.length>250)status.textContent+=` · показаны первые 250`;
  }

  async function loadData(){
    try{
      const [groupsResponse,schedulesResponse]=await Promise.all([
        fetch("./groups.json?t="+Date.now(),{cache:"no-store"}),
        fetch("./group_schedules.json?t="+Date.now(),{cache:"no-store"})
      ]);
      if(!groupsResponse.ok)throw new Error("Не удалось загрузить groups.json");
      if(!schedulesResponse.ok)throw new Error("Не удалось загрузить group_schedules.json");
      const groups=await groupsResponse.json();
      const payload=await schedulesResponse.json();
      catalog=Array.isArray(groups)?groups:[];
      schedules=payload&&typeof payload.groups==="object"?payload.groups:{};
      const current=catalog.find(group=>String(group.id)===String(selectedId));
      if(!current){selectedId=TARGET_GROUP_ID;localStorage.setItem(storageKey,selectedId);}
      const selected=catalog.find(group=>String(group.id)===String(selectedId));
      setHeader(selected?.name||TARGET_GROUP_NAME);
      renderList();
      if(String(selectedId)!==String(TARGET_GROUP_ID))applySelectedSchedule(false);
      status.textContent=`${catalog.length} групп доступно`;
    }catch(error){
      status.textContent=error.message||"Ошибка загрузки групп";
      list.innerHTML="";
    }
  }

  function applySelectedSchedule(showLoading=true){
    const item=schedules[String(selectedId)];
    if(!item||!Array.isArray(item.lessons)||!item.lessons.length){
      status.textContent="Для этой группы расписание пока не загружено";
      return;
    }
    schedule=typeof sort==="function"?sort(item.lessons):item.lessons;
    archive=[];
    if(showLoading)hide();
    renderSchedule();
  }

  function selectGroup(id){
    const group=catalog.find(item=>String(item.id)===String(id));
    if(!group)return;
    selectedId=String(id);
    selectedName=group.name;
    localStorage.setItem(storageKey,selectedId);
    setHeader(group.name);
    renderList();
    applySelectedSchedule(true);
  }

  /* The original page loads the default schedule first. Re-apply a saved
     non-default group after that load, and after manual/periodic refreshes. */
  const restoreSelected=()=>{
    if(String(selectedId)!==String(TARGET_GROUP_ID))applySelectedSchedule(false);
  };
  $("refreshButton").addEventListener("click",()=>setTimeout(restoreSelected,250));
  setInterval(restoreSelected,5*60*1000+1000);

  loadData();
})();
});
"""

text = INDEX.read_text(encoding="utf-8")

# Repair an already-installed picker. The previous version injected the
# picker JS before the picker HTML, so its event handlers were never bound.
if MARKER in text:
    old_start = '/* GROUP_PICKER_VIEW */\n(function(){'
    new_start = '/* GROUP_PICKER_VIEW */\ndocument.addEventListener("DOMContentLoaded", function(){\n(function(){'
    old_end = '  loadData();\n})();\n\n</script>'
    new_end = '  loadData();\n})();\n});\n\n</script>'
    if old_start in text and old_end in text:
        text = text.replace(old_start, new_start, 1)
        text = text.replace(old_end, new_end, 1)
        INDEX.write_text(text, encoding="utf-8")
        print("Repaired existing group picker initialization")
    else:
        print("Group picker marker exists but no repairable old block was found")
    raise SystemExit(0)

style_pos = text.rfind("</style>")
script_pos = text.rfind("</script>")
body_pos = text.rfind("</body>")
if min(style_pos, script_pos, body_pos) < 0:
    raise SystemExit("index.html structure not recognized")

needle = '      <div class="group">\n        МеждОт25-2 · РУЗ\n      </div>'
replacement = needle + '\n\n      <button class="group-picker" id="groupPickerButton" type="button">\n        <span>МеждОт25-2</span>\n        <span class="group-picker-arrow">⌄</span>\n      </button>'
if needle not in text:
    raise SystemExit("group header markup not found")
text = text.replace(needle, replacement, 1)

style_pos = text.rfind("</style>")
text = text[:style_pos] + "\n" + CSS + "\n" + text[style_pos:]
body_pos = text.rfind("</body>")
text = text[:body_pos] + "\n" + HTML + "\n" + text[body_pos:]
script_pos = text.rfind("</script>")
text = text[:script_pos] + "\n" + JS + "\n" + text[script_pos:]

INDEX.write_text(text, encoding="utf-8")
print("Installed group picker into index.html")
