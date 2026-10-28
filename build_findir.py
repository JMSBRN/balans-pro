"""Builds findir/index.html from the shared parts of index.html and findir/content.html.

Run after changing the header, footer or contacts on the main page:
    python3 build_findir.py
"""
import re
from pathlib import Path

root = Path(__file__).parent
page = (root / 'index.html').read_text(encoding='utf-8')
content = (root / 'findir' / 'content.html').read_text(encoding='utf-8')


def cut(start, end):
    i = page.index(start)
    return page[i:page.index(end, i) + len(end)]


# Anchors that live on this page stay local, the rest point back to the main page
LOCAL = {'#contacts', '#top'}


def relink(html):
    html = re.sub(r'href="#(?!i-)([\w-]+)"',
                  lambda m: m.group(0) if '#' + m.group(1) in LOCAL else f'href="../#{m.group(1)}"', html)
    return html.replace('href="findir/"', 'href="./"')


head = cut('<!doctype html>', '</head>')
head = head.replace('href="styles.css"', 'href="../styles.css"')
head = re.sub(r'<title>.*?</title>', '<title>Финансовый директор на аутсорсе в Минске | БалансПро</title>', head)
head = re.sub(r'<meta name="description" content=".*?">',
              '<meta name="description" content="Финансовый директор на аутсорсе: управленческий учёт, '
              'финансовое планирование, контроль денежных потоков и расходов. БалансПро, Минск.">', head)

sprite = cut('<svg width="0" height="0"', '</svg>\n')
header = relink(cut('<header class="site-header">', '</header>'))
header = header.replace('<a class="logo" href="#top"', '<a class="logo" href="../"')
contacts = cut('  <section class="section" id="contacts">', '  </section>')
footer = relink(cut('<footer class="site-footer">', '</footer>'))
tail = cut('<!-- Плавающая кнопка связи -->', '</html>').replace('src="script.js"', 'src="../script.js"')

out = f'''{head}
<body>

{sprite}
{header}

<main id="top">

{content}{contacts}

</main>

{footer}

{tail}
'''
(root / 'findir' / 'index.html').write_text(out, encoding='utf-8')
print('findir/index.html written')
