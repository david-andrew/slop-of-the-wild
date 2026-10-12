#!/usr/bin/env python3
"""Matched warm GPU samples at the default large-output scale. Self-locks the batch."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys

os.chdir(Path(__file__).resolve().parent.parent)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--locked', action='store_true', help=argparse.SUPPRESS)
parser.add_argument('--after-binary', type=Path, default=Path('build/round64/after/game'))
parser.add_argument('--output', type=Path, default=Path('build/round64/gpu'))
args = parser.parse_args()
if not args.locked:
    sys.exit(subprocess.run(['flock', '/tmp/botw-render.lock', sys.executable, __file__, '--locked', *sys.argv[1:]]).returncode)
out = args.output
out.mkdir(parents=True, exist_ok=True)
views = {
    'forest': dict(BOTW_SKIP='1', BOTW_AT='-1000,1620,3.14'),
    'golden': dict(BOTW_SKIP='1', BOTW_AT='-1030,1805,1.57', BOTW_HOUR='6.4'),
    'overview': dict(BOTW_SKIP='1', BOTW_CAM='-700,330,2150,-0.8,-0.35'),
    'snow': dict(BOTW_SKIP='1', BOTW_AT='-1060,2230,2.0', BOTW_GIVE='warm_doublet'),
    'talus': dict(BOTW_SKIP='1', BOTW_AT='-1087.75,1673.18,0', SLOPPY_INPUT='10:w+,150:w-'),
    'wet-forest': dict(BOTW_SKIP='1', BOTW_AT='-1000,1620,3.14', BOTW_HOUR='11', BOTW_WEATHER='storm'),
}
clean = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
report = dict(window='2133x1200', scale=0.8, warm_frames='241-700', budget_ms=20, runs={})
def percentile(v, p):
    return sorted(v)[math.ceil(len(v)*p)-1]
for index, (view, flags) in enumerate(views.items()):
    report['runs'][view] = {}
    for phase in (('before','after') if index%2==0 else ('after','before')):
        binary = (args.after_binary if phase == 'after' else Path('build/round64/before/game')).resolve()
        prefix = out/f'{view}-{phase}'
        settings = dict(clean, **flags, BOTW_NO_PREPARED_ASSETS='1', BOTW_GPU='1', BOTW_GPU_FRAME_LOG='1',
            BOTW_NOVSYNC='1', BOTW_SCALE='0.8', BOTW_FRAME_LOG='1', SLOPPY_STATS='log',
            SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='2133x1200', SLOPPY_FRAMES='720',
            SLOPPY_SCREENSHOT=str(prefix.with_suffix('.png').resolve()))
        prefix.with_suffix('.environment.json').write_text(json.dumps({k:v for k,v in settings.items() if k.startswith(('BOTW_','SLOPPY_'))},indent=2)+'\n')
        with prefix.with_suffix('.log').open('w') as log:
            subprocess.run([sys.executable,'tools/cliff_capture_window.py','2133x1200','timeout','300',str(binary)],env=settings,stdout=log,stderr=subprocess.STDOUT,check=True)
        text = prefix.with_suffix('.log').read_text()
        from PIL import Image
        assert Image.open(prefix.with_suffix('.png')).size==(2133,1200)
        gpu = [(int(f),float(ms)) for f,ms in re.findall(r'^gpu frame: (\d+) .*?= ([\d.]+)$',text,re.M)]
        values = [ms for f,ms in gpu if 241 <= f <= 700]
        assert len(values)>400, f'{view}/{phase}: insufficient warm GPU queries'
        intervals = [float(line.split()[3]) for line in text.splitlines() if line.startswith('frame sample:') and 241 <= int(line.split()[2]) <= 700]
        result = dict(samples=len(values), gpu_p50_ms=percentile(values,.5),gpu_p99_ms=percentile(values,.99),
            gpu_mean_ms=statistics.mean(values),gpu_worst_ms=max(values),interval_p99_ms=percentile(intervals,.99),
            binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
        report['runs'][view][phase]=result
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(f'{view}/{phase}: GPU p50/p99 {result["gpu_p50_ms"]:.2f}/{result["gpu_p99_ms"]:.2f} ms, {len(values)} warm queries',flush=True)
report['passed'] = all(r['after']['gpu_p99_ms'] < report['budget_ms'] for r in report['runs'].values())
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
assert report['passed'], 'large-output GPU budget exceeded; see report.json'
print('PASS default-scale GPU budget: all six changed views below 20 ms at p99')
