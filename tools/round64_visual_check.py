#!/usr/bin/env python3
"""Capture final Round 64 evidence in one serialized batch. Owns its render lock."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
os.chdir(Path(__file__).resolve().parent.parent)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--locked', action='store_true', help=argparse.SUPPRESS)
parser.add_argument('--skip-after', action='store_true', help='Keep completed matched after images')
parser.add_argument('--talus-scenes', default='dormant reveal awake front climb ride weak defeat', help='Space separated documentary Talus scenes')
parser.add_argument('--skip-weather', action='store_true', help='Keep completed weather captures; still verify them')
args = parser.parse_args()
root = Path('build/round64')
talus = root/'talus-visual-final'
weather = root/'weather-silhouette-final'
if not args.locked:
    # These commands only compile snapshots; VISUAL_PREPARE exits before rendering.
    subprocess.run(['tools/talus_visual_check.sh', str(talus)],
        env=dict(os.environ, VISUAL_PREPARE='1'), check=True)
    weather.mkdir(parents=True, exist_ok=True)
    if not args.skip_weather:
        subprocess.run(['sloppy/bin/sloppy', 'build', 'tools/weather_silhouette_capture.jo',
            '-o', str(weather/'game')], check=True)
    captured = subprocess.run(['flock', '/tmp/botw-render.lock', sys.executable, __file__,
        '--locked', *sys.argv[1:]])
    # Image analysis runs after releasing the shared GPU lock.
    from weather_silhouette_check import verify
    verify(weather)
    assert captured.returncode == 0, 'Documentary Talus failure; see individual scene logs'
    print('PASS final Round 64 documentary Talus, weather and matched captures', flush=True)
    sys.exit(0)

from weather_silhouette_check import capture_view, VIEWS
clean = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'TALUS_', 'VISUAL_'))}
sources = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('game').glob('*.jo'))}
binary = (root/'after-final/game').resolve()
previous_manifest = json.loads((root/'visual-sources.json').read_text()) if (root/'visual-sources.json').exists() else {}
scene_executables = previous_manifest.get('talus_scene_executables', {})
# Older full batches recorded one fixture executable for every scene. Preserve
# that provenance when only attack input is changed for a focused rerun.
if not scene_executables and str(talus/'talus-visual') in previous_manifest.get('executables', {}):
    scene_executables = {name:previous_manifest['executables'][str(talus/'talus-visual')]
        for name in ['dormant', 'reveal', 'awake', 'front', 'climb', 'ride', 'weak', 'defeat']}
fixture_sha = hashlib.sha256((talus/'talus-visual').read_bytes()).hexdigest()
for name in args.talus_scenes.split(): scene_executables[name] = fixture_sha
manifest = dict(game_sources=sources, talus_scene_executables=scene_executables, executables={
    str(p):hashlib.sha256(p.read_bytes()).hexdigest()
    for p in [binary, talus/'talus-visual', weather/'game']})
(root/'visual-sources.json').write_text(json.dumps(manifest, indent=2)+'\n')

views = {
    'forest': (150, dict(BOTW_SKIP='1', BOTW_AT='-1000,1620,3.14')),
    'boars': (150, dict(BOTW_SKIP='1', BOTW_CAM='-946,188.0,1660,-0.75,-0.12')),
    'golden': (150, dict(BOTW_SKIP='1', BOTW_AT='-1030,1805,1.57', BOTW_HOUR='6.4')),
    'overview': (150, dict(BOTW_SKIP='1', BOTW_CAM='-700,330,2150,-0.8,-0.35')),
    'snow': (150, dict(BOTW_SKIP='1', BOTW_AT='-1060,2230,2.0')),
    'hylia-pass': (150, dict(BOTW_SKIP='1', BOTW_CAM='-1300,355,2100,3.7,-0.20')),
    'talus': (600, dict(BOTW_SKIP='1', BOTW_AT='-1087.75,1673.18,0',
        SLOPPY_INPUT='10:w+,150:w-', BOTW_CAPTURE_DIR=str((root/'after/talus').resolve()),
        BOTW_CAPTURE_EVERY='50')),
}
(root/'after/talus').mkdir(parents=True, exist_ok=True)
for name, (frames, flags) in ({} if args.skip_after else views).items():
    settings = dict(clean, **flags, BOTW_NOVSYNC='1', BOTW_GPU='1', BOTW_SCALE='1',
        SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='1280x720', SLOPPY_FRAMES=str(frames),
        SLOPPY_SCREENSHOT=str((root/'after'/f'{name}.png').resolve()))
    with (root/'after'/f'{name}.log').open('w') as log:
        subprocess.run(['timeout', '300', str(binary)], env=settings,
            stdout=log, stderr=subprocess.STDOUT, check=True)
    print(f'captured final after/{name}', flush=True)

failed = []
for scene in args.talus_scenes.split():
    assert scene in ['dormant', 'reveal', 'awake', 'front', 'climb', 'ride', 'weak', 'defeat'], scene
    frames = dict(climb=150, ride=700, weak=900, defeat=1800).get(scene, 85)
    settings = dict(clean, BOTW_SKIP='1', BOTW_AT='-1087.75,1673.18,0',
        BOTW_HOUR='10', BOTW_WEATHER='clear', TALUS_VISUAL=scene, BOTW_SCALE='1',
        BOTW_NOVSYNC='1', SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='1280x720',
        SLOPPY_SCREENSHOT=str((talus/f'{scene}.png').resolve()), SLOPPY_FRAMES=str(frames))
    if scene in ['climb', 'ride', 'weak', 'defeat']:
        settings['SLOPPY_INPUT'] = '10:w+'
    with (talus/f'{scene}.log').open('w') as log:
        result = subprocess.run(['timeout', '240', str((talus/'talus-visual').resolve())],
            env=settings, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode != 0: failed.append(scene)
    for line in (talus/f'{scene}.log').read_text().splitlines():
        if line.startswith('talus visual'): print(line, flush=True)

for view in ([] if args.skip_weather else VIEWS):
    capture_view(weather/'game', weather, view)
assert not failed, f'Documentary Talus failures: {failed}; see individual scene logs'
