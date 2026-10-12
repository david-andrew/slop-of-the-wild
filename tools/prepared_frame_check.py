#!/usr/bin/env python3
"""Compare exact first-frame pixels for prepared and generated world assets."""
import argparse
import json
import hashlib
import re
import os
from pathlib import Path
import subprocess
from PIL import Image, ImageChops


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=Path('build/prepared-frame-check'))
    ap.add_argument('--resume', action='store_true', help='retain completed captures only if the rebuilt executable is byte-identical')
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    out = (root / a.output).resolve()
    assert out.is_relative_to(root / 'build'), 'raw captures must stay under build/'
    out.mkdir(parents=True, exist_ok=True)
    clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
    prior_hash = hashlib.sha256((out / 'game').read_bytes()).digest() if a.resume else None
    prior_mtime = (out / 'game').stat().st_mtime_ns if a.resume else None
    if not a.resume: subprocess.run(['tools/prepare_assets.sh'], env=clean, check=True)
    subprocess.run(['sloppy/bin/sloppy', 'build', 'game/main.jo', '-o', str(out / ('game-resume' if a.resume else 'game'))], env=clean, check=True)
    if a.resume:
        assert hashlib.sha256((out / 'game-resume').read_bytes()).digest() == prior_hash, 'executable changed; rerun without --resume'
    base = {**clean, 'SLOPPY_PLATFORM': 'x11', 'SLOPPY_WINDOW': '1280x720',
            'SLOPPY_FRAMES': '1', 'SLOPPY_INPUT': '', 'BOTW_LOADTIME': '1',
            'BOTW_NOVSYNC': '1', 'BOTW_SCALE': '1', 'BOTW_HOUR': '11', 'BOTW_WEATHER': 'clear'}
    views = {'opening': {}, 'overlook': {'BOTW_SKIP': '1', 'BOTW_AT': '-1024,1799,0'},
             'pond': {'BOTW_SKIP': '1', 'BOTW_AT': '-1190,1665,-0.9'},
             'shrine': {'BOTW_SKIP': '1', 'BOTW_SHRINE': '1', 'BOTW_TOWER': '1'}}
    results = {}
    for view, flags in views.items():
        for mode in ('prepared', 'generated'):
            prefix = out / f'{view}-{mode}'
            env = {**base, **flags, 'SLOPPY_SCREENSHOT': str(prefix.with_suffix('.png'))}
            if mode == 'generated': env['BOTW_NO_PREPARED_ASSETS'] = '1'
            log_path = prefix.with_suffix('.log')
            png_path = prefix.with_suffix('.png')
            reuse = a.resume and log_path.is_file() and png_path.is_file() and min(log_path.stat().st_mtime_ns, png_path.stat().st_mtime_ns) >= prior_mtime
            if not reuse:
                with log_path.open('w') as log:
                    subprocess.run(['flock', '/tmp/botw-render.lock', 'python3', 'tools/performance_window.py', '1280x720',
                                    'timeout', '180', str(out / 'game')], env=env,
                                   stdout=log, stderr=subprocess.STDOUT, check=True)
            text = prefix.with_suffix('.log').read_text()
            assert 'loaded in ' in text and not re.search(r'panic:|error:|FAIL', text), text[-2000:]
            for name in ('terrain', 'water', 'farland', 'structures', 'textures'):
                assert (f'prepared {name}: hit' in text) == (mode == 'prepared'), f'{view}/{mode}: {name} cache mode mismatch'
        prepared = Image.open(out / f'{view}-prepared.png').convert('RGB')
        generated = Image.open(out / f'{view}-generated.png').convert('RGB')
        assert prepared.size == generated.size == (1280, 720)
        delta = ImageChops.difference(prepared, generated)
        results[view] = {'identical': delta.getbbox() is None, 'changed_bounds': delta.getbbox()}
        (out / 'summary.json').write_text(json.dumps(results, indent=2) + '\n')
        print(view, results[view], flush=True)
    assert all(r['identical'] for r in results.values())
    print('PASS prepared/generated first-frame pixels: opening, overlook, pond, shrine')


if __name__ == '__main__':
    main()
