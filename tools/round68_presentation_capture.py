#!/usr/bin/env python3
"""Matched shrine/map/storm evidence. Owns one lock per suite, never nested."""
import os
from contextlib import redirect_stdout
from pathlib import Path
import subprocess
import sys
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if '--locked' not in sys.argv:
    os.execvp('flock', ['flock', '/tmp/botw-render.lock', sys.executable, __file__, *sys.argv[1:], '--locked'])
out = ROOT / 'build/round68/sol2' / sys.argv[1]
out.mkdir(parents=True, exist_ok=True)
clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
def capture(name, binary, frames, settings, size='1280x720'):
    env = clean | dict(BOTW_NOVSYNC='1', BOTW_SCALE='1', BOTW_HOUR='11',
        SLOPPY_PLATFORM='x11', SLOPPY_WINDOW=size, SLOPPY_FRAMES=str(frames),
        SLOPPY_SCREENSHOT=str(out / f'{name}.png')) | settings
    with (out / f'{name}.log').open('w') as log:
        command = ['timeout', '180', str(out / binary)]
        if binary != 'map': command = ['python3', 'tools/cliff_capture_window.py', size, *command]
        subprocess.run(command,
            env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    if binary == 'weather':
        # The fixture's final framebuffer is its debug mask pass. Presentation
        # evidence uses the normal visible pass saved at the same instant.
        shutil.copyfile(out / 'critic-storm-visible.png', out / f'{name}.png')
    assert Image.open(out / f'{name}.png').size == tuple(map(int, size.split('x')))
    print(name, flush=True)
if '--maps-only' in sys.argv:
    for size in ('960x540', '1280x720'):
        for pad in (False, True):
            capture(f'map-{size}-{"pad" if pad else "keys"}', 'map', 3,
                dict(MAP_VIEW_PAD='1' if pad else '0'), size)
    sys.exit(0)
for i in range(4):
    capture(f'shrine-{i}-settled', 'game', 200,
        dict(BOTW_SKIP='1', BOTW_TOWER='1', BOTW_ENTER=str(i + 1)))
for frame in (80, 120, 160):
    capture(f'oman-arrival-{frame}', 'game', frame,
        dict(BOTW_SKIP='1', BOTW_TOWER='1', BOTW_ENTER='1'))
capture('forest-storm', 'weather', 300,
    dict(BOTW_SKIP='1', BOTW_AT='-1000,1620,3.14', BOTW_WEATHER='storm',
         BOTW_SILHOUETTE_PREFIX=str(out / 'critic-storm')))
for size in ('960x540', '1280x720'):
    for pad in (False, True):
        # The fixture's update uses normal inventory actions; the final input
        # selector is held after setup rather than depending on a physical pad.
        capture(f'map-{size}-{"pad" if pad else "keys"}', 'map', 3,
            dict(MAP_VIEW_PAD='1' if pad else '0'), size)
if sys.argv[1] == 'after':
    # Inherit the suite's single lock. These helpers never acquire a lock;
    # grouping the twelve views avoids repeatedly entering the shared queue.
    from weather_silhouette_check import VIEWS, capture_view, verify
    weather_out = out / 'silhouettes'
    weather_out.mkdir(exist_ok=True)
    with (out / 'silhouettes.log').open('w') as log, redirect_stdout(log):
        for view in VIEWS: capture_view(out / 'weather', weather_out, view)
        verify(weather_out)
    print('weather silhouettes verified', flush=True)
