#!/usr/bin/env python3
"""Validate matched CPU/GPU tail captures, retaining all raw rows and stage traces.

performance_tail_report.py build/perf-tail docs/performance-round60
The frozen before phase is merged 2eb243a plus identical observational probes.
The final game source manifest must match the working tree. No outliers are removed.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
from performance_bench import percentile, pool_runs, read_run


def rows(text):
    return [[float(v) for v in line.split()[2:]] for line in text.splitlines()
            if line.startswith('frame sample:')]


def gpu_rows(text):
    out = {}
    for line in text.splitlines():
        if not line.startswith('gpu frame:'): continue
        frame = int(line.split()[2])
        assert frame not in out, f'duplicate GPU frame {frame}'
        passes = {k:float(v) for k,v in re.findall(r'([\w-]+) ([\d.]+)',line)}
        out[frame] = {'passes':passes,'total':float(line.rsplit(' = ',1)[1])}
    return out


def analyze(text, *, allow_trace_gaps=False):
    sample = rows(text)
    assert [int(r[0]) for r in sample] == list(range(1,len(sample)+1))
    assert all(len(r)==18 for r in sample)
    traces = {}
    for line in text.splitlines():
        if not line.startswith('long cpu '): continue
        frame = int(re.search(r'; frame (\d+)',line)[1])
        stages = [(k,float(w),float(t)) for k,w,t in re.findall(r'([\w-]+) ([\d.]+)/([\d.]+)',line)]
        traces[frame] = {'line':line,'stages':stages}
    tail = [r for r in sample if r[2]>12]
    missing = [int(r[0])-1 for r in tail if int(r[0])-1 not in traces]
    assert not missing or allow_trace_gaps, f'CPU >12 ms without stage traces: {missing}'
    wall,thread = Counter(),Counter()
    for row in tail:
        if int(row[0])-1 not in traces: continue
        stages=traces[int(row[0])-1]['stages']
        wall[max(stages,key=lambda v:v[1])[0]]+=1
        thread[max(stages,key=lambda v:v[2])[0]]+=1
    gpu = gpu_rows(text)
    steady = [r for r in sample if r[0]>=241]
    worst = sorted(steady,key=lambda r:-r[1])[:12]
    evidence = [{'row':r,'gpu_same_frame':gpu.get(int(r[0])-1),
                 'cpu_trace':traces.get(int(r[0])-1)} for r in worst]
    summary = {'cpu_over_12_ms_all_frames':len(tail),
        'cpu_over_12_ms_steady':sum(r[2]>12 for r in steady),
        'trace_coverage_all_frames':len(tail)-len(missing),'untraced_tail_frames':missing,
        'dominant_wall_stages_all_frames':dict(wall),
        'dominant_thread_stages_all_frames':dict(thread),
        'wall_minus_thread_over_8_ms_steady':sum(r[2]-r[4]>8 for r in steady),
        'gpu_frames_retained':len(gpu),
        'shader_requests':re.findall(r'^shader request:.*$',text,re.M),
        'scale_controller_events':re.findall(r'^scale controller:.*$',text,re.M),
        'worst_interval_evidence':evidence}
    for label,col in [('interval',1),('cpu_wall',2),('cpu_thread',4),('present',11),('residual_gap',12)]:
        v=[r[col] for r in steady]
        summary[label]={k:f(v) for k,f in [('p50',lambda v:percentile(v,.5)),('p95',lambda v:percentile(v,.95)),('p99',lambda v:percentile(v,.99)),('worst',max)]}
    gt=[g['total'] for n,g in gpu.items() if n>=240]
    if gt: summary['gpu_total']={k:f(gt) for k,f in [('p50',lambda v:percentile(v,.5)),('p99',lambda v:percentile(v,.99)),('worst',max)]}
    finish={int(n):{'finish':float(f),'present':float(p)} for n,f,p in
            re.findall(r'^gpu finish: frame (\d+) finish ([\d.]+) present ([\d.]+)$',text,re.M)}
    if finish:
        v=[x['finish'] for n,x in finish.items() if n>=240]
        summary['gpu_finish']={k:f(v) for k,f in [('p50',lambda v:percentile(v,.5)),('p99',lambda v:percentile(v,.99)),('worst',max)]}
    return summary,{'samples':sample,'cpu_traces':traces,'gpu_frames':gpu,'finish_frames':finish}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path);parser.add_argument('output',type=Path)
    a=parser.parse_args()
    report={'protocol':'round60-merged-tails-v1','base_revision':'2eb243a',
        'hardware':'i7-6700 / GTX 1070 / Linux X11 / NVIDIA 580.178.04',
        'sampling':'nearest-rank pooled samples; exclude only frames 1–240 for steady metrics; retain startup and every outlier',
        'alignment':'sample n describes game frame n−1; gpu frame n is an asynchronous query of that draw; last three in-flight GPU queries may be unavailable',
        'phases':{}}
    raw={}
    required={'steady720','steadylarge','motion720','motionlarge','motionlarge08'}
    for phase in ['before','after']:
        base=a.root/phase
        data={'source':json.loads((base/'source.json').read_text()),'groups':{}}
        for directory in sorted(base.iterdir()):
            if directory.name not in required: continue
            logs=[p for p in sorted(directory.glob('*.log')) if p.with_name(p.stem+'.environment.json').exists()]
            assert len(logs)==(3 if directory.name=='motionlarge08' else 6)
            runs={}
            for p in logs:
                result=read_run(p)
                assert result['metadata']['executable_sha256']==data['source']['executable_sha256']
                summary,source=analyze(p.read_text())
                assert len(source['samples'])==int(result['metadata']['flags']['SLOPPY_FRAMES'])
                result['tail_analysis']=summary
                # Full traces are retained once in the compressed artifact.
                for key in ['cpu_spikes','cpu_wall_thread_spikes']: result.pop(key,None)
                raw[f'{phase}/{directory.name}/{p.stem}']=source
                runs[p.stem]=result
                if p.stem.startswith(('talus-','forest-sprint-')):
                    fields=dict(re.findall(r'(distance|sprint|swing|talus_active|talus_strike|hp) ([\d.]+)',result['motion_samples'][-1]))
                    assert float(fields['hp'])>0
                    if p.stem.startswith('talus-'):
                        assert all(int(fields[k])>=v for k,v in [('swing',100),('talus_active',500),('talus_strike',60)])
                    else: assert float(fields['distance'])>80 and int(fields['sprint'])>300
            data['groups'][directory.name]={'runs':runs,'pooled':pool_runs(directory,runs)}
        assert set(data['groups'])==required
        report['phases'][phase]=data
    expected=report['phases']['after']['source']['sources']
    for name,digest in expected.items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest, f'final source changed after capture: {name}'
    for group in required:
        before=report['phases']['before']['groups'][group]['runs']
        after=report['phases']['after']['groups'][group]['runs']
        assert before.keys()==after.keys()
        for name,result in before.items():
            flags=lambda r:{k:v for k,v in r['metadata']['flags'].items() if k!='SLOPPY_SCREENSHOT'}
            assert flags(result)==flags(after[name])
            b=a.root/'before'/group/(name+'.png');c=a.root/'after'/group/(name+'.png')
            equal=b.read_bytes()==c.read_bytes()
            result['paired_png_equal']=equal
            # Only fire ignition discovery changes timing; geometry and physics
            # behavior for the other routes must remain byte-identical.
            if not name.startswith('fire-'):
                assert equal, f'changed fixed-step image: {group}/{name}'
                b_rows=raw[f'before/{group}/{name}']['samples']
                a_rows=raw[f'after/{group}/{name}']['samples']
                assert [(r[5],r[6]) for r in b_rows]==[(r[5],r[6]) for r in a_rows]
                result['paired_instance_uploads_equal']=True
    report['diagnostics']={}
    for p in sorted((a.root/'diagnostics').glob('*.log')):
        summary,source=analyze(p.read_text())
        summary['environment']=json.loads(p.with_suffix('.environment.json').read_text())
        executable=a.root/('finish-game' if p.stem.startswith('finish') else 'after/game')
        summary['executable_sha256']=hashlib.sha256(executable.read_bytes()).hexdigest()
        if p.stem.startswith('finish'):
            group='motion720' if p.stem=='finish720' else 'motionlarge'
            assert p.with_suffix('.png').read_bytes()==(a.root/'after'/group/'forest-sprint-gpu-1-1.png').read_bytes()
            summary['paired_final_png_equal']=True
        summary['scale_batches']=re.findall(r'^frame percentiles:.*$',p.read_text(),re.M)
        report['diagnostics'][p.stem]=summary
        raw['diagnostics/'+p.stem]=source
    assert set(report['diagnostics'])=={'dynamic720','dynamiclarge','vsync720','finish720','finishlarge'}
    report['checks']={}
    for p in (a.root/'checks').glob('*.json'): report['checks'].update(json.loads(p.read_text()))
    for name in ['collision_query_check','fire_scan_check','camera_check','talus_test','talus_mesh_check','talus_skin_check','tree_test']:
        text=(a.root/'checks'/(name+'.log')).read_text()
        if name=='talus_mesh_check':
            assert float(re.search(r'section/triangle samples; worst ([\d.]+)',text)[1])<0.16
        else: assert 'PASS' in text or 'passed' in text
        report['checks'][name]={'exit_code':0,'log':text}
    assert all(r['exit_code']==0 for r in report['checks'].values())
    report['source_counts']=json.loads((a.root/'loc.json').read_text())
    report['compilation']=json.loads((a.root/'compilation.json').read_text())
    report['query_microbenchmark']={phase:(a.root/('query-'+phase+'.log')).read_text()
                                   for phase in ['before','after']}
    # Preserve the actual previous worst fire frame; it was a wall-time stall.
    old=json.loads(Path('docs/performance-round59.json').read_text())['phases']['after']['groups']['large']['runs']['fire-gpu-1-1']
    report['historical_fire_worst']={'row':old['slowest_intervals'][0],
        'trace':next(t for t in old['cpu_spikes'] if '; frame 453;' in t)}
    report['sample_counts']={'runs':len(raw),'raw':sum(len(r['samples']) for r in raw.values()),'gpu':sum(len(r['gpu_frames']) for r in raw.values())}
    a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    with gzip.open(str(a.output)+'-samples.json.gz','wt') as f:json.dump(raw,f,separators=(',',':'))
    print(report['sample_counts'])
    for phase in ['before','after']:
        for group in report['phases'][phase]['groups'].values():
            for key,p in group['pooled'].items():
                print(phase,key,'interval',p['interval']['p99'],p['interval']['worst'],'CPU',p['game_wall']['p99'],p['game_wall']['worst'])


if __name__=='__main__':main()
