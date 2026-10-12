#!/usr/bin/env python3
"""Matched wildlife portraits and critic view; owns one render lock for the suite.

python3 tools/round68_capture.py after boar fox crow birds critic
FAUNA_FACE=3.6 python3 tools/round68_capture.py after-side boar fox
FAUNA_GAME_DIR selects an immutable baseline game tree. --reuse keeps a compiled
fixture; --force replaces existing PNGs. Critic view uses build/round68/LABEL-game.
The portrait fixture freezes subjects and disables cinematic lens exclusion only.
"""
from pathlib import Path
import os, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
out=ROOT/'build/round68'; out.mkdir(parents=True,exist_ok=True)
label=sys.argv[1]
reuse='--reuse' in sys.argv
locked='--locked' in sys.argv
force='--force' in sys.argv
scenes=[arg for arg in sys.argv[2:] if not arg.startswith('--')] or ['boar','fox','crow','birds']
game=Path(os.environ.get('FAUNA_GAME_DIR',str(ROOT/'game'))).resolve()
source=(game/'main.jo').read_text()
for path in game.glob('*.jo'):
    source=source.replace(f"'{path.name}'",f"'{path}'")
source=source.replace('update = (dt0: f64):','production_update = (dt0: f64):').replace('free_cam = false','free_cam = true')
source+=f"\nuse '{game}/wildlife.jo'\n"
source+='''
update = (dt: f64):
    production_update(dt)
    cam.override = false
    cam.blend = 0.0
    scene = env("FAUNA_SCENE") ?? "boar"
    animals.clear()
    p = v3(-950.64, height_at(-950.64, 1649.65), 1649.65)
    kind = if scene == "fox": WKind.fox else: (if scene == "crow": WKind.crow else: (if scene == "birds": WKind.pigeon else: WKind.boar))
    count = if scene == "birds": 2 else: 1
    loop i in [0..count):
        q = p + v3(f64(i) * 0.5, 0.0, 0.0)
        q.y = f32(height_at(f64(q.x), f64(q.z)))
        a = Animal((if i == 1: WKind.sparrow else: kind), q, q, face = (to_float(env("FAUNA_FACE") ?? "2.2") ?? 2.2), seed = 3.7, appearance = 0.56)
        a.idle = to_float(env("FAUNA_TIME") ?? "1.8") ?? 1.8
        a.t = a.idle
        motion = env("FAUNA_MOTION") ?? "graze"
        a.state = if motion == "run": WState.flee else: (if motion == "walk": WState.walk else: (if motion == "fly": WState.fly else: WState.graze))
        a.speed = if motion == "run": 6.0 else: (if motion == "walk": 0.85 else: 0.0)
        a.gait = a.idle * a.speed * 6.5
        if motion == "fly": a.pos.y += 0.45
        if kind == .fox:
            clip = if motion == "run": "run" else: (if motion == "walk": "walk" else: "graze")
            a.skin = skin(fox_m, sample_clip(fox_lib, clip_index(fox_lib, clip), a.idle, true))
        animals.push(a)
    fc_pos = p + (if kind == .boar: vec3(2.7, 1.55, 3.1) else: (if kind == .fox: vec3(1.65, 0.9, 1.9) else: vec3(0.9, 0.55, 1.1)))
    if (env("FAUNA_MOTION") ?? "") == "fly": fc_pos.y += 0.45
    fc_yaw = -0.717
    fc_pitch = if kind == .boar: -0.24 else: (if kind == .fox: -0.22 else: -0.23)
'''
fixture=out/f'{label}-fixture.jo'
if not reuse:
    fixture.write_text(source)
    subprocess.run(['sloppy/bin/sloppy','build',str(fixture),'-o',str(out/f'{label}-fixture-next')],check=True)
    (out/f'{label}-fixture-next').replace(out/f'{label}-fixture')
if '--build-only' in sys.argv: sys.exit(0)
if not locked:
    os.execvp('flock',['flock','/tmp/botw-render.lock',sys.executable,__file__,label,'--reuse','--locked',*(['--force'] if force else []),*scenes])
for scene in scenes:
    for motion in (os.environ['FAUNA_MOTIONS'].split() if os.environ.get('FAUNA_MOTIONS') else (['live'] if scene=='critic' else (['graze','walk','run'] if scene in ['boar','fox'] else ['graze','fly']))):
        name=f'{label}-boars' if scene=='critic' else f'{label}-{scene}-{motion}'
        if not force and (out/f'{name}.png').exists(): continue
        env=os.environ|dict(BOTW_SKIP='1',BOTW_CAM='-946,188,1660,-0.75,-0.12',BOTW_HOUR='8',BOTW_WEATHER='clear',BOTW_NOVSYNC='1',SLOPPY_PLATFORM='x11',SLOPPY_WINDOW='1280x720',SLOPPY_FRAMES='3',SLOPPY_SCREENSHOT=str(out/f'{name}.png'),FAUNA_SCENE=scene,FAUNA_MOTION=motion)
        binary=out/f'{label}-fixture'
        if scene!='critic': env.pop('BOTW_CAM',None)
        if scene=='critic':
            binary=out/f'{label}-game'
            env['SLOPPY_FRAMES']='120'
        with (out/f'{name}.log').open('w') as log:
            subprocess.run(['python3','tools/cliff_capture_window.py','1280x720','timeout','180',str(binary)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        print(name,flush=True)
