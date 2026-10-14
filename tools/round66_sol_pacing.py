#!/usr/bin/env python3
"""Matched WSI comparison; one two-minute render lock per run, never nested.

prepare freezes the current game probe. compare alternates Wayland/X11 in both
Vulkan modes (optionally repeat the matrix). session keeps one game alive for ten
active minutes, pausing and yielding the render lock every two minutes so other
workers can use the shared GPU. report retains every post-warmup tail.
Use --output build/<fresh-name> to preserve an earlier executable/protocol.
"""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import time

import subprocess

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/round66-sol'


def prepare(name="pacing"):
    source = (ROOT / 'tools/render_session.jo').read_text()
    source = re.sub(r"'../game/([^']+)'", lambda m: repr(str(ROOT / 'game' / m[1])), source)
    source += f"\nfrom '{ROOT}/game/main.jo' import __loop_last, __ft_last\nfrom '{ROOT}/game/frametime.jo' import __frame_last\n"
    output = (ROOT / 'tools/performance_output.jo').read_text()
    source = output[output.index('@lib'):output.index('__perf_resizes =')] + source
    source = source.replace('assert(__wayland and not __soft)', 'assert(not __soft)')
    source = source.replace('        now = time()\n        dt =', '''        if not __wayland:
            root: int = 0
            x: i32 = 0
            y: i32 = 0
            w: u32 = 0
            h: u32 = 0
            border: u32 = 0
            depth: u32 = 0
            assert(__perf_geometry(__xdpy, __xwin, &root, &x, &y, &w, &h, &border, &depth) != 0)
            __win_w = int(w)
            __win_h = int(h)
        now = time()
        dt =''')
    source = source.replace('        n = frame_number()-1', '        n = frame_number()-1\n        if n == 0:\n            probe_start = done\n            eprint("probe active start: {probe_start:.9}")')
    source = source.replace('    minute = 0', '    minute = 0\n    yield_interval = clamp(to_float(env("PROBE_YIELD_INTERVAL") ?? "120") ?? 120.0, 1.0, 120.0)\n    checkpoint = yield_interval')
    source = source.replace('        if finished:', '        if probe_soak and not finished and env("PROBE_SHARED_YIELD") != none and done-probe_start >= checkpoint:\n            if __vk: vkDeviceWaitIdle(__vk_dev)\n            else: glFinish()\n            eprint(lines)\n            lines = ""\n            eprint("probe yield: pid={syscall(39)} active_s={done-probe_start:.6}")\n            paused = time()\n            syscall(62, syscall(39), 19)\n            pause = time()-paused\n            probe_start += pause\n            __time0 += pause\n            if __loop_last > 0.0: __loop_last += pause\n            if __ft_last > 0.0: __ft_last += pause\n            if __frame_last > 0.0: __frame_last += pause\n            last += pause\n            returned += pause\n            checkpoint += yield_interval\n        if finished:')
    (OUT / (name+'.jo')).write_text(source)
    subprocess.run(['sloppy/bin/sloppy', 'build', str(OUT / (name+'.jo')), '-o', str(OUT / name)], check=True)
    (OUT / (name+'-sources.json')).write_text(json.dumps({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / 'game').glob('*.jo'))}, indent=2) + '\n')


def metrics(values):
    a = sorted(values)
    return {key: a[max(0, math.ceil(len(a)*q)-1)] for key, q in [('p50', .5), ('p99', .99), ('worst', 1)]}


def report():
    result = {'protocol': 'Real-dt forest waypoint route, seed 64, clear, hour 11, scale recorded per run, '
        'Comparisons use 2133x1200 physical output; the continuous default session uses the normal managed window and production dynamic scale. First 4 seconds retained separately as warmup. '
        'Producer present-return intervals, not scanout. Each comparison holds the shared lock at most 150 seconds. The continuous session yields at PROBE_YIELD_INTERVAL (normally 120 active seconds); all resumed intervals are retained.',
        'runs': {}}
    for meta_path in sorted(OUT.glob('pacing-*.environment.json')):
        meta = json.loads(meta_path.read_text())
        log = meta_path.with_name(meta_path.name.replace('.environment.json', '.log'))
        if not log.exists() or 'probe complete:' not in log.read_text():
            continue
        text = log.read_text()
        rows = [[float(v) for v in line.split()[2:]] for line in text.splitlines() if line.startswith('present return:')]
        dimensions = {(int(r[6]), int(r[7])) for r in rows if r[1] >= 4}
        assert len(dimensions) == 1, 'output resized during measurement'
        actual_size = next(iter(dimensions))
        if not meta['name'].startswith('default-'): assert actual_size == (2133, 1200), log
        with Image.open(log.with_suffix('.png')) as capture:
            assert capture.size == actual_size, 'capture/client output mismatch'
            capture.verify()
        meta['window_protocol'] = ('managed fixed-size dialog' if 'visible managed X11 client' in text else ('override-redirect visible' if 'visible X11 client' in text else ('normal managed launcher' if meta['name'].startswith('default-') else 'native Wayland')))
        selected = [r for r in rows if r[1] >= 4]
        tails = [dict(frame=int(r[0]), elapsed_s=r[1], interval_ms=r[2], present_ms=r[3],
                      callback_wall_ms=r[4], callback_thread_ms=r[5]) for r in selected if r[2] > 25]
        stages = {}
        for line in text.splitlines():
            if line.startswith('return stages:'):
                frame = int(re.search(r'frame (\d+)', line)[1])
                stages[frame] = {k: float(v) for k, v in re.findall(r'([a-z_]+) ([\d.]+)(?:/[\d.]+)?', line) if k not in ['frame', 'interval']}
        for tail in tails:
            tail['stages_ms'] = stages.get(tail['frame'], {})
            tail['dominant_stage'] = max(tail['stages_ms'], key=tail['stages_ms'].get) if tail['stages_ms'] else 'untraced'
        run = dict(meta, physical_output=list(actual_size), elapsed_s=rows[-1][1], samples=len(selected),
                   all_samples=len(rows), warmup_worst_ms=max((r[2] for r in rows if r[1] < 4), default=None),
                   over_25ms=len(tails), all_frames_over_25ms=sum(r[2] > 25 for r in rows),
                   all_interval_ms=metrics([r[2] for r in rows if r[0] > 0]), tails=tails,
                   timings={name: metrics([r[col] for r in selected]) for name, col in
                     [('interval_ms', 2), ('present_ms', 3), ('cpu_wall_ms', 4), ('cpu_thread_ms', 5)]},
                   actual_present_mode=int(re.search(r'probe swapchain: (\d+)', text)[1]),
                   log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
                   waypoints=re.findall(r'^forest waypoint:.*$', text, re.M))
        result['runs'][meta['name']] = run
    (OUT / 'pacing-summary.json').write_text(json.dumps(result, indent=2) + '\n')
    for name, run in result['runs'].items():
        print(name, run['timings']['interval_ms'], 'over25', run['over_25ms'], flush=True)


def run(name, platform, vsync, seconds, scale):
    path = OUT / ('pacing-' + name)
    if Path(str(path)+'.log').exists() and 'probe complete:' in Path(str(path)+'.log').read_text():
        retained = json.loads(Path(str(path)+'.environment.json').read_text())
        assert retained['flags']['PROBE_SECONDS'] == str(seconds), 'retained duration differs; use fresh evidence'
        assert retained['binary_sha256'] == hashlib.sha256((OUT / 'pacing').read_bytes()).hexdigest(), 'retained run belongs to a different executable; preserve it and use fresh evidence'
        print('retained completed run', name, flush=True)
        return
    e = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'PROBE_'))}
    e.update(BOTW_SKIP='1', BOTW_AT='-1140,1500,3.14', BOTW_HOUR='11', BOTW_WEATHER='clear',
             BOTW_SCALE='1', BOTW_FRAME_LOG='1', BOTW_CPU='1', BOTW_CPU_TRACE_MS='12',
             SLOPPY_FRAME_STATS='1', SLOPPY_VULKAN='1', SLOPPY_VSYNC=str(vsync),
             SLOPPY_PLATFORM=platform, SLOPPY_WINDOW='1280x720' if platform == 'wayland' else '2133x1200',
             PROBE_SECONDS=str(seconds), PROBE_ROUTE='forest', PROBE_STAGES='1', PROBE_PNG=str(path)+'.png')
    if scale == 'dynamic': e.pop('BOTW_SCALE')
    if name.startswith('default-'):
        e.pop('SLOPPY_PLATFORM')
        e.pop('BOTW_SCALE')
    meta = {'name': name, 'platform': platform, 'mode': 'fifo' if vsync else 'fast (mailbox preference, immediate fallback)',
            'scene_scale': scale,
            'binary_sha256': hashlib.sha256((OUT / 'pacing').read_bytes()).hexdigest(),
            'flags': {k: v for k, v in e.items() if k.startswith(('BOTW_', 'SLOPPY_', 'PROBE_'))}}
    Path(str(path)+'.environment.json').write_text(json.dumps(meta, indent=2)+'\n')
    command = ['timeout', '-k', '5', str(seconds+30), str(OUT / 'pacing')]
    if platform == 'x11': command = ['python3', 'tools/performance_window.py', '--visible', '2133x1200', *command]
    if name.startswith('default-'):
        # Exercise launcher selection; the X11 helper only manages exact size.
        command = ['tools/play.sh', *command]
    with Path(str(path)+'.log').open('w') as log:
        subprocess.run(['flock', '/tmp/botw-render.lock', *command], env=e, stdout=log, stderr=subprocess.STDOUT, check=True)
    report()


def shared_session(trace=False, seconds=600, interval=120):
    assert isinstance(seconds, int) and isinstance(interval, int) and seconds > interval > 0 and interval <= 120
    # The descriptor-mode flock command and this parent share one open file description.
    # Freeze the entire child process group before releasing it; reacquire via
    # flock before SIGCONT. The probe subtracts only those paused durations.
    name = 'default-traced' if trace else 'default-continuous'
    prefix = OUT / ('pacing-'+name)
    e = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'PROBE_'))}
    e.update(BOTW_SKIP='1', BOTW_AT='-1140,1500,3.14', BOTW_HOUR='11', BOTW_WEATHER='clear',
             BOTW_FRAME_LOG='1', BOTW_CPU='1', BOTW_CPU_TRACE_MS='12', BOTW_CPU_RETURN_TRACE='1',
             SLOPPY_FRAME_STATS='1',
             PROBE_SECONDS=str(seconds), PROBE_YIELD_INTERVAL=str(interval), PROBE_ROUTE='forest', PROBE_STAGES='1',
             PROBE_SHARED_YIELD='1', PROBE_PNG=str(prefix)+'.png')
    if not trace:
        for option in ['BOTW_CPU', 'BOTW_CPU_TRACE_MS', 'BOTW_CPU_RETURN_TRACE', 'BOTW_FRAME_LOG']: e.pop(option, None)
    metadata = {'name': name, 'platform': 'launcher-default', 'mode': 'fast preference',
                'instrumentation': 'full CPU traces' if trace else 'lightweight producer-return timing; no game profiler',
                'binary_sha256': hashlib.sha256((OUT / 'session').read_bytes()).hexdigest(),
                'flags': {k: v for k, v in e.items() if k.startswith(('BOTW_', 'SLOPPY_', 'PROBE_'))},
                'session': f'One persistent real-dt game, {seconds} active seconds; SIGSTOP yields every {interval} seconds. Active time excludes only the paused periods.'}
    Path(str(prefix)+'.environment.json').write_text(json.dumps(metadata, indent=2)+'\n')
    descriptor = os.open('/tmp/botw-render.lock', os.O_RDWR | os.O_CREAT, 0o600)
    try:
        with Path(str(prefix)+'.log').open('w') as log, Path(str(prefix)+'.log').open('r') as observed:
            command = ['bash', '-c', 'flock "$1" || exit; shift; exec "$@"',
                       'shared-render-session', str(descriptor), 'tools/play.sh', str(OUT / 'session')]
            process = subprocess.Popen(command, env=e, stdout=log, stderr=subprocess.STDOUT,
                                       pass_fds=(descriptor,), start_new_session=True)
            handled = 0
            markers = []
            pending = ''
            deadline = time.monotonic()+7200
            try:
                while process.poll() is None:
                    if time.monotonic() > deadline: raise TimeoutError('session exceeded two-hour shared-desktop bound')
                    pending += observed.read()
                    if '\n' in pending:
                        complete, pending = pending.rsplit('\n', 1)
                        markers.extend(re.findall(r'probe yield: pid=(\d+) active_s=([\d.]+)', complete))
                    if len(markers) > handled:
                        pid = int(markers[handled][0])
                        # A flushed marker precedes SIGSTOP by a few microseconds.
                        state = Path(f'/proc/{pid}/status').read_text()
                        if re.search(r'^State:\s+T', state, re.M):
                            os.killpg(process.pid, signal.SIGSTOP)
                            fcntl.flock(descriptor, fcntl.LOCK_UN)
                            print('yielding render lock at active seconds', markers[handled][1], flush=True)
                            # Give already queued renderers a chance to acquire first.
                            time.sleep(.05)
                            subprocess.run(['flock', str(descriptor)], pass_fds=(descriptor,), check=True)
                            os.killpg(process.pid, signal.SIGCONT)
                            handled += 1
                    time.sleep(.2)
                assert process.wait() == 0, 'continuous session failed'
                expected = (seconds-1)//interval
                assert handled == expected, f'expected {expected} render-lock yields, got {handled}'
            finally:
                if process.poll() is None:
                    # A stopped renderer must never resume during unlocked error cleanup.
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
    finally:
        os.close(descriptor)
    report()


def main():
    global OUT
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare', 'compare', 'session', 'report'])
    p.add_argument('--seconds', type=int, default=120)
    p.add_argument('--repeats', type=int, choices=[1, 2], default=1)
    p.add_argument('--scale', choices=['1', 'dynamic'], default='dynamic')
    p.add_argument('--trace', action='store_true', help='full CPU traces for a separate diagnostic session')
    p.add_argument('--output', type=Path, default=OUT, help='fresh evidence directory under build/')
    a = p.parse_args()
    assert 120 <= a.seconds <= 150
    os.chdir(ROOT)
    OUT = a.output.resolve()
    assert OUT.is_relative_to(ROOT / 'build') and OUT != ROOT / 'build', 'evidence must stay under build/'
    OUT.mkdir(parents=True, exist_ok=True)
    if a.action == 'prepare': prepare()
    elif a.action == 'compare':
        for repeat in range(1, a.repeats+1):
            for vsync in [0, 1]:
                for platform in ['wayland', 'x11']:
                    run(f'{platform}-{"fifo" if vsync else "mailbox"}-{repeat}' + ('-dynamic' if a.scale == 'dynamic' else ''), platform, vsync, a.seconds, a.scale)
        report()
    elif a.action == 'session':
        prepare('session')
        shared_session(a.trace)
    else: report()


if __name__ == '__main__': main()
