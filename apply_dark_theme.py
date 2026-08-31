from pathlib import Path

path = Path('index.html')
html = path.read_text(encoding='utf-8')
marker = '<link rel="stylesheet" href="dark-theme.css">'
if marker not in html:
    html = html.replace('</head>', f'  {marker}\n</head>', 1)
    path.write_text(html, encoding='utf-8')
    print('Dark theme link installed')
else:
    print('Dark theme link already installed')
