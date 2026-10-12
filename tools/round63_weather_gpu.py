#!/usr/bin/env python3
"""Paired large-output weather GPU budget probe; self-locks the whole batch."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--locked', action='store_true', help=argparse.SUPPRESS)
p.add_argument('--repeats', type=int, default=2)
a = p.parse_args()
os.chdir(ROOT)
if not a.locked:
    sys.exit(subprocess.run(['flock', '/tmp/botw-render.lock', sys.executable, __file__, '--locked', '--repeats', str(a.repeats)]).returncode)
out = ROOT / 'build/round63/gpu'
out.mkdir(parents=True, exist_ok=True)
subprocess.run(['sloppy/bin/sloppy', 'build', 'game/main.jo', '-o', str(out / 'after-game')], check=True)
scenes = {
    'forest-storm': {'BOTW_AT': '-1000,1620,3.14', 'BOTW_WEATHER': 'storm'},
    'pond-strike': {'BOTW_AT': '-1190,1665,-0.9', 'BOTW_WEATHER': 'storm', 'BOTW_BOLT': '300', 'BOTW_BOLT_AT': '-1201.7,1655.7'},
    'nightcamp': {'BOTW_AT': '-1440,1600,0', 'BOTW_HOUR': '23', 'BOTW_WEATHER': 'clear'},
}
(out/'manifest.json').write_text(json.dumps(dict(output='2133x1200', scale=0.8, frames=600, steady_from_frame=240, simulation_hz=60, repeats=a.repeats, scenes=scenes, binary_sha256={phase: hashlib.sha256(path.read_bytes()).hexdigest() for phase,path in [('before',ROOT/'build/round63/before/game'),('after',out/'after-game')]}, source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'game').glob('*.jo'))}),indent=2)+'\n')
clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
results = []
def quantile(values, q):
    return sorted(values)[min(len(values)-1, math.ceil(q * len(values))-1)]
for repeat in range(a.repeats):
    for scene, flags in scenes.items():
        for phase in ['before', 'after']:
            prefix = out / f'{scene}-{phase}-{repeat+1}'
            binary = ROOT / 'build/round63/before/game' if phase == 'before' else out / 'after-game'
            settings = dict(clean, BOTW_SKIP='1', BOTW_HOUR='11', BOTW_SCALE='0.8', BOTW_GPU='1', BOTW_GPU_FRAME_LOG='1', BOTW_FRAME_LOG='1', BOTW_SCENE_LOG='1', BOTW_NOVSYNC='1', SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='2133x1200', SLOPPY_INPUT='0:w-', SLOPPY_FRAMES='600', SLOPPY_SCREENSHOT=str(prefix)+'.png')
            settings.update(flags)
            with Path(str(prefix)+'.log').open('w') as log:
                subprocess.run([sys.executable, 'tools/cliff_capture_window.py', '2133x1200', 'timeout', '300', str(binary)], env=settings, stdout=log, stderr=subprocess.STDOUT, check=True)
            text = Path(str(prefix)+'.log').read_text()
            rows = [(int(m[1]), float(m[2])) for m in re.finditer(r'gpu frame: (\d+).*? = ([\d.]+)', text) if int(m[1]) >= 240]
            vals = [v for _, v in rows]
            assert len(vals) > 300, (prefix, len(vals))
            electric = [float(m[1]) for m in re.finditer(r'^gpu frame:.*? electric ([\d.]+)', text, re.M)]
            entry = dict(scene=scene, phase=phase, repeat=repeat+1, gpu_samples=len(vals), gpu_p50_ms=quantile(vals,.5), gpu_p95_ms=quantile(vals,.95), gpu_p99_ms=quantile(vals,.99), gpu_worst_ms=max(vals), electric_worst_ms=max(electric,default=0.0), log=str(prefix)+'.log')
            results.append(entry)
            (out/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
            print(json.dumps(entry), flush=True)

failures = [r for r in results if r['phase'] == 'after' and r['gpu_p99_ms'] > 20.0]
(out/'budget.json').write_text(json.dumps(dict(limit_gpu_p99_ms=20.0, passed=not failures, failures=failures), indent=2)+'\n')
if failures:
    raise SystemExit('FAIL: weather GPU p99 exceeds the 20 ms fixed-scale budget')
print('PASS: all final weather GPU p99 samples within 20 ms', flush=True)
