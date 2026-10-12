#!/usr/bin/env python3
"""Capture production weather at exact rendered frames; owns the shared render lock."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tarfile
import io
import sys
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    'pondbolt': dict(BOTW_AT='-1190,1665,-0.9', BOTW_WEATHER='storm', BOTW_BOLT='300', BOTW_BOLT_AT='-1201.7,1655.7'),
    'forest-storm': dict(BOTW_AT='-1000,1620,3.14', BOTW_WEATHER='storm', BOTW_BOLT='300'),
    'pondrain': dict(BOTW_AT='-1190,1665,-0.9', BOTW_WEATHER='rain'),
    'nightcamp': dict(BOTW_AT='-1440,1600,0', BOTW_WEATHER='clear', BOTW_HOUR='23'),
}
a = argparse.ArgumentParser(description=__doc__)
a.add_argument('phase', choices=['before', 'after'])
a.add_argument('--case', choices=CASES)
a.add_argument('--output', type=Path)
a.add_argument('--locked', action='store_true', help=argparse.SUPPRESS)
a.add_argument('--resume', action='store_true', help='skip complete views from the same capture revision')
a.add_argument('--source-revision', help='capture an isolated git revision under the output directory')
args = a.parse_args()
os.chdir(ROOT)
if not args.locked:
    sys.exit(subprocess.run(['flock', '/tmp/botw-render.lock', sys.executable, __file__, *sys.argv[1:], '--locked']).returncode)
out = (args.output or ROOT / 'build' / 'round63' / args.phase).resolve()
out.mkdir(parents=True, exist_ok=True)
game = ROOT / 'game'
if args.source_revision:
    snapshot = out / 'source'
    snapshot.mkdir(exist_ok=True)
    archive = subprocess.check_output(['git', 'archive', args.source_revision, 'game'])
    with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
        contents.extractall(snapshot, filter='data')
    game = snapshot / 'game'
manifest = dict(revision=args.source_revision or subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(game.glob('*.jo'))},
                frames=[299, 300, 302, 305], simulation_hz=60, game_seed=63, weather_seed=2, capture='draw end before presentation')
manifest_path = out / 'capture_manifest.json'
if args.resume and manifest_path.exists() and json.loads(manifest_path.read_text()) != manifest:
    raise SystemExit('Cannot resume captures from a different source revision; choose a new output directory.')
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
source = (game / 'main.jo').read_text()
source = re.sub(r"(?m)^(use|from) '([^']+)'", lambda m: f"{m[1]} '{(game / m[2]).resolve()}'", source)
# The window back buffer at update start can contain an older frame. Read at
# draw end after the current world and HUD, before presentation, for exact timing.
source = re.sub(r'    if __capture_dir != none and __capture_every > 0 and frame_number\(\) > 0 and frame_number\(\) % __capture_every == 0:\n        save_png\(screenshot\(\), __capture_dir! \+ "/frame-\{frame_number\(\)\}.png"\)\n', '', source)
checkpoint = '''
    if __capture_dir != none and (frame_number() == 299 or frame_number() == 300 or frame_number() == 302 or frame_number() == 305):
        save_png(screenshot(), __capture_dir! + "/frame-{frame_number()}.png")
        eprint("checkpoint frame={frame_number()} hp={pl.hp} state={pl.state} lightning={env.lightning:.4}")
'''
source = source.replace('\n\n# Submit representative shader/target/material paths', checkpoint + '\n\n# Submit representative shader/target/material paths')
source += '\nseed_random(63)\nweather_rng_restore(rng(2))\n'
fixture = out / 'capture.jo'
fixture.write_text(source)
binary = out / 'capture'
subprocess.run(['sloppy/bin/sloppy', 'build', str(fixture), '-o', str(binary)], check=True)
clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
for case in ([args.case] if args.case else CASES):
    dest = out / case
    dest.mkdir(exist_ok=True)
    if args.resume and all((dest / f'frame-{f}.png').is_file() for f in [299, 300, 302, 305]):
        print(f'{args.phase}/{case}: retained complete view', flush=True)
        continue
    settings = dict(clean, BOTW_SKIP='1', BOTW_HOUR='7', BOTW_NOVSYNC='1', BOTW_SCALE='0.8',
                    BOTW_CAPTURE_DIR=str(dest), BOTW_CAPTURE_EVERY='1', SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='1280x720',
                    SLOPPY_INPUT='0:w-', SLOPPY_FRAMES='306', SLOPPY_SCREENSHOT=str(dest / 'final.png'), **{})
    settings.update(CASES[case])
    with (dest / 'run.log').open('w') as log:
        subprocess.run(['timeout', '300', str(binary)], env=settings, stdout=log, stderr=subprocess.STDOUT, check=True)
    print(f'{args.phase}/{case}: rendered 299, 300, 302, 305', flush=True)
