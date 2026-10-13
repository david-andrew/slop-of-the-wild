#!/usr/bin/env python3
"""Wayland Vulkan/OpenGL present-return and rendered soak evidence (opt-in).

Owns ONE flock per bounded render; do not wrap this script in flock. All scratch
stays under build/. Presentation timestamps are call returns, never scanout.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(values):
    values = sorted(values)
    assert values, 'missing timing samples'
    return {key: values[max(0, math.ceil(len(values)*p)-1)]
            for key, p in [('p50', .5), ('p99', .99), ('worst', 1)]}


def gpu_memory(pid):
    try:
        xml = subprocess.check_output(['nvidia-smi', '-q', '-x'], timeout=5, text=True)
        root = ET.fromstring(xml)
        processes = root.findall('.//process_info')
        matches = [p for p in processes if p.findtext('pid') == str(pid)]
        return {'process': [p.findtext('used_memory') for p in matches],
                'device_used': [g.findtext('fb_memory_usage/used') for g in root.findall('gpu')]}
    except (OSError, subprocess.SubprocessError, ET.ParseError) as exc:
        return {'unavailable': str(exc)}


def analyze(log, soak=False):
    text = log.read_text()
    rows = [[float(v) for v in line.split()[2:]]
            for line in text.splitlines() if line.startswith('present return:')]
    assert rows and 'probe complete:' in text, 'incomplete window run'
    assert [int(r[0]) for r in rows] == list(range(len(rows))), 'missing/duplicate frame rows'
    assert all(b[1] > a[1] for a, b in zip(rows, rows[1:])), 'non-monotonic return timestamps'
    assert all(r[6:] == [2133, 1200] for r in rows), 'physical viewport mismatch'
    assert 'probe presentation:' in text, 'presentation not confirmed'
    game_rows = [[float(v) for v in line.split()[2:]] for line in text.splitlines()
                 if line.startswith('frame sample:')]
    returns = {int(r[0]): r for r in rows}
    assert all(abs(r[11]-returns[int(r[0])-1][3]) <= .000501 for r in game_rows), 'runtime present counter disagrees'
    assert abs(sum(r[2] for r in rows)/1000-(rows[-1][1]-rows[0][1])) < .00001, 'return delta sum disagrees'
    selected = [r for r in rows if r[0] >= 241]
    result = {'frames': len(rows), 'elapsed_s': rows[-1][1], 'samples_after_240': len(selected),
              'presentation': re.search(r'^probe presentation: (.+)$', text, re.M)[1],
              'load_s': float(re.search(r'loaded in ([\d.]+)s', text)[1]),
              'timing_ms': {name: metrics([r[col] for r in selected])
                            for name, col in [('present_return_interval', 2), ('present_call', 3),
                                              ('callback_wall', 4), ('callback_thread', 5)]},
              'log_sha256': digest(log),
              'scene_positions': sorted(set(re.findall(r'perf scene: frame \d+ pos (\S+) hp', text))),
              'scene_scales': sorted(set(re.findall(r'; 2133x1200 scale ([\d.]+)', text)))}
    if soak:
        minutes = []
        for m in re.finditer(r'^session minute: (.+)$', text, re.M):
            fields = m[1].split()
            entry = {'minute': int(fields[0]), **{fields[i]: float(fields[i+1])
                                                     for i in range(1, len(fields), 2)}}
            minute = entry['minute']
            bucket = [r for r in rows if (minute-1)*60 < r[1] <= minute*60 and r[0] > 0]
            entry['samples'] = len(bucket)
            entry['timing_ms'] = {name: metrics([r[col] for r in bucket])
                                 for name, col in [('present_return_interval', 2), ('present_call', 3),
                                                   ('callback_wall', 4), ('callback_thread', 5)]}
            minutes.append(entry)
        result['minutes'] = minutes
        result['phases'] = re.findall(r'^session phase:.*$', text, re.M)
    return result


def run(exe, out, name, flags, seconds=None, frames=2400):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('BOTW_', 'SLOPPY_', 'PROBE_'))}
    env.update(BOTW_SKIP='1', BOTW_HOUR='11', BOTW_WEATHER='clear', BOTW_LOADTIME='1',
               BOTW_FRAME_LOG='1', BOTW_SCENE_LOG='1', SLOPPY_PLATFORM='wayland',
               SLOPPY_WINDOW='1280x720', PROBE_PNG=str(out/(name+'.png')),
               PROBE_FRAMES=str(frames))
    env.update(flags)
    if seconds is not None:
        env['PROBE_SECONDS'] = str(seconds)
    timeout = math.ceil(seconds + 60) if seconds is not None else max(180, math.ceil(frames/40 + 60))
    assert timeout <= 720
    meta = {'flags': {k: v for k, v in env.items() if k.startswith(('BOTW_', 'SLOPPY_', 'PROBE_'))},
            'timeout_s': timeout, 'load_before': Path('/proc/loadavg').read_text().strip()}
    log_path = out/(name+'.log')
    gpu = []
    print('queued', name, flush=True)
    with log_path.open('w') as log:
        proc = subprocess.Popen(['flock', '/tmp/botw-render.lock', 'timeout', '-k', '5',
                                 str(timeout), str(exe)], env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, start_new_session=True)
        pid = None
        try:
            for line in proc.stdout:
                log.write(line)
                if line.startswith('probe pid:'):
                    pid = int(line.split()[-1])
                    print('rendering', name, 'pid', pid, flush=True)
                if line.startswith('session minute:'):
                    sample = {'minute': int(line.split()[2]), **gpu_memory(pid)}
                    gpu.append(sample)
                    (out/(name+'.gpu.json')).write_text(json.dumps(gpu, indent=2)+'\n')
                    print(line.strip(), sample, flush=True)
            status = proc.wait()
            if status:
                raise RuntimeError(f'{name}: exit {status}; see {log_path}')
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
    if seconds is not None:
        assert 'PROBE_SECONDS' in env and 'SLOPPY_SCREENSHOT' not in env
    expected_mode = 'mailbox' if env.get('SLOPPY_VSYNC') == '0' else 'fifo'
    if env.get('SLOPPY_VULKAN') != '0':
        assert f'probe swapchain: {1 if expected_mode == "mailbox" else 2}' in log_path.read_text(), 'presentation mode mismatch'
    else:
        assert 'vulkan (' not in log_path.read_text(), 'OpenGL was requested'
    meta['load_after'] = Path('/proc/loadavg').read_text().strip()
    from PIL import Image
    assert Image.open(out/(name+'.png')).size == (2133, 1200)
    result = {**meta, **analyze(log_path, seconds is not None), 'gpu_memory': gpu}
    if seconds is not None:
        assert len(result['minutes']) == int(seconds//60), 'missing minute snapshots'
        last = result['minutes'][-1]
        assert last['distance'] > 100, 'traversal did not move'
        if env.get('PROBE_ROUTE') == 'combat':
            score = [(float(t),m) for t,m in re.findall(r'combat score: elapsed ([\d.]+) mood (\w+)',log_path.read_text())]
            entries = [t for t,m in score if 40 <= t < 80 and m == 'combat']
            assert entries, 'combat entry must occur after warmup'
            # Production hits can defeat the camp before the scheduled retreat.
            # Retain either actual victory or escape rather than forcing AI/HP.
            assert any(t > entries[0] and m != 'combat' for t,m in score), 'combat exit must resume field score'
            assert score[-1][1] != 'combat', 'route must finish outside combat'
            assert last['engaged'] > 0 and last['swing'] > 0, 'combat coverage missing'
            result['score_transitions'] = [dict(elapsed_s=t,mood=m) for t,m in score]
        if seconds >= 300 and env.get('PROBE_ROUTE', 'mixed') == 'mixed':
            assert last['engaged'] > 0 and last['swing'] > 0, 'combat coverage missing'
            assert last['fx'] > 0 and last['rain'] > 0 and last['snow'] > 0, 'route coverage missing'
    (out/(name+'.json')).write_text(json.dumps(result, indent=2)+'\n')
    print('complete', name, result['timing_ms']['present_return_interval'], flush=True)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['pacing', 'soak'])
    p.add_argument('--output', type=Path, default=Path('build/render-evidence'))
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--views', nargs='+', choices=['forest', 'fire', 'overlook'], default=['forest', 'fire', 'overlook'])
    p.add_argument('--backend', choices=['vulkan', 'opengl'], default='vulkan')
    p.add_argument('--route', choices=['forest', 'mixed', 'combat'], default='mixed')
    p.add_argument('--stage-trace', action='store_true', help='attribute return tails to poll/resize/runtime and existing game CPU/GPU stages')
    p.add_argument('--frames', type=int, default=2400)
    p.add_argument('--present-modes', nargs='+', choices=['default','mailbox'], default=None)
    p.add_argument('--seconds', type=int, default=600)
    a = p.parse_args()
    if a.present_modes is None: a.present_modes = ['default'] if a.backend == 'opengl' else ['default', 'mailbox']
    if a.backend == 'opengl' and a.present_modes != ['default']:
        p.error('0.6 OpenGL Wayland uses frame callbacks; use --present-modes default')
    os.chdir(ROOT)
    out = a.output.resolve()
    assert out.is_relative_to(ROOT/'build'), 'scratch output must be under build/'
    assert 1 <= a.repeats <= 10 and 360 <= a.frames <= 12000
    assert 60 <= a.seconds <= 600 and a.seconds % 60 == 0
    out.mkdir(parents=True, exist_ok=True)
    exe = out/'game'
    started = time.monotonic()
    subprocess.run(['sloppy/bin/sloppy', 'build', 'tools/render_session.jo', '-o', str(exe)], check=True)
    compile_s = time.monotonic()-started
    result = {'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
              'host': list(os.uname()),
              'compile_s': compile_s, 'executable_sha256': digest(exe),
              'sources': {str(p): digest(p) for p in sorted(Path('game').glob('*.jo'))},
              'tools': {str(p): digest(p) for p in [Path('tools/render_session.jo'), Path(__file__)]},
              'runtime': {str(p): digest(p) for p in sorted(Path('sloppy/lib').rglob('*.jo'))},
              'protocol': 'Wayland backend comparison; 2133x1200 physical pixels; default dynamic scene scale; '
                          'steady probes use fixed 1/60 simulation dt, soak uses real production dt; '
                          'nearest-rank percentiles; present-call return timestamps, NOT compositor delivery; '
                          '240 warmup frames excluded only from pacing aggregate; per-minute soak includes all transitions',
              'runs': {}}
    trace = {'PROBE_STAGES': '1', 'BOTW_CPU': '1', 'BOTW_CPU_TRACE_MS': '8',
             'BOTW_CPU_RETURN_TRACE': '1', 'BOTW_DRAW_TRACE': '1', 'BOTW_GPU_FRAME_LOG': '1'} if a.stage_trace else {}
    trace['SLOPPY_VULKAN'] = '0' if a.backend == 'opengl' else '1'
    if a.backend == 'opengl': trace['SLOPPY_VSYNC'] = '0'
    result['backend'] = a.backend
    result['stage_tracing'] = a.stage_trace
    if a.mode == 'soak':
        for mode in a.present_modes:
            flags = {**trace, 'BOTW_AT': '-1140,1500,3.14' if a.route == 'forest' else ('-1030,1805,1.57' if a.route == 'combat' else '-1000,1620,3.14'), 'PROBE_ROUTE': a.route}
            if a.route in ('mixed','combat'): flags['BOTW_GIVE'] = 'travelers_sword,travelers_shield,warm_doublet'
            if mode == 'mailbox': flags['SLOPPY_VSYNC'] = '0'
            name = f'soak-{mode}'
            result['runs'][name] = run(exe, out, name, flags, seconds=a.seconds)
            from cpu_tail_bench import summarize
            result['runs'][name]['windows'] = summarize(out/(name+'.log'))['windows']
            windows = result['runs'][name]['windows']
            result['runs'][name]['window_count'] = len(windows)
            result['runs'][name]['windows_over_20ms'] = sum(w['interval']['p99'] > 20 for w in windows)
            result['runs'][name]['windows_over_17_5ms'] = sum(w['interval']['p99'] > 17.5 for w in windows)
            (out/'soak.json').write_text(json.dumps(result, indent=2)+'\n')
    else:
        views = {'forest': {'BOTW_AT': '-1000,1620,3.14'}, 'fire': {'BOTW_FIRE': '1'},
                 'overlook': {'BOTW_AT': '-1050,1828,-2.36'}}
        views = {view: flags for view, flags in views.items() if view in a.views}
        for repeat in range(1, a.repeats+1):
            for view, flags in views.items():
                for mode in (a.present_modes if repeat % 2 else list(reversed(a.present_modes))):
                    name = f'{view}-{mode}-{repeat}'
                    settings = {**trace, **flags, **({'SLOPPY_VSYNC': '0'} if mode == 'mailbox' else {})}
                    result['runs'][name] = run(exe, out, name, settings, frames=a.frames)
                    (out/'pacing.json').write_text(json.dumps(result, indent=2)+'\n')
        result['pooled'] = {}
        for view in views:
            for mode in a.present_modes:
                logs = [out/f'{view}-{mode}-{i}.log' for i in range(1, a.repeats+1)]
                rows = [[float(v) for v in l.split()[2:]] for log in logs
                        for l in log.read_text().splitlines() if l.startswith('present return:')]
                selected = [r for r in rows if r[0] >= 241]
                result['pooled'][f'{view}-{mode}'] = {'samples': len(selected),
                    **{name: metrics([r[col] for r in selected]) for name, col in
                       [('present_return_interval', 2), ('present_call', 3), ('callback_wall', 4), ('callback_thread', 5)]}}
    (out/(a.mode+'.json')).write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
