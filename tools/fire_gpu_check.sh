#!/bin/bash
# Alternating native-resolution fire timings. Own one lock per render process.
# FIRE_GPU_WINDOW overrides the verified 2133x1200 scale-1 output.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - "$@" <<'PY'
import argparse, hashlib, json, math, os, re, statistics, subprocess, sys
from pathlib import Path
from PIL import Image
parser = argparse.ArgumentParser(description='Paired GPU and CPU fire budgets (3% + 0.10 ms).')
parser.add_argument('before_game'); parser.add_argument('after_game'); parser.add_argument('output_dir')
parser.add_argument('--verify', action='store_true')
parser.add_argument('--cpu-dir', type=Path, help='Separate production CPU runs with GPU queries off; retain profiled CPU as diagnostics')
args = parser.parse_args()
verify = args.verify
binaries = dict(zip(('before','after'), map(lambda p: str(Path(p).resolve()), (args.before_game,args.after_game))))
digests = {k:hashlib.sha256(Path(v).read_bytes()).hexdigest() for k,v in binaries.items()}
out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
clean = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_'))}
size = os.environ.get('FIRE_GPU_WINDOW', '2133x1200')
resolution = tuple(map(int, size.split('x')))
if verify:
    saved = json.loads((out/'report.json').read_text())
    assert saved['protocol']['binary_sha256'] == digests, 'verify requires the captured executables'
reports = {}
for scene, frames, scene_env in [('fire',720,{'BOTW_FIRE':'1'}),
                                 ('tentfire',960,{'BOTW_TENTFIRE':'5','BOTW_AT':'-955,1964,0'})]:
    results = {'before':[], 'after':[]}
    cpu = {'before':[], 'after':[]}
    profiled_cpu = {'before':[], 'after':[]}
    workloads = {'before':[], 'after':[]}
    for repeat in range(3):
        for label in (('before','after') if repeat % 2 == 0 else ('after','before')):
            picture = out/f'{scene}-{label}-{repeat}.png'
            settings = {**clean, 'BOTW_SKIP':'1', **scene_env,
                        'BOTW_HOUR':'11','BOTW_TIMESCALE':'0','BOTW_WEATHER':'clear',
                        'BOTW_GPU':'1','BOTW_NOVSYNC':'1','BOTW_SCALE':'1.0','BOTW_FRAME_LOG':'1',
                        'SLOPPY_VULKAN':'1','SLOPPY_VSYNC':'0',
                        'SLOPPY_PLATFORM':'x11','SLOPPY_WINDOW':size,
                        'SLOPPY_FRAMES':str(frames),'SLOPPY_SCREENSHOT':str(picture)}
            log_path = out/f'{scene}-{label}-{repeat}.log'
            assert hashlib.sha256(Path(binaries[label]).read_bytes()).hexdigest() == digests[label], 'timing executable changed'
            if not verify:
                with log_path.open('w') as log:
                    subprocess.run(['flock','/tmp/botw-render.lock','python3','tools/cliff_capture_window.py',size,'timeout','180',binaries[label]],env=settings,stdout=log,stderr=subprocess.STDOUT,check=True)
            assert hashlib.sha256(Path(binaries[label]).read_bytes()).hexdigest() == digests[label], 'timing executable changed during capture'
            assert Image.open(picture).size == resolution
            lines = log_path.read_text().splitlines()
            rows = [[float(v) for v in line.split()[2:]] for line in lines if line.startswith('frame sample:')]
            assert len(rows) == frames and [int(r[0]) for r in rows] == list(range(1, frames+1))
            profiled_cpu[label].extend(r for r in rows if r[0] >= 241)
            workloads[label].append([[r[0],r[5],r[6]] for r in rows])
            cpu_rows = rows
            if args.cpu_dir:
                stem = args.cpu_dir/f'{scene}-{label}-{repeat}'
                metadata = json.loads(Path(str(stem)+'-settings.json').read_text())
                assert metadata['binary_sha256'] == digests[label], 'CPU executable mismatch'
                cpu_env = metadata['environment']
                for key in ('BOTW_SKIP','BOTW_HOUR','BOTW_TIMESCALE','BOTW_WEATHER','BOTW_NOVSYNC','BOTW_SCALE','SLOPPY_VULKAN','SLOPPY_VSYNC','SLOPPY_WINDOW','SLOPPY_FRAMES',*scene_env):
                    assert cpu_env.get(key) == settings[key], f'CPU setting mismatch: {key}'
                assert cpu_env.get('BOTW_GPU','0') == '0', 'production CPU must disable GPU profiling'
                assert Image.open(Path(str(stem)+'.png')).size == resolution
                cpu_rows = [[float(v) for v in line.split()[2:]] for line in Path(str(stem)+'.log').read_text().splitlines() if line.startswith('frame sample:')]
                assert [[r[0],r[5],r[6]] for r in cpu_rows] == workloads[label][-1], 'CPU frame/instance/upload workload mismatch'
            cpu[label].extend(r for r in cpu_rows if r[0] >= 241)
            # Current Vulkan telemetry reports every resolved GPU frame. Keep
            # the legacy batch summaries usable for archived GL executables.
            samples = [float(re.search(r'= ([\d.]+)$',line)[1]) for line in lines
                       if line.startswith('gpu frame:') and int(line.split()[2]) >= 240]
            steady_gpu = samples
            if not samples:
                samples = [float(re.search(r'= ([\d.]+)$',line)[1]) for line in lines if line.startswith('gpu ms:')]
                steady_gpu = samples[2:]
            assert len(samples) >= 4, f'insufficient timer-query samples: {scene}/{label}/{repeat}'
            results[label].append(statistics.median(steady_gpu))
            print(f'{scene}/{label}/{repeat}: steady GPU median {results[label][-1]:.2f} ms',flush=True)
    before, after = (statistics.median(results[k]) for k in ('before','after'))
    assert workloads['before'] == workloads['after'], f'{scene}: instance/upload workload changed'
    percentile = lambda values, p: sorted(values)[math.ceil(len(values)*p)-1]
    cpu_stats = {label: {metric: {name: percentile([r[col] for r in rows], p)
                                for name, p in [('p50',.5),('p99',.99),('worst',1.0)]}
                        for metric,col in [('wall',2),('thread',4)]}
                 for label,rows in cpu.items()}
    reports[scene] = dict(cpu_ms=cpu_stats, samples_per_phase=len(cpu['before']), runs=results, before_ms=before, after_ms=after, delta_ms=after-before,
                         delta_percent=(after/before-1)*100, resolution=resolution)
    if args.cpu_dir:
        reports[scene]['profiled_cpu_p99_ms'] = {label:{metric:percentile([r[col] for r in rows],.99) for metric,col in [('wall',2),('thread',4)]} for label,rows in profiled_cpu.items()}
    (out/'report.json').write_text(json.dumps(reports,indent=2)+'\n')
    print(f'{scene} GPU: {before:.2f} -> {after:.2f} ms ({after-before:+.2f} ms; {(after/before-1)*100:+.1f}%)')
    print(f"{scene} CPU p99: thread {cpu_stats['before']['thread']['p99']:.3f} -> {cpu_stats['after']['thread']['p99']:.3f} ms; wall {cpu_stats['before']['wall']['p99']:.3f} -> {cpu_stats['after']['wall']['p99']:.3f} ms")
reports['protocol'] = dict(resolution=resolution, scale=1.0, order='AB/BA/AB', warmup_frames=240,
                           cpu='callback wall includes GPU waits; thread is main-thread execution',
                           cpu_source=str(args.cpu_dir.resolve()) if args.cpu_dir else 'GPU-profiled runs',
                           binary_sha256=digests)
(out/'report.json').write_text(json.dumps(reports,indent=2)+'\n')
for scene in ('fire','tentfire'):
    r = reports[scene]
    assert r['after_ms'] <= r['before_ms'] * 1.03 + 0.10, f'{scene}: GPU regression outside 3% + 0.10 ms timing tolerance'
    for metric in ('thread','wall'):
        assert r['cpu_ms']['after'][metric]['p99'] <= r['cpu_ms']['before'][metric]['p99'] * 1.03 + 0.10, f'{scene}: CPU {metric} p99 regression'
print('PASS paired fire GPU and CPU p99 budgets at '+size+' scale 1.0')
PY
