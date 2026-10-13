#!/usr/bin/env python3
"""Matched critic views. Owns per-render flock; --locked requires a caller-owned flock."""
import argparse, json, os, shutil, subprocess
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parent.parent
SCENES = {
 'guardian': (120, dict(BOTW_SKIP='1', BOTW_CAM='-852,222,1918,2.6,-0.4')),
 'snow': (150, dict(BOTW_SKIP='1', BOTW_AT='-1060,2230,2.0')),
 'storm': (300, dict(BOTW_SKIP='1', BOTW_AT='-1000,1620,3.14', BOTW_WEATHER='storm')),
 'storm-dawn': (600, dict(BOTW_SKIP='1', BOTW_AT='-1000,1620,3.14', BOTW_WEATHER='storm', BOTW_HOUR='6.6')),
 'title': (820, dict(BOTW_TITLE='1', SLOPPY_INPUT='10:w+,300:w-')),
 'wake': (450, {}),
 'wading': (180, dict(BOTW_SKIP='1', BOTW_AT='-1190,1665,-0.9', SLOPPY_INPUT='10:w+,160:w-')),
 'shore': (90, dict(BOTW_SKIP='1', ROUND95_SHORE='1')),
 'roof': (840, dict(BOTW_SKIP='1', ROUND95_ROOF='1')),
}
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--locked', action='store_true', help='caller already owns the render flock; never nest')
p.add_argument('label'); p.add_argument('--scenes', nargs='+', default=list(SCENES)); p.add_argument('--prepare', action='store_true')
a=p.parse_args(); os.chdir(ROOT)
if 'wading' in a.scenes and 'shore' not in a.scenes: a.scenes.append('shore')
out=ROOT/'build/round95'; out.mkdir(parents=True,exist_ok=True)
binary=out/a.label
if a.prepare:
 game=out/(a.label+'-game'); game.mkdir(exist_ok=True)
 for path in Path('game').glob('*.jo'):
  target=game/path.name
  if a.label=='before':
   target.write_bytes(subprocess.check_output(['git','show','500126f:game/'+path.name]))
  else: shutil.copyfile(path,target)
 # Each executable freezes the installed mesh version while it queues for rendering.
 models=out/(a.label+'-models'); models.mkdir(exist_ok=True)
 for name in ['hero','hero_bare']:
  target=models/(name+'.mdl')
  if a.label=='before': target.write_bytes(subprocess.check_output(['git','show','500126f:assets/models/'+name+'.mdl']))
  else: shutil.copyfile(ROOT/'assets/models'/(name+'.mdl'),target)
 chars=game/'chars.jo'; c=chars.read_text()
 for name in ['hero','hero_bare']: c=c.replace('assets/models/'+name+'.mdl',str(models/(name+'.mdl')))
 chars.write_text(c)
 s=(game/'main.jo').read_text()
 for path in game.glob('*.jo'): s=s.replace("'"+path.name+"'",repr(str(path.resolve())))
 s=s.replace('update = (dt0: f64):','production_update = (dt0: f64):')
 s+='''
weather_rng_restore(rng(31))
shore = vec3(0,0,0)
shore_out = vec3(0,0,1)
shore_level = 0.0
round95_ready = false
update = (dt: f64):
    if env("ROUND95_ROOF") != none and not round95_ready:
        story.orbs = 4
        pl.pos = lp(TEMPLE,TEMPLE_ROT,4.0,43.05,34.5)
        pl.face = yaw_of(roof_spot()-pl.pos)
        cam.yaw = pl.face
        cam.pitch = 0.22
        camera_snap()
    if env("ROUND95_SHORE") != none and not round95_ready:
        best=1e9
        loop zi in [0..100):
            loop xi in [0..100):
                x=-1205.0+f64(xi)*0.25
                z=1652.0+f64(zi)*0.25
                depth=water_depth(x,z)
                if depth<0.026 or depth>0.045: continue
                normal=normal_at(x,z)
                uphill=normalize(vec3(-normal.x,0,-normal.z))
                q=v3(x,height_at(x,z),z)
                bank=q+uphill*0.30
                if water_depth(f64(bank.x),f64(bank.z))>0.001: continue
                score=length(q.xz-vec2(-1190,1665))
                if f64(score)>=best: continue
                best=f64(score)
                shore=q
                shore_out=uphill
                shore_level=water_level(x,z) ?? 0.0
        assert(best<100.0,"real pond bank with a dry ring footprint")
        pl.pos=shore+shore_out*1.3
        pl.pos.y=f32(height_at(f64(pl.pos.x),f64(pl.pos.z)))
        print("SHORE wet contact={shore} water={shore_level} dry player={pl.pos}")
    round95_ready=true
    production_update(dt)
    if env("ROUND95_ROOF") != none and frame_number()%60==0:
        print("ROOF frame={frame_number()} beat={story.beat} time={story.t} pos={pl.pos} glider={story.glider_given}")
    if env("ROUND95_SHORE") != none:
        # Reproduce the trailing footfall after Jo has left this real water edge.
        if frame_number()==60: fx_wade(shore,shore_level,shore_out*2.0,true)
        cam.override=true
        cam.blend=1.0
        cam.o_pos=shore+shore_out*2.4+vec3(-shore_out.z,0,shore_out.x)*2.4+vec3(0,1.65,0)
        cam.o_target=shore+vec3(0,0.25,0)
        cam.o_fov=43.0
        ui.hide=true
'''
 source=out/(a.label+'.jo'); source.write_text(s)
 subprocess.run(['sloppy/bin/sloppy','build',str(source),'-o',str(binary)],check=True)
else:
 clean={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_','ROUND95_'))}
 for name in a.scenes:
  frames,flags=SCENES[name]; folder=out/name/a.label; folder.mkdir(parents=True,exist_ok=True)
  env=clean|dict(BOTW_HOUR='11',BOTW_WEATHER='clear',BOTW_SCALE='1',BOTW_NOVSYNC='1',SLOPPY_VSYNC='0',SLOPPY_PLATFORM='x11',SLOPPY_WINDOW='1280x720')|flags
  if name=='wake': env['BOTW_POSE_CAPTURE']=str(folder)
  if name=='storm-dawn': env.update(BOTW_CAPTURE_DIR=str(folder),BOTW_CAPTURE_EVERY='60')
  if name=='roof': env.update(SLOPPY_INPUT='60:e+,61:e-',BOTW_CAPTURE_DIR=str(folder),BOTW_CAPTURE_EVERY='60')
  env.update(SLOPPY_FRAMES=str(frames),SLOPPY_SCREENSHOT=str(folder/'final.png'))
  with (folder/'run.log').open('w') as log:
   command = ([] if a.locked else ['flock','/tmp/botw-render.lock']) + ['python3','tools/performance_window.py','1280x720','timeout','240',str(binary)]
   subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  trail=(folder/'run.log').read_text()
  if name=='roof':
   assert 'beat=ending' in trail and 'glider=true' in trail, 'roof fixture must actually enter and finish the meeting'
   if a.label!='before': assert 'ROOF frame=360 beat=ending' in trail, 'held reveal missing'
  if name=='shore': assert 'SHORE wet contact=' in trail, 'real shore fixture did not initialize'
  (folder/'settings.json').write_text(json.dumps(flags,indent=2)+'\n')
  print('PASS capture',name,a.label,flush=True)
