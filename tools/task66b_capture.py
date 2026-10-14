#!/usr/bin/env python3
"""Matched task66b evidence. Each short batch owns its flock, never wrap this script.
Freeze current sources/models: prepare before|after. Render: capture LABEL [SCENES].
CPU tails: perf LABEL [SCENES], using the identical fixed-step scenes and 720p output.
Interleaved repeats: compare SCENES. --locked always requires caller-owned flock.
"""
import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/task66b'
SCENES = {
    'wake': (420, {}),
    'wake-standing': (520, {}),
    'greeting': (100, dict(BOTW_SKIP='1', BOTW_AT='-951,1876,2.5', SLOPPY_INPUT='5:w+,40:w-')),
    'gameplay': (180, dict(BOTW_SKIP='1', BOTW_AT='-1030,1805,1.57')),
    'boars': (150, dict(BOTW_SKIP='1', BOTW_CAM='-946,188.0,1660,-0.75,-0.12')),
    'enemy': (180, dict(BOTW_SKIP='1', BOTW_AT='-1439,1614,0')),
    'inventory': (60, dict(BOTW_SKIP='1', TASK66B_UI='inventory', BOTW_GIVE='travelers_sword')),
    'options': (60, dict(BOTW_SKIP='1', TASK66B_UI='options')),
    'map': (60, dict(BOTW_SKIP='1', BOTW_TOWER='1', TASK66B_UI='map')),
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
    production_update(dt)
    if let menu=env("TASK66B_UI"):
        invui.open=true
        invui.t=1.0
        invui.tab_t=1.0
        invui.tab=if menu=="options":OPTIONS_TAB else:(if menu=="map":MAP_TAB else:0)
        if menu=="map":
            shrines[0].activated=true
            shrines[1].activated=true
            shrines[1].done=true
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
    clean={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_','TASK66B_'))}
    for name in names:
        frames,flags=SCENES[name]
        if perf: frames=int(os.environ.get('TASK66B_PERF_FRAMES',600 if name.startswith('wake') else 960))
        out=OUT/label/(('perf-' if perf else '')+name); out.mkdir(parents=True,exist_ok=True)
        settings=dict(BOTW_HOUR='11',BOTW_WEATHER='clear',BOTW_SCALE='1',BOTW_NOVSYNC='1',SLOPPY_VSYNC='0',SLOPPY_PLATFORM='x11',SLOPPY_WINDOW='1280x720',SLOPPY_FRAMES=str(frames),SLOPPY_SCREENSHOT=str(out/'final.png'),BOTW_FRAME_LOG='1')|flags
        (out/'settings.json').write_text(json.dumps(settings,indent=2)+'\n')
        with (out/'run.log').open('w') as log:
            subprocess.run(['python3','tools/performance_window.py','1280x720','timeout','-k','5',('70' if sys.argv[1]=='long' else ('35' if sys.argv[1]=='compare' else '50')),str(OUT/label/'game-bin')],env=clean|settings,stdout=log,stderr=subprocess.STDOUT,check=True)
        im=Image.open(out/'final.png'); assert im.size==(1280,720); im.thumbnail((960,540)); im.save(out/'preview.png')
        values=[]
        for line in (out/'run.log').read_text().splitlines():
            if line.startswith('frame sample: '):
                row=line.split()[2:]
                if 240<=int(row[0])<frames: values.append(float(row[4]))
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
        os.environ['TASK66B_PERF_FRAMES']='3600'
        for phase in ['before','after']:
            label=phase+'-long'
            folder=OUT/label; folder.mkdir(exist_ok=True)
            binary=folder/'game-bin'
            if not binary.exists(): os.link(OUT/phase/'game-bin',binary)
            capture(label,[name],True)
def compare(names):
    # ABBA repeated measurements share a short lock to bound machine-load drift.
    # Four runs, each limited to 35 s; retain the original single-run evidence.
    for name in names:
        if '--locked' not in sys.argv:
            subprocess.run(['flock','/tmp/botw-render.lock',sys.executable,__file__,
                'compare',name,'--locked'],check=True)
            continue
        for phase,repeat in [('before',1),('after',1),('after',2),('before',2)]:
            label=phase+'-repeat'+str(repeat)
            folder=OUT/label; folder.mkdir(exist_ok=True)
            binary=folder/'game-bin'
            if not binary.exists(): os.link(OUT/phase/'game-bin',binary)
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
    elif action=='compare': compare([n for n in sys.argv[2:] if n!='--locked'])
    elif action=='prepare': prepare(sys.argv[2])
    else: capture(sys.argv[2],[n for n in sys.argv[3:] if n!='--locked'] or list(SCENES),action=='perf')
