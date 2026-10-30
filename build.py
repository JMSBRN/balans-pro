"""Builds the inner pages, 404.html, sitemap.xml and robots.txt.

Shared parts (head, icon sprite, header, contacts, footer, modal) are taken
from index.html; page-specific content lives in _src/ and, like index.html,
links relative to the site root. Run after changing
the main page or anything in _src/:
    python3 build.py

When the site moves to its own domain, change SITE_URL below and the same
address in the <head> of index.html, then rebuild.
"""
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

SITE_URL = 'https://jmsbrn.github.io/balans-pro/'
BASE_PATH = urlparse(SITE_URL).path  # '/balans-pro/' on GitHub Pages, '/' on a custom domain

root = Path(__file__).parent
page = (root / 'index.html').read_text(encoding='utf-8')

PAGES = [
    {
        'slug': 'findir',
        'title': 'Финансовый директор на аутсорсе в Минске | БалансПро',
        'description': 'Финансовый директор на аутсорсе в Минске: управленческая отчётность, финансовая модель, '
                       'контроль денежных потоков и расходов, защита от кассовых разрывов.',
        'local': {'#tasks', '#why'},
        'contacts': True,
        'priority': '0.8',
        'schema': {
            '@type': 'Service',
            'name': 'Финансовый директор на аутсорсе',
            'serviceType': 'Финансовый директор на аутсорсе',
            'description': 'Управленческая отчётность, финансовое моделирование, контроль денежных потоков '
                           'и поиск резервов для роста бизнеса.',
            'areaServed': {'@type': 'City', 'name': 'Минск'},
        },
    },
    {
        'slug': 'rekvizity',
        'title': 'Реквизиты для уплаты налогов в Минске и Минской области | БалансПро',
        'description': 'Реквизиты для уплаты налогов, ФСЗН и Белгосстраха по инспекциям Минска и Минской области: '
                       'счёт, БИК, УНП бенефициара, код платежа. Копирование в один клик.',
        'local': {'#spravochnik', '#vidy', '#faq', '#pribyl', '#nedvizhimost', '#transport', '#nds', '#nds-vvoz',
                  '#podohodny', '#podohodny-ip', '#dohody', '#usn', '#edinyj', '#reklama', '#fszn', '#fszn-ip',
                  '#belgosstrakh', '#vtorresursy', '#kody-zp'},
        'contacts': True,
        'priority': '0.9',
        'schema': {'@type': 'WebPage', 'name': 'Реквизиты для уплаты налогов в Минске и Минской области'},
    },
    {
        'slug': 'privacy',
        'title': 'Политика обработки персональных данных | БалансПро',
        'description': 'Как БалансПро собирает, использует и защищает персональные данные, которые вы оставляете на сайте.',
        'local': set(),
        'contacts': False,
        'priority': '0.2',
        'schema': {'@type': 'WebPage', 'name': 'Политика обработки персональных данных'},
    },
]


def cut(start, end):
    i = page.index(start)
    return page[i:page.index(end, i) + len(end)]


SKIP = ('http:', 'https:', 'mailto:', 'tel:', 'viber:', 'data:', '/', '#i-')


def relink(html, prefix, local=frozenset()):
    """Rewrites links written relative to the site root so they work from `prefix`."""
    def fix(m):
        attr, url = m.group(1), m.group(2)
        if url.startswith(SKIP) or url in local:
            return m.group(0)
        if url == '#top':
            url = ''
        return f'{attr}="{prefix}{url}"'
    return re.sub(r'(href|src)="([^"]*)"', fix, html)


def jsonld(graph):
    body = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False, indent=2)
    return '  <script type="application/ld+json">\n  ' + body.replace('\n', '\n  ') + '\n  </script>'


def set_meta(head, pattern, value):
    new, n = re.subn(pattern, lambda m: m.group(1) + value + m.group(2), head)
    assert n == 1, pattern
    return new


def make_head(title, description, url, schema, prefix, noindex=False):
    head = cut('<!doctype html>', '</head>')
    head = set_meta(head, r'(<title>).*?(</title>)', title)
    head = set_meta(head, r'(<meta name="description" content=").*?(">)', description)
    head = set_meta(head, r'(<meta property="og:title" content=").*?(">)', title)
    head = set_meta(head, r'(<meta property="og:description" content=").*?(">)', description)
    head = set_meta(head, r'(<meta property="og:url" content=").*?(">)', url)
    head = set_meta(head, r'(<link rel="canonical" href=").*?(">)', url)
    if noindex:
        head = re.sub(r'\n  <link rel="canonical" href=".*?">', '', head)
        head = set_meta(head, r'(<meta name="robots" content=").*?(">)', 'noindex, follow')
    head, n = re.subn(r'\n  <script type="application/ld\+json">.*?</script>',
                      lambda m: '\n' + schema if schema else '', head, flags=re.S)
    assert n == 1
    return relink(head, prefix)


def breadcrumbs(name, url):
    return {
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Главная', 'item': SITE_URL},
            {'@type': 'ListItem', 'position': 2, 'name': name, 'item': url},
        ],
    }


sprite = cut('<svg width="0" height="0"', '</svg>\n')
header_src = cut('<header class="site-header">', '</header>')
contacts_src = cut('  <section class="section" id="contacts">', '  </section>')
footer_src = cut('<footer class="site-footer">', '</footer>')
tail_src = cut('<!-- Плавающая кнопка связи -->', '</html>')


def assemble(head, prefix, content, local, contacts):
    header, footer, tail = (relink(part, prefix, local) for part in (header_src, footer_src, tail_src))
    body_contacts = relink(contacts_src, prefix, local) if contacts else ''
    return f'''{head}
<body>

{sprite}
{header}

<main id="top">

{content}{body_contacts}

</main>

{footer}

{tail}
'''


for cfg in PAGES:
    url = f'{SITE_URL}{cfg["slug"]}/'
    node = {**cfg['schema'], 'url': url}
    node['provider' if node['@type'] == 'Service' else 'publisher'] = {'@id': f'{SITE_URL}#company'}
    schema = jsonld([node, breadcrumbs(cfg['schema']['name'], url)])
    head = make_head(cfg['title'], cfg['description'], url, schema, '../')
    local = cfg['local'] | ({'#contacts'} if cfg['contacts'] else set())
    # _src pages are written with links relative to the site root, like index.html
    content = relink((root / '_src' / f'{cfg["slug"]}.html').read_text(encoding='utf-8'), '../', local)
    out = root / cfg['slug'] / 'index.html'
    out.parent.mkdir(exist_ok=True)
    out.write_text(assemble(head, '../', content, local, cfg['contacts']), encoding='utf-8')
    print(f'{cfg["slug"]}/index.html written')

# 404 is served from any depth, so every link is absolute from the site root
head = make_head('Страница не найдена | БалансПро', 'Такой страницы нет на сайте БалансПро.', SITE_URL, None,
                 BASE_PATH, noindex=True)
content = relink((root / '_src' / '404.html').read_text(encoding='utf-8'), BASE_PATH)
(root / '404.html').write_text(assemble(head, BASE_PATH, content, set(), False), encoding='utf-8')
print('404.html written')

today = date.today().isoformat()
urls = [(SITE_URL, '1.0')] + [(f'{SITE_URL}{p["slug"]}/', p['priority']) for p in PAGES]
lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for loc, priority in urls:
    lines.append(f'  <url>\n    <loc>{loc}</loc>\n    <lastmod>{today}</lastmod>\n    <priority>{priority}</priority>\n  </url>')
lines.append('</urlset>\n')
(root / 'sitemap.xml').write_text('\n'.join(lines), encoding='utf-8')
print('sitemap.xml written')

(root / 'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}sitemap.xml\n', encoding='utf-8')
print('robots.txt written')
