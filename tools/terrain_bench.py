#!/usr/bin/env python3
"""Locked fixed-scale terrain/camera captures and frame-tail attribution.

Capture a prebuilt executable (preserve it before edits):
  tools/terrain_bench.py capture build/game-before build/perf/before
  tools/terrain_bench.py capture build/game-after build/perf/after
Compare: tools/terrain_bench.py compare build/perf/before build/perf/after
GPU/CPU modes use uncapped X11. Paced mode reports the actual Wayland size.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess

CASES = {
    'fire': {'BOTW_FIRE': '1'},
    'snow': {'BOTW_AT': '-1060,2230,2.0'},
    'camp': {'BOTW_AT': '-1439,1606,0'},
    'pond': {'BOTW_AT': '-1190,1665,-0.9'},
    'overlook': {'BOTW_AT': '-1050,1828,-2.36'},
    'climb': {'BOTW_TOWER': '1', 'BOTW_AT': '-560,1722,0',
              'SLOPPY_INPUT': '5:w+', 'BOTW_CAMDBG': '1'},
    'fire300': {'BOTW_FIRE': '1'},
}


def percentile(values, p):
    return sorted(values)[max(0, math.ceil(len(values) * p) - 1)]


def read_log(path):
    text = path.read_text()
    rows = [[float(x) for x in line.split()[2:]] for line in text.splitlines()
            if line.startswith('frame sample:')]
    rows = [r for r in rows if r[0] >= 241]
    if path.stem.endswith(('-gpu', '-cpu')):
        if ('frame cpu:' in text and 'egl window surface' not in text) or 'BOTW_NOVSYNC:' in text:
            raise ValueError(f'{path}: uncapped X11 presentation was not confirmed')
    gpu = []
    for passes, total in re.findall(r'^gpu ms:(.*?)= ([\d.]+)$', text, re.M):
        batch = {k: float(v) for k, v in re.findall(r'(\S+) ([\d.]+)', passes)}
        batch['total'] = float(total)
        gpu.append(batch)
    if any(scale != '0.80' for _, scale in re.findall(r'; (\d+x\d+) scale ([\d.]+)', text)):
        raise ValueError(f'{path}: variable render scale')
    # First batch is startup. Retain all later batches; report their median.
    steady = gpu[1:] or gpu
    result = {'backend_log_confirmed': 'egl window surface' in text, 'gpu_batches': gpu, 'gpu_median': {
        k: statistics.median(b[k] for b in steady) for k in steady[0]
    } if steady else {}, 'resolution': re.findall(r'; (\d+x\d+) scale ([\d.]+)', text),
        'cpu_profiles': re.findall(r'^cpu avg ms:.*$', text, re.M),
        'long_cpu': re.findall(r'^long cpu.*$', text, re.M),
        'load': text.splitlines()[:8]}
    if rows:
        values = [r[1] for r in rows]
        result.update(samples=len(rows), mean=statistics.mean(values),
                      p50=percentile(values, .5), p95=percentile(values, .95),
                      p99=percentile(values, .99), worst=max(values),
                      cpu_mean=statistics.mean(r[2] for r in rows),
                      thread_mean=statistics.mean(r[4] for r in rows),
                      slow_intervals=sorted(rows, key=lambda r: -r[1])[:8],
                      slow_cpu=sorted(rows, key=lambda r: -r[2])[:8])
        # Columns preserve frametime.jo's historical order.
        result['columns'] = ['frame', 'interval_ms', 'game_wall_ms', 'gap_ms',
                             'game_thread_ms', 'uploads', 'upload_bytes',
                             'game_voluntary', 'game_involuntary', 'game_user_ms',
                             'game_system_ms', 'present_ms', 'gap_minus_present_ms',
                             'gap_thread_ms', 'gap_voluntary', 'gap_involuntary',
                             'gap_user_ms', 'gap_system_ms'][:len(rows[0])]
    return result


def capture(args):
    args.output.mkdir(parents=True, exist_ok=True)
    executable = args.executable.resolve()
    for name in args.views:
        modes = args.modes if name in ['camp', 'pond'] else ['gpu']
        for mode in modes:
            prefix = args.output / f'{name}-{mode}'
            env = {k: v for k, v in os.environ.items()
                   if not k.startswith(('BOTW_', 'SLOPPY_'))}
            env.update(BOTW_SKIP='1', BOTW_SCALE='0.8', BOTW_FRAME_LOG='1',
                       BOTW_LOADTIME='1', SLOPPY_WINDOW='2133x1200',
                       SLOPPY_FRAMES=str(300 if name == 'fire300' else args.frames),
                       SLOPPY_FRAME_STATS='1',
                       SLOPPY_SCREENSHOT=str(prefix.with_suffix('.png')))
            if mode == 'paced':
                # Wayland applies output scaling to the requested logical size.
                # Use the game's normal window rather than a giant scaled benchmark window.
                env.pop('SLOPPY_WINDOW')
            if mode != 'paced':
                env.update(BOTW_NOVSYNC='1', SLOPPY_PLATFORM='x11')
            if mode == 'gpu':
                env['BOTW_GPU'] = '1'
            if mode == 'cpu' or mode == 'paced':
                env['BOTW_CPU'] = '1'
            env.update(CASES[name])
            prefix.with_suffix('.environment.json').write_text(json.dumps({
                'executable': str(executable),
                'flags': {k: v for k, v in env.items() if k.startswith(('BOTW_', 'SLOPPY_'))},
            }, indent=2) + '\n')
            print(name, mode, flush=True)
            prefix.with_suffix('.load-start').write_text(Path('/proc/loadavg').read_text())
            with prefix.with_suffix('.log').open('w') as log:
                subprocess.run(['flock', '/tmp/botw-render.lock', 'timeout', '300',
                                str(executable)], env=env, stdout=log,
                               stderr=subprocess.STDOUT, check=True)
            prefix.with_suffix('.load-end').write_text(Path('/proc/loadavg').read_text())


def image_diff(before, after):
    from PIL import Image, ImageChops, ImageStat
    a, b = [Image.open(p).convert('RGB') for p in [before, after]]
    if a.size != b.size:
        return {'error': 'different dimensions', 'before': a.size, 'after': b.size}
    d = ImageChops.difference(a, b)
    h = d.histogram()
    counts = [h[i] + h[256+i] + h[512+i] for i in range(256)]
    cumulative = 0
    p99 = 0
    for i, count in enumerate(counts):
        cumulative += count
        if cumulative >= a.width * a.height * 3 * .99:
            p99 = i
            break
    return {'size': a.size, 'rgb_mae': sum(ImageStat.Stat(d).mean)/3,
            'rgb_mae_percent': sum(ImageStat.Stat(d).mean)/3/255*100,
            'channel_max': max(hi for lo, hi in d.getextrema()), 'channel_p99': p99,
            'channels_changed_percent': (1-counts[0]/(a.width*a.height*3))*100,
            'channels_over_8_percent': sum(counts[9:])/(a.width*a.height*3)*100,
            'before': str(before.resolve()), 'after': str(after.resolve())}


def compare(args):
    report = {'before': {}, 'after': {}, 'images': {}}
    for phase in ['before', 'after']:
        root = getattr(args, phase)
        for path in sorted(root.glob('*.log')):
            if 'frame sample:' in path.read_text():
                report[phase][path.stem] = read_log(path)
    for before in sorted(args.before.glob('*.png')):
        after = args.after / before.name
        if after.exists():
            report['images'][before.stem] = image_diff(before, after)
    target = args.after.parent / 'comparison.json'
    target.write_text(json.dumps(report, indent=2) + '\n')
    for name, b in report['before'].items():
        a = report['after'].get(name)
        if not a:
            continue
        if b['gpu_median'] and a['gpu_median']:
            print(f"{name}: terrain {b['gpu_median']['terrain']:.2f} -> "
                  f"{a['gpu_median']['terrain']:.2f}; total "
                  f"{b['gpu_median']['total']:.2f} -> {a['gpu_median']['total']:.2f} ms")
        if 'p99' in b and 'p99' in a:
            print(f"  interval p99 {b['p99']:.3f} -> {a['p99']:.3f}; "
                  f"worst {b['worst']:.3f} -> {a['worst']:.3f} ms")
    print(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    cap = sub.add_parser('capture')
    cap.add_argument('executable', type=Path)
    cap.add_argument('output', type=Path)
    cap.add_argument('--views', nargs='+', choices=CASES, default=list(CASES))
    cap.add_argument('--modes', nargs='+', choices=['gpu', 'cpu', 'paced'],
                     default=['gpu', 'cpu', 'paced'])
    cap.add_argument('--frames', type=int, default=720)
    comp = sub.add_parser('compare')
    comp.add_argument('before', type=Path)
    comp.add_argument('after', type=Path)
    args = parser.parse_args()
    (capture if args.command == 'capture' else compare)(args)


if __name__ == '__main__':
    main()
