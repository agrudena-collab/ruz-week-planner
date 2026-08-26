import html
import json
import re
from pathlib import Path

INDEX = Path("index.html")
GROUPS = Path("groups.json")
MARKER = "/* GROUP_PICKER_NATIVE */"
END = "/* END_GROUP_PICKER_NATIVE */"
TARGET = "164606"
SW_VERSION = "13"


def marker_blocks(text):
    return re.findall(re.escape(MARKER) + r".*?" + re.escape(END), text, flags=re.S)


def remove_marker_blocks(text):
    return re.sub(re.escape(MARKER) + r".*?" + re.escape(END), "", text, flags=re.S)


def build_options(groups):
    rows = []
    for group in groups:
        gid = str(group["id"])
        name = html.escape(str(group["name"]), quote=True)
        selected = " selected" if gid == TARGET else ""
        rows.append(f'        <option value="{gid}"{selected}>{name}</option>')
    return "\n".join(rows)


text = INDEX.read_text(encoding="utf-8")
groups = json.loads(GROUPS.read_text(encoding="utf-8"))
if not isinstance(groups, list) or not groups:
    raise SystemExit("groups.json must contain a non-empty array")

blocks = marker_blocks(text)
if not blocks:
    raise SystemExit("No GROUP_PICKER_NATIVE blocks found")

css_block = next((b for b in blocks if ".group-picker-wrap" in b and "<" not in b), None)
js_blocks = [b for b in blocks if "function(){" in b]
js_block = js_blocks[-1] if js_blocks else None
if not css_block or not js_block:
    raise SystemExit("Could not identify CSS and runtime group-picker blocks")

# Keep exactly one runtime block: the last one is the mature selector bridge
# already used by the app. Older duplicate runtimes are removed.
js_block = js_block.replace('navigator.serviceWorker.register("./sw.js", {', f'navigator.serviceWorker.register("./sw.js?v={SW_VERSION}", {{')

text = remove_marker_blocks(text)

options = build_options(groups)
new_select = (
    '<div class="group-picker-wrap">\n'
    '      <select class="group-picker" id="groupPickerButton" aria-label="Выбор учебной группы">\n'
    + options + '\n'
    '      </select>\n'
    '</div>'
)

# Normalize only the selector itself. Never consume surrounding structural
# closing tags: the picker must not become part of .brand or .header-right.
selector = re.compile(
    r'(?:\s*<div class="group-picker-wrap">\s*)+'
    r'<select class="group-picker" id="groupPickerButton"[^>]*>.*?</select>'
    r'\s*</div>',
    flags=re.S,
)
if selector.search(text):
    text = selector.sub("\n" + new_select, text, count=1)
else:
    old_select = re.compile(r'<select class="group-picker" id="groupPickerButton"[^>]*>.*?</select>', flags=re.S)
    if old_select.search(text):
        text = old_select.sub(new_select, text, count=1)
    else:
        needle = '      <div class="group">\n        МеждОт25-2 · РУЗ\n      </div>'
        if needle not in text:
            raise SystemExit("group header markup not found")
        text = text.replace(needle, needle + "\n" + new_select, 1)

# The selector is generated inside the title/brand block by the legacy
# template. Move the complete wrapper out of .brand so the header can place
# it in its own second row while keeping the refresh area at the top-right.
picker_match = re.search(r'\n<div class="group-picker-wrap">.*?</div>', text, flags=re.S)
header_right = '\n  <div class="header-right">'
if not picker_match:
    raise SystemExit("group-picker-wrap not found after normalization")
if header_right not in text:
    raise SystemExit("header-right not found")
picker_html = picker_match.group(0).strip()
text = text[:picker_match.start()] + text[picker_match.end():]
text = text.replace(header_right, "\n" + picker_html + header_right, 1)

# Header layout: title on row 1, selector on row 2, refresh area spanning both
# rows. This matches the original visual hierarchy and remains stable on iPad.
header_css = '''.header{
  display:grid;
  grid-template-columns:minmax(0,1fr) auto;
  grid-template-areas:
    "brand actions"
    "picker actions";
  column-gap:20px;
  row-gap:7px;
  align-items:center;
  margin-bottom:20px
}

.brand{grid-area:brand}
.header-right{grid-area:actions;align-self:start}

.group-picker-wrap{
  grid-area:picker;
  position:relative;
  margin-top:0;
  width:min(360px,78vw)
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
  touch-action:manipulation
}

.group-picker:focus{outline:2px solid rgba(66,217,255,.35);outline-offset:2px}
.group-picker-wrap::after{content:"⌄";position:absolute;right:11px;top:50%;transform:translateY(-52%);color:#8e96a8;pointer-events:none}

@media(max-width:640px){
  .header{
    grid-template-columns:1fr;
    grid-template-areas:
      "brand"
      "picker"
      "actions";
    row-gap:9px
  }
  .header-right{justify-self:start;align-self:auto}
  .group-picker-wrap{width:min(330px,82vw)}
  .group-picker{min-height:42px;font-size:14px}
}
'''

style_pos = text.find("</style>")
if style_pos < 0:
    raise SystemExit("</style> not found")
text = text[:style_pos] + "\n" + css_block + "\n" + header_css + "\n" + text[style_pos:]

boot = re.search(r'loadAll\(\)\.then\(\(\) => \{', text)
if not boot:
    raise SystemExit("loadAll boot call not found")
text = text[:boot.start()] + js_block + "\n\n" + text[boot.start():]

if len(marker_blocks(text)) != 2:
    raise SystemExit("expected exactly one CSS and one runtime group-picker block")
if text.count('id="groupPickerButton"') != 1:
    raise SystemExit("groupPickerButton must exist exactly once")
if text.count('navigator.serviceWorker.register') != 1:
    raise SystemExit("service worker registration must exist exactly once")
if len(re.findall(r'<div class="group-picker-wrap">', text)) != 1:
    raise SystemExit("group-picker-wrap must exist exactly once")

# Structural guard: .brand and .header-right must remain direct children of
# .header, and the picker must be a separate direct child between them.
header_match = re.search(r'<div class="header">(.*?)</div>\s*<div class="hero', text, flags=re.S)
if not header_match:
    raise SystemExit("header block not found for structural validation")
header_html = header_match.group(1)
brand_pos = header_html.find('<div class="brand">')
picker_pos = header_html.find('<div class="group-picker-wrap">')
right_pos = header_html.find('<div class="header-right">')
if brand_pos < 0 or picker_pos < 0 or right_pos < 0:
    raise SystemExit("header structure is invalid: required children are missing")
if not (brand_pos < picker_pos < right_pos):
    raise SystemExit("header structure is invalid: expected brand -> picker -> header-right")

# The picker must not be nested inside .brand or .header-right.
brand_chunk = header_html[brand_pos:picker_pos]
right_chunk = header_html[right_pos:]
if 'group-picker-wrap' in brand_chunk or 'group-picker-wrap' in right_chunk:
    raise SystemExit("group picker is still nested in a header child")

INDEX.write_text(text, encoding="utf-8")
print(f"Normalized native group selector: {len(groups)} groups, one runtime block, SW v{SW_VERSION}")
