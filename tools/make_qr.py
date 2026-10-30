"""Draws the QR codes for the contacts block into assets/qr/.

Needs the qrcode package (pip install qrcode). Run after a contact changes:
    python3 tools/make_qr.py
"""
from pathlib import Path

import qrcode

OUT = Path(__file__).resolve().parent.parent / 'assets' / 'qr'
CODES = {
    'phone': 'tel:+375445565857',
    'telegram': 'https://t.me/tatsiana_yakubovskaya',
    'instagram': 'https://www.instagram.com/yakubovska_buh',
    'email': 'mailto:yakubovska16021983@gmail.com',
}
INK = '#2b2140'
QUIET = 2  # modules of white margin; the white tile around the code adds the rest


def svg(data):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=QUIET)
    qr.add_data(data)
    qr.make(fit=True)
    rows = qr.get_matrix()
    size = len(rows)
    # One path of 1×1 squares, merged along each row
    parts = []
    for y, row in enumerate(rows):
        x = 0
        while x < size:
            if row[x]:
                start = x
                while x < size and row[x]:
                    x += 1
                parts.append(f'M{start} {y}h{x - start}v1h{start - x}z')
            else:
                x += 1
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" shape-rendering="crispEdges">'
            f'<rect width="{size}" height="{size}" fill="#fff"/><path fill="{INK}" d="{"".join(parts)}"/></svg>\n')


OUT.mkdir(parents=True, exist_ok=True)
for name, data in CODES.items():
    (OUT / f'{name}.svg').write_text(svg(data), encoding='utf-8')
    print(f'assets/qr/{name}.svg  {data}')
