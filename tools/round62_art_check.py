#!/usr/bin/env python3
"""Matched round62 art captures/GPU pairs. Self-locks the batch; call directly.

Capture: tools/round62_art_check.py capture master|after [scene ...]
GPU: tools/round62_art_check.py gpu [scene ...]
Prepare: tools/round62_art_check.py prepare
Builds pinned da7002f master and working-tree after executables and manifests.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys

from PIL import Image

SCRIPT = Path(__file__).resolve()
os.chdir(SCRIPT.parent.parent)
ROOT = Path('build/round62')
BASELINE = 'da7002f03cb270eacf9ca970c0827fbe371b5ea3'
if sys.argv[1:] == ['prepare']:
    # Compilation does not render and needs no render lock. Freeze all imported
    # game modules, rather than measuring today's moving master branch.
    archive = ROOT / 'master-source' / 'game'
    archive.mkdir(parents=True, exist_ok=True)
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASELINE, 'game'], text=True)
    for name in names.splitlines():
        if name.endswith('.jo'):
            (archive / Path(name).name).write_bytes(subprocess.check_output(['git', 'show', f'{BASELINE}:{name}']))
    climb = Path('tools/cliff_climb_capture.jo').read_text()
    game = "build:\n    opt = release\nuse '../game/main.jo'\nuse 'performance_output.jo'\nmain = (): performance_output_run(update, draw)\n"
    for phase in ('master', 'after'):
        for kind, source in (('game', game), ('climb', climb)):
            source = source.replace("'../game/", "'master-source/game/" if phase == 'master' else "'../../game/")
            source = source.replace("'performance_output.jo'", "'../../tools/performance_output.jo'")
            fixture = ROOT / f'{phase}-{kind}.jo'
            fixture.write_text(source)
            subprocess.run(['sloppy/bin/sloppy', 'build', str(fixture), '-o', str(ROOT / f'{phase}-{kind}')], check=True)
    (ROOT / 'baseline.json').write_text(json.dumps({'revision': BASELINE}, indent=2) + '\n')
    manifests = {phase: {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob('*.jo'))}
                 for phase, folder in (('master', archive), ('after', Path('game')))}
    (ROOT / 'source-manifests.json').write_text(json.dumps(manifests, indent=2) + '\n')
    binaries = {f'{phase}-{kind}': hashlib.sha256((ROOT / f'{phase}-{kind}').read_bytes()).hexdigest()
                for phase in ('master', 'after') for kind in ('game', 'climb')}
    (ROOT / 'binaries.json').write_text(json.dumps(binaries, indent=2) + '\n')
    print('Prepared pinned master and working-tree after; no render lock needed.')
    sys.exit(0)
if '--locked' not in sys.argv:
    os.execvp('flock', ['flock', '/tmp/botw-render.lock', sys.executable,
                        str(SCRIPT), '--locked', *sys.argv[1:]])
sys.argv.remove('--locked')
VIEWS = {
    'waterfall': ('-1585,160,1823,1.5708,0.0', '11'),
    'cliffs': ('-1600,235,1815,1.2,-0.15', '6.6'),
    'climb': ('-1568,213,1758,1.10,-0.08', '11'),
    'waterfall-mid': ('-1710,183,1823,1.5708,0.04', '11'),
    'overview': ('-700,330,2150,-0.8,-0.35', '6.6'),
}
mode = sys.argv[1]
label = sys.argv[2] if mode == 'capture' else None
scenes = sys.argv[3 if label else 2:] or list(VIEWS)
clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
report = {}
for scene in scenes:
    camera, hour = VIEWS[scene]
    runs = {'master': [], 'after': []}
    hashes = {'master': [], 'after': []}
    for repeat in range(3 if mode == 'gpu' else 1):
        phases = (('master', 'after') if repeat % 2 == 0 else ('after', 'master')) if mode == 'gpu' else (label,)
        for phase in phases:
            target = ROOT / ('gpu' if mode == 'gpu' else phase) / (f'{scene}-{phase}-{repeat}' if mode == 'gpu' else scene)
            target.parent.mkdir(parents=True, exist_ok=True)
            settings = {**clean, 'BOTW_SKIP': '1', 'BOTW_CAM': camera, 'BOTW_HOUR': hour,
                        'BOTW_WEATHER': 'clear', 'BOTW_NO_PREPARED_ASSETS': '1',
                        'BOTW_SCALE': '1', 'BOTW_NOVSYNC': '1', 'SLOPPY_PLATFORM': 'x11',
                        'SLOPPY_WINDOW': '1280x720', 'SLOPPY_INPUT': '1:w-',
                        'SLOPPY_FRAMES': '720' if mode == 'gpu' else '180',
                        'SLOPPY_SCREENSHOT': str(target) + '.png'}
            if mode == 'gpu': settings['BOTW_GPU'] = '1'
            binary = ROOT / (phase + ('-climb' if scene == 'climb' else '-game'))
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            hashes[phase].append(digest)
            assert len(set(hashes[phase])) == 1, 'binary changed within measurement round'
            cmd = ['python3', 'tools/cliff_capture_window.py',
                   '1280x720', 'timeout', '300', str(binary)]
            with target.with_suffix('.log').open('w') as log:
                subprocess.run(cmd, env=settings, stdout=log, stderr=subprocess.STDOUT, check=True)
            assert hashlib.sha256(binary.read_bytes()).hexdigest() == digest, 'binary changed during render'
            assert Image.open(target.with_suffix('.png')).size == (1280, 720)
            if mode == 'gpu':
                samples = [float(re.search(r'= ([\d.]+)$', row)[1])
                           for row in target.with_suffix('.log').read_text().splitlines() if row.startswith('gpu ms:')]
                assert len(samples) >= 4, (scene, phase, samples)
                runs[phase].append(statistics.median(samples[2:]))
                print(scene, phase, repeat, runs[phase][-1], flush=True)
            else: print(phase, scene, flush=True)
    if mode == 'gpu':
        master, after = [statistics.median(runs[k]) for k in ('master', 'after')]
        report[scene] = dict(master_ms=master, after_ms=after, delta_ms=after-master,
                             delta_percent=(after/master-1)*100, runs=runs, binary_sha256=hashes,
                             limit_ms=master*1.03+0.1, passed=after <= master*1.03+0.1,
                             resolution=[1280, 720], camera=camera, hour=hour)
        (ROOT / 'gpu' / f'{scene}.json').write_text(json.dumps(report[scene], indent=2) + '\n')
        print(scene, 'PASS' if report[scene]['passed'] else 'FAIL', report[scene], flush=True)
if mode == 'capture':
    (ROOT / label / 'views.json').write_text(json.dumps(VIEWS, indent=2) + '\n')
if mode == 'gpu': sys.exit(any(not row['passed'] for row in report.values()))
