#!/usr/bin/env python3
"""Matched canyon/shrine captures. Never wrap this self-locking tool in flock.

Usage: round84_visual_check.py before|after [view ...]; or pairs.
orb-pairs takes one non-nested lock for all eight ceremony captures.
Build build/round84/<label>-game from main.jo and <label>-inspect with
tools/round87_shrine_inspector.py first. The baseline is c612330.
ROUND84_BINARY_PREFIX selects an immutable binary revision for retakes.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/round84'
VIEWS = {
    'cliffs': {'BOTW_CAM': '-1600,235,1815,1.2,-0.15'},
    'pool': {'BOTW_CAM': '-1565,119,1858,1.22,0.22'},
    'top': {'BOTW_CAM': '-1380,288,1837,-1.78,-0.65'},
    'close': {'BOTW_CAM': '-1550.15,207,1777.21,1.57,0'},
    'jaba0_top': {'BOTW_SHRINE': '2', 'BOTW_CAM': '-402,0.2,2001,0,0.6'},
    'jaba0_up': {'BOTW_SHRINE': '2', 'BOTW_CAM': '-402,0.2,1989.5,0,1.5607963'},
    'jaba0_entry': {'BOTW_SHRINE': '2'},
}
for n, (x, y, z) in enumerate([(0, 3.4, -47), (0, 0, -51.5),
                               (10, 9, -80), (0, 4, -43.5)], 1):
    VIEWS[f'monk{n}'] = {'BOTW_SHRINE': str(n), 'BOTW_SHRINE_STAGE': '2',
                         'BOTW_SHRINE_AT': f'{x},{y},{z+2},0',
                         'SLOPPY_INPUT': '120:e+,121:e-', 'BOTW_SHRINE_LOG': '1'}

def capture(phase, names, locked=False):
    out = OUT / phase
    out.mkdir(parents=True, exist_ok=True)
    clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
    manifest = {}
    for name in names or VIEWS:
        flags = VIEWS[name]
        prefix = os.environ.get('ROUND84_BINARY_PREFIX', phase)
        binary = OUT / f'{prefix}-{"inspect" if "BOTW_SHRINE" in flags else "game"}'
        env = dict(clean, BOTW_SKIP='1', BOTW_TOWER='1', BOTW_HOUR='11', BOTW_TIMESCALE='0',
                   BOTW_WEATHER='clear', BOTW_NO_PREPARED_ASSETS='1', BOTW_NOVSYNC='1', BOTW_SCALE='1',
                   SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='1280x720', SLOPPY_FRAMES='300',
                   SLOPPY_SCREENSHOT=str(out / f'{name}.png'))
        env.update(flags)
        with (out / f'{name}.log').open('w') as log:
            command = ['python3', 'tools/performance_window.py', '1280x720', 'timeout', '240', str(binary)]
            if not locked:
                command = ['flock', '/tmp/botw-render.lock'] + command
            subprocess.run(command, cwd=ROOT, env=env,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        assert Image.open(out / f'{name}.png').size == (1280, 720)
        if name.startswith('monk'):
            assert f'monk {int(name[-1])-1} talks' in (out / f'{name}.log').read_text(), 'capture must start the real orb ceremony'
        manifest[name] = {'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                          'env': {k: v for k, v in env.items() if k.startswith(('BOTW_', 'SLOPPY_'))}}
        print(f'PASS {phase} {name}', flush=True)
    path = out / 'capture.json'
    old = json.loads(path.read_text()) if path.exists() else {}
    path.write_text(json.dumps(old | manifest, indent=2) + '\n')

def pairs():
    for name in VIEWS:
        im = Image.new('RGB', (1280, 1488), '#18212b')
        draw = ImageDraw.Draw(im)
        for row, phase in enumerate(['before', 'after']):
            im.paste(Image.open(OUT / phase / f'{name}.png'), (0, row * 744 + 24))
            draw.text((10, row * 744 + 6), f'{phase.upper()} / {name} / baseline c612330', fill='white')
        im.save(OUT / f'{name}-pair.png')

if __name__ == '__main__':
    if sys.argv[1] == 'orb-pairs':
        subprocess.run(['flock', '/tmp/botw-render.lock', sys.executable, str(Path(__file__).resolve()),
                        '--locked-orb-pairs'], cwd=ROOT, check=True)
    elif sys.argv[1] == '--locked-orb-pairs':
        after_prefix = os.environ.get('ROUND84_BINARY_PREFIX', 'after')
        os.environ['ROUND84_BINARY_PREFIX'] = 'before'
        capture('before', [f'monk{n}' for n in range(1, 5)], locked=True)
        os.environ['ROUND84_BINARY_PREFIX'] = after_prefix
        capture('after', [f'monk{n}' for n in range(1, 5)], locked=True)
    elif sys.argv[1] == 'pairs':
        pairs()
    else:
        assert sys.argv[1].isidentifier(), 'use a simple capture label'
        capture(sys.argv[1], sys.argv[2:])
