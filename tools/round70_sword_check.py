#!/usr/bin/env python3
"""Production hero_draw pose captures; owns one batch lock; never wrap in flock. Scratch stays in build/."""
from pathlib import Path
import os, shutil, subprocess, sys, json, hashlib, io, tarfile
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
OUT=ROOT/'build/round70'
phase=sys.argv[1]
assert phase in ('before','after')
LOCKED='--locked' in sys.argv
if not LOCKED:
 os.execvp('flock',['flock','/tmp/botw-render.lock',sys.executable,__file__,phase,'--locked'])
out=OUT/phase
out.mkdir(parents=True,exist_ok=True)
game=out/'game'
if phase=='after' and game.exists(): shutil.rmtree(game)
if not game.exists():
 if phase=='before':
  baseline=subprocess.check_output(['git','archive','645907d','game'])
  with tarfile.open(fileobj=io.BytesIO(baseline)) as archive:archive.extractall(out,filter='data')
 else:shutil.copytree(ROOT/'game',game)
source=f'''build:
    opt = release
use '{game}/gfx.jo'
use '{game}/chars.jo'
use '{game}/items.jo'
use '{game}/env.jo'
use '{game}/player.jo'
use '{game}/post.jo'
use '{game}/scene.jo'
use '{game}/shadows.jo'
use '{game}/skel.jo'
use '{game}/clips.jo'
use '{game}/terrain.jo'
use '{game}/combat.jo'
window("Back equipment poses",1280,720)
items_init()
chars_init()
shadow_setup()
inv_add("old_shirt")
inv_add("travelers_sword")
if env("SWORD_GEAR")!=none:
    inv_add("travelers_shield")
    inv_add("travelers_bow")
pose_name=env("SWORD_POSE")??"idle"
setup_pose=():
    hero_m=ranger_m
    hero_dressed=true
    pl=Player(pos=vec3(0,0,0),face=PI)
    pl.state=if pose_name=="climb":PState.climb else:(if pose_name=="glide":PState.glide else:(if pose_name=="swim":PState.swim else:PState.ground))
    # Sample the production clips deterministically, retaining the exact back socket
    # and production equipment draw for every pose. No terrain IK changes the pose.
    clip=if pose_name=="glide":"glide" else:(if pose_name=="swim":"swim" else:pose_name)
    hero_world=mat4()
    hero_skin=skin(hero_m,sample_clip(human,ci(clip),0.34,true))
setup_pose()
env.hour=11.0
env_update(0.0,false)
env.density=0.0
update=(dt:f64):pass
draw=():
    flush()
    bind_target(post_begin())
    glClearColor(0.18,0.25,0.31,1)
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    gl_opaque_state()
    yaw=to_float(env("SWORD_YAW")??"3.14159265359")??PI
    sc.cam=v3(sin(yaw)*3.0,1.3,cos(yaw)*3.0)
    sc.view=look_at(sc.cam,vec3(0,0.95,0),vec3(0,1,0))
    sc.vp=perspective(radians(40.0),aspect_ratio(),0.05,100.0)*sc.view
    sc.shadow=false
    hero_draw()
    post_end(0.05,100.0)
    gl_restore_2d()
    text("{{pose_name}}",vec2(16,16),20,rgba(1,1,1,1))
'''
(out/'poses.jo').write_text(source)
subprocess.run(['sloppy/bin/sloppy','build',str(out/'poses.jo'),'-o',str(out/'poses')],check=True)
cases=[(pose,gear,'3.14159265359') for pose in ['idle','run','climb','glide','swim'] for gear in [False,True]]
cases.append(('idle',True,'1.57079632679'))
for pose,gear,yaw in cases:
 name=f'{pose}'+('-gear' if gear else '')+('-side' if yaw.startswith('1.') else '')
 e={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_','SWORD_'))}
 e.update(SWORD_POSE=pose,SWORD_YAW=yaw,SLOPPY_PLATFORM='x11',SLOPPY_WINDOW='1280x720',SLOPPY_FRAMES='4',SLOPPY_SCREENSHOT=str(out/(name+'.png')))
 if gear:e['SWORD_GEAR']='1'
 with (out/(name+'.log')).open('w') as log:
  subprocess.run(['timeout','180',str(out/'poses')],env=e,stdout=log,stderr=subprocess.STDOUT,check=True)
 assert Image.open(out/(name+'.png')).size==(1280,720)
 print(phase,name,flush=True)
(out/'settings.json').write_text(json.dumps({'source':str(game),'pose_seconds':0.34,'camera':'rear','gear':['travelers_sword','travelers_shield','travelers_bow']},indent=2)+'\n')

(out/'sources.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(game.glob('*.jo'))},indent=2)+'\n')
