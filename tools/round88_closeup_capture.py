#!/usr/bin/env python3
"""Hero, 1 m birds, fur, burn and live camp close-ups. Owns one render lock per scene or short matched pair.

python3 tools/round88_closeup_capture.py LABEL [wake boar-clear-side boar-storm-side eat poke]
Additional views: hair-rain hair-storm bird-pigeon bird-pigeon-flight
bird-sparrow bird-crow fox-rain oldman-rain burn-night. --game-dir selects
an immutable baseline source tree; baseline hero assets must be preserved too.
Use --baseline-binary BASE --reuse to capture missing before/after pairs, releasing
the shared lock between pairs. --batch-scenes 2 permits at most two paired
views (normally under a minute). Neither game child locks itself.
Captures the production draw at exact frames. Wake uses no gameplay presets;
camp selects a natural idle phase, then approaches using real perception/AI.
All generated fixtures, executables, logs and images stay under build/round88.
"""
from pathlib import Path
import argparse
import json
import sys
import os
import subprocess

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('label')
p.add_argument('scenes', nargs='*', default=['wake', 'boar-clear-side', 'boar-storm-side', 'eat', 'poke'])
p.add_argument('--reuse', action='store_true')
p.add_argument('--baseline-binary', type=Path, help='render a matched before/after pair per short lock')
p.add_argument('--baseline-label', default='priority-before')
p.add_argument('--batch-scenes', type=int, choices=(1, 2), default=1, help='at most two short paired views per lock')
p.add_argument('--game-dir', type=Path, default=ROOT / 'game')
a = p.parse_args()
out = ROOT / 'build/round88'
out.mkdir(parents=True, exist_ok=True)
binary = out / (a.label + '-closeup')
if not a.reuse:
    game = a.game_dir.resolve()
    s = (game / 'main.jo').read_text()
    for path in game.glob('*.jo'):
        s = s.replace(f"'{path.name}'", f"'{path}'")
    s = s.replace('update = (dt0: f64):', 'production_update = (dt0: f64):')
    s = s.replace('\ndraw = ():', '\nproduction_draw = ():')
    s = s.replace('loop mut e in enemies: e.anim_t += dt', 'enemies_update(dt, env.night > 0.5)')
    s += f"\nuse '{game}/enemy_camp.jo'\nfrom '{game}/wildlife.jo' import __wild_free_view\n"
    s += '''
weather_rng_restore(rng(31))
r88_scene = env("ROUND88_SCENE") ?? "wake"
r88_actor = -1
r88_started = false
r88_frames = if r88_scene == "wake": [330,420,520] else: (if r88_scene=="eat" or r88_scene=="poke": [1,60,120,150,179,192,204,216,240,270] else:[120,300])
update = (dt: f64):
    if r88_scene == "eat" or r88_scene == "poke":
        if not r88_started:
            r88_started = true
            loop i in 0.. and e in enemies:
                if length(e.home-vec3(-955.87,238,1948.86))<20 and e.camp_role==(if r88_scene=="eat":CampRole.sitter else:CampRole.club): r88_actor=i
            assert(r88_actor>=0,"authored camp actor")
            e=enemies[r88_actor]
            # Fixed natural schedule phases, shared by baseline and candidate:
            # sitter reaches a bite after 2 s; club has >3 s of poking before
            # perception is triggered. No activity, pose or alert is forced.
            enemies[r88_actor].anim_t=if r88_scene=="eat":28.3333333333 else:21.0
            world=translation(e.pos)*rotation_y(PI-e.face)
            fc_pos=transform_point(world,(if r88_scene=="eat":vec3(2.6,1.75,2.7) else:vec3(-3.0,2.0,3.2)))
            target=transform_point(world,(if r88_scene=="eat":vec3(0,0.82,0.28) else:vec3(0,0.65,1.45)))
            d=target-fc_pos
            fc_yaw=atan2(f64(d.x),-f64(d.z))
            fc_pitch=atan2(f64(d.y),hypot(f64(d.x),f64(d.z)))
            print("round88 {r88_scene}: actor={r88_actor} start={enemies[r88_actor].anim_t:.4} pos={e.pos}")
        if frame_number()==180:
            e=enemies[r88_actor]
            pl.pos=e.pos+transform_dir(rotation_y(PI-e.face),vec3(0,0,2.7))
            pl.pos.y=f32(height_at(f64(pl.pos.x),f64(pl.pos.z)))
            pl.noise=5.0
            pl.vel=vec3(6,0,0)
            pl.invuln=1000.0
    production_update(dt)
    if r88_scene!="wake":
        cam.override=false
        cam.blend=0.0
    if starts_with(r88_scene,"boar"):
        animals.clear()
        p=v3(-950.64,height_at(-950.64,1649.65),1649.65)
        animal=Animal(.boar,p,p,face=(if contains(r88_scene,"side"):3.6 else:2.2),seed=3.7,appearance=0.56)
        animal.idle=1.8
        animal.t=1.8
        animals.push(animal)
        fc_pos=p+vec3(2.7,1.55,3.1)
        fc_yaw=-0.717
        fc_pitch=-0.24
    if starts_with(r88_scene,"bird") or starts_with(r88_scene,"fox"):
        # Inspection only: permit a true 1 m portrait past cinematic exclusion.
        __wild_free_view=false
        animals.clear()
        p=v3(-818,height_at(-818,1950),1950)
        kind=if starts_with(r88_scene,"fox"):WKind.fox else:(if contains(r88_scene,"crow"):WKind.crow else:(if contains(r88_scene,"sparrow"):WKind.sparrow else:WKind.pigeon))
        a=Animal(kind,p,p,face=3.6,seed=3.7,appearance=0.56)
        a.idle=1.8
        a.t=1.8
        if contains(r88_scene,"flight"):
            a.state=.fly
            a.pos.y+=0.3
        if kind==.fox:a.skin=skin(fox_m,sample_clip(fox_lib,clip_index(fox_lib,"graze"),1.8,true))
        animals.push(a)
        target=a.pos+vec3(0,0.22,0)
        fc_pos=target+(if kind==.fox:vec3(1.1,0.65,1.3) else:vec3(0.60,0.22,0.77))
        d=target-fc_pos
        fc_yaw=atan2(f64(d.x),-f64(d.z))
        fc_pitch=atan2(f64(d.y),hypot(f64(d.x),f64(d.z)))
    if r88_scene=="oldman-rain":
        old_man.visible=true
        world=translation(old_man.pos)*rotation_y(PI-old_man.face)
        fc_pos=transform_point(world,vec3(1.5,1.5,2.0))
        d=transform_point(world,vec3(0,1.1,0))-fc_pos
        fc_yaw=atan2(f64(d.x),-f64(d.z))
        fc_pitch=atan2(f64(d.y),hypot(f64(d.x),f64(d.z)))
    if r88_scene=="burn-night":
        loop mut e in enemies:
            if length(e.home-vec3(-955.87,238,1948.86))<20 and e.camp_role==.club:
                # A fixed burn diagnostic uses the production burn pose, shader
                # and particles. Camp contact/alert scenes above use live AI.
                e.burning=3.0
                e.hp=e.hp_max
                e.state=.idle
                e.anim_t=1.5
                r88_actor=-1
                world=translation(e.pos)*rotation_y(PI-e.face)
                fc_pos=transform_point(world,vec3(2.6,1.65,3.3))
                d=transform_point(world,vec3(0,0.9,0))-fc_pos
                fc_yaw=atan2(f64(d.x),-f64(d.z))
                fc_pitch=atan2(f64(d.y),hypot(f64(d.x),f64(d.z)))
        enemy_anim_update(0.0)
    if r88_actor>=0 and r88_frames.contains(frame_number()):
        e=enemies[r88_actor]
        skin_=eanims[r88_actor].skin
        if camp_day_activity(e)==1:
            mouth=transform_point(bone_world(boko_m,skin_,"Head")*boko_m.ibm[bone_index(boko_m,"Head")],vec3(0,1.055,0.51))
            food=transform_point(bone_world(boko_m,skin_,"hand_l")*SOCKET_HAND_L.offset,vec3(0,0.18,0))
            print("round88 drawn food/mouth gap={length(food-mouth):.5}")
        if camp_has_poker(e):
            tip=transform_point(bone_world(boko_m,skin_,"hand_r")*SOCKET_HAND_R.offset,vec3(0,f32(CAMP_POKER_REACH),0.03))
            print("round88 drawn poker/coal gap={length(tip-camp_poker_tip(e)):.5}")
        print("round88 frame={frame_number()} role={e.camp_role} state={e.state} alert={e.alert:.4} activity={camp_day_activity(e)} poker={camp_has_poker(e)}")
        if frame_number()==179:
            assert(e.state==.idle,"undisturbed close-up")
            if r88_scene=="poke": assert(camp_has_poker(e),"poking continues until interruption")
        if frame_number()==216: assert(e.alert>=1.0,"live interruption within 0.6 seconds")
draw = ():
    production_draw()
    if r88_frames.contains(frame_number()):
        save_png(screenshot(),(env("ROUND88_OUT") ?? "build/round88")+"/frame-{frame_number()}.png")
'''
    source = out / (a.label + '-closeup.jo')
    source.write_text(s)
    with (out / (a.label + '-build.log')).open('w') as log:
        subprocess.run(['sloppy/bin/sloppy', 'build', str(source), '-o', str(binary)], stdout=log, stderr=subprocess.STDOUT, check=True)
clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'ROUND88_'))}
pending = []
for scene_index, scene in enumerate(a.scenes):
    dest = out / (a.label + '-' + scene)
    dest.mkdir(exist_ok=True)
    settings = clean | dict(ROUND88_SCENE=scene, ROUND88_OUT=str(dest),
        SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='1280x720', BOTW_SCALE='1',
        BOTW_NOVSYNC='1', SLOPPY_SCREENSHOT=str(dest / 'final.png'), SLOPPY_FRAMES='521' if scene=='wake' else ('271' if scene in ('eat','poke') else '301'))
    if scene != 'wake':
        settings.update(BOTW_SKIP='1', BOTW_AT='-960,1995,0', BOTW_CAM='-947,243,1956,-0.85,-0.45', BOTW_HOUR='11', BOTW_WEATHER='storm' if 'storm' in scene else ('rain' if 'rain' in scene else 'clear'))
    if scene.startswith('hair'):
        settings.pop('BOTW_CAM', None)
        settings['BOTW_AT'] = '-1190,1665,-0.9'
    if scene=='burn-night': settings['BOTW_HOUR']='23'
    # One render, or one short matched pair, per lock. This process owns no
    # lock while waiting for the next view. Neither child acquires a lock.
    runs = []
    expected = 'frame-520.png' if scene=='wake' else ('frame-270.png' if scene in ('eat','poke') else 'frame-300.png')
    if a.baseline_binary:
        before = out / (a.baseline_label + '-' + scene)
        before.mkdir(exist_ok=True)
        if not (before / expected).exists(): runs.append((str(a.baseline_binary.resolve()), str(before), {k:v for k,v in settings.items() if k.startswith(('BOTW_', 'SLOPPY_', 'ROUND88_'))}))
    if not a.reuse or not (dest / expected).exists(): runs.append((str(binary), str(dest), {k:v for k,v in settings.items() if k.startswith(('BOTW_', 'SLOPPY_', 'ROUND88_'))}))
    pair_script = """
import json,os,subprocess,sys
from pathlib import Path
for binary,directory,overrides in json.loads(sys.argv[1]):
    dest=Path(directory)
    settings=os.environ|overrides|dict(ROUND88_OUT=directory,SLOPPY_SCREENSHOT=str(dest/'final.png'))
    with (dest/'run.log').open('w') as log:
        subprocess.run([sys.executable,'tools/cliff_capture_window.py','1280x720','timeout','180',binary],env=settings,stdout=log,stderr=subprocess.STDOUT,check=True)
    print(directory,flush=True)
"""
    pending.extend(runs)
    if pending and ((scene_index+1) % a.batch_scenes == 0 or scene_index+1 == len(a.scenes)):
        subprocess.run(['flock','/tmp/botw-render.lock',sys.executable,'-c',pair_script,json.dumps(pending)],env=clean,check=True)
        pending.clear()
