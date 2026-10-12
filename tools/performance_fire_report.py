#!/usr/bin/env python3
"""Summarize matched fire/default-scale captures without committing raw evidence.

Run after performance_bench.py captures: ROOT/{before,after}/{fire720,firelarge,
default720,defaultlarge}. Raw rows, images and traces remain under ignored build/.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from performance_bench import percentile, read_run


def stats(values):
    return {name: fn(values) for name, fn in [
        ('p50', lambda v: percentile(v, .5)),
        ('p99', lambda v: percentile(v, .99)), ('worst', max)]}


def load(path):
    result = read_run(path)
    text = path.read_text()
    rows = [[float(x) for x in line.split()[2:]] for line in text.splitlines()
            if line.startswith('frame sample:')]
    assert [int(r[0]) for r in rows] == list(range(1, len(rows) + 1))
    traces = {}
    queue_waits = {}
    for line in text.splitlines():
        if not line.startswith('long cpu '):
            continue
        frame = int(re.search(r'; frame (\d+)', line)[1])
        traces[frame] = [(s, float(w), float(t)) for s, w, t in
                         re.findall(r'([\w-]+) ([\d.]+)/([\d.]+)', line)]
        queue = re.search(r'queue_wait_ms=([\d.]+)', line)
        if queue:
            queue_waits[frame] = float(queue[1])
    gpu = {int(f): float(total) for f, total in
           re.findall(r'^gpu frame: (\d+) .* = ([\d.]+)$', text, re.M)}
    steady = [r for r in rows if r[0] >= 241]
    tail = [r for r in steady if r[2] > 8]
    wall, thread = Counter(), Counter()
    wall_dominant, thread_dominant = Counter(), Counter()
    missing = []
    for row in tail:
        frame = int(row[0]) - 1
        trace = traces.get(frame)
        if trace is None:
            missing.append(frame)
            continue
        wall_dominant[max(trace, key=lambda x: x[1])[0]] += 1
        thread_dominant[max(trace, key=lambda x: x[2])[0]] += 1
        for name, w, t in trace:
            wall[name] += w
            thread[name] += t
    summary = {
        'executable_sha256': result['metadata']['executable_sha256'],
        'flags': result['metadata']['flags'], 'output': result['output'],
        'load_seconds': result['load_seconds'], 'steady_samples': len(steady),
        'interval': stats([r[1] for r in steady]),
        'cpu_wall': stats([r[2] for r in steady]),
        'cpu_thread': stats([r[4] for r in steady]),
        # Quiet untraced rows retain their entire wall time, so this is a
        # conservative bound, never a favourable estimate of an unknown wait.
        'cpu_work_wall_upper_bound': stats([max(0, r[2] - queue_waits.get(int(r[0]) - 1, 0))
                                           for r in steady]) if queue_waits else None,
        'queue_wait_frames_measured': len(queue_waits),
        'gpu': stats([v for n, v in gpu.items() if n >= 240]) if gpu else None,
        'gpu_samples': sum(n >= 240 for n in gpu),
        'settled_interval': stats([r[1] for r in rows if r[0] >= 601]),
        'cpu_over_8_ms': len(tail), 'untraced_over_8_frames': missing,
        'tail_dominant_wall': dict(wall_dominant),
        'tail_dominant_thread': dict(thread_dominant),
        'tail_stage_wall_ms': dict(wall.most_common()),
        'tail_stage_thread_ms': dict(thread.most_common()),
        'scale_batches': re.findall(r'^frame percentiles:.*$', text, re.M),
        'scale_events': re.findall(r'^scale controller:.*$', text, re.M),
        'particles': re.findall(r'^fx particles:.*$', text, re.M),
        'load_start': result['load_start'],
        'load_end': result['metadata'].get('load_end', 'unavailable: capture parent stopped after complete child output'),
        'png_sha256': hashlib.sha256(path.with_suffix('.png').read_bytes()).hexdigest(),
    }
    work_rows = [(int(r[0]), max(0, r[2] - queue_waits.get(int(r[0]) - 1, 0)))
                 for r in rows]
    return summary, rows, gpu, work_rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--phases', nargs='+', default=['before', 'after'])
    args = ap.parse_args()
    report = {'base_revision': '35eaa76',
              'protocol': 'round65-fire-default-v1; X11 client GPU; native Wayland delivery/diagnostics; fixed 1/60 simulation; '
                          'three repeats; warm caches; nearest-rank pooled frames 241 onward; '
                          'settled comparison frames 601 onward; no outliers removed',
              'cpu_accounting': 'wall includes GPU fence waits; thread measures main-thread '
                                'execution; neither includes runtime audio/submit/present gap',
              'phases': {}}
    for phase in args.phases:
        groups = {}
        for directory in sorted((args.root / phase).iterdir()):
            if not directory.is_dir() or directory.name not in {
                    'fire720', 'firelarge', 'default720', 'defaultlarge', 'pacedlarge', 'deliverylarge'}:
                continue
            runs, pooled = {}, {}
            samples, gpu_samples, work_samples = {}, {}, {}
            for path in sorted(directory.glob('*.log')):
                if not path.with_suffix('.environment.json').exists():
                    continue
                summary, rows, gpu, work = load(path)
                runs[path.stem] = summary
                view = re.split(r'-(?:gpu|paced|mailbox)-', path.stem)[0]
                samples.setdefault(view, []).extend(rows)
                gpu_samples.setdefault(view, []).extend(gpu.items())
                work_samples.setdefault(view, []).extend(work)
            if not runs:
                continue
            for view, rows in samples.items():
                steady = [r for r in rows if r[0] >= 241]
                assert len([n for n in runs if re.split(r'-(?:gpu|paced|mailbox)-', n)[0] == view]) == 3
                pooled[view] = {label: stats([r[col] for r in steady]) for label, col in
                                [('interval', 1), ('cpu_wall', 2), ('cpu_thread', 4)]}
                pooled[view]['gpu'] = stats([v for n, v in gpu_samples[view] if n >= 240]) if gpu_samples[view] else None
                pooled[view]['samples'] = len(steady)
                pooled[view]['gpu_samples'] = sum(n >= 240 for n, v in gpu_samples[view])
                pooled[view]['cpu_work_wall_upper_bound'] = stats([v for n, v in work_samples[view] if n >= 241])
                pooled[view]['settled_interval'] = stats([r[1] for r in rows if r[0] >= 601])
                pooled[view]['settled'] = {label: stats([r[col] for r in rows if r[0] >= 601])
                                          for label, col in [('interval', 1), ('cpu_wall', 2), ('cpu_thread', 4)]}
                pooled[view]['settled']['gpu'] = stats([v for n, v in gpu_samples[view] if n >= 600]) if gpu_samples[view] else None
            groups[directory.name] = {'runs': runs, 'pooled': pooled}
        report['phases'][phase] = groups
    first, last = args.phases[0], args.phases[-1]
    for group in ['fire720', 'firelarge']:
        before = report['phases'][first][group]['runs']
        after = report['phases'][last][group]['runs']
        assert before.keys() == after.keys()
        for name in before:
            flags = lambda r: {k: v for k, v in r['flags'].items() if k != 'SLOPPY_SCREENSHOT'}
            assert flags(before[name]) == flags(after[name])
            assert before[name]['png_sha256'] == after[name]['png_sha256'], f'changed fire image: {group}/{name}'
            assert before[name]['particles'] == after[name]['particles'], f'changed fire particle counts: {group}/{name}'
            after[name]['paired_png_equal'] = True
            after[name]['paired_particles_equal'] = True
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    for phase, groups in report['phases'].items():
        for group, data in groups.items():
            for view, metrics in data['pooled'].items():
                print(phase, group, view, metrics)


if __name__ == '__main__':
    main()
