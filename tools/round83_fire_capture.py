#!/usr/bin/env python3
"""Matched fire evidence and AB/BA/AB CPU tails. Owns its flock; never wrap."""
import argparse
import hashlib
import json
import math
import os
import re
from pathlib import Path
import statistics
import subprocess

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/round83'
SCENES = {
    'fire': (720, {'BOTW_FIRE': '1'}, [150, 230, 260, 290, 320, 600]),
    'tentfire': (960, {'BOTW_TENTFIRE': '5', 'BOTW_AT': '-955,1964,0'}, [150, 230, 260, 320, 600, 900]),
}


def prepare(label, game=None):
    OUT.mkdir(parents=True, exist_ok=True)
    game = (game or ROOT / 'game').resolve()
    source = (game / 'main.jo').read_text()
    # Master declares an explicit entry point; replace it for the timed loop.
    source = source.replace('main = (): game_run(update, draw)', '')
    for file in game.glob('*.jo'):
        source = source.replace(f"'{file.name}'", repr(str(file)))
    source += f"\nuse '{ROOT}/tools/performance_output.jo'\nmain=():performance_output_run(update,draw)\n"
    path = OUT / f'{label}.jo'
    path.write_text(source)
    subprocess.run(['sloppy/bin/sloppy', 'build', str(path), '-o', str(OUT / f'{label}-game')], check=True)
    (OUT / f'{label}-source.json').write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in game.glob('*.jo')}, indent=2))


def run(label, scene, directory, capture=False, lock_wait=60, profile=False):
    frames, flags, _ = SCENES[scene]
    directory.mkdir(parents=True, exist_ok=True)
    binary = OUT / f'{label}-game'
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    settings = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
    settings.update(BOTW_SKIP='1', BOTW_WEATHER='clear', BOTW_HOUR='11',
                    BOTW_SCALE='1', BOTW_NO_PREPARED_ASSETS='1', BOTW_FRAME_LOG='1',
                    BOTW_NOVSYNC='1', SLOPPY_VSYNC='0', SLOPPY_PLATFORM='x11',
                    SLOPPY_WINDOW='1280x720', SLOPPY_FRAMES=str(frames),
                    SLOPPY_SCREENSHOT=str(directory / 'final.png'), **flags)
    if capture:
        settings.update(BOTW_CAPTURE_DIR=str(directory), BOTW_CAPTURE_EVERY='10')
    if profile:
        settings.update(BOTW_CPU='1', BOTW_CPU_TRACE_MS='0')
    with (directory / 'run.log').open('w') as log:
        command = ['python3', 'tools/performance_window.py', '1280x720', 'timeout', '240', str(binary)]
        command = ['flock', '-w', str(lock_wait), '-E', '75', '/tmp/botw-render.lock', *command]
        try:
            subprocess.run(command, env=settings,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        except subprocess.CalledProcessError as exc:
            if exc.returncode == 75:
                print(f'Render lock busy for {lock_wait}s; no render started.', flush=True)
                raise SystemExit(75) from None
            raise
    assert Image.open(directory / 'final.png').size == (1280, 720)
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == digest, 'capture executable changed'
    (directory / 'settings.json').write_text(json.dumps({
        'sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
        'flags': {k: v for k, v in settings.items() if k.startswith(('BOTW_', 'SLOPPY_'))}}, indent=2))
    print(f'PASS {scene}/{label}/{directory.name}', flush=True)


def capture(label, lock_wait=60):
    for scene, (_, _, frames) in SCENES.items():
        run(label, scene, OUT / scene / label, True, lock_wait)
        phases = ['before', label] if label != 'before' else ['before']
        strip = Image.new('RGB', (640 * len(frames), 384 * len(phases)), '#181b20')
        draw = ImageDraw.Draw(strip)
        for row, phase in enumerate(phases):
            for col, frame in enumerate(frames):
                path = OUT / scene / phase / f'frame-{frame}.png'
                strip.paste(Image.open(path).convert('RGB').resize((640, 360)), (col * 640, row * 384 + 24))
                draw.text((col * 640 + 8, row * 384 + 6), f'{phase} / {scene} / frame {frame}', fill='white')
        strip.save(OUT / f'{scene}-{label}-strip.jpg', quality=94)


def performance(candidate, repeats=3, lock_wait=60):
    report = {'base_revision': '500126f', 'protocol': {'order': 'alternating AB/BA', 'repeats_per_scene': repeats,
              'warmup_frames': 240, 'resolution': [1280, 720], 'scale': 1,
              'tolerance': '3% + 0.10 ms', 'cpu': 'callback wall and main-thread execution; no outliers removed'}, 'scenes': {}}
    for scene in SCENES:
        runs = {'before': [], 'after': []}
        for repeat in range(repeats):
            for phase in (['before', 'after'] if repeat % 2 == 0 else ['after', 'before']):
                directory = OUT / f'performance-{candidate}' / scene / f'{phase}-{repeat}'
                run('before' if phase == 'before' else candidate, scene, directory, lock_wait=lock_wait)
                rows = [[float(v) for v in l.split()[2:]] for l in (directory / 'run.log').read_text().splitlines() if l.startswith('frame sample:')]
                assert len(rows) == SCENES[scene][0]
                steady = [r for r in rows if r[0] > 240]
                runs[phase].append({metric: sorted(r[col] for r in steady)[math.ceil(len(steady)*.99)-1]
                                    for metric, col in [('wall_p99_ms', 2), ('thread_p99_ms', 4)]})
        result = {phase: {metric: statistics.median(r[metric] for r in runs[phase]) for metric in runs[phase][0]} for phase in runs}
        result['runs'] = runs
        result['repeats'] = repeats
        result['passed'] = all(result['after'][m] <= result['before'][m] * 1.03 + .10 for m in result['before'])
        report['scenes'][scene] = result
        (OUT / f'performance-{candidate}.json').write_text(json.dumps(report, indent=2) + '\n')
        print(scene, result, flush=True)
    assert all(r['passed'] for r in report['scenes'].values()), 'CPU p99 budget regression'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'capture', 'performance', 'profile'])
    parser.add_argument('label', nargs='?', default='after')
    parser.add_argument('--game-dir', type=Path)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--lock-wait', type=float, default=60)
    args = parser.parse_args()
    if args.repeats < 1 or args.lock_wait < 0: parser.error('repeats must be positive; lock wait must be nonnegative')
    if not re.fullmatch('[a-z][a-z0-9-]*', args.label): parser.error('use a lowercase label')
    os.chdir(ROOT)
    if args.mode == 'prepare': prepare(args.label, args.game_dir)
    elif args.mode == 'capture': capture(args.label, args.lock_wait)
    elif args.mode == 'profile':
        for scene in SCENES:
            run(args.label, scene, OUT / f'profile-{args.label}' / scene,
                lock_wait=args.lock_wait, profile=True)
    else: performance(args.label, args.repeats, args.lock_wait)
