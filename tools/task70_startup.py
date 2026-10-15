#!/usr/bin/env python3
"""Exact-output startup samples. Owns bounded render-lock batches; never wrap it.

Cold means a fresh local Vulkan/NVIDIA cache, not a system/page-cache flush.
Wait briefly for low CPU/GPU activity, retain activity and all samples even when
other workers prevent an idle sample. Compilation is outside launch timing.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def activity():
    vals = list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:]))
    return sum(vals[:8]), vals[3] + vals[4]


def quiet(wait=True, max_wait=30):
    started = time.monotonic()
    while True:
        a, idle_a = activity()
        time.sleep(1)
        b, idle_b = activity()
        cpu = 100 * (1 - (idle_b - idle_a) / max(1, b - a))
        gpu = float(subprocess.check_output(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'], text=True).strip())
        row = dict(cpu_busy_pct=round(cpu, 2), gpu_busy_pct=gpu, loadavg=Path('/proc/loadavg').read_text().strip(), quiet_wait_s=time.monotonic()-started)
        row['idle_before_launch'] = cpu < 12 and gpu < 5
        if row['idle_before_launch'] or not wait or time.monotonic()-started > max_wait:
            return row


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('binary', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--warm-runs', type=int, default=18)
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--idle-only', action='store_true', help='require <12%% CPU and <5%% GPU activity before every launch; fail without launching when the quiet timeout expires')
    ap.add_argument('--quiet-timeout', type=float, default=30, help='seconds to wait for quiet activity, 1..60 (default: 30)')
    args = ap.parse_args()
    assert 1 <= args.quiet_timeout <= 60
    assert 1 <= args.warm_runs <= 100
    os.chdir(ROOT)
    out = args.out.resolve()
    assert out.is_relative_to(ROOT/'build') and (args.resume or not out.exists()), 'use a fresh local build/ directory'
    out.mkdir(parents=True, exist_ok=args.resume)
    binary = args.binary.resolve()
    cache = out/'cache'
    (cache/'nvidia').mkdir(parents=True, exist_ok=args.resume)
    rows = json.loads((out/'summary.json').read_text())['runs'] if args.resume else []
    if args.resume: assert json.loads((out/'summary.json').read_text())['executable_sha256'] == hashlib.sha256(binary.read_bytes()).hexdigest()
    remaining = [n for n in ['cold'] + [f'warm-{i}' for i in range(1,args.warm_runs+1)] if n not in {r['name'] for r in rows}]
    lock = open('/tmp/botw-render.lock','w')
    batch_start = 0.0
    for name in remaining:
        if batch_start == 0.0 or time.monotonic()-batch_start > 60:
            if batch_start: fcntl.flock(lock,fcntl.LOCK_UN)
            fcntl.flock(lock,fcntl.LOCK_EX)
            batch_start = time.monotonic()
            idle = quiet(max_wait=args.quiet_timeout)
        else: idle = quiet(wait=args.idle_only, max_wait=args.quiet_timeout)
        if args.idle_only and not idle['idle_before_launch']:
            raise RuntimeError(f'machine stayed busy; no {name} launch: {idle}')
        settings = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'CP_', 'PROBE_'))}
        settings.update(XDG_CACHE_HOME=str(cache), __GL_SHADER_DISK_CACHE_PATH=str(cache/'nvidia'),
            SLOPPY_PLATFORM='x11', SLOPPY_VULKAN='1', SLOPPY_VSYNC='0', SLOPPY_WINDOW='2133x1200',
            SLOPPY_FRAMES='1', SLOPPY_SCREENSHOT=str(out/f'{name}.png'), BOTW_LOADTIME='1',
            BOTW_FRAME_LOG='1', BOTW_SKIP='1', BOTW_HOUR='11', BOTW_TIMESCALE='0', BOTW_WEATHER='clear', BOTW_SCALE='1')
        command = ['python3', 'tools/performance_window.py', '2133x1200', 'python3', 'tools/startup_measure.py', 'timeout', '60', str(binary)]
        with (out/f'{name}.log').open('w') as log:
            subprocess.run(command, env=settings, stdout=log, stderr=subprocess.STDOUT, check=True)
        text = (out/f'{name}.log').read_text()
        assert all(f'prepared {p}: hit' in text for p in ['terrain','water','farland','structures','textures'])
        from PIL import Image
        assert Image.open(out/f'{name}.png').size == (2133,1200)
        row = dict(name=name, load_s=float(re.search(r'loaded in ([\d.]+)s', text)[1]),
            warmup_s=float(re.search(r'render_warmup ([\d.]+)s', text)[1]),
            terrain_upload_s=float(re.search(r'^  terrain_upload ([\d.]+)s', text, re.M)[1]),
            first_callback_end_s=float(re.search(r'startup_first_callback_end_s=([\d.]+)', text)[1]),
            process_s=float(re.search(r'startup_elapsed_s=([\d.]+)', text)[1]),
            cache_hit='game pipeline cache: hit' in text, activity=idle, command=command,
            environment={k:v for k,v in settings.items() if k.startswith(('BOTW_', 'SLOPPY_', 'XDG_', '__GL_'))})
        rows.append(row)
        summary = dict(protocol=f'2133x1200 exact X11/Vulkan output, full scale, prepared assets, one completed frame, fresh local Vulkan/NVIDIA caches for cold; reused for {args.warm_runs} warm launches; no system/page-cache flush; render-lock and quiet wait excluded; load ends before first game draw, first callback and process include it',
            executable_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(), idle_required=args.idle_only, quiet_timeout_s=args.quiet_timeout, runs=rows)
        if len(rows)>1:
            summary['warm'] = {k:dict(median=statistics.median(r[k] for r in rows[1:]), min=min(r[k] for r in rows[1:]), max=max(r[k] for r in rows[1:])) for k in ('load_s','warmup_s','terrain_upload_s','first_callback_end_s','process_s')}
        (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
        print(name, row['load_s'], row['warmup_s'], idle, flush=True)
    lock.close()


if __name__ == '__main__':
    main()
