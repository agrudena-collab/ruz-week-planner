import html
import json
import re
from pathlib import Path

INDEX = Path("index.html")
GROUPS = Path("groups.json")
MARKER = "/* GROUP_PICKER_NATIVE */"
END = "/* END_GROUP_PICKER_NATIVE */"
TARGET = "164606"
SW_VERSION = "16"


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


def remove_element(text, tag, class_name):
    """Remove and return one matching element, respecting nested same-tag elements."""
    start_re = re.compile(
        rf'<{tag}\b(?=[^>]*\bclass=["\'][^"\']*\b{re.escape(class_name)}\b[^"\']*["\'])[^>]*>',
        re.I,
    )
    start = start_re.search(text)
    if not start:
        return text, None

    token_re = re.compile(rf'<(/?){tag}\b[^>]*>', re.I)
    depth = 0
    end = None
    for token in token_re.finditer(text, start.start()):
        if token.group(1):
            depth -= 1
            if depth == 0:
                end = token.end()
                break
        else:
            depth += 1

    if end is None:
        raise SystemExit(f"Unclosed {tag}.{class_name} element")
    return text[:start.start()] + text[end:], text[start.start():end]


def div_depth(fragment):
    """Count div nesting in a small HTML fragment."""
    opens = len(re.findall(r'<div\b[^>]*>', fragment, re.I))
    closes = len(re.findall(r'</div\s*>', fragment, re.I))
    return opens - closes


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
    f'navigator.serviceWorker.register("./sw.js?v={SW_VERSION}", {{',
)

text = strip_blocks(text)

picker = (
    '<div class="group-picker-wrap">\n'
    '  <select class="group-picker" id="groupPickerButton" aria-label="Выбор учебной группы">\n'
    + options(groups) + '\n'
    '  </select>\n'
    '</div>'
)

# The old page had malformed nesting: title/group lived inside an inner div that
# was never closed before the picker/header-right. Rebuild the header DOM itself
# instead of trying to patch that malformed tree with regex insertion.
header = re.search(r'<header\s+class="header">(.*?)</header>', text, re.S | re.I)
if not header:
    raise SystemExit("header element not found")
header_html = header.group(1)

title_match = re.search(r'<div\b[^>]*\bclass=["\'][^"\']*\btitle\b[^"\']*["\'][^>]*>(.*?)</div>', header_html, re.S | re.I)
group_match = re.search(r'<div\b[^>]*\bclass=["\'][^"\']*\bgroup\b[^"\']*["\'][^>]*>(.*?)</div>', header_html, re.S | re.I)
if not title_match or not group_match:
    raise SystemExit("header title/group markup not found")

_, right_markup = remove_element(header_html, "div", "header-right")
if not right_markup:
    raise SystemExit("header-right markup not found")

# Keep the existing menu/label content while normalizing only the hierarchy.
brand_markup = (
    '  <div class="brand">\n'
    '    <button\n'
    '      class="menu-button"\n'
    '      id="menuOpen"\n'
    '      aria-label="Открыть меню"\n'
    '    >\n'
    '      ☰\n'
    '    </button>\n\n'
    '    <div>\n'
    f'      <div class="title">{title_match.group(1).strip()}</div>\n\n'
    f'      <div class="group">{group_match.group(1).strip()}</div>\n'
    '    </div>\n'
    '  </div>'
)

normalized_header = (
    '<header class="header">\n\n'
    + brand_markup + '\n\n'
    + '  ' + picker + '\n\n'
    + '  ' + right_markup.strip() + '\n\n'
    + '</header>'
)
text = text[:header.start()] + normalized_header + text[header.end():]

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
.header > .brand{grid-area:brand}
.header > .group-picker-wrap{grid-area:picker;position:relative;margin-top:0;width:min(360px,78vw)}
.header > .header-right{grid-area:actions;align-self:start}
.header > .group-picker-wrap .group-picker{width:100%;min-height:38px;appearance:auto;-webkit-appearance:auto;border:1px solid rgba(255,255,255,.10);border-radius:12px;padding:7px 34px 7px 10px;background:rgba(255,255,255,.045);color:#cbd1dd;font-size:13px;font-weight:750;cursor:pointer;touch-action:manipulation}
.header > .group-picker-wrap .group-picker:focus{outline:2px solid rgba(66,217,255,.35);outline-offset:2px}
.header > .group-picker-wrap::after{content:"⌄";position:absolute;right:11px;top:50%;transform:translateY(-52%);color:#8e96a8;pointer-events:none}
@media(max-width:640px){
  .header{grid-template-columns:1fr;grid-template-areas:"brand" "picker" "actions";row-gap:9px}
  .header > .header-right{justify-self:start;align-self:auto}
  .header > .group-picker-wrap{width:min(330px,82vw)}
  .header > .group-picker-wrap .group-picker{min-height:42px;font-size:14px}
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

# Structural validation: CSS Grid only works if these are real direct children.
header = re.search(r'<header\s+class="header">(.*?)</header>', text, re.S | re.I)
if not header:
    raise SystemExit("header block not found for structural validation")
h = header.group(1)
brand = re.search(r'<div\b[^>]*\bclass=["\'][^"\']*\bbrand\b[^"\']*["\'][^>]*>', h, re.I)
pick = re.search(r'<div\b[^>]*\bclass=["\'][^"\']*\bgroup-picker-wrap\b[^"\']*["\'][^>]*>', h, re.I)
right = re.search(r'<div\b[^>]*\bclass=["\'][^"\']*\bheader-right\b[^"\']*["\'][^>]*>', h, re.I)
if not brand or not pick or not right:
    raise SystemExit("header structure is invalid: required elements are missing")
if not (brand.start() < pick.start() < right.start()):
    raise SystemExit("header structure is invalid: expected brand -> picker -> header-right")
if div_depth(h[:pick.start()]) != 0:
    raise SystemExit("group picker is nested inside another div")
if div_depth(h[:right.start()]) != 0:
    raise SystemExit("header-right is nested inside another div")
if div_depth(h[pick.start():right.start()]) != 0:
    raise SystemExit("group picker does not close before header-right")
if text.count('id="groupPickerButton"') != 1:
    raise SystemExit("groupPickerButton must exist exactly once")
if text.count('navigator.serviceWorker.register') != 1:
    raise SystemExit("service worker registration must exist exactly once")
if len(blocks(text)) != 2:
    raise SystemExit("expected exactly one CSS and one runtime native block")

INDEX.write_text(text, encoding="utf-8")
print(f"Installed stable native group selector: {len(groups)} groups, SW v{SW_VERSION}")
