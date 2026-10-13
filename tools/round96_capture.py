#!/usr/bin/env python3
"""Weather evidence and cumulative layer isolation. Owns one flock per game run."""
import argparse, hashlib, json, os, re, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/round96'
STAGES = ['terrain', 'vegetation', 'shadows', 'canopy', 'cloud-shadow', 'wet-darkening', 'puddles', 'storm-light', 'storm-grade', 'water', 'props', 'fx']

def prepare(label, revision=None):
    source = OUT / label / 'game'
    shutil.copytree(ROOT / 'game', source, dirs_exist_ok=True)
    if revision:
        for p in source.glob('*.jo'):
            p.write_bytes(subprocess.check_output(['git','show',f'{revision}:game/{p.name}'],cwd=ROOT))
    (OUT / label / 'source.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.jo')},indent=2))
    def edit(name, changes):
        p = source / name
        s = p.read_text()
        for old, new in changes:
            assert old in s, (name, old)
            s = s.replace(old, new)
        p.write_text(s)
    edit('terrain.jo', [
        ('    has_canopy = 0.0', '    r96_stage = 99.0\n    has_canopy = 0.0'),
        ('sh = cascade_shadow(w, ndl, u.vp0, u.vp1, u.vp2, u.sm0, u.sm1, u.sm2) * cloud_shade(w.xz, u.time, u.clouds)', 'sh = if u.r96_stage >= 2.0: cascade_shadow(w, ndl, u.vp0, u.vp1, u.vp2, u.sm0, u.sm1, u.sm2) else: f32(1.0)\n    if u.r96_stage >= 4.0: sh *= cloud_shade(w.xz, u.time, u.clouds)'),
        ('if u.has_canopy > 0.5 and u.shadow_pass < 0.5:', 'if u.has_canopy > 0.5 and u.shadow_pass < 0.5 and u.r96_stage >= 3.0:'),
        ('wetness = if soaked:', 'wetness = if soaked and u.r96_stage >= 5.0:'),
        ('if wetness > 0.62:', 'if wetness > 0.62 and u.r96_stage >= 6.0 and u.r96_stage != 21.0:'),
        ('if soaked and u.r96_stage >= 5.0:', 'if soaked and u.r96_stage >= 5.0 and u.r96_stage != 20.0:'),
        ('if u.r96_stage >= 2.0:', 'if u.r96_stage >= 2.0 and u.r96_stage != 23.0:'),
        ('if u.r96_stage >= 4.0:', 'if u.r96_stage >= 4.0 and u.r96_stage != 24.0:'),
        ('and u.r96_stage >= 3.0:', 'and u.r96_stage >= 3.0 and u.r96_stage != 22.0:'),
        ('roots = canopy.y * (0.7+grain*0.3)', 'roots = if u.r96_stage == 28.0: f32(0.0) else: canopy.y * (0.7+grain*0.3)'),
        ('if fo > 0.0 and snk < 1.0:', 'if fo > 0.0 and snk < 1.0 and u.r96_stage != 29.0:'),
        ('bt = sample(u.burn, i.uv)', 'bt = if u.r96_stage == 30.0: vec4(0,0,0,0) else: sample(u.burn, i.uv)'),
        ('    rk = clamp(mt.y', '    if u.r96_stage == 40.0: return vec4(canopy.y,canopy.y,canopy.y,1)\n    if u.r96_stage == 41.0: return vec4(canopy.x,canopy.x,canopy.x,1)\n    if u.r96_stage == 42.0: return vec4(puddle,puddle,puddle,1)\n    if u.r96_stage == 43.0: return vec4(bt.xyz,1)\n    rk = clamp(mt.y'),
    ])
    edit('render.jo', [
        ('terr_u = (', 'r96_stage = 99\n\nterr_u = ('),
        ('TerrU(vp = vp,', 'TerrU(r96_stage = f32(r96_stage), vp = vp,'),
        ('wet = f32(env.wet),', 'wet = (if r96_stage >= 5 and r96_stage < 7: f32(1) else: f32(env.wet)),'),
        ('    build_draw(bu, vp, cam_pos, 5000.0)', '    if r96_stage >= 10: build_draw(bu, vp, cam_pos, 5000.0)'),
        ('    __draw_named_all(bu)\n    gpu_mark("trees")', '    if r96_stage >= 10: __draw_named_all(bu)\n    gpu_mark("trees")'),
        ('        vegetation_draw(vp, false)', '        if r96_stage >= 1 and r96_stage != 27: vegetation_draw(vp, false)'),
        ('    hooks.opaque()\n    gl_opaque_state()', '    if r96_stage >= 10: hooks.opaque()\n    gl_opaque_state()'),
        ('if not under: grass_draw(', 'if not under and r96_stage >= 1 and r96_stage != 27: grass_draw('),
        ('if not under: water_draw(', 'if not under and r96_stage >= 9 and r96_stage != 25: water_draw('),
        ('    hooks.transparent()', '    if r96_stage >= 11 and r96_stage != 26: hooks.transparent()'),
    ])
    edit('fx.jo', [
        ('contact_shadows: vec4[]', 'r96_fx_stage = 99\ncontact_shadows: vec4[]'),
        ('    loop c in contact_shadows:', '    loop c in contact_shadows:\n        if r96_fx_stage == 31: continue'),
        ('if not indoor and not snowing and env.wet > 0.62:', 'if not indoor and not snowing and env.wet > 0.62 and r96_fx_stage != 32:'),
    ])
    s = (source / 'main.jo').read_text()
    s = re.sub(r"(?m)^(use|from) '([^']+)'", lambda m: f"{m[1]} '{source / m[2]}'", s)
    s = s.replace('update = (dt0: f64):', 'production_update = (dt0: f64):').replace('\ndraw = ():', '\nproduction_draw = ():')
    s += f"\nuse '{ROOT}/tools/performance_output.jo'\nfrom '{source}/fx.jo' import __pinst_alpha\n"
    s += '''
update = (dt: f64):
    pl.invuln = max(pl.invuln, 1.0)
    production_update(dt)
r96_out = env("R96_OUT") ?? "build/round96"
r96_frames = [loop f in split(env("R96_FRAMES") ?? "300", ","): to_int(f) ?? 300]
draw = ():
    saved_contact = contact_shadows
    production_draw()
    if r96_frames.contains(frame_number()) or (env("R96_MINUTE") != none and (frame_number() % 12 == 0 or env.lightning > 0.0)):
        assert(save_png(screenshot(), r96_out + "/frame-{frame_number()}.png"))
    if frame_number() == 300:
        rain_near = 0
        rain_far = 0
        loop drop in __pinst_alpha:
            if drop.data.y != 4.0 or drop.data.w <= 0.0: continue
            clip = sc.vp * vec4(drop.pos.xyz,1)
            if clip.w <= 0.0 or abs(clip.x) > clip.w or abs(clip.y) > clip.w: continue
            if length(drop.pos.xyz-sc.cam) < 12.0: rain_near += 1
            else: rain_far += 1
        eprint("rain-volume near={rain_near} far={rain_far}")
    if env("R96_MINUTE") != none:
        eprint("minute f={frame_number()} dark={env.dark:.6} sky={luma(env.sky_amb):.6} flash={env.lightning:.6}")
    if env("R96_LAYERS") != none and frame_number() == 300:
        saved = env
        saved_post = post
        saved_moon = post_moon
        saved_gold = post_golden
        loop stage in [0..12):
            env = saved
            if stage < 7:
                env.weather = .clear
                env.clouds = 0.42
                env.rain = 0.0
                env.wet = 0.0
                env.storm_k = 0.0
                env.lightning = 0.0
                env_update(0.0, false)
            environment_visuals_update()
            if stage < 8:
                post.sat = 1.15
                post_moon = 0.0
                post_golden = 0.0
            r96_stage = stage
            contact_shadows = saved_contact
            production_draw()
            assert(save_png(screenshot(), r96_out + "/layer-{stage}.png"))
        env = saved
        post = saved_post
        post_moon = saved_moon
        post_golden = saved_gold
        loop stage in [20,21,22,23,24,25,26,27,28,29,30,31,32,40,41,42,43]:
            r96_stage = stage
            r96_fx_stage = stage
            contact_shadows = saved_contact
            production_draw()
            assert(save_png(screenshot(), r96_out + "/ablate-{stage}.png"))
        r96_stage = 99
        r96_fx_stage = 99
        env = saved
        post = saved_post
        post_moon = saved_moon
        post_golden = saved_gold
main = ():
    weather_rng_restore(rng(31))
    performance_output_run(update, draw)
'''
    fixture = OUT / label / 'fixture.jo'
    fixture.write_text(s)
    with (OUT / label / 'build.log').open('w') as log:
        subprocess.run(['sloppy/bin/sloppy', 'build', str(fixture), '-o', str(OUT / label / 'capture')], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)

def capture(label, scene):
    settings = dict(BOTW_SKIP='1', BOTW_AT='-1000,1620,3.14', BOTW_HOUR='11', BOTW_TIMESCALE='0', BOTW_WEATHER='storm')
    frames = 300
    if scene.endswith('-default'): settings.update(BOTW_HOUR='6.6', BOTW_TIMESCALE='1')
    if scene in ('clear', 'clear-default'): settings['BOTW_WEATHER'] = 'clear'
    if scene in ('layers', 'layers-default'): settings['R96_LAYERS'] = '1'
    if scene == 'dawn': settings.update(BOTW_HOUR='6.4', BOTW_WEATHER='clear', BOTW_CAM='-1030,260,1805,1.97,0.05')
    if scene == 'minute':
        frames = 3600
        settings.update(R96_MINUTE='1', BOTW_CAMDBG='1')
    out = OUT / scene / label
    out.mkdir(parents=True, exist_ok=True)
    settings.update(BOTW_SCALE='1', BOTW_NOVSYNC='1', SLOPPY_VSYNC='0', SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='1280x720', SLOPPY_FRAMES=str(frames), SLOPPY_SCREENSHOT=str(out / 'final.png'), R96_OUT=str(out))
    clean = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'R96_'))}
    (out / 'settings.json').write_text(json.dumps(settings, indent=2))
    with (out / 'run.log').open('w') as log:
        prefix = ['flock', '/tmp/botw-render.lock']
        subprocess.run(prefix + ['python3', 'tools/performance_window.py', '1280x720', 'timeout', '900', str(OUT / label / 'capture')], cwd=ROOT, env=clean | settings, stdout=log, stderr=subprocess.STDOUT, check=True)
    assert Image.open(out / 'frame-300.png').size == (1280, 720)
    print('PASS', label, scene, flush=True)

def pairs():
    for scene in ('storm', 'clear', 'dawn', 'storm-default', 'clear-default'):
        sheet = Image.new('RGB', (2560, 748), (24,27,30))
        for k, label in enumerate(('before', 'after')):
            sheet.paste(Image.open(OUT / scene / label / 'frame-300.png'), (1280*k,28))
            ImageDraw.Draw(sheet).text((1280*k+12,8),label,fill='white')
        sheet.save(OUT / scene / 'pair.png')

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['prepare','capture','pairs'])
    p.add_argument('label', nargs='?', default='after')
    p.add_argument('scenes', nargs='*')
    p.add_argument('--ref', help='prepare a frozen historical source, e.g. 431a3f5')
    a=p.parse_args()
    if a.mode=='prepare': prepare(a.label,a.ref)
    elif a.mode=='pairs': pairs()
    else:
        for scene in a.scenes or ['storm','clear','dawn','layers']: capture(a.label,scene)
