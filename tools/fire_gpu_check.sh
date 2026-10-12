#!/bin/bash
# Alternating native-resolution fire timings. Own one lock per render process.
# FIRE_GPU_WINDOW overrides the verified 2133x1200 scale-1 output.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - "$@" <<'PY'
import hashlib, json, math, os, re, statistics, subprocess, sys
from pathlib import Path
from PIL import Image
verify = len(sys.argv) == 5 and sys.argv[-1] == '--verify'
if verify: sys.argv.pop()
if len(sys.argv) != 4:
    sys.exit('Usage: tools/fire_gpu_check.sh before-game after-game output-dir [--verify]')
binaries = dict(zip(('before','after'), map(lambda p: str(Path(p).resolve()), sys.argv[1:3])))
digests = {k:hashlib.sha256(Path(v).read_bytes()).hexdigest() for k,v in binaries.items()}
out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
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
    workloads = {'before':[], 'after':[]}
    for repeat in range(3):
        for label in (('before','after') if repeat % 2 == 0 else ('after','before')):
            picture = out/f'{scene}-{label}-{repeat}.png'
            settings = {**clean, 'BOTW_SKIP':'1', **scene_env,
                        'BOTW_GPU':'1','BOTW_NOVSYNC':'1','BOTW_SCALE':'1.0','BOTW_FRAME_LOG':'1',
                        'SLOPPY_PLATFORM':'x11','SLOPPY_WINDOW':size,
                        'SLOPPY_FRAMES':str(frames),'SLOPPY_SCREENSHOT':str(picture)}
            log_path = out/f'{scene}-{label}-{repeat}.log'
            assert hashlib.sha256(Path(binaries[label]).read_bytes()).hexdigest() == digests[label], 'timing executable changed'
            if not verify:
                with log_path.open('w') as log:
                    subprocess.run(['flock','/tmp/botw-render.lock','python3','tools/cliff_capture_window.py',size,'timeout','300',binaries[label]],env=settings,stdout=log,stderr=subprocess.STDOUT,check=True)
            assert hashlib.sha256(Path(binaries[label]).read_bytes()).hexdigest() == digests[label], 'timing executable changed during capture'
            assert Image.open(picture).size == resolution
            lines = log_path.read_text().splitlines()
            rows = [[float(v) for v in line.split()[2:]] for line in lines if line.startswith('frame sample:')]
            assert len(rows) == frames and [int(r[0]) for r in rows] == list(range(1, frames+1))
            cpu[label].extend(r for r in rows if r[0] >= 241)
            workloads[label].append([[r[0],r[5],r[6]] for r in rows])
            samples = [float(re.search(r'= ([\d.]+)$',line)[1]) for line in lines if line.startswith('gpu ms:')]
            assert len(samples) >= 4, f'insufficient timer-query samples: {scene}/{label}/{repeat}'
            results[label].append(statistics.median(samples[2:]))
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
    (out/'report.json').write_text(json.dumps(reports,indent=2)+'\n')
    print(f'{scene} GPU: {before:.2f} -> {after:.2f} ms ({after-before:+.2f} ms; {(after/before-1)*100:+.1f}%)')
    print(f"{scene} CPU p99: thread {cpu_stats['before']['thread']['p99']:.3f} -> {cpu_stats['after']['thread']['p99']:.3f} ms; wall {cpu_stats['before']['wall']['p99']:.3f} -> {cpu_stats['after']['wall']['p99']:.3f} ms")
reports['protocol'] = dict(resolution=resolution, scale=1.0, order='AB/BA/AB', warmup_frames=240,
                           cpu='callback wall includes GPU waits; thread is main-thread execution',
                           binary_sha256=digests)
(out/'report.json').write_text(json.dumps(reports,indent=2)+'\n')
for scene in ('fire','tentfire'):
    r = reports[scene]
    assert r['after_ms'] <= r['before_ms'] * 1.03 + 0.10, f'{scene}: GPU regression outside 3% + 0.10 ms timing tolerance'
    for metric in ('thread','wall'):
        assert r['cpu_ms']['after'][metric]['p99'] <= r['cpu_ms']['before'][metric]['p99'] * 1.03 + 0.10, f'{scene}: CPU {metric} p99 regression'
print('PASS paired fire GPU and CPU p99 budgets at '+size+' scale 1.0')
PY
