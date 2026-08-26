import html
import json
import re
from pathlib import Path

INDEX = Path("index.html")
GROUPS = Path("groups.json")
MARKER = "/* GROUP_PICKER_NATIVE */"
END = "/* END_GROUP_PICKER_NATIVE */"
TARGET = "164606"
SW_VERSION = "12"


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

# Collapse only the selector wrapper itself. Do NOT consume following structural
# </div> tags: those close the title/brand containers and keep .header-right as a
# sibling of .brand. The previous broad regex swallowed those tags and moved the
# refresh button inside the title block on iPad.
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
        text = text.replace(needle, needle + "\n\n" + new_select, 1)

style_pos = text.find("</style>")
if style_pos < 0:
    raise SystemExit("</style> not found")
text = text[:style_pos] + "\n" + css_block + "\n" + text[style_pos:]

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

# Structural guard: the refresh area must remain a direct child of .header,
# after .brand. This catches the exact regression before it reaches GitHub Pages.
header_match = re.search(r'<div class="header">(.*?)</div>\s*<div class="hero', text, flags=re.S)
if header_match:
    header_html = header_match.group(1)
    brand_pos = header_html.find('<div class="brand">')
    right_pos = header_html.find('<div class="header-right">')
    if brand_pos < 0 or right_pos < 0 or right_pos < brand_pos:
        raise SystemExit("header structure is invalid: .brand/.header-right order is broken")

INDEX.write_text(text, encoding="utf-8")
print(f"Normalized native group selector: {len(groups)} groups, one runtime block, SW v{SW_VERSION}")
