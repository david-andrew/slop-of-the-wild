#!/usr/bin/env python3
"""Rootless, verified cold prepared-file startup; one render lock per launch.

Evicts only this worktree's prepared packs, shader binaries and test executable.
Model/texture/source-input, kernel/driver and shared-library caches remain warm.
"""
import argparse
import ctypes
import hashlib
import json
import mmap
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
out = ROOT / 'build/round71/startup'
out.mkdir(parents=True, exist_ok=True)
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--reuse-measurements', action='store_true', help='validate and summarize completed measurement rows without rendering again')
ap.add_argument('--single', choices=('cold', 'warm'), help=argparse.SUPPRESS)
ap.add_argument('--repeat', type=int, default=1, help=argparse.SUPPRESS)
a = ap.parse_args()
if not a.single:
    if not a.reuse_measurements:
        subprocess.run(['sloppy/bin/sloppy', 'build', 'tools/performance_game.jo', '-o', str(out / 'game')], check=True)
        for repeat in range(1, 4):
            for mode in ('cold', 'warm'):
                subprocess.run(['flock', '/tmp/botw-render.lock', sys.executable, __file__,
                                '--single', mode, '--repeat', str(repeat)], check=True)
    else:
        recorded = json.loads((out / 'summary.json').read_text())
        assert recorded['executable_sha256'] == hashlib.sha256((out / 'game').read_bytes()).hexdigest(), 'measurement executable changed'
    rows = [json.loads((out / f'{mode}-{repeat}.row.json').read_text())
            for repeat in range(1, 4) for mode in ('cold', 'warm')]
    from PIL import Image
    for row in rows:
        names = {Path(r['file']).stem for r in row['residency_before']}
        assert 'textures' in names, 'old measurements omit texture pack'
        if row['mode'] == 'cold': assert sum(r['resident_pages'] for r in row['residency_before']) == 0
        name = f"{row['mode']}-{row['repeat']}"
        log = (out / (name + '.log')).read_text()
        assert 'prepared textures: hit' in log and 'PNG decodes 0' in log
        assert Image.open(out / (name + '.png')).size == (1280, 720)
    summary = {'protocol': 'rootless POSIX_FADV_DONTNEED on all local prepared packs, shader binaries and executable; mincore verifies zero pages immediately before each cold launch, inside its individual render lock; other caches remain warm',
               'executable_sha256': hashlib.sha256((out / 'game').read_bytes()).hexdigest(), 'runs': rows}
    for mode in ('cold', 'warm'):
        runs = [r for r in rows if r['mode'] == mode]
        summary[mode] = {k: {'median': statistics.median(r[k] for r in runs),
                            'min': min(r[k] for r in runs), 'max': max(r[k] for r in runs)}
                         for k in ('load_s', 'elapsed_s', 'major_faults')}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('PASS verified cold/warm prepared startup: three pairs, texture pack included, zero cold residency, exact 1280x720')
    sys.exit(0)

libc = ctypes.CDLL(None, use_errno=True)
libc.mincore.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_ubyte)]
PAGE = os.sysconf('SC_PAGE_SIZE')
packs = sorted((ROOT / 'assets/prepared').glob('*.bin'))
required = {'world', 'terrain', 'water', 'farland', 'structures', 'sfx', 'piano', 'chime', 'textures'}
assert required <= {p.stem for p in packs}, 'warm_assets.sh must prepare all packs, including textures'
files = packs + sorted((ROOT / 'build/shader-cache').rglob('*.bin')) + [out / 'game']
assert all(p.resolve().is_relative_to(ROOT) for p in files)

def resident(path, evict=False):
    with path.open('rb') as f:
        if evict:
            os.fsync(f.fileno())
            os.posix_fadvise(f.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
        size = path.stat().st_size
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_COPY) as mapped:
            view = (ctypes.c_char * size).from_buffer(mapped)
            n = (size + PAGE - 1) // PAGE
            vec = (ctypes.c_ubyte * n)()
            if libc.mincore(ctypes.addressof(view), size, vec): raise OSError(ctypes.get_errno(), 'mincore')
            pages = sum(v & 1 for v in vec)
            del view
    return {'file': str(path.relative_to(ROOT)), 'bytes': size, 'pages': n, 'resident_pages': pages}

residency = [resident(p, evict=a.single == 'cold') for p in files]
if a.single == 'cold': assert sum(r['resident_pages'] for r in residency) == 0, residency
name = f'{a.single}-{a.repeat}'
(out / (name + '.residency.json')).write_text(json.dumps(residency, indent=2) + '\n')
env = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
env.update(BOTW_LOADTIME='1', BOTW_SCALE='1', BOTW_NOVSYNC='1', SLOPPY_PLATFORM='x11',
           SLOPPY_WINDOW='1280x720', SLOPPY_FRAMES='1', SLOPPY_SCREENSHOT=str(out / (name + '.png')))
with (out / (name + '.log')).open('w') as log:
    subprocess.run(['python3', 'tools/performance_window.py', '1280x720', '/usr/bin/time',
                    '-f', 'startup_elapsed_s=%e major_faults=%F minor_faults=%R',
                    'timeout', '180', str(out / 'game')], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
text = (out / (name + '.log')).read_text()
assert all(f'prepared {pack}: hit' in text for pack in ('terrain', 'water', 'farland', 'structures', 'textures')), 'pack miss invalidates prepared startup'
assert 'PNG decodes 0' in text and 'startup textures: PNG decodes' not in text
row = {'mode': a.single, 'repeat': a.repeat, 'residency_before': residency,
       'load_s': float(re.search(r'loaded in ([0-9.]+)s', text)[1]),
       'elapsed_s': float(re.search(r'startup_elapsed_s=([0-9.]+)', text)[1]),
       'major_faults': int(re.search(r'major_faults=(\d+)', text)[1]),
       'loadavg': Path('/proc/loadavg').read_text().strip()}
(out / (name + '.row.json')).write_text(json.dumps(row, indent=2) + '\n')
print(name, row['load_s'], row['elapsed_s'], flush=True)
