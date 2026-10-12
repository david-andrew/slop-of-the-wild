#!/usr/bin/env python3
"""Bounded mailbox CPU-tail probe; owns one render flock per scene. Never wrap.

Real-dt forest/meadow movement; fixed-dt fire/overlook keep their workload
comparable across machines. Two-second windows use monotonic return timestamps,
not 120-frame batches. Returns measure handoff, not compositor scanout.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True

from render_evidence import analyze, metrics

ROOT = Path(__file__).resolve().parents[1]
SCENES = {'forest': {'BOTW_AT': '-1140,1500,3.14'},
          'fire': {'BOTW_FIRE': '1', 'PROBE_FIXED': '1'},
          'overlook': {'BOTW_AT': '-1050,1828,-2.36', 'PROBE_FIXED': '1'}}


def summarize(path):
    result = analyze(path)
    text = path.read_text()
    rows = [[float(v) for v in line.split()[2:]] for line in text.splitlines()
            if line.startswith('present return:')]
    # First four seconds are warmup; retain every subsequent complete window.
    windows = []
    warm_end = math.ceil((rows[0][1] + 4)/2)*2
    for start in range(warm_end, int(rows[-1][1])-1, 2):
        bucket = [r for r in rows if start <= r[1] < start+2]
        assert bucket, 'empty window'
        windows.append({'start_s': start, 'samples': len(bucket),
                        **{name: metrics([r[col] for r in bucket]) for name, col in
                           [('interval', 2), ('cpu_wall', 4), ('cpu_thread', 5)]}})
    assert windows, 'run finished during warmup; use a longer duration'
    selected = [r for r in rows if warm_end <= r[1] < windows[-1]['start_s']+2]
    traces = {}
    for line in text.splitlines():
        if line.startswith('long cpu '): n = int(re.search(r'; frame (\d+)', line)[1])
        elif line.startswith('tail cpu:'): n = int(re.search(r'frame (\d+)', line)[1])
        else: continue
        stages = Counter()
        walls = Counter()
        for name, wall, cpu in re.findall(r'([\w-]+) ([\d.]+)/([\d.]+)', line):
            stages[name] += float(cpu)
            walls[name] += float(wall)
        traces[n] = {'thread_ms': dict(stages), 'wall_ms': dict(walls),
                     'simulation_ticks': len(re.findall(r'player_update [\d.]+/[\d.]+', line))}
    tails = [r for r in selected if r[5] > 8]
    dominant = Counter()
    evidence = []
    for row in tails:
        stage = traces.get(int(row[0]))
        name = max(stage['thread_ms'], key=stage['thread_ms'].get) if stage else 'untraced'
        dominant[name] += 1
        evidence.append({'frame': int(row[0]), 'elapsed_s': row[1], 'interval_ms': row[2],
                         'cpu_wall_ms': row[4], 'cpu_thread_ms': row[5],
                         'dominant_stage': name, 'simulation_ticks': stage['simulation_ticks'] if stage else None, 'stages': stage})
    result.update(windows=windows, window_count=len(windows),
                  windows_over_20ms=sum(w['interval']['p99'] > 20 for w in windows),
                  windows_over_17_5ms=sum(w['interval']['p99'] > 17.5 for w in windows),
                  windows_cpu_over_8ms=sum(w['cpu_thread']['p99'] > 8 for w in windows),
                  distribution={name: metrics([r[col] for r in selected]) for name, col in
                                [('interval', 2), ('cpu_wall', 4), ('cpu_thread', 5)]},
                  cpu_frames_over_8ms=len(tails), dominant_cpu_tail_stages=dict(dominant),
                  cpu_tails=evidence,
                  interval_frames_over_17_5ms=sum(r[2] > 17.5 for r in selected),
                  interval_frames_over_20ms=sum(r[2] > 20 for r in selected),
                  cpu_frames_over_14ms=sum(r[5] > 14 for r in selected),
                  worst_window_p99_ms=max(w['interval']['p99'] for w in windows),
                  waypoints=re.findall(r'^forest waypoint:.*$', text, re.M),
                  minutes=re.findall(r'^session minute:.*$', text, re.M))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--executable', type=Path)
    parser.add_argument('--seconds', type=int, default=300)
    parser.add_argument('--scene-seconds', type=int, help='shorter duration for fire/overlook')
    parser.add_argument('--views', nargs='+', choices=SCENES, default=list(SCENES))
    parser.add_argument('--scale', default='0.80', choices=['dynamic', '0.72', '0.80'])
    parser.add_argument('--trace', action='store_true')
    parser.add_argument('--cpu-trace-ms', type=float, help='also retain every callback CPU trace above this threshold')
    parser.add_argument('--cpu-workers', type=int, default=0, help='controlled CPU-only contention, started only inside this render lock')
    parser.add_argument('--check', action='store_true', help='bounded regression budget, not the aspirational 100 target')
    a = parser.parse_args()
    assert 0 <= a.cpu_workers <= 16
    assert a.cpu_trace_ms is None or a.cpu_trace_ms >= 0
    os.chdir(ROOT)
    out = a.output.resolve()
    assert out.is_relative_to(ROOT/'build') and 10 <= a.seconds <= 600
    out.mkdir(parents=True, exist_ok=True)
    exe = a.executable.resolve() if a.executable else out/'game'
    if not a.executable:
        subprocess.run(['sloppy/bin/sloppy', 'build', 'tools/render_session.jo', '-o', str(exe)], check=True)
    sources = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('game').glob('*.jo'))} if not a.executable else None
    provenance = Path(str(exe)+'.sources.json')
    if not a.executable: provenance.write_text(json.dumps(sources, indent=2)+'\n')
    elif provenance.exists(): sources = json.loads(provenance.read_text())
    summary = {'protocol': '2133x1200 Vulkan swapchain mailbox; 4s warmup; complete 2s monotonic windows; nearest rank; handoff proxy, not scanout',
               'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
               'executable_sha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
               'sources': sources,
               'runs': {}}
    for view in a.views:
        seconds = a.scene_seconds if view != 'forest' and a.scene_seconds else a.seconds
        assert 10 <= seconds <= 600
        env = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'PROBE_'))}
        env.update(BOTW_SKIP='1', BOTW_HOUR='11', BOTW_WEATHER='clear', BOTW_LOADTIME='1',
                   BOTW_FRAME_LOG='1', BOTW_SCENE_LOG='1', SLOPPY_PLATFORM='wayland',
                   SLOPPY_VSYNC='0', SLOPPY_WINDOW='1280x720', PROBE_SECONDS=str(seconds),
                   PROBE_ROUTE=view, PROBE_PNG=str(out/(view+'.png')))
        env.update(SCENES[view])
        if a.scale != 'dynamic': env['BOTW_SCALE'] = a.scale
        if a.trace or a.cpu_trace_ms is not None:
            env.update(BOTW_CPU='1', BOTW_CPU_TRACE_MS=str(a.cpu_trace_ms if a.cpu_trace_ms is not None else 1000), PROBE_STAGES='1')
        if a.trace:
            env.update(BOTW_CPU_RETURN_TRACE='1', BOTW_GPU='1', BOTW_GPU_FRAME_LOG='1')
        print('queued', view, seconds, a.scale, flush=True)
        path = out/(view+'.log')
        with path.open('w') as log:
            command = ['timeout', '-k', '5', str(seconds+60), str(exe)]
            if a.cpu_workers:
                command = [sys.executable, str(ROOT/'tools/cpu_contention.py'), str(a.cpu_workers), *command]
            subprocess.run(['flock', '/tmp/botw-render.lock', *command], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        from PIL import Image
        assert Image.open(out/(view+'.png')).size == (2133, 1200), 'screenshot viewport mismatch'
        result = summarize(path)
        result['flags'] = {k:v for k,v in env.items() if k.startswith(('BOTW_', 'SLOPPY_', 'PROBE_'))}
        result['load_end'] = Path('/proc/loadavg').read_text().strip()
        result['controlled_cpu_workers'] = a.cpu_workers
        (out/(view+'.json')).write_text(json.dumps(result, indent=2)+'\n')
        summary['runs'][view] = result
        (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
        print(view, result['distribution'], 'windows', result['window_count'],
              '>20', result['windows_over_20ms'], '>17.5', result['windows_over_17_5ms'],
              'CPU>8', result['dominant_cpu_tail_stages'], flush=True)
        if a.trace:
            # Return-triggered traces cover long intervals, not harmless CPU-only
            # frames below the interval threshold. Attribution validates coverage.
            if result['interval_frames_over_17_5ms']:
                assert 'tail cpu:' in path.read_text()
        if a.check:
            assert result['distribution']['cpu_thread']['p99'] < 8, 'callback CPU tail regression'
            assert result['distribution']['interval']['p99'] < 20, 'mailbox interval regression'
    print('PASS CPU tail probe', flush=True)


if __name__ == '__main__':
    main()
