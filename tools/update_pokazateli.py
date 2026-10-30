"""Refreshes assets/data/pokazateli.json from the sources that publish the indicators.

Runs in the Pages workflow before build.py (daily and on every push):
    python3 tools/update_pokazateli.py                     # update the file in place
    python3 tools/update_pokazateli.py --report report.txt  # write a reminder e-mail if anything needs a person
    python3 tools/update_pokazateli.py --report report.txt --always  # ...or a test one regardless

Base value, base rent value and the subsistence budget come from the reference
tables of bii.by, where the newest row is on top; the refinancing rate comes
from the National Bank API. A source that can't be reached or parsed leaves
the last known value in place. The minimum wage, the childcare allowance and
the tax rates are kept by hand: each has a review_by date, and --report writes
a reminder e-mail two weeks before it (the workflow sends it on Mondays).
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


def update(write=True):
    """Pulls the automatic values; returns the problems met, in Russian, for the e-mail report."""
    data = json.loads(DATA.read_text(encoding='utf-8'))
    today = date.today().isoformat()
    problems = []
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
            problems.append(f'{item["title"]}: источник не ответил или изменил вид страницы ({why}). '
                            f'На сайте остаётся {item["value"]} с {item["since"]}. Источник: {item["source"]}')
            print(f'::warning::{item["abbr"]}: kept {item["value"]} from {item["since"]} ({why})')
            continue
        if got['since'] < item['since']:
            print(f'{item["abbr"]}: source still shows {got["since"]}, kept {item["value"]} from {item["since"]}')
            continue
        if abs(got['value'] - item['value']) > MAX_CHANGE * item['value']:
            problems.append(f'{item["title"]}: источник дал {got["value"]} вместо {item["value"]} — слишком большой скачок, '
                            f'значение не принято, проверьте вручную. Источник: {item["source"]}')
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
    if write:
        if not problems:
            data['checked'] = today
        DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return problems, data


# Reminders start this many days before a hand-kept value is due
NOTICE_DAYS = 14


def report(path, always=False):
    """Writes the reminder e-mail to `path` if anything needs a person; writes nothing otherwise."""
    problems, data = update(write=False)
    today = date.today()
    soon = date.fromordinal(today.toordinal() + NOTICE_DAYS).isoformat()
    due = []
    for i in data['indicators']:
        if i.get('review_by', '9999') <= soon:
            due.append(f'{i["title"]}: сейчас на сайте {i["value"]} {i["unit"]} с {i["since"]}, '
                       f'проверить до {i["review_by"]}. Источник: {i["source"]}')
        elif i.get('until', '9999') < today.isoformat():
            due.append(f'{i["title"]}: срок действия {i["value"]} {i["unit"]} закончился {i["until"]}, '
                       f'а новое значение так и не появилось в источнике. Источник: {i["source"]}')
    if data['taxes_review_by'] <= soon:
        due.append(f'Ставки налогов: проверить до {data["taxes_review_by"]} (обычно меняются с 1 января).')
    if not (due or problems or always):
        print('Nothing to report')
        return
    parts = ['Здравствуйте!', '', 'Еженедельная проверка страницы «Актуальная информация» на сайте БалансПро.']
    if due:
        parts += ['', 'Пора проверить и обновить:'] + [f'— {d}' for d in due]
    if problems:
        parts += ['', 'Автоматическое обновление не сработало:'] + [f'— {p}' for p in problems]
    if not (due or problems):
        parts += ['', 'Всё в порядке: автоматические источники ответили, ручные показатели обновлять пока не нужно. '
                  'Это пробное письмо — обычные приходят только когда что-то требует внимания.']
    parts += ['', 'Как обновить: поправьте значения и даты в файле assets/data/pokazateli.json '
              '(у пересмотренного показателя сдвиньте review_by на следующий срок) — или пришлите новые цифры Claude.',
              '', 'Страница: https://jmsbrn.github.io/balans-pro/pokazateli/',
              'Файл: https://github.com/JMSBRN/balans-pro/blob/main/assets/data/pokazateli.json']
    Path(path).write_text('\n'.join(parts) + '\n', encoding='utf-8')
    print('\n'.join(parts))


if __name__ == '__main__':
    if '--report' in sys.argv:
        report(sys.argv[sys.argv.index('--report') + 1], '--always' in sys.argv)
    else:
        update()
