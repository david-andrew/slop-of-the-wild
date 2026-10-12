#!/bin/bash
# Paired critic-camera GPU timings, one lock for the complete alternating batch.
# Invoke directly; do not wrap this self-locking script in another flock.
# CLIFF_GPU_SCENE=talus|overview selects another view. For a fixed full-body
# Talus camera, pass prepared talus_visual_check binaries and TALUS_VISUAL=awake.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ${1:-} != --locked ]]; then
    exec flock /tmp/botw-render.lock "$PWD/tools/cliff_gpu_check.sh" --locked "$@"
fi
shift
python3 - "$@" <<'PY'
import json, os, re, statistics, subprocess, sys
from pathlib import Path
from PIL import Image
if len(sys.argv) != 4:
    sys.exit('Usage: tools/cliff_gpu_check.sh before-game after-game output-dir')
binaries = dict(zip(('before','after'), map(lambda p: str(Path(p).resolve()), sys.argv[1:3])))
out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
clean = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_'))}
scene = os.environ.get('CLIFF_GPU_SCENE', 'cliffs')
views = {
    'cliffs': {'BOTW_SKIP':'1', 'BOTW_CAM':'-1600,235,1815,1.2,-0.15'},
    'talus': {'BOTW_SKIP':'1', 'BOTW_AT':'-1087.75,1669.68,0'},
    'overview': {'BOTW_SKIP':'1', 'BOTW_CAM':'-700,330,2150,-0.8,-0.35'},
}
assert scene in views, f'unknown GPU scene: {scene}'
results = {'before':[], 'after':[]}
for repeat in range(3):
    for label in (('before','after') if repeat % 2 == 0 else ('after','before')):
        image = out/f'{label}-{repeat}.png'
        settings = {**clean, **views[scene],
                    'BOTW_GPU':'1','BOTW_NOVSYNC':'1','BOTW_SCALE':'1.0',
                    'SLOPPY_PLATFORM':'x11','SLOPPY_WINDOW':'1280x720',
                    'SLOPPY_FRAMES':'720','SLOPPY_SCREENSHOT':str(image)}
        with (out/f'{label}-{repeat}.log').open('w') as log:
            subprocess.run(['python3','tools/cliff_capture_window.py','1280x720','timeout','300',binaries[label]],env=settings,stdout=log,stderr=subprocess.STDOUT,check=True)
        assert Image.open(image).size == (1280,720)
        lines = (out/f'{label}-{repeat}.log').read_text().splitlines()
        samples = [float(re.search(r'= ([\d.]+)$',line)[1]) for line in lines if line.startswith('gpu ms:')]
        assert len(samples) >= 4, f'insufficient timer-query samples: {label}/{repeat}'
        steady = samples[2:]
        results[label].append(statistics.median(steady))
        print(f'{label}/{repeat}: steady GPU median {results[label][-1]:.2f} ms',flush=True)
before, after = (statistics.median(results[k]) for k in ('before','after'))
report = dict(scene=scene, runs=results, before_ms=before, after_ms=after, delta_ms=after-before,
              delta_percent=(after/before-1)*100, resolution=[1280,720])
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'GPU: {before:.2f} -> {after:.2f} ms ({after-before:+.2f} ms; {(after/before-1)*100:+.1f}%)')
assert after <= before * 1.05 + 0.10, 'GPU regression outside 5% + 0.10 ms timing tolerance'
print(f'PASS paired {scene} GPU budget')
PY
