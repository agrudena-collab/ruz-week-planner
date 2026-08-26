import html
import json
import re
from pathlib import Path

INDEX = Path("index.html")
GROUPS = Path("groups.json")
MARKER = "/* GROUP_PICKER_NATIVE */"
END = "/* END_GROUP_PICKER_NATIVE */"
TARGET = "164606"
SW_VERSION = "15"


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
    """Remove one matching element while respecting nested same-tag elements."""
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
        if token.start() < start.start():
            continue
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


def direct_child_divs(header_html):
    """Return direct-child div classes from a header fragment."""
    token_re = re.compile(r'<(/?)div\b([^>]*)>', re.I)
    depth = 0
    result = []
    for token in token_re.finditer(header_html):
        if token.group(1):
            depth -= 1
            if depth < 0:
                raise SystemExit("Invalid header markup: negative div depth")
            continue

        attrs = token.group(2)
        if depth == 0:
            match = re.search(r'\bclass=["\']([^"\']*)["\']', attrs, re.I)
            classes = match.group(1).split() if match else []
            result.append((classes, token.start()))
        depth += 1

    if depth != 0:
        raise SystemExit("Invalid header markup: unbalanced div nesting")
    return result


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

# Remove every previous generated block before rebuilding one deterministic version.
text = strip_blocks(text)

picker = (
    '<div class="group-picker-wrap">\n'
    '  <select class="group-picker" id="groupPickerButton" aria-label="Выбор учебной группы">\n'
    + options(groups) + '\n'
    '  </select>\n'
    '</div>'
)

# Remove any stale picker from the header (including a nested copy), then insert
# exactly one picker as a direct child of the semantic header element.
text, _ = remove_element(text, "div", "group-picker-wrap")
header = re.search(r'<header\s+class="header">(.*?)</header>', text, re.S | re.I)
if not header:
    raise SystemExit("header element not found")
header_html = header.group(1)
right = re.search(r'<div\b[^>]*\bclass=["\'][^"\']*\bheader-right\b[^"\']*["\'][^>]*>', header_html, re.I)
if not right:
    raise SystemExit("header-right not found inside header")
insert_at = header.start(1) + right.start()
text = text[:insert_at] + "  " + picker + "\n\n  " + text[insert_at:]

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

# Structural validation must prove direct-child placement, not just string order.
header = re.search(r'<header\s+class="header">(.*?)</header>', text, re.S | re.I)
if not header:
    raise SystemExit("header block not found for structural validation")
children = direct_child_divs(header.group(1))
classes = [set(item[0]) for item in children]
expected = [{"brand"}, {"group-picker-wrap"}, {"header-right"}]
if classes[:3] != expected or len(classes) != 3:
    raise SystemExit(f"header direct children invalid: {children}")

if text.count('id="groupPickerButton"') != 1:
    raise SystemExit("groupPickerButton must exist exactly once")
if text.count('navigator.serviceWorker.register') != 1:
    raise SystemExit("service worker registration must exist exactly once")
if len(blocks(text)) != 2:
    raise SystemExit("expected exactly one CSS and one runtime native block")

INDEX.write_text(text, encoding="utf-8")
print(f"Installed stable native group selector: {len(groups)} groups, SW v{SW_VERSION}")
