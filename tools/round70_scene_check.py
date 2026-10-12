#!/usr/bin/env python3
"""Matched production sword/combat screenshots. Owns one batch lock; do not wrap."""
from pathlib import Path
import os,subprocess,sys,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];os.chdir(ROOT)
phase=sys.argv[1];assert phase in ('before','after')
out=ROOT/'build/round70'/('scene-'+phase);out.mkdir(parents=True,exist_ok=True)
game=ROOT/'build/round70/before/game' if phase=='before' else ROOT/'game'
if '--locked' not in sys.argv:
 source=f'''build:
    opt = release
use '{game}/main.jo'
use '{game}/enemies.jo'
use '{game}/player.jo'
use '{ROOT}/tools/performance_output.jo'
scene_update=(dt:f64):
    update(dt)
    if frame_number()==419:
        count=0
        pair=1e9
        loop i in 0.. and e in enemies:
            if not enemy_alive(e) or length(e.pos-pl.pos)>20.0: continue
            count+=1
            print("scene enemy {{i}} kind={{e.kind}} state={{e.state}} pos={{e.pos}} engaged={{e.may_engage}}")
            loop j in [i+1..enemies.len()):
                other=enemies[j]
                if enemy_alive(other) and length(other.pos-pl.pos)<20.0: pair=min(pair,f64(length((e.pos-other.pos).xz)))
        print("scene combat: alive={{count}} pair_min={{pair:.3}}m")
main=():performance_output_run(scene_update,draw)
'''
 (out/'scene.jo').write_text(source)
 subprocess.run(['sloppy/bin/sloppy','build',str(out/'scene.jo'),'-o',str(out/'scene')],check=True)
 os.execvp('flock',['flock','/tmp/botw-render.lock',sys.executable,__file__,phase,'--locked'])
cases={'sword':dict(BOTW_AT='-1030,1805,0',BOTW_GIVE='travelers_sword',SLOPPY_FRAMES='90'),
       'sword-gear':dict(BOTW_AT='-1030,1805,0',BOTW_GIVE='travelers_sword,travelers_shield,travelers_bow',SLOPPY_FRAMES='90'),
       'combat420':dict(BOTW_AT='-1439,1614,0',BOTW_GIVE='travelers_sword,travelers_shield',SLOPPY_FRAMES='420',SLOPPY_INPUT='10:w+,50:w-,60:k+,'+','.join(f'{f}:j+,{f+1}:j-' for f in range(90,420,60)))}
for name,flags in cases.items():
 e={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_'))}
 e.update(BOTW_SKIP='1',BOTW_HOUR='11',BOTW_WEATHER='clear',BOTW_SCALE='1',BOTW_NOVSYNC='1',SLOPPY_PLATFORM='x11',SLOPPY_WINDOW='1280x720',SLOPPY_SCREENSHOT=str(out/(name+'.png')),**flags)
 with (out/(name+'.log')).open('w') as log:
  subprocess.run(['python3','tools/performance_window.py','1280x720','timeout','180',str(out/'scene')],env=e,stdout=log,stderr=subprocess.STDOUT,check=True)
 assert Image.open(out/(name+'.png')).size==(1280,720)
 (out/(name+'.environment.json')).write_text(json.dumps(flags,indent=2)+'\n')
 print(phase,name,flush=True)
