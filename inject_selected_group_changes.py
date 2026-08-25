from pathlib import Path

INDEX = Path("index.html")
MARKER = "/* SELECTED_GROUP_CHANGES */"

JS = r'''/* SELECTED_GROUP_CHANGES */
(function(){
  "use strict";
  const STORAGE_KEY="ruz.selectedGroupId";
  const DEFAULT_GROUP_ID="164606";
  if(window.__selectedGroupChangesFetch) return;
  window.__selectedGroupChangesFetch=true;

  const originalFetch=window.fetch.bind(window);
  window.fetch=function(input,init){
    try{
      const raw=typeof input === "string" ? input : (input && input.url) || "";
      if(raw.includes("./changes.json")){
        const saved=localStorage.getItem(STORAGE_KEY);
        const groupId=saved && /^[0-9]+$/.test(String(saved)) ? String(saved) : DEFAULT_GROUP_ID;
        const target="./changes_by_group/"+encodeURIComponent(groupId)+".json"+ (raw.includes("?") ? raw.slice(raw.indexOf("?")) : "");
        if(typeof input === "string") return originalFetch(target,init);
        return originalFetch(new Request(target,input),init);
      }
    }catch(_error){}
    return originalFetch(input,init);
  };
})();
/* END_SELECTED_GROUP_CHANGES */
'''

text=INDEX.read_text(encoding="utf-8")
if MARKER in text:
    print("Selected-group changes bridge already installed")
    raise SystemExit(0)

script_pos=text.rfind("</script>")
if script_pos<0:
    raise SystemExit("index.html script structure not recognized")

text=text[:script_pos]+"\n"+JS+text[script_pos:]
INDEX.write_text(text,encoding="utf-8")
print("Connected changes.json requests to changes_by_group/<selectedGroupId>.json")
