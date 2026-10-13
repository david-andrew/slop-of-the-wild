#!/usr/bin/env python3
"""Rendered Vulkan/OpenGL noise-seam regression; owns one flock per capture.

Capture all four critic views at exact X11 1280x720. Compare broad residuals
in quiet surface regions, so subpixel rasterization, grain, actors and particles
cannot hide a lattice-sized rectangle behind a whole-frame average.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from PIL import Image, ImageChops, ImageFilter, ImageStat

ROOT = Path(__file__).resolve().parents[1]
VIEWS = {
    'pond': ({'BOTW_AT': '-1190,1665,-0.9'}, (80, 420, 550, 700)),
    'pondrain': ({'BOTW_AT': '-1190,1665,-0.9', 'BOTW_WEATHER': 'rain'}, (80, 400, 550, 700)),
    'temple': ({'BOTW_AT': '-818,1950,3.14'}, (280, 575, 560, 700)),
    'fire260': ({'BOTW_FIRE': '1', 'SLOPPY_FRAMES': '260'}, (760, 335, 1140, 430)),
}


def compare(directory):
    results = {}
    for name, (_, roi) in VIEWS.items():
        for mode, backend in [('vk', 'vulkan ('), ('gl', 'egl window surface')]:
            assert backend in (directory / f'{name}-{mode}.log').read_text(), f'{name}/{mode}: expected native renderer was not used'
        images = [Image.open(directory / f'{name}-{mode}.png').convert('RGB') for mode in ('vk', 'gl')]
        assert all(i.size == (1280, 720) for i in images), 'comparison requires exact 1280x720 captures'
        delta = ImageChops.difference(*images)
        delta.point(lambda v: min(255, v * 4)).save(directory / f'{name}-diff.png')
        surfaces = [i.crop(roi) for i in images]
        coarse = ImageChops.difference(*(i.filter(ImageFilter.BoxBlur(4)) for i in surfaces))
        # A nine-pixel box suppresses fine material grain. Persistent >6-count
        # RGB differences across >2% of a quiet surface flag broad hash seams.
        channels = coarse.split()
        peak = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
        fraction = sum(peak.histogram()[7:]) / (peak.width * peak.height)
        result = {
            'roi': roi,
            'whole_frame_mean_absolute_rgb': sum(ImageStat.Stat(delta).mean) / 3,
            'surface_mean_absolute_rgb': sum(ImageStat.Stat(ImageChops.difference(*surfaces)).mean) / 3,
            'coarse_pixels_over_6_counts_pct': fraction * 100,
            'limit_pct': 2.0,
            'passed': fraction <= .02,
        }
        results[name] = result
        coarse.point(lambda v: min(255, v * 8)).save(directory / f'{name}-surface-diff.png')
        print(f"{'PASS' if result['passed'] else 'FAIL'} {name}: broad residual {fraction * 100:.3f}% (limit 2%)", flush=True)
    (directory / 'structure-summary.json').write_text(json.dumps(results, indent=2) + '\n')
    return all(r['passed'] for r in results.values())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--binary', type=Path, help='use an already built game executable')
    ap.add_argument('--output', type=Path, default=Path('build/round64/renderer/regression'))
    ap.add_argument('--compare-only', action='store_true', help='check existing captured pairs without launching the game')
    args = ap.parse_args()
    os.chdir(ROOT)
    out = args.output.resolve()
    assert out.is_relative_to(ROOT / 'build'), 'evidence must remain under build/'
    out.mkdir(parents=True, exist_ok=True)
    if not args.compare_only:
        binary = args.binary.resolve() if args.binary else out / 'game'
        if not args.binary:
            subprocess.run(['sloppy/bin/sloppy', 'build', 'game/main.jo', '-o', str(binary)], check=True)
        clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
        manifest = {'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                    'sources': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted((ROOT / 'game').glob('*.jo'))}, 'captures': {}}
        for name, (flags, _) in VIEWS.items():
            for mode in ('vk', 'gl'):
                env = {**clean, 'BOTW_SKIP': '1', 'BOTW_HOUR': '11', 'BOTW_WEATHER': 'clear', 'BOTW_SCALE': '1',
                       'BOTW_LOADTIME': '1', 'BOTW_NOVSYNC': '1', 'SLOPPY_PLATFORM': 'x11', 'SLOPPY_WINDOW': '1280x720',
                       'SLOPPY_FRAMES': '1', 'SLOPPY_VSYNC': '0', **flags,
                       'SLOPPY_SCREENSHOT': str(out / f'{name}-{mode}.png')}
                if mode == 'gl':
                    env['SLOPPY_VULKAN'] = '0'
                print('capture', name, mode, flush=True)
                with (out / f'{name}-{mode}.log').open('w') as log:
                    subprocess.run(['flock', '/tmp/botw-render.lock', 'python3', 'tools/performance_window.py', '1280x720',
                                    'timeout', '180', str(binary)], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
                manifest['captures'][f'{name}-{mode}'] = {k: v for k, v in env.items() if k.startswith(('BOTW_', 'SLOPPY_'))}
        (out / 'capture-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    raise SystemExit(0 if compare(out) else 1)


if __name__ == '__main__':
    main()
