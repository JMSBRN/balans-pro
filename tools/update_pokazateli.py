"""Refreshes assets/data/pokazateli.json from the sources that publish the indicators.

Runs in the Pages workflow before build.py (daily and on every push):
    python3 tools/update_pokazateli.py          # update the file in place
    python3 tools/update_pokazateli.py --check  # fail if a hand-kept value is due for review

Base value, base rent value and the subsistence budget come from the reference
tables of bii.by, where the newest row is on top; the refinancing rate comes
from the National Bank API. A source that can't be reached or parsed leaves
the last known value in place. The minimum wage, the childcare allowance and
the tax rates are kept by hand: each has a review_by/until date, and --check
fails the workflow once that date has passed, so GitHub e-mails a reminder.
"""
import json
import re
import sys
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / 'assets' / 'data' / 'pokazateli.json'
UA = 'Mozilla/5.0 (compatible; BalansPro site updater)'
DATE = r'(\d{2})\.(\d{2})\.(\d{4})'


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'ru'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'replace')


class Rows(HTMLParser):
    """Collects table rows as lists of cell texts."""

    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = []
        elif tag == 'br' and self.cell is not None:
            self.cell.append(' ')

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data.replace('\xa0', ' '))


def rows(url):
    p = Rows()
    p.feed(fetch(url))
    return p.rows


def iso(m, offset=0):
    d, mth, y = m.group(1 + offset), m.group(2 + offset), m.group(3 + offset)
    return f'{y}-{mth}-{d}'


def number(text):
    """'45' -> 45, '535,70' -> 535.7, '20 руб. 3 коп.' -> 20.03"""
    m = re.fullmatch(r'(\d[\d ]*) руб\. (\d{1,2}) коп\.', text)
    if m:
        return int(m.group(1).replace(' ', '')) + int(m.group(2)) / 100
    m = re.fullmatch(r'\d[\d ]*(?:,\d+)?', text)
    if m:
        return float(text.replace(' ', '').replace(',', '.'))
    return None


def pick(candidates, today):
    """The value in force today: the latest one that has already started."""
    started = [c for c in candidates if c['since'] <= today]
    return max(started, key=lambda c: c['since']) if started else None


def from_since_table(url, today):
    # «С 01.01.2026 | 45 | Постановление …»
    found = []
    for r in rows(url):
        if len(r) >= 2:
            m = re.fullmatch('С ' + DATE, r[0])
            value = number(r[1])
            if m and value is not None:
                found.append({'since': iso(m), 'value': value})
    return pick(found, today)


def bpm(url, today):
    # «Июнь 2026 г. | С 01.08.2026 по 31.10.2026 | 530,37 | …»
    found = []
    for r in rows(url):
        if len(r) >= 3:
            m = re.fullmatch('С ' + DATE + ' по ' + DATE, r[1])
            value = number(r[2])
            if m and value is not None:
                found.append({'since': iso(m), 'until': iso(m, 3), 'value': value})
    return pick(found, today)


def refin(_url, today):
    data = json.loads(fetch('https://api.nbrb.by/refinancingrate'))
    found = [{'since': d['Date'][:10], 'value': float(d['Value'])} for d in data]
    return pick(found, today)


FETCHERS = {'bv': from_since_table, 'bav': from_since_table, 'bpm': bpm, 'refin': refin}
# A value that jumps by more than this share is more likely a parsing slip than news
MAX_CHANGE = 0.5


def update():
    data = json.loads(DATA.read_text(encoding='utf-8'))
    today = date.today().isoformat()
    ok = True
    for item in data['indicators']:
        fetcher = FETCHERS.get(item['id']) if item.get('auto') else None
        if not fetcher:
            continue
        try:
            got = fetcher(item['source'], today)
        except Exception as e:  # network errors, layout changes
            got, why = None, f'{type(e).__name__}: {e}'
        else:
            why = 'no current row found'
        if not got:
            ok = False
            print(f'::warning::{item["abbr"]}: kept {item["value"]} from {item["since"]} ({why})')
            continue
        if got['since'] < item['since']:
            print(f'{item["abbr"]}: source still shows {got["since"]}, kept {item["value"]} from {item["since"]}')
            continue
        if abs(got['value'] - item['value']) > MAX_CHANGE * item['value']:
            ok = False
            print(f'::warning::{item["abbr"]}: {got["value"]} looks wrong next to {item["value"]}, kept the old value')
            continue
        if (got['value'], got['since']) != (item['value'], item['since']):
            print(f'{item["abbr"]}: {item["value"]} from {item["since"]} -> {got["value"]} from {got["since"]}')
        else:
            print(f'{item["abbr"]}: {item["value"]} from {item["since"]} is current')
        value = round(got['value'], 2)
        got['value'] = int(value) if value == int(value) else value
        item.update(got)
        if 'until' not in got:
            item.pop('until', None)
    if ok:
        data['checked'] = today
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def check():
    data = json.loads(DATA.read_text(encoding='utf-8'))
    today = date.today().isoformat()
    due = [f'{i["title"]} (срок {i["review_by"]})' for i in data['indicators'] if i.get('review_by', '9999') <= today]
    due += [f'Ставки налогов (срок {data["taxes_review_by"]})'] if data['taxes_review_by'] <= today else []
    for d in due:
        print(f'::error::Пора обновить в assets/data/pokazateli.json: {d}')
    sys.exit(1 if due else 0)


if __name__ == '__main__':
    check() if '--check' in sys.argv else update()
