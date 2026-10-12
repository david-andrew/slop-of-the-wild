#!/usr/bin/env python3
"""Fixed-frame, locked GTX benchmark with actual output sizes and immutable executables.

capture EXE OUTPUT [--repeats 3 --scale .8 --mode gpu]
report OUTPUT writes summary.json (all batches, startup, RSS, frame delivery).
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
    'forest': {'BOTW_AT': '-1000,1620,3.14', 'BOTW_WEATHER':'clear'},
    'fire': {'BOTW_FIRE': '1', 'BOTW_WEATHER':'clear'},
    'forest-orbit': {'BOTW_AT': '-1000,1620,3.14', 'SLOPPY_INPUT': '241:right+,721:right-'},
    'camp': {'BOTW_AT': '-1439,1606,0'},
    'pond': {'BOTW_AT': '-1190,1665,-0.9'},
    'overlook': {'BOTW_AT': '-1050,1828,-2.36'},
    'snow': {'BOTW_AT': '-1060,2230,2.0'},
    'storm': {'BOTW_AT': '-1000,1620,3.14', 'BOTW_WEATHER': 'storm'},
    'combat': {'BOTW_AT': '-1439,1614,0', 'BOTW_GIVE': 'travelers_sword,travelers_shield', 'SLOPPY_INPUT': '10:w+,50:w-,60:k+,' + ','.join(f'{f}:j+,{f+1}:j-' for f in range(90,720,60))},
    'traversal': {'BOTW_AT': '-1000,1620,3.14', 'SLOPPY_INPUT': '5:w+,5:shift+,1000:shift-,1400:shift+,2200:shift-'},
    'mixed': {'BOTW_AT': '-1000,1620,3.14', 'BOTW_TOWER': '1',
              'BOTW_GIVE': 'travelers_sword,travelers_shield,warm_doublet',
              'BOTW_WEATHER_SEQ': '4800:storm,6000:clear',
              'SLOPPY_INPUT': '1:w+,1:shift+,1:right+,1100:w-,1100:shift-,1100:right-,'
                  '1201:w+,1300:w-,1320:k+,'
                  + ','.join(f'{f}:j+,{f+1}:j-' for f in range(1320,2350,45))
                  + ',2400:k-,2401:w+,2401:right+,3550:w-,3550:right-,'
                  '3850:right+,4400:right-,4801:w+,4801:right+,5950:w-,5950:right-,'
                  '6001:w+,6001:shift+,6001:right+,7100:w-,7100:shift-,7100:right-'},
    'forest-sprint': {'BOTW_AT': '-1000,1620,3.14', 'BOTW_BENCH_ROUTE': 'forest-sprint', 'BOTW_WEATHER':'clear',
                      'SLOPPY_INPUT': '1:w+,' + ','.join(f'{f}:shift+,{f+150}:shift-' for f in range(1,2400,360))
                          + ',' + ','.join(f'{f}:right+,{f+39}:right-' for f in range(480,2400,480)) + ',2400:w-'},
    'talus': {'BOTW_AT': '-1087.75,1673.18,0', 'BOTW_BENCH_ROUTE': 'talus', 'BOTW_WEATHER':'clear',
              'BOTW_GIVE': 'travelers_sword,travelers_shield',
              'SLOPPY_INPUT': '1:w+,240:w-,241:k+,' + ','.join(f'{f}:j+,{f+1}:j-' for f in range(270,2400,45))},
    'forest-long': {'BOTW_AT': '-1140,1500,3.14', 'BOTW_BENCH_ROUTE': 'forest-long', 'BOTW_WEATHER':'clear',
                    'SLOPPY_INPUT': '1:w+,' + ','.join(f'{f}:shift+,{f+150}:shift-' for f in range(1,12000,360))
                        + ',' + ','.join(f'{f}:right+,{f+39}:right-' for f in range(480,12000,480))},
    'opening': {},
    'title': {'BOTW_TITLE': '1', 'BOTW_AT': '-1024,1799,0'},
    'entry': {'BOTW_TOWER': '1', 'BOTW_ENTER': '1'},
}


def percentile(v, p):
    return sorted(v)[max(0, math.ceil(len(v)*p)-1)]


def capture(a):
    if a.repeats < 1 or a.frames < 360 or a.frames % 120 or not .5 <= a.scale <= 1.0:
        raise ValueError('positive repeats, >=360 frames in batches of 120, and .5–1 scale required')
    if 'mixed' in a.views and a.frames != 7200:
        raise ValueError('mixed-v1 requires exactly 7200 frames and the performance_route executable')
    a.output.mkdir(parents=True, exist_ok=True)
    # Prepare the same output/pipeline before warm repeats. Retain the preparation
    # process separately: its cache-miss cost never silently replaces a measured run.
    if a.shader_cache == 'warm' and a.exact_output and a.mode == 'gpu':
        e = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_')) and k != '__GL_SHADER_DISK_CACHE'}
        e.update(BOTW_SKIP='1', BOTW_LOADTIME='1', BOTW_SCALE=str(a.scale), BOTW_NOVSYNC='1',
                 SLOPPY_PLATFORM='x11', SLOPPY_WINDOW=a.window, SLOPPY_FRAMES='1', SLOPPY_FRAME_STATS='1',
                 SLOPPY_SCREENSHOT=str((a.output/'prepare.png').resolve()))
        if a.window_loop == 'client': e['BOTW_BENCH_CLIENT_SIZE'] = '1'
        if a.prepared_assets == 'disabled': e['BOTW_NO_PREPARED_ASSETS'] = '1'
        e.update(CASES[a.views[0]])
        if a.views[0] == 'opening': e.pop('BOTW_SKIP')
        cmd = ['python3', 'tools/performance_window.py', a.window, '/usr/bin/time', '-v',
               'timeout', '-k', '10', '180', str(a.executable.resolve())]
        if not a.locked: cmd = ['flock', '/tmp/botw-render.lock'] + cmd
        (a.output/'prepare.json').write_text(json.dumps({'source_revision': a.revision,
            'flags': {k: v for k,v in e.items() if k.startswith(('BOTW_', 'SLOPPY_'))},
            'protocol': 'unmeasured preparation for the same output/pipeline'}, indent=2)+'\n')
        with (a.output/'prepare.log').open('w') as log:
            subprocess.run(cmd, env=e, stdout=log, stderr=subprocess.STDOUT, check=True)
    for repeat in range(1, a.repeats+1):
        for name in a.views:
            prefix = a.output / f'{name}-{a.mode}-{a.scale:g}-{repeat}'
            e = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_')) and k != '__GL_SHADER_DISK_CACHE'}
            e.update(BOTW_SKIP='1', BOTW_SCALE=str(a.scale), BOTW_FRAME_LOG='1',
                     BOTW_LOADTIME='1', BOTW_SCENE_LOG='1', SLOPPY_FRAME_STATS='1',
                     SLOPPY_FRAMES=str(a.frames))
            # with_suffix treats the decimal in scale as an extension: append instead.
            png = Path(str(prefix)+'.png'); e['SLOPPY_SCREENSHOT'] = str(png.resolve())
            if a.mode == 'gpu':
                e.update(BOTW_GPU='1', BOTW_NOVSYNC='1', SLOPPY_PLATFORM='x11', SLOPPY_WINDOW=a.window)
            else:
                e.update(BOTW_CPU='1', SLOPPY_PLATFORM='wayland')
                if a.mode == 'mailbox': e['SLOPPY_PRESENT'] = 'mailbox'
            if a.shader_cache == 'disabled':
                e['__GL_SHADER_DISK_CACHE'] = '0'
                e['BOTW_NO_SHADER_CACHE'] = '1'
            if a.window_loop == 'client': e['BOTW_BENCH_CLIENT_SIZE'] = '1'
            if a.prepared_assets == 'disabled': e['BOTW_NO_PREPARED_ASSETS'] = '1'
            e.update(CASES[name])
            if name == 'opening': e.pop('BOTW_SKIP')
            if name == 'forest-long': e['BOTW_BENCH_SAVE'] = str(Path(str(prefix)+'.save').resolve())
            if a.cpu_trace: e['BOTW_CPU'] = '1'
            if a.no_stage_trace: e.pop('BOTW_CPU', None)
            if a.cpu_trace_ms is not None: e['BOTW_CPU_TRACE_MS'] = str(a.cpu_trace_ms)
            if a.dynamic_scale: e.pop('BOTW_SCALE')
            if a.gpu_frame_trace: e['BOTW_GPU_FRAME_LOG'] = '1'
            meta = {'executable': str(a.executable.resolve()), 'source_revision': a.revision,
                    'executable_sha256': __import__('hashlib').sha256(a.executable.read_bytes()).hexdigest(),
                    'flags': {k: v for k, v in e.items() if k.startswith(('BOTW_', 'SLOPPY_', '__GL_'))},
                    'capture_helper_sha256': __import__('hashlib').sha256(Path('tools/performance_window.py').read_bytes()).hexdigest() if a.exact_output else None,
                    'shader_cache_protocol': a.shader_cache, 'prepared_assets_protocol': a.prepared_assets, 'protocol_id': 'round56-sol-loading-v1',
                    'route_protocol': 'mixed-v1' if name == 'mixed' else ('forest-square-v1' if name.startswith('forest-') and name != 'forest-orbit' else ('talus-input-v1' if name == 'talus' else None)), 'window_loop': a.window_loop}
            if a.resume and Path(str(prefix)+'.environment.json').exists() and Path(str(prefix)+'.log').exists():
                previous_log = Path(str(prefix)+'.log')
                if previous_log.stat().st_size:
                    old = read_run(previous_log)
                    if (old['metadata']['executable_sha256'] != meta['executable_sha256'] or
                        old['metadata']['flags'] != meta['flags'] or
                        old['metadata'].get('exact_output') != (a.window if a.exact_output else None)):
                        raise ValueError(f'{prefix}: refusing to resume a different executable or protocol')
                    print('resume complete', prefix, flush=True)
                    continue
            print(prefix, flush=True)
            # Time/load are inside the lock, excluding lock contention from process startup/RSS.
            cmd = ['flock', '/tmp/botw-render.lock', 'sh', '-c',
                   'cat /proc/loadavg; exec /usr/bin/time -v timeout -k 10 300 "$1"', 'bench', str(a.executable.resolve())]
            if a.exact_output:
                if a.mode != 'gpu': raise ValueError('--exact-output requires X11 GPU mode')
                cmd = ['flock', '/tmp/botw-render.lock', 'sh', '-c',
                       'cat /proc/loadavg; exec python3 tools/performance_window.py "$1" /usr/bin/time -v timeout -k 10 600 "$2"',
                       'bench', a.window, str(a.executable.resolve())]
                meta['exact_output'] = a.window
            if a.locked: cmd = cmd[2:] # caller owns the one outer render lock
            Path(str(prefix)+'.environment.json').write_text(json.dumps(meta, indent=2)+'\n')
            with Path(str(prefix)+'.log').open('w') as log:
                subprocess.run(cmd, env=e, stdout=log, stderr=subprocess.STDOUT, check=True)
            meta['load_end'] = Path('/proc/loadavg').read_text().strip()
            Path(str(prefix)+'.environment.json').write_text(json.dumps(meta, indent=2)+'\n')
    report(a.output)


def read_run(p):
    s=p.read_text(); meta=json.loads(Path(str(p)[:-4]+'.environment.json').read_text())
    rows=[[float(x) for x in line.split()[2:]] for line in s.splitlines() if line.startswith('frame sample:')]
    steady=[r for r in rows if r[0]>=241]
    dims=re.findall(r'; (\d+x\d+) scale ([\d.]+)',s)
    fixed = meta['flags'].get('BOTW_SCALE')
    expected = f"{float(fixed):.2f}" if fixed is not None else 'dynamic'
    if not dims or (fixed is not None and any(scale!=expected for _,scale in dims)): raise ValueError(f'{p}: missing/variable dimensions or scale')
    expected_samples=int(meta['flags']['SLOPPY_FRAMES'])-240
    if len(steady)!=expected_samples: raise ValueError(f'{p}: expected {expected_samples} intervals, got {len(steady)}')
    if len({d for d,_ in dims[2:]})!=1: raise ValueError(f'{p}: resizing in steady state')
    if '-gpu-' in p.name and ('egl window surface' not in s or 'BOTW_NOVSYNC:' in s): raise ValueError(f'{p}: X11 swap interval failed')
    if meta['flags'].get('SLOPPY_PLATFORM')=='wayland':
        if 'wayland' not in s or 'dma-buf' not in s: raise ValueError(f'{p}: GPU Wayland presentation was not confirmed')
        if meta['flags'].get('SLOPPY_PRESENT')=='mailbox' and 'dma-buf, mailbox,' not in s: raise ValueError(f'{p}: mailbox runtime was not confirmed')
    if meta.get('exact_output') and any(d != meta['exact_output'] for d, _ in dims):
        raise ValueError(f'{p}: actual size differs from required {meta["exact_output"]}')
    batches=[]
    for passes,total in re.findall(r'^gpu ms:(.*?)= ([\d.]+)$',s,re.M):
        b={k:float(v) for k,v in re.findall(r'(\S+) ([\d.]+)',passes)};b['total']=float(total);batches.append(b)
    gpu=batches[2:]
    result={'metadata':meta,'output':dims[-1][0],'scale':expected,'samples':len(steady),
            'load_start':s.splitlines()[0],'gpu_batches':batches,'gpu_median':{k:statistics.median(b[k] for b in gpu) for k in gpu[0]} if gpu else {},
            'gpu_peak_batch':max((b['total'] for b in gpu),default=None),
            'gpu_peak_all_batches':max((b['total'] for b in batches),default=None),
            'gpu_skipped':re.findall(r'^gpu skipped:.*$',s,re.M),
            'load_sections':re.findall(r'^  \w+ [\d.]+s$',s,re.M),
            'first_frame':re.findall(r'^first frame:.*$',s,re.M),
            'load_total':re.findall(r'^.*loaded.*$',s,re.M),
            'rss_kib':int(re.search(r'Maximum resident set size \(kbytes\): (\d+)',s)[1]),
            'early_worst':max((r[1] for r in rows if r[0]<=120),default=None),
            'scene_samples':re.findall(r'^perf scene:.*$',s,re.M),
            'shadow_triangle_upper_bounds':re.findall(r'^veg triangles per frame:.*$',s,re.M)}
    for label,index in [('interval',1),('game_wall',2),('game_thread',4),('present',11),('residual_gap',12),('runtime_thread',13)]:
        v=[r[index] for r in steady]; result[label]={k:f(v) for k,f in [('mean',statistics.mean),('p50',lambda v:percentile(v,.5)),('p95',lambda v:percentile(v,.95)),('p99',lambda v:percentile(v,.99)),('worst',max)]}
    early = [r for r in rows if 1 <= r[0] <= 600]
    if int(meta['flags']['SLOPPY_FRAMES']) >= 600 and len(early) != 600:
        raise ValueError(f'{p}: expected all first 600 intervals, got {len(early)}')
    result['first_600'] = {'samples': len(early)}
    for label, index in [('interval', 1), ('game_wall', 2), ('game_thread', 4), ('present', 11)]:
        v = [r[index] for r in early]
        result['first_600'][label] = {'p50': percentile(v, .5), 'p95': percentile(v, .95),
                                      'p99': percentile(v, .99), 'worst': max(v),
                                      'over_16_7_ms': sum(x > 16.7 for x in v),
                                      'over_33_3_ms': sum(x > 33.3 for x in v)}
    result['load_seconds'] = float(re.search(r'^loaded in ([\d.]+)s$', s, re.M)[1])
    result['load_stage_seconds'] = {k: float(v) for k, v in re.findall(r'^  (\w+) ([\d.]+)s$', s, re.M)}
    result['slowest_intervals']=sorted(steady,key=lambda r:-r[1])[:8]
    result['long_frames']=sum(r[1]>result['interval']['p50']*1.5+1 for r in steady)
    result['interval_batches'] = []
    for start in range(241, int(meta['flags']['SLOPPY_FRAMES']) + 1, 120):
        batch = [r[1] for r in steady if start <= r[0] < start + 120]
        if len(batch) != 120: raise ValueError(f'{p}: incomplete late interval batch at {start}')
        result['interval_batches'].append({'first_frame': start, 'last_frame': start + 119,
            'p50': percentile(batch, .5), 'p95': percentile(batch, .95),
            'p99': percentile(batch, .99), 'worst': max(batch)})
    result['shader_cache_hits'] = len(re.findall(r'^    shader cache hit ', s, re.M))
    result['terrain_upload_details'] = re.findall(r'^    terrain .*$', s, re.M)
    result['memory_hwm_samples'] = [{'frame': int(f), 'hwm_kib': int(m)} for f,m in
                                     re.findall(r'^perf memory: frame (\d+) hwm_kib (\d+)$', s, re.M)]
    result['route_samples'] = re.findall(r'^perf route:.*$', s, re.M)
    result['phases'] = re.findall(r'^perf phase:.*$', s, re.M)
    if meta['flags'].get('BOTW_WEATHER_SEQ') == CASES['mixed']['BOTW_WEATHER_SEQ']:
        if len(result['phases']) != 7 or len(result['memory_hwm_samples']) != 61:
            raise ValueError(f'{p}: mixed-v1 phase/memory evidence incomplete')
        route = result['route_samples'][-1]
        counts = dict(re.findall(r'(distance|camera|engaged|swing|fire_fx|indoor) ([\d.]+)', route))
        if any(float(counts.get(k, 0)) <= 0 for k in ['distance', 'camera', 'engaged', 'swing', 'fire_fx', 'indoor']):
            raise ValueError(f'{p}: mixed-v1 missing active workload: {route}')
    result['output_viewports'] = [{'frame':int(f), 'client':int(c), 'width':int(w), 'height':int(h), 'resizes':int(n)}
        for f,c,w,h,n in re.findall(r'^benchmark viewport: frame (\d+) client (\d+) (\d+)x(\d+) resizes (\d+)$',s,re.M)]
    if meta.get('window_loop') == 'client':
        viewport = result['output_viewports']
        expected_frames = list(range(0, int(meta['flags']['SLOPPY_FRAMES'])+1, 120))
        if [v['frame'] for v in viewport] != expected_frames:
            raise ValueError(f'{p}: missing actual-client viewport evidence')
        width, height = map(int, meta['flags']['SLOPPY_WINDOW'].split('x'))
        if any((v['width'], v['height']) != (width, height) or v['client'] != viewport[0]['client'] for v in viewport):
            raise ValueError(f'{p}: actual client or viewport changed')
        if any(v['resizes'] != viewport[0]['resizes'] for v in viewport):
            raise ValueError(f'{p}: client resized during measured frames')
    result['motion_samples'] = re.findall(r'^perf motion:.*$', s, re.M)
    result['autosaves'] = re.findall(r'^perf autosave:.*$', s, re.M)
    result['cpu_spikes'] = re.findall(r'^long cpu .*$', s, re.M)
    result['cpu_wall_thread_spikes'] = re.findall(r'^cpu wall/thread:.*$', s, re.M)
    result['cpu_averages'] = re.findall(r'^cpu avg ms:.*$', s, re.M)
    result['vegetation_profiles'] = re.findall(r'^veg cpu:.*$', s, re.M)
    return result



def pool_runs(root, runs):
    """Pool raw intervals, rather than averaging per-run percentiles."""
    groups = {}
    for name, result in runs.items():
        view = name.split('-gpu-')[0].split('-paced-')[0].split('-mailbox-')[0]
        key = f"{view}/{result['output']}/{result['scale']}"
        groups.setdefault(key, []).append((name, result))
    pooled = {}
    for key, group in groups.items():
        protocols = {(r['metadata'].get('executable_sha256'), r['metadata']['flags']['SLOPPY_FRAMES'],
                      r['metadata'].get('shader_cache_protocol'),r['metadata'].get('window_loop','native')) for _,r in group}
        if len(protocols) != 1: raise ValueError(f'{key}: refusing to pool different executables or protocols')
        rows = []
        for name, _ in group:
            rows += [[float(x) for x in line.split()[2:]] for line in (root/(name+'.log')).read_text().splitlines() if line.startswith('frame sample:')]
        steady = [r for r in rows if r[0] >= 241]
        early = [r for r in rows if 1 <= r[0] <= 600]
        out = {'runs': [n for n,_ in group], 'load_seconds': [r['load_seconds'] for _,r in group],
               'rss_kib': [r['rss_kib'] for _,r in group], 'steady_samples': len(steady),
               'first_600_samples': len(early), 'first_600': {}}
        for label, col in [('interval',1), ('game_wall',2), ('game_thread',4), ('present',11)]:
            for source, destination in [(steady,out), (early,out['first_600'])]:
                v = [r[col] for r in source]
                destination[label] = {'p50':percentile(v,.5), 'p95':percentile(v,.95),
                    'p99':percentile(v,.99), 'worst':max(v), 'over_16_7_ms':sum(x>16.7 for x in v),
                    'over_33_3_ms':sum(x>33.3 for x in v)}
        gpu = [b['total'] for _,r in group for b in r['gpu_batches'][2:]]
        out['gpu_batch_median_ms'] = statistics.median(gpu) if gpu else None
        pooled[key] = out
    return pooled

def report(root):
    runs={p.stem:read_run(p) for p in sorted(root.glob('*.log')) if Path(str(p)[:-4]+'.environment.json').exists()}
    Path(root/'summary.json').write_text(json.dumps(runs,indent=2)+'\n')
    Path(root/'pooled-summary.json').write_text(json.dumps(pool_runs(root,runs),indent=2)+'\n')
    for n,r in runs.items():
        g=r['gpu_median'];print(f"{n}: {r['output']} @ {r['scale']}, GPU {g.get('total')} peak {r['gpu_peak_batch']}; p99 {r['interval']['p99']:.2f}, worst {r['interval']['worst']:.2f}, RSS {r['rss_kib']/1024:.1f} MiB")


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('capture');c.add_argument('executable',type=Path);c.add_argument('output',type=Path)
    c.add_argument('--views',nargs='+',choices=CASES,default=['forest','fire','camp','pond','overlook','snow','storm','combat']);c.add_argument('--repeats',type=int,default=3)
    c.add_argument('--frames',type=int,default=720);c.add_argument('--scale',type=float,default=.8)
    c.add_argument('--window',default='2133x1200');c.add_argument('--revision',required=True)
    c.add_argument('--mode',choices=['gpu','paced','mailbox'],default='gpu')
    c.add_argument('--window-loop', choices=['native', 'client'], default='native', help='client uses performance_game/output or the route client-size switch')
    c.add_argument('--locked', action='store_true', help='caller already holds /tmp/botw-render.lock; never acquire a nested lock')
    c.add_argument('--resume', action='store_true', help='validate and keep complete existing runs; capture missing repeats')
    c.add_argument('--shader-cache', choices=['warm', 'disabled'], default='warm', help='per-process NVIDIA cache protocol (no cache deletion)')
    c.add_argument('--prepared-assets', choices=['prepared', 'disabled'], default='prepared', help='disable optional CPU packs to measure generation fallback without deleting assets')
    c.add_argument('--exact-output', action='store_true', help='hide/resize only the child X11 window; verify exact pixels')
    stage = c.add_mutually_exclusive_group()
    stage.add_argument('--cpu-trace',action='store_true',help='attribute game CPU spikes in uncapped GPU runs too')
    stage.add_argument('--no-stage-trace',action='store_true',help='retain raw frame CPU measurements without per-stage BOTW_CPU instrumentation')
    c.add_argument('--cpu-trace-ms',type=float,help='diagnostic stage trace threshold (default 10 ms)')
    c.add_argument('--dynamic-scale',action='store_true',help='exercise the production scale controller without BOTW_SCALE')
    c.add_argument('--gpu-frame-trace',action='store_true',help='retain nonblocking per-frame GPU pass times in addition to 120-frame batches')
    r=sub.add_parser('report');r.add_argument('output',type=Path)
    a=p.parse_args();capture(a) if a.command=='capture' else report(a.output)

if __name__=='__main__':main()
