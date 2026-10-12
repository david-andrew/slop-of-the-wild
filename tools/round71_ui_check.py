#!/usr/bin/env python3
"""Matched 20 m combat and inventory captures. Owns one batch flock; do not wrap."""
import os, subprocess, sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
phase=sys.argv[1]
assert phase in ('before','after')
out=ROOT/'build/round71'/phase
out.mkdir(parents=True,exist_ok=True)
game=out/'game' if phase=='before' else ROOT/'game'
if phase=='before' and not game.exists():
 archive=subprocess.check_output(['git','archive','36f77b7','game'])
 subprocess.run(['tar','-x','-C',str(out)],input=archive,check=True)
source=f'''build:
    opt = release
use '{game}/main.jo'
use '{ROOT}/tools/performance_output.jo'
use '{game}/enemies.jo'
use '{game}/player.jo'
use '{game}/items.jo'
use '{game}/inventory.jo'
use '{game}/combat.jo'
use '{game}/camera.jo'
use '{game}/terrain.jo'
use '{game}/ui.jo'
case_ = env("UI_CASE") ?? "lock-day"
ready_ = false
foe_ = -1
ui_update=(dt:f64):
    update(dt)
    if not ready_:
        loop mut e in enemies: e.state=.gone
        inv=Inventory()
        inv_add("old_shirt")
        if case_=="weapons-partial":
            inv_add("travelers_sword")
            inv_add("woodcutters_axe")
        if case_=="talus":
            foe_=spawn_enemy(.talus,pl.pos+vec3(0,0,-20))
        else if case_=="lock-day" or case_=="lock-night":
            foe_=spawn_enemy(.blue_bokoblin,pl.pos+vec3(0,0,-20))
        ready_=true
    if foe_>=0:
        enemies[foe_].pos=pl.pos+vec3(0,0,-20)
        enemies[foe_].pos.y=f32(height_at(f64(enemies[foe_].pos.x),f64(enemies[foe_].pos.z)))
        enemies[foe_].state=.chase
        enemies[foe_].face=PI
        enemies[foe_].hp=enemies[foe_].hp_max*0.6
        fight.target=foe_
        enemies[foe_].weapon="spiked_club"
    if case_=="weapons-empty" or case_=="weapons-partial": invui=InvUI(open=true,tab=0,t=1.0,tab_t=1.0)
    cam.override=true
    cam.blend=1.0
    cam.o_pos=pl.pos+vec3(1.2,3.0,5.0)
    cam.o_target=if foe_>=0: enemies[foe_].pos+vec3(0,1.5,0) else: pl.pos+vec3(0,1.5,-20)
    cam.o_fov=50.0
    ui.banners.clear()
    if frame_number()==89 and foe_>=0: print("UI evidence: target distance={{length(enemies[foe_].pos-pl.pos):.3}} hp={{enemies[foe_].hp}}")
main=():performance_output_run(ui_update,draw)
'''
if '--locked' not in sys.argv:
 (out/'ui.jo').write_text(source)
 subprocess.run(['sloppy/bin/sloppy','build',str(out/'ui.jo'),'-o',str(out/'ui')],check=True)
 os.execvp('flock',['flock','/tmp/botw-render.lock',sys.executable,__file__,phase,'--locked'])
for case in ('lock-day','lock-night','talus','weapons-empty','weapons-partial'):
 e={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_','UI_CASE'))}
 e.update(BOTW_SKIP='1',BOTW_AT='-1050,1920,0',BOTW_HOUR='0' if case=='lock-night' else '11',BOTW_WEATHER='clear',BOTW_SCALE='1',BOTW_NOVSYNC='1',SLOPPY_PLATFORM='x11',SLOPPY_WINDOW='1280x720',SLOPPY_FRAMES='90',SLOPPY_SCREENSHOT=str(out/(case+'.png')),UI_CASE=case)
 with (out/(case+'.log')).open('w') as log:
  subprocess.run(['python3','tools/performance_window.py','1280x720','timeout','180',str(out/'ui')],env=e,stdout=log,stderr=subprocess.STDOUT,check=True)
 assert Image.open(out/(case+'.png')).size==(1280,720)
 print(phase,case,flush=True)
