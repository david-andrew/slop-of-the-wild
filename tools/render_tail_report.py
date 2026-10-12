#!/usr/bin/env python3
"""Attribute existing present-return tails to probe and game stages; no render/lock.

Usage: python3 tools/render_tail_report.py build/music-tails --output docs/performance-return-tails.json
Run render_evidence.py --stage-trace first. Keep all rows in build/; this report
retains the twelve slowest intervals per run and checks stage coverage of >25 ms.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def analyze(path):
    text = path.read_text()
    assert 'probe complete:' in text, f'incomplete run: {path}'
    rows = [[float(v) for v in line.split()[2:]] for line in text.splitlines()
            if line.startswith('present return:')]
    assert [int(r[0]) for r in rows] == list(range(len(rows)))
    traces = {}
    cpu = {}
    gpu = {}
    for line in text.splitlines():
        if line.startswith('return stages:'):
            n = int(re.search(r'frame (\d+)', line)[1])
            values = {name: {'wall_ms': float(w), 'thread_ms': float(t) if t else None}
                      for name,w,t in re.findall(r'([a-z_]+) ([\d.]+)(?:/([\d.]+))?', line)}
            stages = {k:v for k,v in values.items() if k not in ['frame','interval']}
            traces[n] = {'line': line, 'stages': stages,
                         'dominant_stage': max(stages, key=lambda k: stages[k]['wall_ms'])}
        if line.startswith('long cpu '):
            n = int(re.search(r'; frame (\d+)', line)[1])
            stages = [{'name':name,'wall_ms':float(w),'thread_ms':float(t)}
                      for name,w,t in re.findall(r'([\w-]+) ([\d.]+)/([\d.]+)',line)]
            cpu[n] = stages[:8]
        if line.startswith('gpu frame:'):
            n = int(line.split()[2])
            gpu[n] = float(line.rsplit(' = ',1)[1])
    steady = [r for r in rows if r[0] >= 241]
    tail = [r for r in steady if r[2] > 25]
    assert all(int(r[0]) in traces for r in tail), 'missing return-stage trace'
    evidence = []
    for row in sorted(steady, key=lambda r:-r[2])[:12]:
        n = int(row[0])
        evidence.append({'frame':n,'elapsed_s':row[1],'interval_ms':row[2],
                         'present_ms':row[3],'callback_wall_ms':row[4],'callback_thread_ms':row[5],
                         'return_trace':traces.get(n),'largest_cpu_stages':cpu.get(n,[]),
                         'gpu_same_frame_ms':gpu.get(n)})
    dominant = {}
    for row in tail:
        name = traces[int(row[0])]['dominant_stage']
        dominant[name] = dominant.get(name,0)+1
    metadata = json.loads(path.with_suffix('.json').read_text())
    return {'log':str(path),'log_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'samples_after_frame_240':len(steady),'intervals_over_25ms':len(tail),
            'dominant_tail_stages':dominant,'timing_ms':metadata['timing_ms'],
            'flags':metadata['flags'],'presentation':metadata['presentation'],
            'steady_shader_request_frames':[int(n) for n in re.findall(r'^shader request: frame (\d+)$',text,re.M) if int(n)>240],
            'worst_intervals':evidence}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    logs=sorted(args.directory.glob('*.log'))
    assert logs
    result={'protocol':'Opt-in Wayland return tracing; fixed 1/60 steady scenes, real-dt traversal. '
                       'Return frame n describes callback n; raw sample n+1 contains callback n but '
                       'may shift poll work to the previous runtime gap. Wall/thread stages separate '
                       'CPU work from waits; GPU queries are asynchronous. Diagnostic instrumentation '
                       'and concurrent desktop activity prevent direct percentile comparison with untraced runs.',
            'runs':{path.stem:analyze(path) for path in logs}}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(args.output)
    for name,run in result['runs'].items():
        print(name,run['dominant_tail_stages'],run['worst_intervals'][0])


if __name__=='__main__':
    main()
