"""Parses the saved ketuta.by requisites page into structured JSON."""
import json, re, sys
from bs4 import BeautifulSoup, NavigableString

src, out = sys.argv[1], sys.argv[2]
soup = BeautifulSoup(open(src, encoding='utf-8').read(), 'lxml')

tab_names = {}
for a in soup.select('a.ui-tabs-anchor'):
    tab_names[a['href'].split('#')[-1]] = a.get_text(strip=True)

def clean(s):
    return re.sub(r'\s+', ' ', s.replace('\xa0', ' ')).strip()

KEYMAP = [
    ('УНП фактического бенефициара', 'actualUnp'),
    ('Наименование фактического бенефициара', 'actualName'),
    ('УНП бенефициара', 'unp'),
    ('Наименование бенефициара', 'name'),
    ('Номер счета', 'account'),
    ('р/с', 'account'),
    ('Наименование банка', 'bank'),
    ('БИК банка', 'bic'),
    ('БИК', 'bic'),
    ('УНП', 'unp'),
    ('Код платежа', 'payCode'),
    ('Код назначения платежа', 'purposeCode'),
    ('Категория перевода', 'category'),
    ('Очередность', 'priority'),
    ('Примечание', 'note'),
]

def parse_lines(node):
    """Text lines of a content node split on <br> and block elements."""
    parts, cur = [], []
    for el in node.descendants:
        if isinstance(el, NavigableString):
            cur.append(str(el))
        elif el.name in ('br', 'p', 'li', 'div'):
            parts.append(''.join(cur)); cur = []
    parts.append(''.join(cur))
    return [clean(p) for p in parts if clean(p)]

def parse_record(lines):
    rec, extra = {}, []
    for line in lines:
        if line in ('Местный бюджет', 'Республиканский бюджет'):
            rec['budget'] = line; continue
        if line.startswith('Код валюты'):
            rec['currency'] = '933 — белорусский рубль'; continue
        for label, key in KEYMAP:
            m = re.match(re.escape(label) + r'\s*[:\-–]\s*(.*)$', line)
            if m:
                val = m.group(1).strip()
                if key == 'account':
                    val = re.sub(r'\s+', '', val).replace('ВАРВ', 'BAPB')  # some accounts use Cyrillic letters
                rec[key] = val
                break
        else:
            extra.append(line)
    if extra:
        rec['text'] = extra
    return rec

def content_after(header):
    sib = header.find_next_sibling('div')
    return sib if sib is not None and 'list-content' in sib.get('class', []) else None

def parse_panel(panel):
    """Walks every header/content of a tab in document order.

    The source HTML has unbalanced tags, so the parsed tree does not keep all
    cards inside one list; nesting is read from each card's own content instead.
    """
    items, groups = [], {}
    for header in panel.select('div.list-header'):
        content = content_after(header)
        title = clean(header.get_text(' '))
        if content is not None and content.find('div', class_='list-group') is not None:
            group = {'title': title, 'items': []}
            groups[id(content)] = group
            items.append(group)
            continue
        record = {'title': title, **parse_record(parse_lines(content) if content is not None else [])}
        parent = None
        for anc in header.parents:
            if id(anc) in groups:
                parent = groups[id(anc)]; break
        (parent['items'] if parent else items).append(record)
    for c in panel.select('div.list-content'):
        prev = c.find_previous_sibling('div')
        if (prev is None or 'list-header' not in prev.get('class', [])) and c.find('div', class_='list-group') is None:
            items.append({'title': None, **parse_record(parse_lines(c))})
    return items

tabs = []
for panel in soup.select('div.ui-tabs-panel'):
    tabs.append({'id': panel['id'], 'name': tab_names.get(panel['id']), 'items': parse_panel(panel)})

json.dump(tabs, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def count(items):
    return sum(count(x['items']) if 'items' in x else 1 for x in items)
for t in tabs:
    print(f"{t['name']:<40} {count(t['items']):>4}")
print('total', sum(count(t['items']) for t in tabs))
