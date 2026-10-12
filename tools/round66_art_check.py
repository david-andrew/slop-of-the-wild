#!/usr/bin/env python3
"""Matched material-paint evidence. Self-locks capture batches and each paired GPU view; do not wrap in flock.

Build build/round66/{before,after}-game from the complete production entry point
plus tools/performance_output.jo. Captures and paired GPU samples use those frozen
binaries. Raw evidence stays ignored. Run capture before|after, gpu, or prepare before|after.
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
ROOT = Path('build/round66')
VIEWS = {
    'wake': ({}, 330),
    'combat': ({'BOTW_SKIP':'1', 'BOTW_AT':'-1439,1614,0',
                'BOTW_GIVE':'travelers_sword,travelers_shield',
                'SLOPPY_INPUT':'10:w+,50:w-,60:k+,90:j+,91:j-,150:j+,151:j-'}, 180),
    'cliffs': ({'BOTW_SKIP':'1', 'BOTW_CAM':'-1600,235,1815,1.2,-0.15'}, 180),
    'pond': ({'BOTW_SKIP':'1', 'BOTW_AT':'-1190,1665,-0.9'}, 300),
    'title': ({'BOTW_SKIP':'1', 'BOTW_TITLE':'1', 'BOTW_AT':'-1024,1799,0'}, 720),
    'forest': ({'BOTW_SKIP':'1', 'BOTW_AT':'-1000,1620,3.14'}, 300),
}

BASELINE = 'c4ec99d8cc3b5b8ba7d0f333f89917c76bfc5651'

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
    source += "\nuse '../../tools/performance_output.jo'\nupdate = (dt: f64):\n    freeze = to_int(env(\"ROUND66_FREEZE\") ?? \"0\") ?? 0\n    if freeze == 0 or frame_number() <= freeze: production_update(dt)\n    else: frame_stats_begin(post.scale)\nmain = (): performance_output_run(update, draw)\n"
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
    env = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'ROUND66_'))}
    env.update(BOTW_HOUR='11', BOTW_WEATHER='clear', BOTW_SCALE='1',
               BOTW_NOVSYNC='1', BOTW_NO_PREPARED_ASSETS='1', SLOPPY_PLATFORM='x11',
               SLOPPY_WINDOW=size, SLOPPY_FRAMES=str((discard + 4) * 120 if gpu else frame),
               SLOPPY_SCREENSHOT=str(out.with_suffix('.png').resolve()))
    env.update(flags)
    if gpu: env.update(BOTW_GPU='1', ROUND66_FREEZE=str(frame))
    with out.with_suffix('.log').open('w') as log:
        command = ['python3','tools/cliff_capture_window.py',size,'timeout','300',str(binary)]
        if not locked: command = ['flock','/tmp/botw-render.lock',*command]
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    assert Image.open(out.with_suffix('.png')).size == tuple(map(int,size.split('x')))
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == digest
    samples = [float(re.search(r'= ([\d.]+)$',line)[1]) for line in out.with_suffix('.log').read_text().splitlines() if line.startswith('gpu ms:')]
    row = dict(binary_sha256=digest, env={k:v for k,v in env.items() if k.startswith(('BOTW_', 'SLOPPY_', 'ROUND66_'))}, samples=samples)
    if gpu:
        assert len(samples) >= discard + 3, samples
        row['discard_batches'] = discard
        row['median_ms'] = statistics.median(samples[discard:])
    out.with_suffix('.json').write_text(json.dumps(row,indent=2)+'\n')
    print(phase, view, size, row.get('median_ms','captured'),flush=True)
    return row

if __name__ == '__main__':
    mode=sys.argv[1]
    if mode=='prepare': prepare(sys.argv[2])
    elif mode=='capture':
        result = subprocess.run(['flock','/tmp/botw-render.lock',sys.executable,__file__,'_capture',*sys.argv[2:]],
                                env={**os.environ,'ROUND66_RENDER_LOCKED':'1'})
        sys.exit(result.returncode)
    elif mode=='_capture':
        assert os.environ.get('ROUND66_RENDER_LOCKED') == '1'
        for view in sys.argv[3:] or VIEWS: run(sys.argv[2],view,'1280x720',locked=True)
    elif mode=='_gpu':
        # Internal child: the parent owns the sole flock for these six renders.
        assert os.environ.get('ROUND66_RENDER_LOCKED') == '1'
        size,view=sys.argv[2:]
        runs={p:[] for p in ['before','after']}
        for repeat in range(3):
            for phase in (['before','after'] if repeat%2==0 else ['after','before']):
                runs[phase].append(run(phase,view,size,True,repeat,locked=True)['median_ms'])
        b,a=[statistics.median(runs[p]) for p in ['before','after']]
        row=dict(before_ms=b,after_ms=a,delta_ms=a-b,limit_ms=b*1.03+.1,passed=a<=b*1.03+.1,runs=runs)
        (ROOT/'gpu'/f'{size}-{view}-summary.json').write_text(json.dumps(row,indent=2)+'\n')
        print(view,size,'PASS' if row['passed'] else 'FAIL',row,flush=True)
    elif mode=='gpu':
        # Resume immutable completed pairs; each view releases the shared lock.
        results={}
        pending=[]
        for size in ['1280x720','2133x1200']:
            for view in sys.argv[2:] or VIEWS:
                summary = ROOT/'gpu'/f'{size}-{view}-summary.json'
                valid = summary.exists()
                for phase in ['before','after']:
                    digest = hashlib.sha256((ROOT/f'{phase}-game').read_bytes()).hexdigest()
                    for repeat in range(3):
                        metadata = ROOT/'gpu'/f'{size}-{view}-{phase}-{repeat}.json'
                        valid = valid and metadata.exists()
                        if valid: valid = json.loads(metadata.read_text())['binary_sha256'] == digest
                # Queue independent paired groups together; flock still serializes
                # every renderer and releases between views for other queued work.
                child = None if valid else subprocess.Popen(
                    ['flock','/tmp/botw-render.lock',sys.executable,__file__,'_gpu',size,view],
                    env={**os.environ,'ROUND66_RENDER_LOCKED':'1'})
                pending.append((f'{size}/{view}',summary,child))
        failures=[]
        for key,summary,child in pending:
            if child is not None and child.wait() != 0:
                failures.append(key)
                continue
            results[key]=json.loads(summary.read_text())
            (ROOT/'gpu-summary.json').write_text(json.dumps(results,indent=2)+'\n')
        assert not failures, f'GPU capture failed: {failures}'
        sys.exit(any(not r['passed'] for r in results.values()))
