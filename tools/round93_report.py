#!/usr/bin/env python3
"""Assemble retained round-93 comparisons without rendering the game."""
import base64
import html
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/round93'
PAIRS = OUT / 'pairs'
PAIRS.mkdir(exist_ok=True)
VIEWS = [
    ('malice-day', 'Castle / day', 'title', 'final', 820, (135, 85, 365, 290),
     'Three overlapping turbulent banks replace the rising glyph.'),
    ('malice-night', 'Castle / night', 'swirl-night', 'accepted', 820, (135, 85, 365, 290),
     'The same spatial volume retains dim magenta energy at night.'),
    ('lightning', 'Lightning', 'forest-bolt', 'final', 300, (820, 0, 1570, 600),
     'A wider white core and a feathered halo. The dry forest strike still costs no health.'),
    ('dusk', 'Dusk lighting', 'dusk', 'final', 300, (510, 305, 815, 720),
     'Cloud-filtered light keeps golden hair and brown trousers; silhouette contrast is checked separately.'),
    ('wake', 'Wake anatomy', 'wake', 'final', 420, (510, 230, 815, 585),
     'Tapered forearms and curved wrist/hand loops preserve the existing rig and palm contacts.'),
]


def pair(before, after, target, crop=None, caption=''):
    a, b = Image.open(before).convert('RGB'), Image.open(after).convert('RGB')
    assert a.size == b.size
    if crop:
        a, b = a.crop(crop), b.crop(crop)
    w, h = a.size
    image = Image.new('RGB', (w * 2, h + 32), '#181b21')
    image.paste(a, (0, 32))
    image.paste(b, (w, 32))
    draw = ImageDraw.Draw(image)
    draw.text((8, 10), 'BEFORE  c612330', fill='white')
    draw.text((w + 8, 10), 'AFTER' + ('  ' + caption if caption else ''), fill='white')
    image.save(target)


for key, title, scene, label, frame, crop, caption in VIEWS:
    pair(OUT / scene / 'before' / f'frame-{frame}.png',
         OUT / scene / label / f'frame-{frame}.png', PAIRS / f'{key}.png', crop)

# Full-size, matching frames for every critic view; phase sweeps are separate.
for scene, label in [('title', 'final'), ('night', 'after'), ('rise', 'after'),
                     ('combat', 'after'), ('combat-castle', 'final'), ('combat-panorama', 'final'), ('bolt', 'final'), ('forest-bolt', 'final'),
                     ('dusk', 'final'), ('overcast', 'final'), ('dark', 'final'), ('wake', 'final')]:
    folder = PAIRS / scene
    folder.mkdir(exist_ok=True)
    for before in sorted((OUT / scene / 'before').glob('frame-*.png')):
        if not before.stem[6:].isdigit():
            continue
        after = OUT / scene / label / before.name
        assert after.exists(), after
        pair(before, after, folder / before.name)

# Thirty random elapsed times per lighting, holding the title camera fixed.
for lighting in ('day', 'night'):
    scene = OUT / f'swirl-{lighting}'
    samples = sorted((scene / 'before').glob('sample-*.png'), key=lambda p: int(p.stem[7:]))
    assert len(samples) == 30
    sheet = Image.new('RGB', (460 * 5, 242 * 6), '#181b21')
    for index, before in enumerate(samples):
        after = scene / 'accepted' / before.name
        tile = PAIRS / f'{lighting}-{before.name}'
        tick = int(before.stem[7:])
        pair(before, after, tile, (135, 85, 365, 290), f'{tick / 60:.1f}s')
        sheet.paste(Image.open(tile), ((index % 5) * 460, (index // 5) * 242))
    sheet.save(PAIRS / f'30-times-{lighting}.png')

style = '''
body{margin:0;color:var(--foreground,#ddd);font-family:var(--font-sans,system-ui)}
nav{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}button{font:inherit;padding:7px 12px;border:1px solid var(--border,#555);border-radius:7px;background:transparent;color:inherit;cursor:pointer}button[aria-selected=true]{background:var(--secondary,#343a43);border-color:var(--foreground,#ddd)}figure{margin:0}figure[hidden]{display:none}img{display:block;width:100%;height:380px;object-fit:contain}figcaption{font-size:14px;line-height:1.5;margin:10px 0;color:var(--muted-foreground,#aaa)}small{display:block;line-height:1.5;color:var(--muted-foreground,#aaa)}
'''
script = '''
const buttons=[...document.querySelectorAll('button')];
buttons.forEach(button=>button.onclick=()=>{buttons.forEach(b=>b.setAttribute('aria-selected',String(b===button)));document.querySelectorAll('figure').forEach(f=>f.hidden=f.id!==button.dataset.view)});
Promise.all([...document.images].map(i=>i.decode())).then(()=>console.log('PASS: five before/after comparisons loaded'));
'''


def page(embedded):
    buttons, figures = [], []
    for index, (key, title, _, _, _, _, caption) in enumerate(VIEWS):
        buttons.append(f'<button data-view="{key}" aria-selected="{str(index == 0).lower()}">{html.escape(title)}</button>')
        source = str(PAIRS / f'{key}.png')
        if embedded:
            source = 'data:image/png;base64,' + base64.b64encode(Path(source).read_bytes()).decode()
        figures.append(f'<figure id="{key}"' + (' hidden' if index else '') +
                       f'><img src="{source}" alt="Before and after: {html.escape(title)}"><figcaption>{html.escape(caption)}</figcaption></figure>')
    return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Round 93 comparisons</title><style>' + style + '</style></head><body><nav aria-label="Comparison scene">' + ''.join(buttons) + '</nav>' + ''.join(figures) + '<small>Matched camera and frame. Luminance limits compare equivalent material illumination; the separate silhouette checks measure body/background contrast.</small><script>' + script + '</script></body></html>'


(OUT / 'index.html').write_text(page(True))
(OUT / 'preview.html').write_text(page(False))
print(f'Wrote comparison pairs, two 30-time contact sheets, and {OUT / "index.html"}')
