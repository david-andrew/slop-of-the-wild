#!/usr/bin/env python3
"""Production death/input captures. Owns one bounded render lock; never wrap."""
import os
from pathlib import Path
import subprocess
import shutil
import sys
sys.dont_write_bytecode = True
from critic_pack import BASE, clean_env, capture_source
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'build/death-visual-check'
FIXTURE = r'''
use '../tools/performance_output.jo'
use 'death.jo'
from 'save.jo' import __save_file
probe_time = 0.0
probe_pos = vec3()
probe_checkpoint = vec3()
update = (dt: f64):
    if frame_number()==1:
        probe_checkpoint=pl.pos
        respawn_checkpoint=pl.pos
        respawn_face=pl.face
    if frame_number()==30:
        pl.pos+=vec3(0,0,2)
        pl.last_safe=pl.pos
        damage_player(pl.hp,pl.pos)
    production_update(dt)
    if frame_number()==90:
        assert(pl.state==.dead and not death_card_visible(),"early jump did not skip collapse")
    if frame_number()==155:
        assert(death_card_visible())
        probe_time=env.hour
        probe_pos=pl.pos
    if frame_number()==200:
        assert(death_card_visible() and not invui.open,"inventory input cannot dismiss death")
        assert(env.hour==probe_time and pl.pos==probe_pos,"card pauses world and blocks held movement")
    if frame_number()==210:
        assert(pl.state==.ground and pl.hp==pl.hp_max and pl.pos==probe_checkpoint,"Enter continues at checkpoint")
        assert(not act.jump and not act.attack and act.move==vec2(),"Continue consumes gameplay input")
    if frame_number()==230:
        assert(pl.state!=.dead and pl.hp==pl.hp_max,"healthy respawn")
        print("PASS production death: collapse, paused card, blocked movement/inventory, Enter Continue and checkpoint")
draw = ():
    production_draw()
    if frame_number()==45 or frame_number()==115 or frame_number()==180 or frame_number()==210 or frame_number()==230:
        flush()
        assert(save_png(screenshot(),"build/death-visual-check/frame-{frame_number()}.png"))
main = (): performance_output_run(update,draw)
'''

def main():
    os.chdir(ROOT)
    OUT.mkdir(parents=True,exist_ok=True)
    game=OUT/'fixture/game'
    game.mkdir(parents=True,exist_ok=True)
    scripts=OUT/'fixture/tools'
    scripts.mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'tools/performance_output.jo',scripts/'performance_output.jo')
    for path in (ROOT/'game').glob('*.jo'): shutil.copyfile(path,game/path.name)
    source=game/'main.jo'
    text=capture_source().split("\nuse '../tools/performance_output.jo'",1)[0]
    source.write_text(text+FIXTURE)
    binary=OUT/'fixture/capture'
    subprocess.run(['sloppy/bin/sloppy','build',str(source),'-o',str(binary)],check=True)
    env=clean_env()|BASE|dict(BOTW_SKIP='1',BOTW_AT='-1030,1805,1.57',BOTW_TIMESCALE='1',
        SLOPPY_FRAMES='240',SLOPPY_SCREENSHOT=str(OUT/'final.png'),
        SLOPPY_INPUT='45:space+,46:space-,160:w+,200:w-,180:i+,181:i-,210:enter+,211:enter-')
    with (OUT/'run.log').open('w') as log:
        subprocess.run(['flock','/tmp/botw-render.lock','python3','tools/performance_window.py','1280x720','timeout','90',str(binary)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    print((OUT/'run.log').read_text()[-2000:])

if __name__=='__main__':main()
