#!/usr/bin/env python3
"""Summarize matched pacing runs and retain EVERY >20 ms interval with attribution.

Read-only: no game render or lock. Sources are return-stage/draw/resource traces
and optional LD_AUDIT Vulkan call boundaries. Missing historical instrumentation
is explicit; native waits are never inferred from pipeline-cache hit status.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True
from render_evidence import analyze, metrics
from cpu_tail_bench import summarize


def report(path):
    text = path.read_text()
    rows = [[float(v) for v in line.split()[2:]] for line in text.splitlines()
            if line.startswith('present return:')]
    result = analyze(path, soak='session minute:' in text)
    if rows[-1][1] >= 60:
        result.update({k: v for k, v in summarize(path).items()
                       if k in ['windows', 'window_count', 'windows_over_20ms', 'windows_over_17_5ms']})
        windows = result['windows']
        result['window_count'] = len(windows)
        result['windows_over_20ms'] = sum(w['interval']['p99'] > 20 for w in windows)
        result['windows_over_17_5ms'] = sum(w['interval']['p99'] > 17.5 for w in windows)
    stages, cpu, resources = {}, {}, {}
    draws = defaultdict(list)
    native = []
    origin = re.search(r'^probe monotonic start: ([\d.]+)$', text, re.M)
    for line in text.splitlines():
        if line.startswith('return stages:'):
            n = int(re.search(r'frame (\d+)', line)[1])
            stages[n] = {k: {'wall_ms': float(w), 'thread_ms': float(t) if t else None}
                         for k, w, t in re.findall(r'([a-z_]+) ([\d.]+)(?:/([\d.]+))?', line)
                         if k not in ['frame', 'interval']}
        elif line.startswith('tail cpu:') or line.startswith('long cpu '):
            n = int(re.search(r'(?:; )?frame (\d+)', line)[1])
            entries = defaultdict(lambda: [0, 0])
            for k, w, t in re.findall(r'([\w-]+) ([\d.]+)/([\d.]+)', line):
                entries[k][0] += float(w)
                entries[k][1] += float(t)
            cpu[n] = dict(entries)
        elif line.startswith('draw trace:'):
            m = re.search(r'frame (\d+) program (\d+) mode (\d+) ms ([\d.]+) pipelines (\d+)', line)
            draws[int(m[1])].append(dict(program=int(m[2]), mode=int(m[3]), wall_ms=float(m[4]), pipelines=int(m[5])))
        elif line.startswith('resource trace:'):
            n = int(re.search(r'frame (\d+)', line)[1])-1
            resources[n] = {k: int(v) for k, v in re.findall(r'(images|buffers|pipelines|blocks|slots|swapchain) (\d+)', line)}
        elif line.startswith('vk call:'):
            assert origin, 'native calls require the probe monotonic origin'
            m = re.search(r'vk call: (\w+) ([\d.]+) ([\d.]+) ([\d.]+) result (-?\d+)', line)
            native.append(dict(call=m[1], start_s=float(m[2])-float(origin[1]),
                               end_s=float(m[3])-float(origin[1]), wall_ms=float(m[4]), result=int(m[5])))
    by_frame = defaultdict(list)
    i = 1
    for event in sorted(native, key=lambda e: e['end_s']):
        while i < len(rows) and rows[i][1] < event['end_s']: i += 1
        if i < len(rows) and rows[i-1][1] <= event['start_s']:
            by_frame[int(rows[i][0])].append(event)
    result['native_trace'] = bool(native)
    result['native_calls_in_play'] = dict(Counter(e['call'] for events in by_frame.values() for e in events))
    result['pipeline_first_uses_in_play'] = {str(n): d for n, d in draws.items() if n > 0 and any(e['pipelines'] for e in d)}
    result['resource_changes_in_play'] = {str(n): r for n, r in resources.items() if n > 0}
    evidence = []
    previous_resource = None
    for row in rows:
        n = int(row[0])
        resource = resources.get(n)
        delta = {k: resource[k]-previous_resource[k] for k in resource} if resource and previous_resource else {}
        if resource: previous_resource = resource
        if row[2] <= 20: continue
        stage = stages.get(n, {})
        dominant = max(stage, key=lambda k: stage[k]['wall_ms']) if stage else ('present' if row[3] > row[4] else 'callback')
        calls = by_frame[n]
        pipeline_ms = sum(e['wall_ms'] for e in draws[n] if e['pipelines'])
        waits = [e for e in calls if e['call'] in ['vkWaitForFences', 'vkAcquireNextImageKHR', 'vkQueuePresentKHR', 'vkDeviceWaitIdle']]
        if pipeline_ms and row[2]-pipeline_ms <= 20:
            category = 'pipeline first use'
        elif any(e['call'] == 'vkQueueSubmit2' and e['wall_ms'] > row[2]*.4 for e in calls):
            category = 'native submission: vkQueueSubmit2'
        elif waits and (max(e['wall_ms'] for e in waits) > row[2]*.4 or sum(e['wall_ms'] for e in waits) > row[2]*.5):
            category = 'native wait: '+max(waits, key=lambda e: e['wall_ms'])['call']
        elif dominant == 'callback':
            parts = cpu.get(n, {})
            part = max(parts, key=lambda k: parts[k][0]) if parts else 'untraced'
            category = ('CPU callback: ' if row[5] >= row[4]*.65 else 'callback wait: ')+part
        else:
            category = dominant
        evidence.append(dict(frame=n, elapsed_s=row[1], interval_ms=row[2], present_ms=row[3],
                             callback_wall_ms=row[4], callback_thread_ms=row[5], attribution=category,
                             stages=stage, cpu_stages=cpu.get(n, {}), draws=draws[n],
                             resource_change=delta, native_calls=calls))
    if stages: assert all(e['stages'] for e in evidence), 'not every >20 ms interval has a stage trace'
    result['all_intervals_over_20ms'] = evidence
    result['attribution_counts'] = dict(Counter(e['attribution'] for e in evidence))
    result['stage_coverage'] = f'{sum(bool(e["stages"]) for e in evidence)}/{len(evidence)}'
    result['historical_limit'] = None if stages else 'This log predates stage/draw/resource tracing; callback versus present is observable, precise native/first-use causes cannot be recovered retrospectively.'
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('logs', nargs='+', type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    data = {'protocol': 'All >20 ms producer-return intervals retained, including initial window transitions. Native call boundaries are monotonic CPU wall times, not GPU completion times. Descriptor array capacity is fixed at 16384 in 0.6; slot high-water is not descriptor-array reallocation. Diagnostic runs are not used as uninstrumented percentile comparisons.',
            'runs': {str(path): report(path) for path in a.logs}}
    raw = (json.dumps(data, indent=2)+'\n').encode()
    if a.output.suffix == '.gz':
        with gzip.GzipFile(filename=a.output, mode='wb', mtime=0) as f: f.write(raw)
    else: a.output.write_bytes(raw)
    for name, r in data['runs'].items():
        print(name, r['timing_ms']['present_return_interval'],
              r.get('windows_over_20ms'), r.get('window_count'), r['attribution_counts'], r['stage_coverage'])


if __name__ == '__main__': main()
