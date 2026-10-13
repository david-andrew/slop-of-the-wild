#!/usr/bin/env python3
"""Render every interior portal, annex mouth and stair refuge from its approach.

Usage: shrine_gap_visual_check.py [--batch] OUTPUT INSPECTOR [VIEW ...]
Build INSPECTOR with round87_shrine_inspector.py first. Each render is protected
by one flock; --batch shares it across up to eight short views. Never wrap this
self-locking script. Settings and binary hashes accompany every image.
Intended fractures, shutter, gate and climbing ledges are recorded separately
from open passages. The normal chase-camera blast/walk check is complementary.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ORIGINS = [(-681, -8, 1501), (-400, -1, 2002),
           (-925, 93, 2321), (-365, 260, 1720)]
# id, local eye x/y/z, yaw, puzzle stage. Eyes stay on the approach side.
VIEWS = {
    'oman-main': (1, 0, 1.65, -20, 0, 1),
    'oman-main-return': (1, 0, 1.65, -29, math.pi, 1),
    'oman-foundry': (1, -8, 1.65, -28, -math.pi/2, 1),
    'oman-foundry-return': (1, -17, 1.65, -28, math.pi/2, 1),
    'jaba-north-intact': (2, 0, 1.65, -16, 0, 0),
    'jaba-north-open': (2, 0, 1.65, -16, 0, 3),
    'jaba-north-return': (2, 0, 1.65, -25, math.pi, 3),
    'jaba-east-intact': (2, 6, 1.65, -10, math.pi/2, 0),
    'jaba-east-open': (2, 6, 1.65, -10, math.pi/2, 3),
    'jaba-east-return': (2, 14, 1.65, -10, -math.pi/2, 3),
    'jaba-gallery': (2, 12, 1.65, -10, math.pi/2, 3),
    'jaba-gallery-return': (2, 20, 1.65, -10, -math.pi/2, 3),
    'jaba-shutter': (2, 28, 1.65, -10, math.pi/2, 3),
    'jaba-far-fracture': (2, 57, 1.65, -10, math.pi/2, 3),
    'jaba-monk': (2, 0, 1.65, -40, 0, 3),
    'jaba-monk-return': (2, 0, 1.65, -49, math.pi, 3),
    'owa-stair': (3, 0, 1.65, -38, 0, 0),
    'owa-stair-return': (3, 0, 2.4, -47, math.pi, 0),
    'owa-clockwork': (3, 8, 1.65, -28.5, math.pi/2, 0),
    'owa-clockwork-return': (3, 17, 1.65, -28.5, -math.pi/2, 0),
    'owa-refuge-low': (3, 0, 4.15, -51, math.pi/2, 0),
    'owa-refuge-mid': (3, 0, 6.65, -61, math.pi/2, 0),
    'owa-refuge-high': (3, 0, 9.15, -71, math.pi/2, 0),
    'owa-monk': (3, -1, 10.65, -80, math.pi/2, 0),
    'owa-monk-return': (3, 7, 10.65, -80, -math.pi/2, 0),
    'keh-gate-closed': (4, 0, 1.65, -26, 0, 0),
    'keh-gate-open': (4, 0, 1.65, -26, 0, 3),
    'keh-gate-return': (4, 0, 1.65, -35, math.pi, 3),
    'keh-niche': (4, -8, 5.25, -14, -math.pi/2, 1),
    'keh-niche-return': (4, -15, 5.25, -14, math.pi/2, 1),
    'keh-cistern': (4, -13, 5.25, -14, -math.pi/2, 1),
    'keh-cistern-return': (4, -21, 5.25, -14, math.pi/2, 1),
}
EXTERIORS = {
    # Actual actor positions transformed by lp(shrine.pos, shrine.rot, 0,2.1,12).
    'oman-exterior': '-663.8501,174.19,1520.4694,-0.9,0',
    'jaba-exterior': '-458.7,181.12001,1990.18,1.5708,0',
    'owa-exterior': '-925.02997,275.27002,2309.23,3.1416,0',
    'keh-exterior': '-1424.848,338.68,1987.5688,-1.8599,0',
}


def capture(out, binary, name, locked=False):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('BOTW_', 'SLOPPY_'))}
    if name in EXTERIORS:
        env.update(BOTW_CAM=EXTERIORS[name], BOTW_SHRINE_ACTIVE='1', BOTW_TOWER='1')
    else:
        n, x, y, z, yaw, stage = VIEWS[name]
        origin = ORIGINS[n-1]
        eye = (origin[0]+x, origin[1]+y, origin[2]+z, yaw, 0)
        env.update(BOTW_SHRINE=str(n), BOTW_SHRINE_STAGE=str(stage),
                   BOTW_SHRINE_AT=f'{x},{max(0,y-1.65)},{z},{yaw}',
                   BOTW_CAM=','.join(map(str, eye)))
    env.update(BOTW_SKIP='1', BOTW_HOUR='11', BOTW_TIMESCALE='0',
               BOTW_WEATHER='clear', BOTW_SCALE='1', BOTW_NOVSYNC='1', BOTW_NO_PREPARED_ASSETS='1',
               SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='1280x720',
               SLOPPY_VSYNC='0',
               SLOPPY_FRAMES='120', SLOPPY_SCREENSHOT=str(out/f'{name}.png'))
    with (out/f'{name}.log').open('w') as log:
        command = ['python3', str(ROOT/'tools/performance_window.py'),
                   '1280x720', 'timeout', '240', str(binary)]
        if not locked:
            command = ['flock', '/tmp/botw-render.lock', *command]
        subprocess.run(command, cwd=ROOT, env=env,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    from PIL import Image
    assert Image.open(out/f'{name}.png').size == (1280, 720)
    (out/f'{name}.json').write_text(json.dumps({
        'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
        'settings': {k: v for k, v in env.items()
                     if k.startswith(('BOTW_', 'SLOPPY_'))}}, indent=2)+'\n')
    print(f'captured {name}', flush=True)


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    mode = args.pop(0) if args[0] in ('--batch', '_batch') else ''
    if len(args) < 2:
        raise SystemExit(__doc__)
    out, binary = (Path(p).resolve() for p in args[:2])
    out.mkdir(parents=True, exist_ok=True)
    names = args[2:] or [*VIEWS, *EXTERIORS]
    if mode == '--batch':
        for start in range(0, len(names), 8):
            subprocess.run(['flock', '/tmp/botw-render.lock', sys.executable,
                            __file__, '_batch', str(out), str(binary),
                            *names[start:start+8]], cwd=ROOT,
                           env={**os.environ, 'SHRINE_GAP_BATCH_LOCK': '1'}, check=True)
    else:
        if mode == '_batch':
            assert os.environ.get('SHRINE_GAP_BATCH_LOCK') == '1', 'private mode requires the parent flock'
        for name in names:
            capture(out, binary, name, locked=mode == '_batch')
