#!/usr/bin/env python3
"""Matched tower/resting-HUD captures and CPU tails; owns one flock per run."""
import argparse, hashlib, json, math, os, re, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/task69-sol'
FIXTURE='''
weather_rng_restore(rng(31))
fixture_ready=false
fixture_update=(dt:f64):
    if not fixture_ready:
        if (env("TASK69_SCENE") ?? "")=="tower":
            p=TOWER+vec3(0,0,12.0)
            p.y=f32(height_at(f64(p.x),f64(p.z)))
            pl=Player(pos=p,last_safe=p,face=0)
            cam=Cam(yaw=0,pitch=0.25)
            camera_snap()
        fixture_ready=true
    update(dt)
    if (env("TASK69_SCENE") ?? "")=="tower" and (frame_number()==120 or frame_number()==300): eprint("tower fixture: state {pl.state} pos {pl.pos} collider {pl.climb_col} view {view_pos()}")
fixture_draw=():
    draw()
    if frame_number()==120 or frame_number()==300:
        flush()
        assert(save_png(screenshot(),env("TASK69_OUT")!+"/frame-{frame_number()}.png"))
main=():performance_output_run(fixture_update,fixture_draw)
'''
def build(label):
    folder=OUT/label; game=folder/'game'; game.mkdir(parents=True,exist_ok=True)
    for p in (ROOT/'game').glob('*.jo'):
        if label.startswith('before'):
            old=subprocess.run(['git','show','cb21e87:game/'+p.name],cwd=ROOT,capture_output=True)
            if old.returncode==0:(game/p.name).write_bytes(old.stdout)
        else:shutil.copy2(p,game/p.name)
    scripts=folder/'tools';scripts.mkdir(exist_ok=True)
    shutil.copy2(ROOT/'tools/performance_output.jo',scripts/'performance_output.jo')
    source=(game/'main.jo').read_text().replace('main = (): game_run(update, draw)','production_main = (): game_run(update, draw)')
    source+="\nuse '../tools/performance_output.jo'\n"+FIXTURE
    (game/'main.jo').write_text(source)
    subprocess.run(['sloppy/bin/sloppy','build',str(game/'main.jo'),'-o',str(folder/'fixture')],cwd=ROOT,check=True)
    (folder/'source-hashes.json').write_text(json.dumps({'baseline_revision':'cb21e87' if label.startswith('before') else None,'fixture_sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in game.glob('*.jo')}},indent=2))
def run(label,scene,repeat,locked=False):
    dest=OUT/'pairs'/scene/f'{label}-{repeat}';dest.mkdir(parents=True,exist_ok=True)
    env={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_','TASK69_'))}
    env.update(BOTW_SKIP='1',BOTW_AT='-1000,1620,3.14',BOTW_HOUR='11',BOTW_TIMESCALE='0',BOTW_WEATHER='clear',BOTW_SCALE='1',BOTW_FRAME_LOG='1',BOTW_LOADTIME='1',SLOPPY_PLATFORM='x11',SLOPPY_VULKAN='1',SLOPPY_VSYNC='0',SLOPPY_WINDOW='1280x720',SLOPPY_FRAMES='720',SLOPPY_SCREENSHOT=str(dest/'final.png'),TASK69_SCENE=scene,TASK69_OUT=str(dest))
    if scene=='tower':env['SLOPPY_INPUT']='1:w+,301:w-'
    command=([] if locked else ['flock','/tmp/botw-render.lock'])+['python3','tools/performance_window.py','1280x720','timeout','100',str(OUT/label/'fixture')]
    (dest/'settings.json').write_text(json.dumps({'env':{k:v for k,v in env.items() if k.startswith(('BOTW_','SLOPPY_','TASK69_'))},'binary_sha256':hashlib.sha256((OUT/label/'fixture').read_bytes()).hexdigest(),'command':command},indent=2))
    with (dest/'run.log').open('w') as log:subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    print(label,scene,repeat,flush=True)
def report(before="before-final",after="final-v3",repeats=None):
    labels={"before":before,"after":after}
    result={}
    for scene in ['forest','tower']:
        result[scene]={}
        for label in ['before','after']:
            rows=[]
            for p in sorted((OUT/'pairs'/scene).glob(f'{labels[label]}-*/run.log')):
                if repeats is not None and int(p.parent.name.rsplit('-',1)[1]) not in repeats:continue
                all_rows=[[float(v) for v in l.split()[2:]] for l in p.read_text().splitlines() if l.startswith('frame sample:')]
                assert len(all_rows)==720 and [int(r[0]) for r in all_rows]==list(range(1,721)),str(p)
                import json
                assert json.loads((p.parent/'settings.json').read_text())['binary_sha256']==hashlib.sha256((OUT/labels[label]/'fixture').read_bytes()).hexdigest(),str(p)
                rows += [r for r in all_rows if r[0]>360]
            result[scene][label]={name:sorted(r[i] for r in rows)[math.ceil(len(rows)*.99)-1] for name,i in [('cpu_thread_p99_ms',4),('producer_p99_ms',1)]}|{'samples':len(rows)}
        result[scene]['cpu_delta_ms']=result[scene]['after']['cpu_thread_p99_ms']-result[scene]['before']['cpu_thread_p99_ms']
        for frame in [120,300]:
            sheet=Image.new('RGB',(1280,384),'#171c22');d=ImageDraw.Draw(sheet)
            for i,label in enumerate(['before','after']):
                im=Image.open(OUT/'pairs'/scene/f'{labels[label]}-{min(repeats) if repeats is not None else 0}'/f'frame-{frame}.png').convert('RGB').resize((640,360),Image.Resampling.LANCZOS)
                sheet.paste(im,(i*640,24));d.text((i*640+8,6),f'{scene} {label} {frame}',fill='white')
            sheet.save(OUT/'pairs'/scene/f'compare-{frame}.jpg',quality=92)
    (OUT/'pairs/summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['build','run','report']);ap.add_argument('label',nargs='?',default='before');ap.add_argument('--repeat',type=int,default=0);a=ap.parse_args();os.chdir(ROOT)
    if a.action=='build':build(a.label)
    elif a.action=='run':
        for scene in ['forest','tower']:run(a.label,scene,a.repeat)
    else:report(repeats=[4,5])
