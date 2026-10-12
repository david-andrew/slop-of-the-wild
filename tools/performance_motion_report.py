#!/usr/bin/env python3
"""Retain all matched forest/steady/Talus runs, raw samples, and CPU tail attribution.

Usage: performance_motion_report.py build/perf-motion docs/performance-round59
Each before/after phase has source.json and 720/large/motion720/motionlarge/long720/
longlarge directories emitted by performance_bench.py. Extra diagnostics are retained.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
from performance_bench import pool_runs, read_run, percentile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    report = {'protocol': 'round59-forest-cpu-v1', 'base_revision': 'a9e1104',
              'hardware': 'i7-6700 / GTX 1070 / Linux X11 / NVIDIA 580.178.04',
              'sampling': 'nearest-rank pooled producer intervals; exclude only frames 1–240; CPU is update+draw; raw row n describes game frame n−1',
              'derived_clocks': 'producer_thread sums the recorded callback and runtime-gap thread intervals; gap includes native audio/graphics-end/input/adapter/bookkeeping, not isolated mixer cost',
              'raw_sample_columns': ['frame_n', 'interval_ms', 'cpu_wall_ms', 'gap_ms', 'cpu_thread_ms', 'instance_uploads', 'instance_bytes', 'cpu_voluntary_switches', 'cpu_involuntary_switches', 'cpu_user_ms', 'cpu_system_ms', 'present_ms', 'residual_gap_ms', 'gap_thread_ms', 'gap_voluntary_switches', 'gap_involuntary_switches', 'gap_user_ms', 'gap_system_ms'],
              'phases': {}}
    raw = {}
    required = {'720', 'large', 'motion720', 'motionlarge', 'long720', 'longlarge', 'motionlarge08'}
    for phase in ('before', 'after'):
        base = a.root / phase
        phase_data = {'source': json.loads((base/'source.json').read_text()), 'groups': {}}
        for directory in sorted(base.iterdir()):
            if directory.name not in required: continue
            logs = [p for p in sorted(directory.glob('*.log')) if p.with_name(p.stem+'.environment.json').exists()]
            if not logs: continue
            expected = 3 if directory.name.startswith('long') or directory.name == 'motionlarge08' else 6
            if len(logs) != expected: raise ValueError(f'{phase}/{directory.name}: need {expected} runs, got {len(logs)}')
            runs = {p.stem: read_run(p) for p in logs}
            for name, run in runs.items():
                if run['metadata']['executable_sha256'] != phase_data['source']['executable_sha256']:
                    raise ValueError(f'{phase}/{name}: executable differs from frozen manifest')
                if run['gpu_skipped']: raise ValueError(f'{phase}/{name}: incomplete GPU samples')
                if run['metadata'].get('route_protocol') in ('forest-square-v1', 'talus-input-v1'):
                    motion = run['motion_samples']
                    fields = dict(re.findall(r'(distance|moving|sprint|swing|talus_active|talus_strike|hp) ([\d.]+)', motion[-1]))
                    if float(fields['hp']) <= 0: raise ValueError(f'{phase}/{name}: died during route')
                    if name.startswith('forest-'):
                        if float(fields['distance']) < 80 or int(fields['sprint']) < 300:
                            raise ValueError(f'{phase}/{name}: insufficient forest movement: {fields}')
                    if name.startswith('talus-') and any(int(fields[k]) < v for k,v in [('swing',100),('talus_active',500),('talus_strike',60)]):
                        raise ValueError(f'{phase}/{name}: insufficient live Talus combat: {fields}')
                    if name.startswith('forest-long-') and not run['autosaves']:
                        raise ValueError(f'{phase}/{name}: missing production autosave')
                text = (directory/(name+'.log')).read_text()
                rows = [[float(v) for v in line.split()[2:]] for line in text.splitlines() if line.startswith('frame sample:')]
                if any(not math.isfinite(v) for r in rows for v in r):
                    raise ValueError(f'{phase}/{name}: non-finite raw sample')
                if any(len(r) != len(report['raw_sample_columns']) for r in rows):
                    raise ValueError(f'{phase}/{name}: unexpected raw sample schema')
                expected_frames = int(run['metadata']['flags']['SLOPPY_FRAMES'])
                if [int(r[0]) for r in rows] != list(range(1, expected_frames+1)):
                    raise ValueError(f'{phase}/{name}: raw frame sequence incomplete')
                raw[f'{phase}/{directory.name}/{name}'] = rows
                long_rows = [r for r in rows if r[0] >= 241 and r[2] > 12]
                traces = {}
                for line in run['cpu_spikes']:
                    frame = int(re.search(r'; frame (\d+)',line)[1])
                    stages = [(k,float(w),float(t)) for k,w,t in re.findall(r'([\w-]+) ([\d.]+)/([\d.]+)',line)]
                    traces[frame] = {'line':line,'stages':stages}
                top = Counter()
                top_thread = Counter()
                for row in long_rows:
                    trace = traces.get(int(row[0])-1)
                    if trace and trace['stages']:
                        top[max(trace['stages'], key=lambda s:s[1])[0]] += 1
                        top_thread[max(trace['stages'], key=lambda s:s[2])[0]] += 1
                run['tail_attribution'] = {'cpu_over_12_ms':len(long_rows),
                    'trace_coverage':sum(int(r[0])-1 in traces for r in long_rows),
                    'dominant_wall_stages':dict(top), 'dominant_thread_stages':dict(top_thread),
                    'wall_minus_thread_over_8_ms':sum(r[2]-r[4]>8 for r in long_rows),
                    'involuntary_preemptions':sum(int(r[8]) for r in long_rows),
                    'all_tail_rows':long_rows,
                    'untraced_tail_frames':[int(r[0])-1 for r in long_rows if int(r[0])-1 not in traces],
                    'all_frames_cpu_over_12_ms':sum(r[2]>12 for r in rows),
                    'all_frames_trace_coverage':sum(r[2]>12 and int(r[0])-1 in traces for r in rows),
                    'all_frames_untraced':[int(r[0])-1 for r in rows if r[2]>12 and int(r[0])-1 not in traces]}
                if run['tail_attribution']['all_frames_untraced']:
                    raise ValueError(f'{phase}/{name}: CPU tails missing stage traces: {run["tail_attribution"]["all_frames_untraced"]}')
            group = {'runs':runs,'pooled':pool_runs(directory,runs)}
            for pooled in group['pooled'].values():
                steady = [r for name in pooled['runs'] for r in raw[f'{phase}/{directory.name}/{name}'] if r[0]>=241]
                for label, values in [('residual_gap', [r[12] for r in steady]),
                                      ('runtime_thread', [r[13] for r in steady]),
                                      ('producer_thread', [r[4]+r[13] for r in steady])]:
                    pooled[label] = {'p50':percentile(values,.5), 'p95':percentile(values,.95),
                                     'p99':percentile(values,.99), 'worst':max(values)}
            if (directory/'prepare.log').exists():
                log = (directory/'prepare.log').read_text()
                group['preparation'] = {'metadata':json.loads((directory/'prepare.json').read_text()), 'log':log}
            phase_data['groups'][directory.name] = group
        if set(phase_data['groups']) != required:
            raise ValueError(f'{phase}: missing groups {required-set(phase_data["groups"])}')
        report['phases'][phase] = phase_data
    before = report['phases']['before']['source']['sources']
    after = report['phases']['after']['source']['sources']
    changed = [p for p in before if before[p] != after[p]]
    if changed != ['game/gfx.jo', 'game/vegetation.jo', 'game/wildlife.jo']: raise ValueError(f'unexpected source changes: {changed}')
    report['changed_sources'] = changed
    for directory, group in report['phases']['before']['groups'].items():
        matched = report['phases']['after']['groups'][directory]['runs']
        for name, run in group['runs'].items():
            other = matched[name]
            flags = lambda r: {k:v for k,v in r['metadata']['flags'].items() if k not in {'SLOPPY_SCREENSHOT','BOTW_BENCH_SAVE'}}
            if flags(run) != flags(other): raise ValueError(f'{directory}/{name}: unmatched flags')
            # Byte equality of the final fixed-step PNG validates unchanged rendering/simulation.
            b = (a.root/'before'/directory/(name+'.png')).read_bytes()
            c = (a.root/'after'/directory/(name+'.png')).read_bytes()
            run['paired_png_sha256'] = hashlib.sha256(b).hexdigest()
            run['paired_png_bytes_equal'] = b == c
            if b != c: raise ValueError(f'{directory}/{name}: changed fixed-step screenshot')
            rows = lambda phase: [[float(v) for v in l.split()[2:]] for l in (a.root/phase/directory/(name+'.log')).read_text().splitlines() if l.startswith('frame sample:')]
            if [(r[5],r[6]) for r in rows('before')] != [(r[5],r[6]) for r in rows('after')]:
                raise ValueError(f'{directory}/{name}: changed per-frame instance uploads/bytes')
            run['paired_all_frame_uploads_equal'] = True
    if (a.root/'checks.json').exists(): report['checks'] = json.loads((a.root/'checks.json').read_text())
    if (a.root/'provenance.json').exists(): report['provenance'] = json.loads((a.root/'provenance.json').read_text())
    if (a.root/'compilation.json').exists(): report['compilation'] = json.loads((a.root/'compilation.json').read_text())
    report['source_counts'] = json.loads((a.root/'loc.json').read_text())
    report['sample_counts'] = {'runs':len(raw), 'raw':sum(len(v) for v in raw.values()), 'steady':sum(sum(r[0]>=241 for r in v) for v in raw.values())}
    a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    with gzip.open(str(a.output)+'-samples.json.gz','wt') as f: json.dump(raw,f,separators=(',',':'))
    print(f'{sum(len(v) for v in raw.values())} raw intervals retained in {len(raw)} runs')

if __name__ == '__main__': main()
