#!/usr/bin/env python3
"""Capture and compare active fire before/after at both exact outputs.

Owns one render flock per process. Run with the client-size performance_game
executables; output and raw captures must stay under ignored build/.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

from PIL import Image, ImageChops


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('before', type=Path)
    ap.add_argument('after', type=Path)
    ap.add_argument('output', type=Path)
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    out = a.output.resolve()
    assert out.is_relative_to(root / 'build')
    binaries = {'before': a.before.resolve(), 'after': a.after.resolve()}
    clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
    results = {}
    for size in ['1280x720', '2133x1200']:
        for phase, binary in binaries.items():
            directory = out / size / phase
            directory.mkdir(parents=True, exist_ok=True)
            settings = {**clean, 'BOTW_SKIP': '1', 'BOTW_FIRE': '1',
                        'BOTW_WEATHER': 'clear', 'BOTW_SCALE': '1',
                        'BOTW_NOVSYNC': '1', 'SLOPPY_PLATFORM': 'x11',
                        'SLOPPY_WINDOW': size, 'SLOPPY_FRAMES': '720',
                        'SLOPPY_SCREENSHOT': str(directory / 'final.png'),
                        'BOTW_CAPTURE_DIR': str(directory), 'BOTW_CAPTURE_EVERY': '120'}
            with (directory / 'run.log').open('w') as log:
                subprocess.run(['flock', '/tmp/botw-render.lock', 'python3',
                                'tools/performance_window.py', size, 'timeout', '180', str(binary)],
                               env=settings, stdout=log, stderr=subprocess.STDOUT, check=True)
        comparisons = {}
        for name in [f'frame-{n}.png' for n in range(120, 721, 120)] + ['final.png']:
            b, c = (out / size / phase / name for phase in ['before', 'after'])
            assert Image.open(b).size == tuple(map(int, size.split('x')))
            assert Image.open(c).size == tuple(map(int, size.split('x')))
            equal = b.read_bytes() == c.read_bytes()
            assert ImageChops.difference(Image.open(b), Image.open(c)).getbbox() is None
            assert equal, f'changed deterministic fire PNG: {size}/{name}'
            comparisons[name] = {'byte_identical': equal}
        results[size] = comparisons
        (out / 'summary.json').write_text(json.dumps(results, indent=2) + '\n')
        print(size, 'PASS: active front, roots, embers, smoke and scorch; seven identical PNG pairs', flush=True)


if __name__ == '__main__':
    main()
