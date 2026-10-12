#!/usr/bin/env python3
"""Attribute every >17.5 ms return in complete monotonic two-second windows.

No render/lock. Queries for frame n describe its world draw; callback n waits on
frame n-1's fence. GPU elapsed queries include submission bubbles/preemption,
so a high pass time is evidence of a delayed pass, not proof of shader cost.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True
from cpu_tail_bench import summarize
from render_evidence import metrics


def stages(line):
    result = defaultdict(lambda: {'wall_ms': 0.0, 'thread_ms': 0.0})
    for name, wall, thread in re.findall(r'([\w-]+) ([\d.]+)/([\d.]+)', line):
        result[name]['wall_ms'] += float(wall)
        result[name]['thread_ms'] += float(thread)
    return dict(result)


def gpu_group(name):
    if name.startswith(('shadow', 'sh-')): return 'shadows'
    if name in ('trees', 'grass', 'far-trees'): return 'vegetation'
    if name == 'water': return 'water'
    if name == 'post': return 'post/watercolour'
    return name


def analyze(path, traced=True):
    text = path.read_text()
    summary = summarize(path)
    rows = [[float(v) for v in line.split()[2:]] for line in text.splitlines()
            if line.startswith('present return:')]
    gpu, cpu, returns, usage = {}, {}, {}, {}
    for line in text.splitlines():
        if line.startswith('gpu frame:'):
            n = int(line.split()[2])
            assert n not in gpu
            gpu[n] = {'passes_ms': {k:float(v) for k,v in re.findall(r'([\w-]+) ([\d.]+)',line)},
                      'total_ms':float(line.rsplit(' = ',1)[1])}
        elif line.startswith('tail cpu:'):
            n = int(re.search(r'frame (\d+)',line)[1])
            cpu[n] = {'stages': stages(line), 'detail': line.split(';',1)[1],
                      'simulation_ticks':len(re.findall(r'player_update [\d.]+/[\d.]+',line))}
        elif line.startswith('return stages:'):
            n = int(re.search(r'frame (\d+)',line)[1])
            returns[n] = stages(line)
            returns[n]['prior'] = {'wall_ms':float(re.search(r'prior ([\d.]+)',line)[1]), 'thread_ms':None}
        elif line.startswith('frame sample:'):
            r = [float(v) for v in line.split()[2:]]
            usage[int(r[0])-1] = {'callback_voluntary_switches':int(r[7]),
                                 'callback_involuntary_switches':int(r[8]),
                                 'gap_voluntary_switches':int(r[14]),
                                 'gap_involuntary_switches':int(r[15])}
    windows = summary['windows']
    first, last = windows[0]['start_s'], windows[-1]['start_s']+2
    shader_frames = [int(n) for n in re.findall(r'^shader request: frame (\d+)$',text,re.M)]
    vertex_frames = [int(n) for n in re.findall(r'^vertex first use: frame (\d+)',text,re.M)]
    tails = []
    for r in rows:
        n = int(r[0])
        if not first <= r[1] < last or r[2] <= 17.5: continue
        w = next(w for w in windows if w['start_s'] <= r[1] < w['start_s']+2)
        record = {'frame':n, 'elapsed_s':r[1], 'interval_ms':r[2], 'present_ms':r[3],
                  'callback_wall_ms':r[4], 'callback_thread_ms':r[5],
                  'window_start_s':w['start_s'], 'window_p99_ms':w['interval']['p99'],
                  'in_failing_window':w['interval']['p99']>17.5}
        if not traced:
            record.update(category='unresolved (historical untraced capture)',
                          evidence='Callback/present totals alone cannot identify a GPU pass or a fence wait.')
            tails.append(record)
            continue
        assert n in returns and n in cpu and n-1 in gpu and n in gpu, f'incomplete attribution frame {n}'
        s, rt = cpu[n]['stages'], returns[n]
        queue = s.get('gpu_queue_wait', {'wall_ms':0.0,'thread_ms':0.0})
        prev, same = gpu[n-1], gpu[n]
        cpumax = max(s, key=lambda k:s[k]['thread_ms'])
        nonqueue = {k:v for k,v in s.items() if k != 'gpu_queue_wait'}
        stall = max(nonqueue, key=lambda k:nonqueue[k]['wall_ms']-nonqueue[k]['thread_ms'])
        gap = max((k for k in rt if k != 'callback'), key=lambda k:rt[k]['wall_ms'])
        # Conservative high-load guards: never call a wait presentation-only if
        # either adjacent world query exceeds 14 ms or callback CPU exceeds 8 ms.
        # These are explicit attribution cutoffs, not the strict window target.
        idle_gpu = max(prev['total_ms'], same['total_ms']) < 14.0
        low_cpu = r[5] < 8.0
        present_wait = rt['present']['wall_ms']-rt['present']['thread_ms']
        nongpu_stall = nonqueue[stall]['wall_ms']-nonqueue[stall]['thread_ms']
        distributed_gap = sum(max(0.0,v['wall_ms']-v['thread_ms']) for v in nonqueue.values())
        reason = ''
        if n in shader_frames:
            category, reason = 'shader first use', 'Program requested in this callback.'
        elif n in vertex_frames:
            category, reason = 'binding first use', 'A mesh/shader or vegetation instance VAO was created in this callback.'
        elif r[5] >= 8.0 and s[cpumax]['thread_ms'] >= 3.0:
            category, reason = 'CPU: '+cpumax, 'Callback thread CPU >=8 ms and a stage consumes >=3 ms CPU; summed repeated stages retained.'
        elif same['total_ms'] >= 14.0 and nongpu_stall >= 3.0:
            category, reason = 'scheduler/driver wait: '+stall, 'Current elapsed GPU query is high alongside a >=3 ms CPU submission sleep; cannot identify pure GPU shader cost.'
        elif same['total_ms'] >= 14.0 and distributed_gap >= 3.0:
            category, reason = 'scheduler/preemption: distributed (GPU elapsed elevated)', 'Current GPU elapsed query is high alongside accumulated CPU submission pauses >=3 ms. Full stages identify the pauses; cannot isolate GPU instruction cost.'
        elif not idle_gpu and queue['wall_ms'] >= 3.0:
            # Retain both neighboring draws: present-return n contains submission
            # n and the preceding fence, and a concurrent CPU stall can inflate queries.
            delayed = prev if prev['total_ms'] >= same['total_ms'] else same
            delayed_n = n-1 if delayed is prev else n
            excess = {}
            for name, value in delayed['passes_ms'].items():
                peers = [gpu[i]['passes_ms'][name] for i in range(max(0,delayed_n-60),delayed_n+61)
                         if i in gpu and i != delayed_n and name in gpu[i]['passes_ms']]
                excess[name] = value-(metrics(peers)['p50'] if peers else 0.0)
            name = max(excess,key=excess.get)
            record['delayed_gpu_frame'] = delayed_n
            record['gpu_pass_excess_vs_local_median_ms'] = excess
            category = 'GPU/pass delay: '+gpu_group(name)
            reason = f'Adjacent world draw >=14 ms; largest pass excess versus local median: {name}. Elapsed timer may include scheduling/submission gaps.'
        elif not low_cpu:
            category, reason = 'CPU distributed: '+cpumax, 'Callback thread CPU >=8 ms, without a >=3 ms CPU stage. Largest summed stage named; catch-up ticks and scheduler switches retained.'
        elif idle_gpu and present_wait >= 3.0 and present_wait >= max(queue['wall_ms']-queue['thread_ms'],nongpu_stall):
            category, reason = 'presentation-only: present', 'Present sleeps with low callback CPU and both adjacent measured world draws <14 ms.'
        elif idle_gpu and queue['wall_ms']-queue['thread_ms'] >= 3.0 and queue['wall_ms']-queue['thread_ms'] >= nongpu_stall:
            category, reason = 'presentation-only: fence/scheduling', 'Fence wait dominates; low callback CPU and both adjacent measured world draws <14 ms.'
        elif nongpu_stall >= 3.0:
            category, reason = 'scheduler/driver wait: '+stall, 'Non-fence stage wall time exceeds its thread CPU by >=3 ms.'
        elif idle_gpu and low_cpu and distributed_gap >= 3.0:
            category, reason = 'scheduler/preemption: distributed', 'Non-fence stage wall-minus-thread gaps accumulate >=3 ms; no single >=3 ms pause. Stage rows and context switches retained.'
        elif gap != 'present' and rt[gap]['wall_ms'] >= 3.0:
            category, reason = 'runtime/scheduler: '+gap, 'Measured return-loop stage outside callback dominates the residual.'
        else:
            category, reason = 'mixed/budget boundary', 'No single measured wait or CPU/GPU load meets the attribution cutoff; no presentation-only claim.'
        record.update(category=category,evidence=reason,queue_wait=queue,
                      gpu_previous=prev,gpu_same=same,cpu=cpu[n],return_stages=rt,
                      switches=usage.get(n))
        tails.append(record)
    counts = Counter(r['category'] for r in tails)
    failed = [r for r in tails if r['in_failing_window']]
    def fraction(rs):
        count = sum(r['category'].startswith('presentation-only:') for r in rs)
        return {'count':count,'total':len(rs),'fraction':count/len(rs) if rs else 0.0}
    selected_gpu = [g for n,g in gpu.items() if first <= rows[n][1] < last]
    pass_times = defaultdict(list)
    for g in selected_gpu:
        for k,v in g['passes_ms'].items(): pass_times[k].append(v)
    return {'log':str(path),'log_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'window_count':len(windows),'windows_over_20ms':summary['windows_over_20ms'],
            'windows_over_17_5ms':summary['windows_over_17_5ms'],
            'distribution':summary['distribution'],'windows':windows,
            'tail_count':len(tails),'tail_categories':dict(counts),
            'failing_window_tail_count':len(failed),
            'failing_window_tail_categories':dict(Counter(r['category'] for r in failed)),
            'presentation_only':fraction(tails),'failing_window_presentation_only':fraction(failed),
            'gpu_total_ms':metrics([g['total_ms'] for g in selected_gpu]) if selected_gpu else None,
            'gpu_passes_ms':{k:metrics(v) for k,v in pass_times.items()},
            'steady_shader_requests':[n for n in shader_frames if n<len(rows) and first<=rows[n][1]<last],
            'vertex_first_use_count':len(vertex_frames),
            'steady_vertex_first_use':[n for n in vertex_frames if n<len(rows) and first<=rows[n][1]<last],
            'minutes':summary['minutes'],'tails':tails}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before',type=Path,required=True);p.add_argument('--after',type=Path)
    p.add_argument('--historical',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    report={'protocol':'600s forest waypoint route; 2133x1200 Wayland dma-buf mailbox; fixed scale 0.80; real dt; 4s warmup then complete 2s monotonic windows; nearest rank; all outliers retained',
            'attribution':'Frame n waits on draw n-1. All >17.5ms intervals retained, with failing-window membership. Presentation-only is an inference from low callback CPU (<8ms) and adjacent measured world draws (<14ms), not compositor telemetry. GPU timer intervals can include scheduling and CPU submission bubbles; passes are not additive with callback times. Driver specialization has no direct telemetry; shader-request markers cover program creation only.',
            'runs':{'before':analyze(a.before)}}
    if a.after:report['runs']['after']=analyze(a.after)
    if a.historical:report['runs']['historical']=analyze(a.historical,False)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    for name,r in report['runs'].items(): print(name,r['window_count'],r['windows_over_20ms'],r['windows_over_17_5ms'],r['tail_categories'],r['presentation_only'])


if __name__=='__main__':main()
