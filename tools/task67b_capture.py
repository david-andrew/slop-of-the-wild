#!/usr/bin/env python3
"""Matched close-up evidence; self-locking, never wrap this script in flock.
Before editing: prepare before; capture before. After editing: prepare after;
capture after; pairs. Each snapshot copies game sources and both hero models.
For CPU tails: measureprepare before; measureprepare after; compare SCENES.
The corrected timing probes hold the capture pose, discard another 120 frames,
and run ABBA under one short lock per scene. livecompare SCENES retains the
production update for an additional gameplay/monk/greeting CPU comparison.
TASK67B_PERF_FRAMES controls the sample length (1200 by default).
TASK67B_AFTER selects an alternate final snapshot; TASK67B_SERIES prefixes
repeat folders so later iterations retain the original measurements.
All binaries, source manifests, raw logs, settings and downscaled PNGs stay in
build/task67b. --locked is internal and requires a caller-owned render flock.
"""
import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/task67b'
SCENES = {
    'wake': (420, {}),
    'wake-standing': (520, {}),
    'greeting': (100, dict(BOTW_SKIP='1', BOTW_AT='-951,1876,2.5', SLOPPY_INPUT='5:w+,40:w-')),
    'gameplay': (180, dict(BOTW_SKIP='1', BOTW_AT='-1030,1805,1.57')),
    'monk': (180, dict(BOTW_SKIP='1', BOTW_TOWER='1', BOTW_SHRINE='2', BOTW_SHRINE_AT='3.5,0,-50,-1.2')),
}
def manifest(label):
    out=OUT/label
    files=[out/'game-bin',*(out/'game').glob('*.jo'),*(out/'models').glob('*.mdl')]
    (out/'manifest.json').write_text(json.dumps({str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2)+'\n')
def prepare(label):
    out=OUT/label; game=out/'game'; game.mkdir(parents=True,exist_ok=True)
    for p in (ROOT/'game').glob('*.jo'): shutil.copyfile(p,game/p.name)
    models=out/'models'; models.mkdir(exist_ok=True)
    p=game/'chars.jo'; s=p.read_text()
    for name in ('hero','hero_bare'):
        dest=models/(name+'.mdl'); shutil.copyfile(ROOT/'assets/models'/dest.name,dest)
        s=s.replace('assets/models/'+dest.name,str(dest))
    p.write_text(s)
    p=game/'main.jo'; s=p.read_text().replace('update = (dt0: f64):','production_update = (dt0: f64):')
    s+='''
weather_rng_restore(rng(31))
update = (dt: f64):
    hold=to_int(env("TASK67B_HOLD") ?? "0") ?? 0
    if hold==0 or frame_number()<=hold: production_update(dt)
    else: frame_stats_begin(post.scale)
'''
    s=s.replace('main = (): game_run(update, draw)', '')
    s+=f"\nuse '{ROOT/'tools/performance_output.jo'}'\nmain = (): performance_output_run(update,draw)\n"
    p.write_text(s)
    subprocess.run(['sloppy/bin/sloppy','build',str(p),'-o',str(out/'game-bin')],check=True)
    manifest(label)
def capture(label,names,perf):
    if '--locked' not in sys.argv:
        # Three processes at most, each bounded to 50 s. Release the shared
        # lock between batches so other workers can continue their renders.
        for first in range(0,len(names),3):
            subprocess.run(['flock','/tmp/botw-render.lock',sys.executable,__file__,
                'perf' if perf else 'capture',label,*names[first:first+3],'--locked'],check=True)
        return
    clean={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_','TASK67B_'))}
    for name in names:
        frames,flags=SCENES[name]
        flags=flags|dict(TASK67B_HOLD=str(0 if sys.argv[1]=="livecompare" else frames))
        if perf: frames=int(os.environ.get('TASK67B_PERF_FRAMES',1200))
        out=OUT/label/(('perf-' if perf else '')+name); out.mkdir(parents=True,exist_ok=True)
        settings=dict(BOTW_HOUR='11',BOTW_TIMESCALE='0',BOTW_WEATHER='clear',BOTW_SCALE='1',BOTW_NOVSYNC='1',SLOPPY_VSYNC='0',SLOPPY_PLATFORM='x11',SLOPPY_WINDOW='1280x720',SLOPPY_FRAMES=str(frames),SLOPPY_SCREENSHOT=str(out/'final.png'),BOTW_FRAME_LOG='1')|flags
        (out/'settings.json').write_text(json.dumps(settings,indent=2)+'\n')
        with (out/'run.log').open('w') as log:
            subprocess.run(['python3','tools/performance_window.py','1280x720','timeout','-k','5',('70' if sys.argv[1]=='long' else ('35' if sys.argv[1] in ('compare','livecompare') else '50')),str(OUT/label/'game-bin')],env=clean|settings,stdout=log,stderr=subprocess.STDOUT,check=True)
        im=Image.open(out/'final.png'); assert im.size==(1280,720); im.thumbnail((960,540)); im.save(out/'preview.png')
        values=[]
        for line in (out/'run.log').read_text().splitlines():
            if line.startswith('frame sample: '):
                row=line.split()[2:]
                if max(240,int(flags["TASK67B_HOLD"])+120 if perf else 240)<=int(row[0])<frames: values.append(float(row[4]))
        if values:
            values.sort(); stats=dict(samples=len(values),thread_cpu_p50_ms=values[len(values)//2],thread_cpu_p99_ms=values[min(len(values)-1,int(len(values)*.99))])
            (out/'cpu.json').write_text(json.dumps(stats,indent=2)+'\n')
            print(label,name,stats,flush=True)
        print('PASS capture',label,name,flush=True)
def long_compare(names):
    # Larger tail sample when short ABBA runs show substantial run-to-run noise.
    # Two 70 s bounded processes at most per lock; all shorter runs are retained.
    for name in names:
        if '--locked' not in sys.argv:
            subprocess.run(['flock','/tmp/botw-render.lock',sys.executable,__file__,
                'long',name,'--locked'],check=True)
            continue
        os.environ['TASK67B_PERF_FRAMES']='3600'
        for phase in ['before','after']:
            label=phase+'-long'
            folder=OUT/label; folder.mkdir(exist_ok=True)
            binary=folder/'game-bin'
            if not binary.exists(): os.link(OUT/(os.environ.get('TASK67B_AFTER','after')+'-cpu' if phase=='after' else 'before-cpu')/'game-bin',binary)
            capture(label,[name],True)
def compare(names):
    # ABBA repeated measurements share a short lock to bound machine-load drift.
    # Four runs, each limited to 35 s; retain the original single-run evidence.
    for name in names:
        if '--locked' not in sys.argv:
            subprocess.run(['flock','/tmp/botw-render.lock',sys.executable,__file__,
                sys.argv[1],name,'--locked'],check=True)
            continue
        for phase,repeat in [('before',1),('after',1),('after',2),('before',2)]:
            label=os.environ.get('TASK67B_SERIES','')+phase+('-live-repeat' if sys.argv[1]=='livecompare' else '-repeat')+str(repeat)
            folder=OUT/label; folder.mkdir(exist_ok=True)
            binary=folder/'game-bin'
            if not binary.exists(): os.link(OUT/(os.environ.get('TASK67B_AFTER','after')+'-cpu' if phase=='after' else 'before-cpu')/'game-bin',binary)
            capture(label,[name],True)
def pairs(after="after"):
    for name in SCENES:
        paths=[OUT/label/name/'final.png' for label in ('before',after)]
        if not all(p.exists() for p in paths): continue
        im=Image.new('RGB',(1280,384),(20,24,28)); d=ImageDraw.Draw(im)
        for i,p in enumerate(paths):
            src=Image.open(p); src.thumbnail((640,360)); im.paste(src,(i*640,24)); d.text((i*640+6,6),f'{p.parts[-3]} / {name}',fill='white')
        im.save(OUT/(name+'-pair.png'))
if __name__=='__main__':
    os.chdir(ROOT)
    action=sys.argv[1]
    if action=='pairs': pairs(sys.argv[2] if len(sys.argv)>2 else 'after')
    elif action=='long': long_compare([n for n in sys.argv[2:] if n!='--locked'])
    elif action in ('compare','livecompare'): compare([n for n in sys.argv[2:] if n!='--locked'])
    elif action=='measureprepare':
        source=OUT/sys.argv[2]; dest=OUT/(sys.argv[2]+'-cpu')
        shutil.copytree(source/'game',dest/'game',dirs_exist_ok=True)
        p=dest/'game/main.jo'; s=p.read_text()
        anchor='    if hold==0 or frame_number()<=hold: production_update(dt)\n'
        if anchor+'    else:' not in s: s=s.replace(anchor,anchor+'    else: frame_stats_begin(post.scale)\n')
        p.write_text(s)
        subprocess.run(['sloppy/bin/sloppy','build',str(p),'-o',str(dest/'game-bin')],check=True)
        manifest(sys.argv[2]+'-cpu')
    elif action=='prepare': prepare(sys.argv[2])
    else: capture(sys.argv[2],[n for n in sys.argv[3:] if n!='--locked'] or list(SCENES),action=='perf')
