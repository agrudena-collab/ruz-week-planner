from pathlib import Path

INDEX = Path("index.html")
MARKER = "<!-- SCHEDULE_CHANGES_VIEW -->"

CSS = r"""
/* SCHEDULE_CHANGES_VIEW */
.changes-fab{
  position:fixed;
  right:18px;
  bottom:18px;
  z-index:90;
  border:1px solid rgba(255,255,255,.12);
  border-radius:16px;
  padding:12px 15px;
  background:rgba(18,22,32,.94);
  color:#fff;
  box-shadow:0 14px 40px rgba(0,0,0,.35);
  backdrop-filter:blur(16px);
  font-weight:850;
  cursor:pointer;
}
.changes-fab strong{color:#42d9ff;margin-left:5px}
.changes-backdrop{
  position:fixed;
  inset:0;
  z-index:120;
  display:none;
  background:rgba(0,0,0,.62);
  backdrop-filter:blur(8px);
}
.changes-backdrop.open{display:block}
.changes-panel{
  position:absolute;
  right:14px;
  bottom:14px;
  width:min(720px,calc(100% - 28px));
  max-height:min(82vh,760px);
  overflow:auto;
  padding:20px;
  border:1px solid rgba(255,255,255,.10);
  border-radius:24px;
  background:linear-gradient(160deg,#111624,#090b12);
  box-shadow:0 30px 90px rgba(0,0,0,.55);
}
.changes-head{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:14px}
.changes-title{font-size:24px;font-weight:900}
.changes-close{border:1px solid rgba(255,255,255,.10);border-radius:12px;background:rgba(255,255,255,.06);color:#fff;padding:9px 12px;cursor:pointer}
.changes-muted{color:#8e96a8;font-size:13px}
.change-card{border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:15px;margin-top:10px;background:rgba(255,255,255,.035)}
.change-top{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
.change-date{font-weight:900;color:#fff}
.change-time{color:#42d9ff;font-weight:850}
.change-subject{font-size:17px;font-weight:850;margin:8px 0}
.change-field{display:flex;gap:8px;flex-wrap:wrap;color:#b9c0ce;font-size:12px;margin-top:6px}
.change-field b{color:#dce2ed}
.change-old{text-decoration:line-through;color:#777f90}
.change-new{color:#27df91;font-weight:800}
"""

HTML = r"""
<!-- SCHEDULE_CHANGES_VIEW -->
<button class="changes-fab" id="scheduleChangesButton" type="button">Изменения <strong id="scheduleChangesCount"></strong></button>
<div class="changes-backdrop" id="scheduleChangesBackdrop" aria-hidden="true">
  <section class="changes-panel" role="dialog" aria-modal="true" aria-labelledby="scheduleChangesTitle">
    <div class="changes-head">
      <div>
        <div class="changes-title" id="scheduleChangesTitle">Изменения расписания</div>
        <div class="changes-muted" id="scheduleChangesStatus">Загрузка…</div>
      </div>
      <button class="changes-close" id="scheduleChangesClose" type="button">Закрыть</button>
    </div>
    <div id="scheduleChangesList"></div>
  </section>
</div>
"""

JS = r"""
/* SCHEDULE_CHANGES_VIEW */
(function(){
  const button=document.getElementById("scheduleChangesButton");
  const backdrop=document.getElementById("scheduleChangesBackdrop");
  const close=document.getElementById("scheduleChangesClose");
  const list=document.getElementById("scheduleChangesList");
  const status=document.getElementById("scheduleChangesStatus");
  const count=document.getElementById("scheduleChangesCount");
  if(!button||!backdrop||!close||!list)return;

  const esc=value=>String(value??"").replace(/[&<>\"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[ch]));
  const open=()=>{backdrop.classList.add("open");backdrop.setAttribute("aria-hidden","false");loadChanges();};
  const hide=()=>{backdrop.classList.remove("open");backdrop.setAttribute("aria-hidden","true");};
  button.addEventListener("click",open);
  close.addEventListener("click",hide);
  backdrop.addEventListener("click",e=>{if(e.target===backdrop)hide();});
  document.addEventListener("keydown",e=>{if(e.key==="Escape")hide();});

  async function loadChanges(){
    status.textContent="Загрузка…";
    try{
      const response=await fetch("./changes.json?t="+Date.now(),{cache:"no-store"});
      if(!response.ok)throw new Error("HTTP "+response.status);
      const changes=await response.json();
      if(!Array.isArray(changes))throw new Error("Некорректный формат данных");
      count.textContent=changes.length?""+changes.length:"";
      status.textContent=changes.length?`${changes.length} изменений обнаружено`:"Изменений нет";
      if(!changes.length){list.innerHTML='<div class="changes-muted">Расписание пока не изменялось.</div>';return;}
      list.innerHTML=changes.map(change=>{
        const fields=Array.isArray(change.fields)?change.fields:[];
        return `<article class="change-card">
          <div class="change-top"><span class="change-date">${esc(change.date)}</span><span class="change-time">${esc(change.beginLesson)}–${esc(change.endLesson)}</span></div>
          <div class="change-subject">${esc(change.discipline||"Занятие")}</div>
          ${fields.map(field=>`<div class="change-field"><b>${esc(field.label)}:</b><span class="change-old">${esc(field.old)}</span><span>→</span><span class="change-new">${esc(field.new)}</span></div>`).join("")}
        </article>`;
      }).join("");
    }catch(error){
      count.textContent="";
      status.textContent="Не удалось загрузить изменения";
      list.innerHTML=`<div class="changes-muted">${esc(error.message||"Ошибка загрузки")}</div>`;
    }
  }

  fetch("./changes.json?t="+Date.now(),{cache:"no-store"})
    .then(r=>r.ok?r.json():[])
    .then(data=>{if(Array.isArray(data)&&data.length)count.textContent=data.length;})
    .catch(()=>{});
})();
"""

text = INDEX.read_text(encoding="utf-8")
if MARKER in text:
    print("Changes view already installed")
    raise SystemExit(0)

style_pos = text.rfind("</style>")
script_pos = text.rfind("</script>")
body_pos = text.rfind("</body>")
if min(style_pos, script_pos, body_pos) < 0:
    raise SystemExit("index.html structure not recognized")

text = text[:style_pos] + "\n" + CSS + "\n" + text[style_pos:]
body_pos = text.rfind("</body>")
text = text[:body_pos] + "\n" + HTML + "\n" + text[body_pos:]
script_pos = text.rfind("</script>")
text = text[:script_pos] + "\n" + JS + "\n" + text[script_pos:]

INDEX.write_text(text, encoding="utf-8")
print("Installed schedule changes view into index.html")
