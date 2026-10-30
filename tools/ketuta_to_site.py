"""Turns the JSON from parse_ketuta.py into assets/data/rekvizity.json for the requisites page.

Refreshing the data:
    1. Save https://ketuta.by/rekvizity-uplaty-nalogov/ as HTML (e.g. ketuta.html)
    2. python3 tools/parse_ketuta.py ketuta.html ketuta.json
    3. python3 tools/ketuta_to_site.py ketuta.json YYYY-MM-DD
"""
import json
import re
import sys
from pathlib import Path

src, checked = sys.argv[1], sys.argv[2]
tabs = json.load(open(src, encoding='utf-8'))

# Source tab name -> slug used in links and a clearer title for the page
TAXES = {
    'Налог на прибыль': ('pribyl', 'Налог на прибыль'),
    'Налог на недвижимость юр лиц': ('nedvizhimost', 'Налог на недвижимость организаций'),
    'Транспортный налог юр лиц': ('transport', 'Транспортный налог организаций'),
    'НДС': ('nds', 'НДС'),
    'НДС ввозной': ('nds-vvoz', 'НДС при ввозе товаров'),
    'Подоходный налог за наемных рабочих': ('podohodny', 'Подоходный налог за работников'),
    'Подоходный налог (ИП за себя)': ('podohodny-ip', 'Подоходный налог ИП за себя'),
    'Налог на доходы': ('dohody', 'Налог на доходы'),
    'Налог при УСН': ('usn', 'Налог при УСН'),
    'Единый налог с ИП и иных физ. лиц': ('edinyj', 'Единый налог с ИП и физлиц'),
    'Сбор за распространение рекламы': ('reklama', 'Сбор за распространение рекламы'),
    'ФСЗН (за наемных рабочих)': ('fszn', 'ФСЗН за работников'),
    'ФСЗН (ИП за себя)': ('fszn-ip', 'ФСЗН ИП за себя'),
    'Белгосстрах': ('belgosstrakh', 'Белгосстрах'),
    'Вторресурсы': ('vtorresursy', 'Оператор вторичных ресурсов'),
    'Коды для ЗП без налогов': ('kody-zp', 'Коды для выплат без налогов'),
}
FIELDS = ['budget', 'name', 'unp', 'actualName', 'actualUnp', 'account', 'bank', 'bic',
          'payCode', 'purposeCode', 'category', 'priority', 'currency', 'note']


def region(title):
    if not title:
        return None
    return 'Минск' if re.search(r'г\. ?Минск(а|у)?\b', title) else 'Минская область'


def record(r):
    out = {'title': r.get('title'), 'region': region(r.get('title'))}
    for k in FIELDS:
        if r.get(k):
            out[k] = r[k].strip()
    return out


taxes = []
for tab in tabs:
    slug, title = TAXES[tab['name']]
    entry = {'slug': slug, 'title': title}
    items = tab['items']
    if any('items' in x for x in items):
        entry['groups'] = [{'title': g['title'], 'records': [record(r) for r in g['items']]} for g in items]
    elif items and items[0].get('text'):
        entry['text'] = items[0]['text']
    else:
        entry['records'] = [record(r) for r in items]
    taxes.append(entry)

order = [v[0] for v in TAXES.values()]
taxes.sort(key=lambda t: order.index(t['slug']))
data = {'checked': checked, 'source': 'https://ketuta.by/rekvizity-uplaty-nalogov/', 'taxes': taxes}
out = Path(__file__).resolve().parent.parent / 'assets' / 'data' / 'rekvizity.json'
out.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print(out, out.stat().st_size, 'bytes')
