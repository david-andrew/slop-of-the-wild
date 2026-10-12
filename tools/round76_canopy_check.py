#!/usr/bin/env python3
"""Round 76 vegetation captures at native 1280x720.

prepare before|after; capture before|after [views...]; pairs after.
Snapshots source before compilation. Each capture owns one flock; do not wrap.
"""
import hashlib, json, os, subprocess, sys
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/round76'
VIEWS = {'crow': ({'BOTW_SKIP': '1', 'BOTW_CAM': '-946,188.0,1660,-0.75,-0.12'}, 720),
 'pond': ({'BOTW_SKIP': '1', 'BOTW_AT': '-1190,1665,-0.9'}, 300),
 'forest': ({'BOTW_SKIP': '1', 'BOTW_AT': '-1000,1620,3.14'}, 300),
 'title600': ({'BOTW_TITLE': '1', 'SLOPPY_INPUT': '10:w+,300:w-'}, 600),
 'title720': ({'BOTW_TITLE': '1', 'SLOPPY_INPUT': '10:w+,300:w-'}, 720),
 'title900': ({'BOTW_TITLE': '1', 'SLOPPY_INPUT': '10:w+,300:w-'}, 900)}
VIEWS['crow150'] = ({'BOTW_CAM': '-946,188.0,1660,-0.75,-0.12'}, 150)
VIEWS['combat155'] = ({'BOTW_SKIP': '1', 'BOTW_AT': '-1439,1606,0', 'BOTW_GIVE': 'travelers_sword,travelers_shield', 'SLOPPY_INPUT': '5:w+,40:w-,45:k+,100:j+,106:j-,125:j+,131:j-,150:d+,152:space+,154:space-,170:d-,300:j+,306:j-,330:j+,336:j-'}, 155)

VIEWS.update({
    'camp': ({'BOTW_SKIP': '1', 'BOTW_CAM': '-947,243,1956,-0.85,-0.45'}, 120),
    'oldman': ({'BOTW_SKIP': '1', 'BOTW_AT': '-951,1876,2.5'}, 300),
    'cave-meadow': ({'BOTW_SKIP': '1', 'BOTW_AT': '-1054,1834,0.85'}, 300),
    'temple': ({'BOTW_SKIP': '1', 'BOTW_AT': '-818,1950,3.14'}, 300),
    'boars': ({'BOTW_SKIP': '1', 'BOTW_CAM': '-946,188.0,1660,-0.75,-0.12'}, 150),
    'boars10': ({'BOTW_CAM': '-946,188.0,1660,-0.75,-0.12', 'BOTW_HOUR': '10'}, 150),
    'temple10': ({'BOTW_SKIP': '1', 'BOTW_AT': '-818,1950,3.14', 'BOTW_HOUR': '10'}, 300),
})

def prepare(phase):
    out = OUT / phase
    game = out / 'game'
    game.mkdir(parents=True, exist_ok=True)
    for p in (ROOT / 'game').glob('*.jo'):
        data = subprocess.check_output(['git', 'show', f'159dda5:game/{p.name}'], cwd=ROOT) if phase == 'before' else p.read_bytes()
        (game / p.name).write_bytes(data)
    helper = (ROOT / 'tools/performance_output.jo').read_text()
    import re
    helper = re.sub("'../game/([^']+)'", lambda m: repr(str(game / m[1])), helper)
    (out / 'performance_output.jo').write_text(helper)
    (out / 'main.jo').write_text(f"build:\n    opt = release\nuse '{game / 'main.jo'}'\nuse 'performance_output.jo'\nmain = (): performance_output_run(update, draw)\n")
    with (out / 'build.log').open('w') as log:
        subprocess.run(['sloppy/bin/sloppy', 'build', str(out / 'main.jo'), '-o', str(out / 'game-bin')], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    (out / 'sources.json').write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in game.glob('*.jo')}, indent=2))

def capture(phase, names):
    out = OUT / phase
    for name in names or VIEWS:
        flags, frames = VIEWS[name]
        env = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
        env.update(BOTW_NOVSYNC='1', BOTW_SCALE='1', BOTW_HOUR='11', BOTW_WEATHER='clear', BOTW_BENCH_CLIENT_SIZE='1', SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='1280x720', SLOPPY_FRAMES=str(frames), SLOPPY_SCREENSHOT=str(out / f'{name}.png'))
        env.update(flags)
        (out / f'{name}.environment.json').write_text(json.dumps({k: v for k, v in env.items() if k.startswith(('BOTW_', 'SLOPPY_'))}, indent=2))
        with (out / f'{name}.log').open('w') as log:
            subprocess.run(['flock', '/tmp/botw-render.lock', 'python3', 'tools/performance_window.py', '1280x720', 'timeout', '300', str(out / 'game-bin')], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        assert Image.open(out / f'{name}.png').size == (1280, 720)
        print(phase, name, flush=True)

def pairs(phase):
    from PIL import ImageDraw
    out = OUT
    boxes = {'crow': (0, 0, 620, 310),
     'crow150': (300, 0, 920, 310),
     'pond': (320, 0, 940, 300),
     'forest': (200, 0, 820, 330),
     'title600': (500, 350, 1120, 650),
     'title720': (500, 350, 1120, 650),
     'title900': (500, 350, 1120, 650),
     'combat155': (620, 0, 1240, 235),
     'camp': (0, 350, 620, 680),
     'oldman': (500, 210, 1120, 540),
     'cave-meadow': (100, 380, 720, 690),
     'temple': (660, 350, 1280, 680),
     'boars': (0, 350, 620, 680),
     'boars10': (0, 350, 620, 680),
     'temple10': (660, 350, 1280, 680)}
    for name, box in boxes.items():
        paths = [out / p / f'{name}.png' for p in ('before', phase)]
        if not all((p.exists() for p in paths)):
            continue
        imgs = [Image.open(p).convert('RGB') for p in paths]
        w, h = (box[2] - box[0], box[3] - box[1])
        canvas = Image.new('RGB', (2 * w, h + 24), (25, 28, 29))
        d = ImageDraw.Draw(canvas)
        for j, im in enumerate(imgs):
            crop = im.crop(box)
            canvas.paste(crop, (j * w, 24))
            d.text((j * w + 8, 6), ('BEFORE 159dda5' if j == 0 else 'AFTER round 76') + ' - native pixels', fill='white')
            crop.save(out / phase / f"{name}-{['before', 'after'][j]}-crop.png")
        canvas.save(out / phase / f'{name}-detail-pair.png')
        full = Image.new('RGB', (1280, 1488), (25, 28, 29))
        d = ImageDraw.Draw(full)
        for j, im in enumerate(imgs):
            full.paste(im, (0, j * 744 + 24))
            d.text((8, j * 744 + 6), ['BEFORE 159dda5', 'AFTER round 76'][j], fill='white')
        full.save(out / phase / f'{name}-pair.png')
if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[2] not in ('before', 'after'):
        raise SystemExit(__doc__)
    if sys.argv[1] == 'prepare':
        prepare(sys.argv[2])
    elif sys.argv[1] == 'capture':
        capture(sys.argv[2], sys.argv[3:])
    elif sys.argv[1] == 'pairs':
        pairs(sys.argv[2])
    else:
        raise SystemExit(__doc__)
