#!/usr/bin/env python3
"""Matched round-65 landscape follow-up against 500126f, in build/round85.

prepare before|after; capture before|after|both [views...]; perf [views...]; pairs.
Each render owns one flock, released before the next launch.
Never wrap this script in another flock.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/round85/landscape'
BASE = '500126f'
PERF_VIEWS = ('cliffs', 'overview', 'overlook', 'forest', 'temple', 's2ceil')
VIEWS = {
    'cliffs': {'BOTW_CAM': '-1600,235,1815,1.2,-0.15'},
    'pool': {'BOTW_CAM': '-1565,119,1858,1.22,0.22'},
    'close': {'BOTW_CAM': '-1549.128,180,1785,1.5707963,0'},
    'crown': {'BOTW_CAM': '-1380,288,1837,-1.78,-0.65'},
    'overview': {'BOTW_CAM': '-700,330,2150,-0.8,-0.35', 'BOTW_HOUR': '6.6'},
    'overview-day': {'BOTW_CAM': '-700,330,2150,-0.8,-0.35'},
    'overlook': {'BOTW_AT': '-1050,1828,-2.36'},
    'plateau-overlook': {'BOTW_CAM': '-1024,255,1799,0.80,-0.18'},
    'forest': {'BOTW_AT': '-1000,1620,3.14'},
    'temple': {'BOTW_CAM': '-802,237,1900,-2.967,-0.14'},
    'temple-side': {'BOTW_CAM': '-774,239,1915,-2.67,-0.16'},
    's2ceil': {'BOTW_SHRINE': '2', 'BOTW_CAM': '-400,2.5,1994,0,1.5607963'},
    's2roof-wide': {'BOTW_SHRINE': '2', 'BOTW_CAM': '-402,0.6,1998,0,0.55'},
    's2eave': {'BOTW_SHRINE': '2', 'BOTW_CAM': '-411,0.6,1992,1.5707963,0.5'},
    's2shaft': {'BOTW_SHRINE': '2', 'BOTW_CAM': '-400,2.5,2002,0,1.5607963'},
    's2up-pan': {'BOTW_SHRINE': '2', 'SLOPPY_INPUT': '100:down+,140:down-,180:right+,339:right-'},
}

def prepare(phase):
    out = OUT / phase
    game = out / 'game'
    game.mkdir(parents=True, exist_ok=True)
    for p in (ROOT/'game').glob('*.jo'):
        (game/p.name).write_bytes(subprocess.check_output(['git', 'show', f'{BASE}:game/{p.name}'], cwd=ROOT) if phase == 'before' else p.read_bytes())
    source = (game/'main.jo').read_text()
    for p in game.glob('*.jo'):
        source = source.replace(f"'{p.name}'", f"'{p}'")
    source = source.replace('update = (dt0: f64):', 'production_update = (dt0: f64):')
    source += f"\nuse '{ROOT/'tools/performance_output.jo'}'\n"
    source += '''
update = (dt: f64):
    freeze = to_int(env("ROUND85_FREEZE") ?? "0") ?? 0
    if freeze == 0 or frame_number() <= freeze:
        production_update(dt)
        if free_cam and env("BOTW_SHRINE") != none: shrines_update(1.0 / 60.0)
    else: frame_stats_begin(post.scale)
main = (): performance_output_run(update, draw)
'''
    (out/'main.jo').write_text(source)
    with (out/'build.log').open('w') as log:
        subprocess.run(['sloppy/bin/sloppy', 'build', str(out/'main.jo'), '-o', str(out/'game-bin')], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    (out/'sources.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in game.glob('*.jo')}, indent=2)+'\n')
    print('prepared', phase, flush=True)

def capture(phase, view, perf=False, rep=0, motion=False):
    out = OUT/phase
    name = f'{view}-perf-{rep}' if perf else view
    dest = out/name
    env = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'ROUND'))}
    env.update(BOTW_SKIP='1', BOTW_TOWER='1', BOTW_HOUR='11', BOTW_TIMESCALE='0', BOTW_WEATHER='clear', BOTW_NOVSYNC='1', BOTW_NO_PREPARED_ASSETS='1', BOTW_SCALE='1', SLOPPY_PLATFORM='x11', SLOPPY_VSYNC='0', SLOPPY_WINDOW='1280x720', SLOPPY_FRAMES=os.environ.get('ROUND85_PERF_FRAMES','1440') if perf else '360', SLOPPY_SCREENSHOT=str(dest.with_suffix('.png')))
    env.update(VIEWS[view])
    if perf: env.update(BOTW_FRAME_LOG='1', BOTW_GPU='1', BOTW_GPU_FRAME_LOG='1', ROUND85_FREEZE='360')
    if motion:
        sequence=out/(view+'-motion')
        sequence.mkdir(exist_ok=True)
        env.update(BOTW_CAPTURE_DIR=str(sequence),BOTW_CAPTURE_EVERY='10')
    with dest.with_suffix('.log').open('w') as log:
        command=['python3', 'tools/performance_window.py', '1280x720', 'timeout', '180', str(out/'game-bin')]
        command=['flock','/tmp/botw-render.lock',*command]
        subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    assert Image.open(dest.with_suffix('.png')).size == (1280,720)
    row = {'binary_sha256':hashlib.sha256((out/'game-bin').read_bytes()).hexdigest(), 'env':{k:v for k,v in env.items() if k.startswith(('BOTW_', 'SLOPPY_', 'ROUND'))}}
    if perf:
        rows = [[float(x) for x in l.split()[2:]] for l in dest.with_suffix('.log').read_text().splitlines() if l.startswith('frame sample:')]
        rows = [r for r in rows if r[0] > 480]
        assert len(rows) >= 950
        def p99(col):
            samples=sorted(r[col] for r in rows)
            return samples[math.ceil(len(samples)*.99)-1]
        row['samples'] = len(rows)
        row['frame_p99_ms'] = p99(1)
        row['cpu_p99_ms'] = p99(2)
    dest.with_suffix('.json').write_text(json.dumps(row, indent=2)+'\n')
    print(phase, name, row.get('frame_p99_ms', 'captured'), flush=True)

def pairs():
    for view in VIEWS:
        paths = [OUT/p/(view+'.png') for p in ('before','after')]
        if not all(p.exists() for p in paths): continue
        im = Image.new('RGB', (1280,1488), '#202629')
        draw = ImageDraw.Draw(im)
        for i,p in enumerate(paths):
            im.paste(Image.open(p), (0,i*744+24))
            draw.text((12,i*744+6), ('BEFORE 500126f' if i==0 else 'AFTER')+' / '+view, fill='white')
        im.save(OUT/(view+'-pair.png'))

if __name__ == '__main__':
    os.chdir(ROOT)
    mode=sys.argv[1]
    if mode=='prepare': prepare(sys.argv[2])
    elif mode=='capture':
        phases=('before',os.environ.get('ROUND85_AFTER_PHASE','after')) if sys.argv[2]=='both' else (sys.argv[2],)
        for phase in phases:
            for view in sys.argv[3:] or VIEWS:
                meta=OUT/phase/(view+'.json')
                if meta.exists() and json.loads(meta.read_text())['env'].get('BOTW_CAM')!=VIEWS[view].get('BOTW_CAM'):
                    rejected=OUT/phase/'rejected-camera-fixtures'
                    rejected.mkdir(exist_ok=True)
                    for suffix in ('.png','.log','.json'):
                        p=OUT/phase/(view+suffix)
                        if p.exists():shutil.copy2(p,rejected/p.name)
                capture(phase,view)
    elif mode=='motion':
        for view in sys.argv[3:] or ('cliffs','pool'): capture(sys.argv[2], view, motion=True)
    elif mode=='perf':
        for view in sys.argv[2:] or PERF_VIEWS:
            start=int(os.environ.get('ROUND85_PERF_START','0'))
            count=int(os.environ.get('ROUND85_PERF_COUNT','3'))
            for rep in range(start,start+count):
                after=os.environ.get('ROUND85_AFTER_PHASE','after')
                for phase in (('before',after) if rep%2==0 else (after,'before')): capture(phase,view,True,rep)
    elif mode=='pairs': pairs()
    else: raise SystemExit(__doc__)
