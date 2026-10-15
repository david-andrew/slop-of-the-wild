#!/usr/bin/env python3
"""Fixed critic evidence. Owns bounded render-lock batches; never wrap in a flock."""
import argparse
import concurrent.futures
import csv
import fcntl
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
_capture_lock = None
_capture_lock_started = 0.0
_capture_lock_count = 0
_capture_batch_limit = 4


def release_capture_lock():
    global _capture_lock, _capture_lock_count
    if _capture_lock is not None:
        fcntl.flock(_capture_lock, fcntl.LOCK_UN)
        _capture_lock.close()
        _capture_lock = None
    _capture_lock_count = 0


PREFIXES = ('BOTW_', 'SLOPPY_', 'ROUND', 'PROBE_', 'CP_', 'LISTEN_')
BASE = dict(BOTW_HOUR='11', BOTW_TIMESCALE='0', BOTW_WEATHER='clear', BOTW_SCALE='1',
            SLOPPY_PLATFORM='x11', SLOPPY_VULKAN='1', SLOPPY_VSYNC='0', SLOPPY_WINDOW='1280x720')
CAMP_INPUT = '1:k+,1:w+,150:j+,151:j-,165:j+,166:j-,195:j+,196:j-,200:w-,225:j+,226:j-,255:j+,256:j-'
# Each sequence renders once and retains ONLY these frames. Coordinates/inputs
# come from the named existing fixtures, rather than fresh critic camera choices.
# (area, name, [(frame, purpose)], environment, fixture provenance)
SCENES = [
    ('opening', 'wake', [(420, 'Wake chamber and Jo close-up')], {}, 'round88_closeup_capture.py'),
    ('opening', 'passage', [(90, 'Passage start'), (850, 'Passage mouth reveal')],
     dict(BOTW_PASSAGE='1', SLOPPY_INPUT='20:w+'), 'passage_visual_check.sh'),
    ('opening', 'title', [(660, 'Overlook title moment'), (720, 'Title card')],
     dict(BOTW_TITLE='1', SLOPPY_INPUT='10:w+,300:w-'), 'round95_visual_check.py'),
    ('landscape', 'forest', [(150, 'Forest canopy and grass')], dict(BOTW_SKIP='1', BOTW_AT='-1000,1620,3.14'), 'round82_critic_capture.py'),
    ('landscape', 'waterfall', [(300, 'Waterfall cliffs and falling water')], dict(BOTW_SKIP='1', BOTW_CAM='-1660,175,1888,1.24,-0.05'), 'round69_waterfall_check.py'),
    ('landscape', 'cliffs', [(300, 'Cliff geology and silhouette')], dict(BOTW_SKIP='1', BOTW_CAM='-1600,235,1815,1.2,-0.15'), 'round85_landscape_capture.py'),
    ('landscape', 'pool', [(300, 'Waterfall receiving pool and foam')], dict(BOTW_SKIP='1', BOTW_CAM='-1535,120,1823,1.5707963,-0.3'), 'round76/85 pool fixture, aimed down the receiving channel'),
    ('landscape', 'temple', [(300, 'Temple entrance')], dict(BOTW_SKIP='1', BOTW_CAM='-802,237,1900,-2.967,-0.14'), 'round85_landscape_capture.py'),
    ('landscape', 'husks', [(120, 'Guardian husks')], dict(BOTW_SKIP='1', BOTW_CAM='-852,222,1918,2.6,-0.4'), 'round95_visual_check.py'),
    ('story', 'roof', [(180, 'Meeting approach'), (360, 'Held roof reveal'), (780, 'Farewell and paraglider')],
     dict(BOTW_SKIP='1', SLOPPY_INPUT='60:e+,61:e-'), 'round95_visual_check.py roof filming'),
    ('weather', 'snow', [(150, 'Snow firs and hero')], dict(BOTW_SKIP='1', BOTW_AT='-1060,2230,2.0'), 'round94_fir_capture.py'),
    ('weather', 'firs', [(150, 'Fir bough surfaces')], dict(BOTW_SKIP='1', BOTW_CAM='-880,206,2273,2.60,-0.16'), 'round94_fir_capture.py'),
    ('weather', 'dawn', [(300, 'Dawn landscape')], dict(BOTW_SKIP='1', BOTW_CAM='-700,330,2150,-0.8,-0.35', BOTW_HOUR='6.6'), 'round85_landscape_capture.py'),
    ('weather', 'golden', [(300, 'Golden hour field')], dict(BOTW_SKIP='1', BOTW_AT='-1030,1805,1.57', BOTW_HOUR='18.6'), 'round93_capture.py'),
    ('weather', 'night', [(300, 'Night campfire illumination')], dict(BOTW_SKIP='1', BOTW_AT='-955,1964,0', BOTW_HOUR='22'), 'round93_capture.py / camp fixture'),
    ('weather', 'storm', [(299, 'Storm without strike'), (300, 'Forced lightning strike')],
     dict(BOTW_SKIP='1', BOTW_AT='-1000,1620,3.14', BOTW_WEATHER='storm', BOTW_BOLT='300'), 'round93_capture.py forest-bolt'),
    ('weather', 'rain', [(300, 'Rain near camera and wet surfaces')], dict(BOTW_SKIP='1', BOTW_AT='-1000,1620,3.14', BOTW_WEATHER='rain'), 'round96_capture.py'),
    ('combat', 'camp', [(180, 'Camp foreground vegetation clearance'), (300, 'Camp combat framing'), (420, 'Camp combat recovery'), (640, 'Camp combat aftermath')],
     dict(BOTW_SKIP='1', BOTW_AT='-1439,1606,0', BOTW_GIVE='travelers_sword,travelers_shield', SLOPPY_INPUT=CAMP_INPUT), 'README.md / combat_framing_check.py camp'),
    ('fire', 'grass-fire', [(150, 'Grass ignition'), (260, 'Advancing flame front'), (600, 'Burn aftermath')], dict(BOTW_SKIP='1', BOTW_FIRE='1'), 'round83_fire_capture.py'),
    ('fire', 'tent-fire', [(900, 'Tent fire and crowd')], dict(BOTW_SKIP='1', BOTW_TENTFIRE='5', BOTW_AT='-955,1964,0'), 'round83_fire_capture.py'),
    ('fire', 'body-fire', [(300, 'Production body burn pose and particles')], dict(BOTW_SKIP='1', BOTW_HOUR='22', BOTW_AT='-960,1995,0', BOTW_CAM='-947,243,1956,-0.85,-0.45'), 'round88_closeup_capture.py burn-night'),
    ('wildlife', 'boar', [(150, 'Boar coat and silhouette')], dict(BOTW_SKIP='1', BOTW_CAM='-947,188,1653,-0.717,-0.24'), 'round88_closeup_capture.py boar-clear-side'),
    ('wildlife', 'bird', [(120, 'Bird at one metre')], dict(BOTW_SKIP='1', BOTW_CAM='-818,195,1950,0,0'), 'round88_closeup_capture.py bird-pigeon'),
    ('wildlife', 'bird-flight', [(120, 'Bird flight pose')], dict(BOTW_SKIP='1', BOTW_CAM='-818,195,1950,0,0'), 'round88_closeup_capture.py bird-pigeon-flight'),
    ('traversal', 'swim', [(180, 'Swim surface, stroke and camera')], dict(BOTW_SKIP='1', BOTW_AT='-1161,1684,-0.9', SLOPPY_INPUT='10:w+'), 'Hopper Pond depth scan / swim_surface_check.jo'),
    ('traversal', 'climb', [(180, 'Real cliff climb')], dict(BOTW_SKIP='1'), 'cliff_climb_capture.jo'),
    ('traversal', 'temple-climb', [(180, 'Temple wall climb and soft masonry clearance')], dict(BOTW_SKIP='1', SLOPPY_INPUT='1:w+'), 'round67 temple inner-wall climb; fixed opposing-wall camera'),
    ('traversal', 'glide', [(90, 'Paraglider pose over the Plateau')], dict(BOTW_SKIP='1', BOTW_AT='-1050,1828,-2.36', BOTW_GIVE='paraglider', SLOPPY_INPUT='10:space+,11:space-'), 'overlook fixture / production glider input'),
    *[('shrines', f'shrine-{n}', [(180, f'Shrine {n} interior')], dict(BOTW_SKIP='1', BOTW_TOWER='1', BOTW_SHRINE=str(n)), 'BOTW_SHRINE interior fixture') for n in range(1, 5)],
    ('interface', 'map', [(120, 'Slate map')], dict(BOTW_SKIP='1', BOTW_TOWER='1', SLOPPY_INPUT='20:m+,21:m-'), 'slate_map_view.jo / production map input'),
    ('interface', 'inventory', [(120, 'Inventory and item icons')], dict(BOTW_SKIP='1', BOTW_GIVE='travelers_sword,travelers_shield,apple', SLOPPY_INPUT='20:i+,21:i-'), 'inventory_check.sh / production inventory input'),
    ('interface', 'options', [(150, 'Options contrast and controls')], dict(BOTW_SKIP='1', BOTW_AT='-1054,1834,0.85'), 'round82_critic_capture.py options-grass'),
]
FAST_CHECKS = ['feel_test', 'integration_test', 'input_check', 'opening_test', 'combat_check', 'weather_fx_test', 'music_harmony_check', 'late_story_check']

FIXTURE = '''
use '{root}/tools/performance_output.jo'
use '{game}/inventory.jo'
from '{game}/wildlife.jo' import __wild_free_view
weather_rng_restore(rng(31))
cp_scene = env("CP_SCENE") ?? "forest"
cp_frames = [loop f in split(env("CP_FRAMES") ?? "150", ","): to_int(f)!]
cp_ready = false
cp_climb_y = 0.0
cp_climb_normal = vec3(0,0,1)
update = (dt: f64):
    if not cp_ready:
        if cp_scene == "temple-climb":
            origin=lp(TEMPLE,TEMPLE_ROT,0.0,6.0,-20.0)
            hit=raycast(origin,transform_dir(rotation_y(TEMPLE_ROT),vec3(1,0,0)),18.0,true,false)
            assert(hit.hit,"temple wall fixture")
            p=hit.pos+hit.normal*0.45-vec3(0,1,0)
            pl=Player(pos=p,last_safe=p,state=.climb,grounded=false,climb_n=hit.normal,climb_col=hit.collider,face=yaw_of(hit.normal*-1.0))
            cam.yaw=pl.face
            camera_snap()
        if cp_scene == "roof":
            story.orbs = 4
            pl.pos = lp(TEMPLE,TEMPLE_ROT,4.0,43.05,34.5)
            pl.face = yaw_of(roof_spot()-pl.pos)
            cam.yaw = pl.face
            cam.pitch = 0.22
            camera_snap()
        if cp_scene == "swim":
            level = water_level(f64(pl.pos.x),f64(pl.pos.z))!
            assert(water_depth(f64(pl.pos.x),f64(pl.pos.z)) > 1.4,"deep pond fixture")
            pl.pos.y = f32(level-SWIM_FOOT_DEPTH)
            pl.state = .swim
            pl.grounded = false
            pl.water_y = level
            camera_snap()
        if cp_scene == "glide":
            pl.pos.y += 24
            pl.state = .air
            pl.grounded = false
            pl.st_t = 0.3
            pl.has_glider = true
            camera_snap()
        if cp_scene == "climb":
            hit = raycast(v3(-1640,208,1752),vec3(1,0,0),200,true,false)
            assert(hit.hit)
            p = hit.pos + hit.normal*0.45-vec3(0,1,0)
            pl = Player(pos=p,last_safe=p,state=.air,grounded=false,st_t=0.3,vel=vec3(0,-1,0),face=yaw_of(hit.normal*-1.0),air_peak=f64(p.y))
            cp_climb_normal=hit.normal
            cam_yaw_global=yaw_of(hit.normal*-1.0)
            cp_climb_y=f64(p.y)
            fc_pos=v3(-1568,213,1758)
            fc_yaw=1.10
            fc_pitch=-0.08
            free_cam=true
        cp_ready=true
    if cp_scene == "climb": act=Actions()
    production_update(dt)
    if cp_scene == "climb":
        cam_yaw_global=yaw_of(cp_climb_normal*-1.0)
        act=Actions(move=vec2(0,1))
        if frame_number()<180: player_update(dt)
        act=Actions()
    if cp_scene == "temple-climb":
        cam.pos=lp(TEMPLE,TEMPLE_ROT,-12.8,10.0,-22.0)
        cam.target=pl.pos+vec3(0,1.0,0)
        cam.blend=0.0
        assert(pl.state==.climb,"temple climb left wall")
    if cp_scene == "options": invui=InvUI(open=true,tab=6,t=1.0,tab_t=1.0)
    if cp_scene == "boar":
        animals.clear()
        p=v3(-950.64,height_at(-950.64,1649.65),1649.65)
        animal=Animal(.boar,p,p,face=3.6,seed=3.7,appearance=0.56)
        animal.idle=1.8
        animal.t=1.8
        animals.push(animal)
        fc_pos=p+vec3(2.7,1.55,3.1)
        fc_yaw=-0.717
        fc_pitch=-0.24
    if starts_with(cp_scene,"bird"):
        __wild_free_view=false
        animals.clear()
        p=v3(-818,height_at(-818,1950),1950)
        animal=Animal(.pigeon,p,p,face=3.6,seed=3.7,appearance=0.56)
        animal.idle=1.8
        animal.t=1.8
        if cp_scene=="bird-flight":
            animal.state=.fly
            animal.pos.y+=0.3
        animals.push(animal)
        target=animal.pos+vec3(0,0.22,0)
        fc_pos=target+vec3(0.60,0.22,0.77)
        d=target-fc_pos
        fc_yaw=atan2(f64(d.x),-f64(d.z))
        fc_pitch=atan2(f64(d.y),hypot(f64(d.x),f64(d.z)))
    if cp_scene=="body-fire":
        loop mut e in enemies:
            if length(e.home-vec3(-955.87,238,1948.86))<20 and e.camp_role==.club:
                e.burning=3.0
                e.hp=e.hp_max
                e.state=.idle
                e.anim_t=1.5
                world=translation(e.pos)*rotation_y(PI-e.face)
                fc_pos=transform_point(world,vec3(2.6,1.65,3.3))
                d=transform_point(world,vec3(0,0.9,0))-fc_pos
                fc_yaw=atan2(f64(d.x),-f64(d.z))
                fc_pitch=atan2(f64(d.y),hypot(f64(d.x),f64(d.z)))
        enemy_anim_update(0.0)
    if cp_frames.contains(frame_number()):
        eprint("pack checkpoint: scene {cp_scene} frame {frame_number()} state {pl.state} beat {story.beat} glider {story.glider_given}")
        if cp_scene=="roof" and frame_number()==360: assert(story.beat==.ending,"held roof reveal")
        if cp_scene=="roof" and frame_number()==780: assert(story.glider_given,"roof gift completed")
        if cp_scene=="swim": assert(pl.state==.swim,"swimming fixture")
        if cp_scene=="climb": assert(pl.state==.climb and f64(pl.pos.y)>cp_climb_y+2.0,"climbing fixture")
        if cp_scene=="glide": assert(pl.state==.glide,"gliding fixture")
draw = ():
    production_draw()
    if cp_frames.contains(frame_number()):
        flush()
        assert(save_png(screenshot(),(env("CP_OUT")!)+"/frame-{frame_number()}.png"))
main = (): performance_output_run(update,draw)
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_env():
    return {k: v for k, v in os.environ.items() if not k.startswith(PREFIXES)} | {'PYTHONDONTWRITEBYTECODE': '1'}


def command_run(command, log, env=None, capture_batch=False):
    global _capture_lock, _capture_lock_started, _capture_lock_count
    started = time.monotonic()
    launch = command
    if command[:2] == ['flock', '/tmp/botw-render.lock']:
        # This marker executes after flock acquires the lock, before the bounded
        # child starts. Queue wait is reported separately from idle-machine cost.
        marker = 'import os,sys,time; print("pack lock acquired:",time.monotonic(),flush=True); os.execvp(sys.argv[1],sys.argv[1:])'
        if capture_batch:
            if _capture_lock is None:
                _capture_lock = open('/tmp/botw-render.lock', 'a')
                fcntl.flock(_capture_lock, fcntl.LOCK_EX)
                _capture_lock_started = time.monotonic()
            # The parent already owns the same flock; do not nest acquisition.
            launch = [sys.executable, '-c', marker] + command[2:]
        else:
            launch = command[:2] + [sys.executable, '-c', marker] + command[2:]
    with log.open('w') as stream:
        result = subprocess.run(launch, cwd=ROOT, env=env or clean_env(), stdout=stream, stderr=subprocess.STDOUT,
                                pass_fds=(_capture_lock.fileno(),) if capture_batch else ())
    if capture_batch:
        _capture_lock_count += 1
        if _capture_lock_count >= _capture_batch_limit or time.monotonic()-_capture_lock_started >= 60 or result.returncode:
            release_capture_lock()
    if result.returncode:
        raise RuntimeError(f'exit {result.returncode}: {shlex.join(command)}; see {log}')
    return time.monotonic() - started


def lock_wait(log, started):
    marker = re.search(r'^pack lock acquired: ([\d.]+)$', log.read_text(), re.M)
    assert marker, 'render lock timing marker missing'
    return max(0, float(marker[1])-started)


def capture_source():
    source = (ROOT / 'game/main.jo').read_text()
    for old, new in [('update = (dt0: f64):', 'production_update = (dt0: f64):'), ('\ndraw = ():', '\nproduction_draw = ():')]:
        assert source.count(old) == 1, f'production anchor changed: {old}'
        source = source.replace(old, new)
    source = source.replace('main = (): game_run(update, draw)', '')
    extension = FIXTURE.replace("'{root}/tools/performance_output.jo'", "'../tools/performance_output.jo'").replace("'{game}/", "'")
    return source + extension


def build_fixture(out):
    game = out / 'fixture/game'
    game.mkdir(parents=True, exist_ok=True)
    scripts = out / 'fixture/tools'
    scripts.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'tools/performance_output.jo', scripts / 'performance_output.jo')
    for path in (ROOT / 'game').glob('*.jo'):
        shutil.copyfile(path, game / path.name)
    fixture = game / 'main.jo'
    # Retain original relative imports; all fixture references share the same
    # mutable production modules, including player, inventory and terrain.
    fixture.write_text(capture_source())
    binary = out / 'fixture/capture'
    command_run(['sloppy/bin/sloppy', 'build', str(fixture), '-o', str(binary)], out / 'fixture/build.log')
    return binary


def capture(out, manifest):
    binary = out/'fixture/capture'
    cached = {s['name']:s for s in manifest.get('shots',[])}
    reusable = (binary.is_file() and (out/'fixture/game/main.jo').read_text()==capture_source() and
                digest(binary)==manifest.get('capture_executable_sha256') and
                digest(out/'fixture/tools/performance_output.jo')==digest(ROOT/'tools/performance_output.jo'))
    if not reusable:
        binary = build_fixture(out)
        cached = {}
    manifest['capture_executable_sha256'] = digest(binary)
    # Keep cache/build startup distinct from lock queue time and scene costs.
    if 'startup' not in manifest:
        from round67_startup import measure, rebuilt_fixture
        startup_out = out/'startup'
        startup_out.mkdir(exist_ok=True)
        production = startup_out/'plateau'
        command_run(['sloppy/bin/sloppy','build','tools/performance_game.jo','-o',str(production)],startup_out/'build.log')
        manifest['startup'] = measure(production, startup_out, rebuilt_fixture(production,startup_out))
        save_manifest(out,manifest)
    shots = []
    for area, name, frames, flags, provenance in SCENES:
        folder = out / 'captures' / name
        folder.mkdir(parents=True, exist_ok=True)
        run_frames = max(121,max(f for f,_ in frames)+1)
        expected = BASE | flags | dict(CP_SCENE=name,CP_FRAMES=','.join(str(f) for f,_ in frames),SLOPPY_FRAMES=str(run_frames))
        saved = json.loads((folder/'settings.json').read_text())['environment'] if (folder/'settings.json').exists() else {}
        retained = [cached.get(f'{name}-{f}') for f,_ in frames]
        if (all(retained) and name in manifest.get('capture_cpu_ms',{}) and all(saved.get(k)==v for k,v in expected.items()) and
            all((out/s['png']).is_file() and digest(out/s['png'])==s['sha256'] and (out/s['jpg']).is_file() for s in retained)):
            shots.extend(retained)
            manifest['shots'] = shots
            save_manifest(out,manifest)
            print(f'PASS retained capture {name}: {len(frames)} shots',flush=True)
            continue
        env = clean_env() | BASE | flags | dict(CP_SCENE=name, CP_FRAMES=','.join(str(f) for f, _ in frames), CP_OUT=str(folder),
            SLOPPY_FRAMES=str(run_frames), SLOPPY_SCREENSHOT=str(folder / 'final.png'), BOTW_FRAME_LOG='1', BOTW_LOADTIME='1')
        # Release after the configured short batch or 60 seconds;
        # the 90 s child timeout bounds a slow final render to about 150 s total.
        command = ['flock', '/tmp/botw-render.lock', 'python3', 'tools/performance_window.py', '1280x720', 'timeout', '90', str(binary)]
        settings = {k: v for k, v in env.items() if k.startswith(PREFIXES)}
        display_command = shlex.join(['env', *[f'{k}={v}' for k, v in sorted(settings.items())], *command])
        started = time.monotonic()
        wall_s = command_run(command, folder / 'run.log', env, capture_batch=True)
        wait_s = lock_wait(folder / 'run.log', started)
        manifest['render_lock_wait_s'] = manifest.get('render_lock_wait_s', 0) + wait_s
        (folder / 'settings.json').write_text(json.dumps({'command': command, 'environment': settings, 'wall_s': wall_s, 'lock_wait_s': wait_s, 'render_process_s': wall_s-wait_s}, indent=2)+'\n')
        rows = [[float(v) for v in line.split()[2:]] for line in (folder / 'run.log').read_text().splitlines() if line.startswith('frame sample:')]
        for frame, purpose in frames:
            png = folder / f'frame-{frame}.png'
            jpg = folder / f'frame-{frame}.jpg'
            with Image.open(png) as image:
                assert image.size == (1280, 720), f'wrong viewport: {png}'
                image.convert('RGB').resize((640, 360), Image.Resampling.LANCZOS).save(jpg, quality=90)
            shots.append(dict(area=area, name=f'{name}-{frame}', frame=frame, purpose=purpose, fixture=provenance,
                png=str(png.relative_to(out)), jpg=str(jpg.relative_to(out)), log=str((folder / 'run.log').relative_to(out)),
                settings=str((folder / 'settings.json').relative_to(out)), command=display_command, sha256=digest(png)))
        steady = [r for r in rows if r[0] > 60]
        manifest.setdefault('capture_cpu_ms', {})[name] = {key: percentiles([r[col] for r in steady]) for key, col in [('callback_wall', 2), ('callback_thread', 4)]}
        manifest['shots'] = shots
        save_manifest(out, manifest)
        print(f'PASS capture {name}: {len(frames)} shots, {wall_s-wait_s:.1f}s rendering, {wait_s:.1f}s lock wait', flush=True)
    release_capture_lock()
    assert digest(binary) == manifest['capture_executable_sha256'], 'capture executable changed'
    sheets = out / 'contact-sheets'
    sheets.mkdir(exist_ok=True)
    for area in dict.fromkeys(s['area'] for s in shots):
        group = [s for s in shots if s['area'] == area]
        sheet = Image.new('RGB', (3*384, math.ceil(len(group)/3)*240), '#171c22')
        draw = ImageDraw.Draw(sheet)
        for i, shot in enumerate(group):
            x, y = (i % 3)*384, (i // 3)*240
            with Image.open(out / shot['jpg']) as im:
                sheet.paste(im.resize((384, 216), Image.Resampling.LANCZOS), (x, y+24))
            draw.text((x+6, y+5), shot['name'], fill='white')
        sheet.save(sheets / f'{area}.jpg', quality=90)
    manifest['contact_sheets'] = [str(p.relative_to(out)) for p in sorted(sheets.glob('*.jpg'))]


def percentiles(values):
    assert values, 'missing timing samples'
    values = sorted(values)
    return {k: values[math.ceil(len(values)*p)-1] for k, p in [('p50', .5), ('p99', .99), ('worst', 1)]} | {'frames_over_25ms': sum(v > 25 for v in values), 'samples': len(values)}


def performance(out, manifest):
    folder = out / 'performance'
    folder.mkdir(exist_ok=True)
    # Reuse the existing real-time forest route and present-return instrumentation.
    # Adapt only platform assertion/output geometry in a generated probe, never Sloppy.
    source = (ROOT / 'tools/render_session.jo').read_text()
    game = folder / 'game'
    game.mkdir(exist_ok=True)
    for path in (ROOT / 'game').glob('*.jo'):
        shutil.copyfile(path, game / path.name)
    scripts = folder / 'tools'
    scripts.mkdir(exist_ok=True)
    source = source.replace('assert(__wayland and not __soft)', 'assert(not __wayland and not __soft and __xdpy != null)')
    geometry = (ROOT / 'tools/performance_output.jo').read_text().split('performance_output_run =', 1)[0]
    source += '\n' + geometry
    anchor = '        __gl_screen_resize(__win_w, __win_h)'
    assert source.count(anchor) == 1, 'route geometry anchor changed'
    source = source.replace(anchor, '''        root: int = 0
        x: i32 = 0
        y: i32 = 0
        w: u32 = 0
        h: u32 = 0
        border: u32 = 0
        depth: u32 = 0
        assert(__perf_geometry(__xdpy,__xwin,&root,&x,&y,&w,&h,&border,&depth)!=0)
        if w!=2133 or h!=1200:
            __perf_resize(__xdpy,__xwin,2133,1200)
            __perf_sync(__xdpy,0)
            assert(__perf_geometry(__xdpy,__xwin,&root,&x,&y,&w,&h,&border,&depth)!=0)
        assert(w==2133 and h==1200)
        __win_w=int(w)
        __win_h=int(h)
''' + anchor)
    fixture = scripts / 'route.jo'
    fixture.write_text(source)
    binary = folder / 'route'
    compile_s = command_run(['sloppy/bin/sloppy', 'build', str(fixture), '-o', str(binary)], folder / 'build.log')
    env = clean_env() | dict(BOTW_SKIP='1', BOTW_AT='-1140,1500,3.14', BOTW_HOUR='11', BOTW_TIMESCALE='0', BOTW_WEATHER='clear',
        BOTW_FPS='0', BOTW_FRAME_LOG='1', BOTW_LOADTIME='1', BOTW_SCENE_LOG='1', SLOPPY_PLATFORM='x11', SLOPPY_VULKAN='1',
        SLOPPY_VSYNC='0', SLOPPY_WINDOW='2133x1200', PROBE_ROUTE='forest', PROBE_SECONDS='120', PROBE_PNG=str(folder / 'route.png'))
    # No SLOPPY_SCREENSHOT: the route uses real dt and two minutes of wall time.
    command = ['flock', '/tmp/botw-render.lock', 'python3', 'tools/performance_window.py', '--visible', '2133x1200', 'timeout', '180', 'tools/play.sh', str(binary)]
    settings = dict(command=command, environment={k:v for k,v in env.items() if k.startswith(PREFIXES)}, compile_s=compile_s)
    (folder / 'run-settings.json').write_text(json.dumps(settings,indent=2)+'\n')
    started = time.monotonic()
    wall_s = command_run(command, folder / 'route.log', env)
    wait_s = lock_wait(folder / 'route.log', started)
    manifest['render_lock_wait_s'] = manifest.get('render_lock_wait_s', 0) + wait_s
    settings.update(wall_s=wall_s, lock_wait_s=wait_s)
    (folder / 'run-settings.json').write_text(json.dumps(settings,indent=2)+'\n')
    report = performance_report(folder, command, env, compile_s, wall_s, wait_s)
    manifest['performance'] = report
    print('PASS 120s pacing:', report['actual_present_mode'], report['timing_ms']['present_return_interval'], flush=True)


def performance_report(folder, command, env, compile_s, wall_s, wait_s):
    binary = folder / 'route'
    text = (folder / 'route.log').read_text()
    mode = re.search(r'^probe swapchain: ([01])$', text, re.M)
    assert 'probe complete:' in text and mode, 'incomplete/non-fastest-default pacing run'
    present_mode = 'mailbox' if mode[1] == '1' else 'immediate (driver mailbox fallback)'
    assert 'visible managed' in text, 'launcher presentation must remain managed'
    rows = [[float(v) for v in line.split()[2:]] for line in text.splitlines() if line.startswith('present return:')]
    assert rows and all(r[6:] == [2133,1200] for r in rows), 'route viewport mismatch'
    assert [int(r[0]) for r in rows] == list(range(len(rows))), 'missing/duplicated pacing frames'
    assert all(b[1]>a[1] for a,b in zip(rows,rows[1:])), 'non-monotonic pacing timestamps'
    assert rows[-1][1] >= 120, 'route must last two minutes'
    distance = re.findall(r'^session minute: 2 .*? distance ([\d.]+)', text, re.M)
    assert distance and float(distance[-1]) > 100, 'route did not traverse the Plateau'
    with Image.open(folder / 'route.png') as im:
        assert im.size == (2133,1200)
        im.convert('RGB').resize((960,540), Image.Resampling.LANCZOS).save(folder / 'route.jpg', quality=90)
    steady = [r for r in rows if r[0] > 240]
    startup = re.search(r'loaded in ([\d.]+)s', text)
    assert startup, 'startup timing missing'
    report = dict(protocol='120s real-dt forest route; launcher-default X11 Vulkan mailbox preference / immediate fallback; managed 2133x1200 output; dynamic scene scale; first 240 frames excluded from steady percentiles; nearest rank; present-call returns, not scanout',
        compile_s=compile_s, process_wall_s_including_lock_wait=wall_s, lock_wait_s=wait_s, process_wall_s=wall_s-wait_s if wall_s is not None else None, actual_present_mode=present_mode, startup_in_game_s=float(startup[1]),
        route_elapsed_s=rows[-1][1], route_distance_m=float(distance[-1]), total_frames=len(rows),
        timing_ms={k: percentiles([r[col] for r in steady]) for k,col in [('present_return_interval',2),('present_call',3),('callback_wall',4),('callback_thread',5)]},
        all_frame_intervals_ms=percentiles([r[2] for r in rows[1:]]), command=shlex.join(command),
        environment={k:v for k,v in env.items() if k.startswith(PREFIXES)}, executable_sha256=digest(binary))
    (folder / 'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def note_name(midi):
    return ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][midi % 12] + str(midi // 12 - 1)


def audio(out, manifest):
    folder = out / 'audio'
    folder.mkdir(exist_ok=True)
    command = ['python3', 'tools/listen.py', '--clips-only', '--notes', '--out', str(folder)]
    wall_s = command_run(command, folder / 'listen.log')
    timings = json.loads((folder / 'render-timing.json').read_text())
    wait_s = sum(r['lock_wait_s'] for r in timings)
    manifest['render_lock_wait_s'] = manifest.get('render_lock_wait_s', 0) + wait_s
    clips = []
    for path in sorted(folder.glob('*.wav')):
        notes = folder / f'{path.stem}-notes.csv'
        score = folder / f'{path.stem}-score.md'
        lines = [f'# {path.stem}', '', 'Production piano dispatch; 1/60 s onset resolution. MIDI octave convention: C4 = 60. Ambience/foley have no pitched note score.', '']
        if path.stem in ['shrine_hum','shrine_room','shrine_steps','shrine_bed']:
            lines += ['This stem mutes the piano. The dispatch log below is retained for comparison with the full mix; these notes are inaudible in this stem.', '']
        if notes.exists():
            rows = list(csv.DictReader(notes.open()))
            lines += ['| Onset (s) | Note | MIDI | Velocity | Kind |', '|---:|---|---:|---:|---|']
            lines += [f'| {float(r.get("onset_s") or r["time"]):.3f} | {note_name(int(r["midi"]))} | {r["midi"]} | {float(r.get("velocity", 0)):.2f} | {r.get("kind", "piano")} |' for r in rows]
            if not rows: lines += ['', 'No piano notes dispatched in this clip.']
        else:
            lines += ['Note log unavailable for this fixture.']
        score.write_text('\n'.join(lines)+'\n')
        clips.append(dict(name=path.stem, wav=str(path.relative_to(out)), score=str(score.relative_to(out)), notes=str(notes.relative_to(out)) if notes.exists() else None))
    assert len(clips) == 13, 'missing listening clips/stems'
    manifest['audio'] = dict(wall_s=wall_s, lock_wait_s=wait_s, command=shlex.join(command), clips=clips, levels=json.loads((folder / 'levels.json').read_text()))
    print(f'PASS audio: {len(clips)} clips and scores, {wall_s:.1f}s', flush=True)


def checks(out, manifest):
    folder = out / 'checks'
    folder.mkdir(exist_ok=True)
    def run(name):
        command = ['tools/run_all_checks.sh', '-j', '1', '--only', name]
        log = folder / f'{name}.log'
        started = time.monotonic()
        with log.open('w') as stream:
            result = subprocess.run(command, cwd=ROOT, env=clean_env(), stdout=stream, stderr=subprocess.STDOUT)
        text = log.read_text()
        evidence = re.search(r'^Evidence: (.+)$', text, re.M)
        if evidence:
            evidence_path = Path(evidence[1])
            shutil.copyfile(evidence_path / f'{name}.log', folder / f'{name}-detail.log')
        return dict(name=name, status='PASS' if result.returncode == 0 else 'FAIL', exit=result.returncode,
            wall_s=time.monotonic()-started, log=str(log.relative_to(out)), command=shlex.join(command), evidence=evidence[1] if evidence else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(4,(os.cpu_count() or 2)//2))) as pool:
        results = list(pool.map(run, FAST_CHECKS))
    (folder / 'results.tsv').write_text(''.join(f'{r["name"]}\t{r["status"]}\t{r["exit"]}\n' for r in results))
    manifest['checks'] = results
    for result in results: print(result['status'], result['name'], flush=True)
    if any(r['status'] != 'PASS' for r in results): raise RuntimeError(f'fast check failed: {folder}')


def save_manifest(out, manifest):
    (out / 'pack.json').write_text(json.dumps(manifest, indent=2)+'\n')


def capture_settings_match(out):
    for _,name,frames,flags,_ in SCENES:
        path = out/'captures'/name/'settings.json'
        if not path.exists(): return False
        saved = json.loads(path.read_text())['environment']
        expected = BASE | flags | dict(CP_SCENE=name,CP_FRAMES=','.join(str(f) for f,_ in frames),SLOPPY_FRAMES=str(max(121,max(f for f,_ in frames)+1)))
        if any(saved.get(k)!=v for k,v in expected.items()): return False
    return True


def indexes(out, manifest):
    shots = manifest.get('shots', [])
    md = ['# Fixed critic pack', '', f'Revision: `{manifest["revision"]}`. Wall time: {manifest["wall_s"]:.1f} s. Status: {manifest["status"]}.', '',
          '1280×720 full PNGs, 640×360 JPEGs; 1/60 s simulation, fixed hour/weather, weather seed 31, production world seeds. Captures and audio each own one render lock. Pacing uses real dt. Commands run from the repository root.', '']
    sections = []
    for area in dict.fromkeys(s['area'] for s in shots):
        md += [f'## {area}', '', f'![{area} contact sheet](contact-sheets/{area}.jpg)', '']
        cards = []
        for shot in [s for s in shots if s['area'] == area]:
            md += [f'- [{shot["name"]}]({shot["png"]}) · [small JPEG]({shot["jpg"]}) · {shot["purpose"]}. Fixture: `{shot["fixture"]}`.', '', '```sh', shot['command'], '```', '']
            cards.append(f'<article><a href="{shot["png"]}"><img loading="lazy" src="{shot["jpg"]}" alt="{html.escape(shot["purpose"])}"></a><h3>{shot["name"]}</h3><p>{html.escape(shot["purpose"])}</p><details><summary>Command and fixture</summary><p>{html.escape(shot["fixture"])}</p><pre>{html.escape(shot["command"])}</pre><a href="{shot["log"]}">Log</a> · <a href="{shot["settings"]}">Settings</a></details></article>')
        sections.append(f'<section><h2>{area}</h2><a href="contact-sheets/{area}.jpg">Contact sheet</a><div class="grid">{"".join(cards)}</div></section>')
    if 'startup' in manifest:
        report = manifest['startup']
        md += ['## Startup', '', f'Cold: {report["cold_s"]:.3f} s; warm median: {report["warm_median_s"]:.3f} s; changed executable, identical shaders: {report["new_build_s"]:.3f} s. [Details](startup/summary.json).', '', report['protocol'], '']
        sections.append('<section><h2>Startup</h2><a href="startup/summary.json">Cold, warm and new-build summary</a><pre>'+html.escape(json.dumps(report,indent=2))+'</pre></section>')
    if 'performance' in manifest:
        report = manifest['performance']
        md += ['## Performance', '', f'Startup: {report["startup_in_game_s"]:.3f} s in game. [Raw route log](performance/route.log), [summary](performance/summary.json).', '', '| Metric (ms) | p50 | p99 | Worst | Frames >25 ms |', '|---|---:|---:|---:|---:|']
        for metric, row in report['timing_ms'].items(): md.append(f'| {metric} | {row["p50"]:.3f} | {row["p99"]:.3f} | {row["worst"]:.3f} | {row["frames_over_25ms"]} |')
        md += ['', report['protocol'], '']
        sections.append('<section><h2>Performance</h2><a href="performance/summary.json">Summary</a> · <a href="performance/route.log">Raw log</a><pre>'+html.escape(json.dumps(report,indent=2))+'</pre></section>')
    if 'audio' in manifest:
        md += ['## Audio', '', '[Listening levels](audio/LEVELS.md) · [Audio players](audio/index.html). Scores list actual dispatched piano note names and onset times; ambience and foley are unpitched.', '']
        players = []
        for clip in manifest['audio']['clips']:
            md.append(f'- [{clip["name"]}]({clip["wav"]}) · [note score]({clip["score"]})')
            players.append(f'<article><h3>{clip["name"]}</h3><audio controls preload="none" src="{clip["wav"]}"></audio><a href="{clip["score"]}">Readable score</a> · <a href="{clip["notes"]}">Onset/MIDI CSV</a></article>')
        sections.append('<section><h2>Audio</h2><a href="audio/LEVELS.md">Listening levels</a><div class="grid">'+''.join(players)+'</div></section>')
    if 'checks' in manifest:
        md += ['', '## Fast headless checks', '', '| Check | Result | Wall seconds |', '|---|---|---:|']
        for row in manifest['checks']: md.append(f'| [{row["name"]}]({row["log"]}) | {row["status"]} | {row["wall_s"]:.1f} |')
        sections.append('<section><h2>Fast headless checks</h2><ul>'+''.join(f'<li><a href="{r["log"]}">{r["name"]}</a>: {r["status"]}</li>' for r in manifest['checks'])+'</ul></section>')
    (out / 'index.md').write_text('\n'.join(md)+'\n')
    (out / 'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fixed critic pack</title><style>body{margin:24px;background:#171c22;color:#e8edf2;font:16px system-ui}a{color:#9acaff}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:20px}article{background:#252d36;padding:12px;border-radius:8px}img,audio{width:100%}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}section{margin:32px 0}</style><h1>Fixed critic pack</h1><p>'+html.escape(f'{manifest["revision"]} · {len(shots)} shots · {manifest["wall_s"]:.1f} s · {manifest["status"]}')+'</p><p>Fixed seeds, hours, weather and 1/60 s capture simulation. Click images for full PNGs. <a href="index.md">Markdown index</a> · <a href="pack.json">Manifest</a></p>'+''.join(sections)+'</html>')


def main():
    global _capture_batch_limit
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out_dir', type=Path)
    parser.add_argument('--only', nargs='+', choices=['captures','performance','audio','checks'], help='partial diagnostic pack; default includes everything')
    parser.add_argument('--capture-batch-scenes', type=int, choices=range(1,9), default=4, help='scenes per short render-lock batch; always release after 60 seconds')
    parser.add_argument('--resume', action='store_true', help='retain complete matching capture/performance sections after a tooling interruption')
    # Accept the brief's `--only captures OUT` spelling as well as `OUT --only captures`.
    argv = sys.argv[1:]
    if argv and argv[0] == '--only':
        for i, value in enumerate(argv[1:], 1):
            if argv[i-1] == "--capture-batch-scenes": continue
            if not value.startswith('-') and value not in ['captures','performance','audio','checks']:
                argv = [value, *argv[:i], *argv[i+1:]]
                break
    args = parser.parse_args(argv)
    _capture_batch_limit = args.capture_batch_scenes
    os.chdir(ROOT)
    out = args.out_dir.resolve()
    if not out.is_relative_to(ROOT / 'build') or out == ROOT / 'build': parser.error('OUT_DIR must be a new directory under this checkout\'s build/')
    if not args.resume and out.exists() and any(out.iterdir()): parser.error('OUT_DIR must be empty; use a new directory or --resume')
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    manifest = dict(revision=subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
        worktree=subprocess.check_output(['git','status','--short'], text=True),
        sources={str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT / 'game').glob('*.jo'))},
        tools={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__), ROOT / 'tools/listen.py', ROOT / 'tools/run_all_checks.sh', ROOT / 'tools/render_session.jo', ROOT / 'tools/performance_output.jo']},
        selected=args.only or ['captures','performance','audio','checks'], status='RUNNING', wall_s=0)
    previous_wall_s = 0
    if args.resume:
        original = json.loads((out / 'pack.json').read_text())
        if original['revision'] != manifest['revision'] or original['sources'] != manifest['sources']:
            parser.error('resume requires the original HEAD and byte-identical game sources')
        if original['status'] == 'RUNNING': parser.error('pack is still running; wait for it to finish')
        changed_assets = subprocess.check_output(['git','diff','HEAD','--name-only','--','assets'],text=True)
        if changed_assets: parser.error('asset edits require a fresh pack')
        previous_wall_s = original['wall_s']
        original.setdefault('attempts',[]).append(dict(status=original['status'],wall_s=previous_wall_s))
        original.update(selected=manifest['selected'],status='RUNNING',resumed_tools=manifest['tools'])
        manifest = original
        manifest.pop('error',None)
    save_manifest(out, manifest)
    try:
        for name in manifest['selected']:
            if args.resume and name == 'captures':
                expected = {f'{n}-{f}' for _,n,frames,_,_ in SCENES for f,_ in frames}
                shots = manifest.get('shots',[])
                if ({s['name'] for s in shots} == expected and
                    (out/'fixture/game/main.jo').is_file() and
                    (out/'fixture/game/main.jo').read_text() == capture_source() and
                    capture_settings_match(out) and
                    all(digest(out/s['png']) == s['sha256'] and (out/s['jpg']).is_file() for s in shots) and
                    len(manifest.get('contact_sheets',[])) == len({s[0] for s in SCENES})):
                    print(f'PASS retained {len(shots)} matched captures',flush=True)
                    continue
            if args.resume and name == 'performance' and (out/'performance/route.log').exists():
                folder = out/'performance'
                if 'probe complete:' in (folder/'route.log').read_text() and all(digest(folder/'game'/Path(p).name)==v for p,v in manifest['sources'].items()):
                    settings = json.loads((folder/'run-settings.json').read_text()) if (folder/'run-settings.json').exists() else dict(command=[],environment={},compile_s=None,wall_s=None,lock_wait_s=None)
                    manifest['performance'] = performance_report(folder,settings['command'],settings['environment'],settings['compile_s'],settings.get('wall_s'),settings.get('lock_wait_s'))
                    print('PASS retained complete native-default pacing log',flush=True)
                    continue
            {'captures': capture, 'performance': performance, 'audio': audio, 'checks': checks}[name](out, manifest)
            save_manifest(out, manifest)
        assert all(digest(ROOT / name) == value for name,value in manifest['sources'].items()), 'game sources changed during pack'
        manifest['status'] = 'PASS' if args.only is None else 'PASS (partial diagnostic)'
    except Exception as exc:
        manifest['status'] = 'FAIL'
        manifest['error'] = str(exc)
        raise
    finally:
        release_capture_lock()
        manifest['wall_s'] = previous_wall_s + time.monotonic()-started
        manifest['wall_s_excluding_render_lock_wait'] = manifest['wall_s'] - manifest.get('render_lock_wait_s', 0)
        manifest['under_25_minutes'] = manifest['wall_s'] <= 1500
        save_manifest(out, manifest)
        indexes(out, manifest)
        print(f'Pack: {out / "index.html"}; {manifest["wall_s"]:.1f}s; {manifest["status"]}', flush=True)


if __name__ == '__main__':
    main()
