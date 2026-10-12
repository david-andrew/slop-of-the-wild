#!/usr/bin/env python3
"""Matched captures in one self-locking batch. Do not wrap in another flock."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('phase', choices=['before', 'after'])
p.add_argument('--binary', type=Path, required=True)
p.add_argument('--output', type=Path, default=Path('build/round66'))
p.add_argument('--shrine', type=int, choices=range(1, 5))
p.add_argument('--arrival-only', action='store_true')
p.add_argument('--field-only', action='store_true')
p.add_argument('--baseline', type=Path, help='Capture both real arrivals and the final field in one locked batch.')
p.add_argument('--resume', action='store_true')
p.add_argument('--locked', action='store_true', help=argparse.SUPPRESS)
a = p.parse_args()
if not a.locked:
    sys.exit(subprocess.call(['flock', '/tmp/botw-render.lock', sys.executable,
                             str(Path(__file__).resolve()), *sys.argv[1:], '--locked']))
if a.baseline is not None:
    for phase, binary in [('before', a.baseline), ('after', a.binary)]:
        subprocess.run([sys.executable, str(Path(__file__).resolve()), phase,
                        '--binary', str(binary), '--output', str(a.output),
                        '--arrival-only', '--locked'], check=True)
    subprocess.run([sys.executable, str(Path(__file__).resolve()), 'after',
                    '--binary', str(a.binary), '--output', str(a.output),
                    '--field-only', '--locked'], check=True)
    sys.exit(0)
out = (a.output / a.phase).resolve()
out.mkdir(parents=True, exist_ok=True)
options = Path.home() / '.botw-clone-options'
look = 'down' if options.exists() and any(s.startswith('invert_y=') and float(s.split('=')[1]) > .5 for s in options.read_text().splitlines()) else 'up'

def capture(name, frames, flags, window='1280x720'):
    target = out / (name + '.png')
    target.parent.mkdir(parents=True, exist_ok=True)
    if a.resume and target.is_file():
        print('retained ' + str(target), flush=True)
        return
    target.unlink(missing_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
    env.update(BOTW_NOVSYNC='1', BOTW_SCALE='1', BOTW_WEATHER='clear', BOTW_HOUR='11',
               SLOPPY_PLATFORM='x11', SLOPPY_WINDOW=window, SLOPPY_FRAMES=str(frames),
               SLOPPY_SCREENSHOT=str(target))
    env.update(flags)
    with target.with_suffix('.log').open('w') as log:
        subprocess.run(['timeout', '300', str(a.binary.resolve())], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    assert target.is_file(), target
    print(target, flush=True)

if a.shrine is None and not a.arrival_only and not a.field_only:
    capture('passage/frame-750', 750, {'BOTW_PASSAGE': '1', 'SLOPPY_INPUT': '20:w+'}, '960x540')
    capture('passage/frame-830', 830, {'BOTW_PASSAGE': '1', 'SLOPPY_INPUT': '20:w+'}, '960x540')
for n in [] if a.field_only else ([a.shrine] if a.shrine is not None else range(1, 5)):
    flags = {'BOTW_SKIP': '1', 'BOTW_TOWER': '1', 'BOTW_SHRINE': str(n)}
    if not a.arrival_only:
        capture(f'shrines/{n}-entry', 720, flags)
        capture(f'shrines/{n}-shaft', 120, {**flags, 'SLOPPY_INPUT': f'90:{look}+,106:{look}-'})
    capture(f'shrines/{n}-arrival', 120, {'BOTW_SKIP': '1', 'BOTW_TOWER': '1', 'BOTW_ENTER': str(n)})
if a.shrine is None and not a.arrival_only:
    capture('field/overlook', 300, {'BOTW_SKIP': '1', 'BOTW_AT': '-1030,1805,1.57'})
    capture('field/title', 850, {'BOTW_TITLE': '1', 'BOTW_HOUR': '7', 'SLOPPY_INPUT': '10:w+,300:w-'})
