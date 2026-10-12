#!/usr/bin/env python3
"""Matched master 1bc8463/current waterfall and far-woodland evidence.

Capture mode locks each game render itself; never wrap this script in flock.
The production entry point plus performance_output pins real X11 pixels.
Commands: prepare before|after; capture before|after [views...]; capture-batch before|after [views...]; gpu view size.
Frozen GPU pairs alternate phase order, with three repetitions.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
from PIL import Image

os.chdir(Path(__file__).resolve().parent.parent)
ROOT = Path('build/round69')
VIEWS = {
    'title': ({'BOTW_SKIP':'1', 'BOTW_TITLE':'1', 'BOTW_AT':'-1024,1799,0'}, 720),
    'overlook': ({'BOTW_SKIP':'1', 'BOTW_CAM':'-700,330,2150,-0.8,-0.35'}, 300),
    'waterfall': ({'BOTW_SKIP':'1', 'BOTW_CAM':'-1660,175,1888,1.24,-0.05'}, 300),
    'cliffs': ({'BOTW_SKIP':'1', 'BOTW_CAM':'-1600,235,1815,1.2,-0.15'}, 300),
}
BASELINE = '1bc8463'

def prepare(phase):
    ROOT.mkdir(parents=True, exist_ok=True)
    game = Path('game').resolve()
    if phase == 'before':
        game = (ROOT / 'before-source' / 'game').resolve()
        game.mkdir(parents=True, exist_ok=True)
        names = subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,'game'],text=True)
        for name in names.splitlines():
            if name.endswith('.jo'):
                (game / Path(name).name).write_bytes(subprocess.check_output(['git','show',f'{BASELINE}:{name}']))
    source = (game / 'main.jo').read_text()
    source = re.sub(r"(?m)^(use|from) '([^']+)'",lambda m:f"{m[1]} '{game / m[2]}'",source)
    source = source.replace('update = (dt0: f64):','production_update = (dt0: f64):')
    source += "\nuse '../../tools/performance_output.jo'\nupdate = (dt: f64):\n    freeze = to_int(env(\"ROUND69_FREEZE\") ?? \"0\") ?? 0\n    if freeze == 0 or frame_number() <= freeze: production_update(dt)\n    else: frame_stats_begin(post.scale)\nmain = (): performance_output_run(update, draw)\n"
    fixture = ROOT / f'{phase}.jo'
    fixture.write_text(source)
    subprocess.run(['sloppy/bin/sloppy','build',str(fixture),'-o',str(ROOT / f'{phase}-game')],check=True)
    manifest = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(game.glob('*.jo'))}
    (ROOT / f'{phase}-source.json').write_text(json.dumps(dict(baseline=BASELINE,modules=manifest),indent=2)+'\n')

def run(phase, view, size, gpu=False, repeat=0, locked=False):
    flags, frame = VIEWS[view]
    discard = max(4, frame // 120 + 1)
    out = ROOT / ('gpu' if gpu else phase) / (f'{size}-{view}-{phase}-{repeat}' if gpu else view)
    out.parent.mkdir(parents=True, exist_ok=True)
    binary = ROOT / f'{phase}-game'
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    env = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'ROUND69_'))}
    env.update(BOTW_HOUR='11', BOTW_WEATHER='clear', BOTW_SCALE='1',
               BOTW_NOVSYNC='1', BOTW_NO_PREPARED_ASSETS='1', SLOPPY_PLATFORM='x11',
               SLOPPY_WINDOW=size, SLOPPY_FRAMES=str((discard + 4) * 120 if gpu else frame),
               SLOPPY_SCREENSHOT=str(out.with_suffix('.png').resolve()))
    env.update(flags)
    if gpu: env.update(BOTW_GPU='1', BOTW_GPU_FRAME_LOG='1', ROUND69_FREEZE=str(frame), ROUND68_FREEZE=str(frame))
    with out.with_suffix('.log').open('w') as log:
        command = ['python3','tools/cliff_capture_window.py',size,'timeout','300',str(binary)]
        if not locked: command = ['flock','/tmp/botw-render.lock',*command]
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    assert Image.open(out.with_suffix('.png')).size == tuple(map(int,size.split('x')))
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == digest
    samples = [float(re.search(r'= ([\d.]+)$',line)[1]) for line in out.with_suffix('.log').read_text().splitlines() if line.startswith('gpu ms:')]
    row = dict(binary_sha256=digest, env={k:v for k,v in env.items() if k.startswith(('BOTW_', 'SLOPPY_', 'ROUND69_'))}, samples=samples)
    if gpu:
        assert len(samples) >= discard + 3, samples
        row['discard_batches'] = discard
        row['median_ms'] = statistics.median(samples[discard:])
    out.with_suffix('.json').write_text(json.dumps(row,indent=2)+'\n')
    print(phase, view, size, row.get('median_ms','captured'),flush=True)
    return row

VIEWS['mid'] = ({'BOTW_SKIP':'1','BOTW_CAM':'-1630,155,1890,1.24,-0.06'},300)
for weather in ('rain','storm'):
    for view in ('waterfall','cliffs','mid'):
        VIEWS[view+'-'+weather] = ({**VIEWS[view][0],'BOTW_WEATHER':weather},300)
for view in ('waterfall','cliffs','mid'):
    VIEWS[view+'-dawn'] = ({**VIEWS[view][0],'BOTW_HOUR':'6.4','BOTW_TIMESCALE':'0'},300)
VIEWS['mid-motion'] = (VIEWS['mid'][0],345)
if __name__ == '__main__':
    if sys.argv[1]=='prepare': prepare(sys.argv[2])
    elif sys.argv[1]=='capture':
        for v in sys.argv[3:] or VIEWS: run(sys.argv[2],v,'1280x720')
    elif sys.argv[1]=='capture-batch':
        phase=sys.argv[2]
        pending=[]
        digest=hashlib.sha256((ROOT/f'{phase}-game').read_bytes()).hexdigest()
        for view in sys.argv[3:] or VIEWS:
            path=ROOT/phase/f'{view}.json'
            flags,frame=VIEWS[view]
            row=json.loads(path.read_text()) if path.exists() else {}
            if (row.get('binary_sha256')==digest and
                row.get('env',{}).get('SLOPPY_FRAMES')==str(frame) and
                all(row.get('env',{}).get(k)==v for k,v in flags.items()) and
                (ROOT/phase/f'{view}.png').exists()):continue
            pending.append(view)
        for index in range(0,len(pending),4):
            subprocess.run(['flock','/tmp/botw-render.lock',sys.executable,__file__,'_capture-batch',phase,*pending[index:index+4]],check=True)
    elif sys.argv[1]=='_capture-batch':
        for view in sys.argv[3:]:run(sys.argv[2],view,'1280x720',locked=True)
    elif sys.argv[1]=='gpu':
        for rep in range(3):
            subprocess.run(['flock','/tmp/botw-render.lock',sys.executable,__file__,'_gpu-pair',sys.argv[2],sys.argv[3],str(rep)],check=True)
    elif sys.argv[1]=='_gpu-pair':
        rep=int(sys.argv[4])
        for phase in (('before','after') if rep%2==0 else ('after','before')):
            run(phase,sys.argv[2],sys.argv[3],gpu=True,repeat=rep,locked=True)
