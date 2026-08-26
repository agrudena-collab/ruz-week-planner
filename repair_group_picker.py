import html
import json
import re
from pathlib import Path

INDEX = Path("index.html")
GROUPS = Path("groups.json")
MARKER = "/* GROUP_PICKER_NATIVE */"
END = "/* END_GROUP_PICKER_NATIVE */"
TARGET = "164606"
SW_VERSION = "14"


def blocks(text):
    return re.findall(re.escape(MARKER) + r".*?" + re.escape(END), text, flags=re.S)


def strip_blocks(text):
    return re.sub(re.escape(MARKER) + r".*?" + re.escape(END), "", text, flags=re.S)


def options(groups):
    out = []
    for group in groups:
        gid = str(group["id"])
        name = html.escape(str(group["name"]), quote=True)
        selected = " selected" if gid == TARGET else ""
        out.append(f'        <option value="{gid}"{selected}>{name}</option>')
    return "\n".join(out)

text = INDEX.read_text(encoding="utf-8")
groups = json.loads(GROUPS.read_text(encoding="utf-8"))
if not isinstance(groups, list) or not groups:
    raise SystemExit("groups.json must contain a non-empty array")

native = blocks(text)
if not native:
    raise SystemExit("No GROUP_PICKER_NATIVE blocks found")
css = next((b for b in native if ".group-picker-wrap" in b and "function()" not in b), None)
runtimes = [b for b in native if "function(){" in b]
runtime = runtimes[-1] if runtimes else None
if not css or not runtime:
    raise SystemExit("Could not identify native selector CSS/runtime blocks")
runtime = runtime.replace(
    'navigator.serviceWorker.register("./sw.js", {',
    f'navigator.serviceWorker.register("./sw.js?v={SW_VERSION}", {{'
)

# Remove old generated native-selector blocks first.
text = strip_blocks(text)

# Rebuild exactly one picker wrapper from the current groups catalog.
picker = (
    '<div class="group-picker-wrap">\n'
    '  <select class="group-picker" id="groupPickerButton" aria-label="Выбор учебной группы">\n'
    + options(groups) + '\n'
    '  </select>\n'
    '</div>'
)
text = re.sub(
    r'\s*<div class="group-picker-wrap">.*?</div>',
    "\n" + picker,
    text,
    count=1,
    flags=re.S,
)
if 'group-picker-wrap' not in text:
    needle = '      <div class="group">\n        МеждОт25-2 · РУЗ\n      </div>'
    if needle not in text:
        raise SystemExit("group header markup not found")
    text = text.replace(needle, needle + "\n" + picker, 1)

# Force the picker to be a direct child of <header class="header">.
# Remove it from wherever it currently lives, then insert it immediately
# before the direct header-right block.
picker_re = re.compile(r'\s*<div class="group-picker-wrap">.*?</div>', re.S)
m = picker_re.search(text)
if not m:
    raise SystemExit("group-picker-wrap not found")
picker_html = m.group(0).strip()
text = text[:m.start()] + text[m.end():]
header = re.search(r'<header class="header">(.*?)</header>', text, re.S)
if not header:
    raise SystemExit("header element not found")
header_html = header.group(1)
right = re.search(r'\n\s*<div class="header-right">', header_html)
if not right:
    raise SystemExit("header-right not found inside header")
insert_at = header.start(1) + right.start()
text = text[:insert_at] + "\n\n  " + picker_html + text[insert_at:]

header_css = '''.header{
  display:grid;
  grid-template-columns:minmax(0,1fr) auto;
  grid-template-areas:
    "brand actions"
    "picker actions";
  column-gap:20px;
  row-gap:7px;
  align-items:start;
  margin-bottom:20px
}
.brand{grid-area:brand}
.group-picker-wrap{grid-area:picker;position:relative;margin-top:0;width:min(360px,78vw)}
.header-right{grid-area:actions;align-self:start}
.group-picker{width:100%;min-height:38px;appearance:auto;-webkit-appearance:auto;border:1px solid rgba(255,255,255,.10);border-radius:12px;padding:7px 34px 7px 10px;background:rgba(255,255,255,.045);color:#cbd1dd;font-size:13px;font-weight:750;cursor:pointer;touch-action:manipulation}
.group-picker:focus{outline:2px solid rgba(66,217,255,.35);outline-offset:2px}
.group-picker-wrap::after{content:"⌄";position:absolute;right:11px;top:50%;transform:translateY(-52%);color:#8e96a8;pointer-events:none}
@media(max-width:640px){
  .header{grid-template-columns:1fr;grid-template-areas:"brand" "picker" "actions";row-gap:9px}
  .header-right{justify-self:start;align-self:auto}
  .group-picker-wrap{width:min(330px,82vw)}
  .group-picker{min-height:42px;font-size:14px}
}
'''
style = text.find("</style>")
if style < 0:
    raise SystemExit("</style> not found")
text = text[:style] + "\n" + css + "\n" + header_css + "\n" + text[style:]

boot = re.search(r'loadAll\(\)\.then\(\(\) => \{', text)
if not boot:
    raise SystemExit("loadAll boot call not found")
text = text[:boot.start()] + runtime + "\n\n" + text[boot.start():]

# Structural validation uses the actual semantic header element, not a div.
header = re.search(r'<header class="header">(.*?)</header>', text, re.S)
if not header:
    raise SystemExit("header block not found for structural validation")
h = header.group(1)
brand = h.find('<div class="brand">')
pick = h.find('<div class="group-picker-wrap">')
right = h.find('<div class="header-right">')
if min(brand, pick, right) < 0:
    raise SystemExit("header structure is invalid: required children are missing")
if not (brand < pick < right):
    raise SystemExit("header structure is invalid: expected brand -> picker -> header-right")
if 'group-picker-wrap' in h[brand:pick] or 'group-picker-wrap' in h[right:]:
    raise SystemExit("group picker remains nested in brand/header-right")
if text.count('id="groupPickerButton"') != 1:
    raise SystemExit("groupPickerButton must exist exactly once")
if text.count('navigator.serviceWorker.register') != 1:
    raise SystemExit("service worker registration must exist exactly once")
if len(blocks(text)) != 2:
    raise SystemExit("expected exactly one CSS and one runtime native block")

INDEX.write_text(text, encoding="utf-8")
print(f"Installed stable native group selector: {len(groups)} groups, SW v{SW_VERSION}")
