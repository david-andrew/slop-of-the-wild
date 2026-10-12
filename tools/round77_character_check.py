#!/usr/bin/env python3
"""Round 77 heads/husks, native 1280x720 with 300x300 pixel crops.

prepare before|after; capture before|after [views...]; heads before|after;
variant before|after 0|1|2|3; oldman-close before|after; pairs.
Before is 9bea708. Each scene owns one render lock; the eight tiny
model-viewer launches form one short locked batch. Never wrap this script.
"""
import os
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True
from PIL import Image, ImageDraw
import round69_character_check as base

base.OUT = base.ROOT / 'build/round77'
base.BASELINE = '9bea708'
base.VIEWS = {
    'combat': base.VIEWS['combat'], 'camp': base.VIEWS['camp'],
    'blue-camp': ({'BOTW_SKIP':'1','BOTW_AT':'-982,1654,0','BOTW_CAM':'-987,190.4,1646,1.05,-0.16'},120),
    'oldman': ({'BOTW_SKIP':'1','BOTW_AT':'-951,1876,2.5','SLOPPY_INPUT':'5:w+,40:w-'},100),
    'oldman-sit': ({'BOTW_SKIP':'1','BOTW_AT':'-951,1876,2.5'},300),
    'guardian': ({'BOTW_SKIP':'1','BOTW_CAM':'-852,222,1918,2.6,-0.4'},120),
}


def prepare(phase):
    base.prepare(phase)
    out, game = base.OUT / phase, base.game_dir(phase)
    source = (base.ROOT / 'tools/model_viewer.jo').read_text()
    source = re.sub(r"'../game/([^']+)'", lambda m: repr(str(game / m[1])), source)
    source = re.sub(r'^add_actor\(.*$', '', source, flags=re.M)
    source = source.replace('# a crowd for performance tests:',
        'add_actor("head", "bokoblin", vec3(0,0,0),variant=to_int(env("VIEW_VARIANT") ?? "0") ?? 0)\n# a crowd for performance tests:')
    source = source.replace('paused = false', 'paused = true')
    # Normal gameplay FOV and an actual four-metre orbit, not the viewer's
    # default 0.75 m / 30-degree face zoom. Pixel crops are never enlarged.
    source = source.replace('radians((if face: 30.0 else: 45.0))', 'radians(50.0)')
    source = source.replace('dist = min(cam_dist, 0.75)', 'dist = cam_dist')
    source = source.replace('dist = min(cam_dist, 3.6)', 'dist = cam_dist')
    source += f"\nuse '{base.ROOT/'tools/performance_output.jo'}'\nmain = (): performance_output_run(update,draw)\n"
    (out / 'viewer.jo').write_text(source)
    base.build(out / 'viewer.jo', out / 'viewer')
    prepare_variants(phase)


def heads(phase):
    if '--locked' not in sys.argv:
        os.execvp('flock', ['flock', '/tmp/botw-render.lock', sys.executable, __file__, *sys.argv[1:], '--locked'])
    base.LOCKED = True
    for variant in range(4):
        for angle in ('0', '0.65'):
            base.render(phase, f'head-{variant}-{angle}', base.OUT/phase/'viewer', dict(
                VIEW_VARIANT=str(variant), VIEW_FOCUS='1', VIEW_FACE='1', VIEW_DIST='4',
                VIEW_YAW=angle, VIEW_PITCH='0.04', VIEW_T='0.4', VIEW_HOUR='11',
                VIEW_NOPROPS='1', SLOPPY_FRAMES='4'))


def prepare_variants(phase):
    import shutil
    out = base.OUT/phase
    game = out/'variants-game'
    game.mkdir(exist_ok=True)
    for p in base.game_dir(phase).glob('*.jo'):
        shutil.copyfile(p,game/p.name)
    path = game/'chars.jo'
    source = path.read_text()
    needle = '                if e.state == .dead: p.dissolve'
    assert source.count(needle)==1
    source = source.replace(needle,
        '                if let v = env("ROUND77_VARIANT"): p.variant = to_int(v) ?? p.variant\n'+needle)
    path.write_text(source)
    path = game/'main.jo'
    source = path.read_text().replace('update = (dt0: f64):','capture_update = (dt0: f64):')
    source += '''
update = (dt0: f64):
    capture_update(dt0)
    if env("ROUND77_CLOSE") != none:
        wm = facing_mat(old_man.pos,old_man.face)
        focus = transform_point(wm * bone_world(ranger_m,old_man.skin,"Head"),v3(0,0.07,0.17))
        fc_pos = focus + transform_dir(wm,vec3(0,0,1))*4.0
        direction=normalize(focus-fc_pos)
        fc_yaw=atan2(f64(direction.x),-f64(direction.z))
        fc_pitch=asin(f64(direction.y))
        free_cam=true
'''
    source += f"\nuse '{base.ROOT/'tools/performance_output.jo'}'\nmain = (): performance_output_run(update,draw)\n"
    path.write_text(source)
    base.build(path,out/'variants')


def variants(phase, variant=None):
    if '--locked' not in sys.argv:
        os.execvp('flock', ['flock','/tmp/botw-render.lock',sys.executable,__file__,*sys.argv[1:],'--locked'])
    base.LOCKED = True
    if variant is None:
        base.render(phase,'oldman-4m',base.OUT/phase/'variants',dict(BOTW_SKIP='1',
            BOTW_AT='-951,1876,2.5',SLOPPY_INPUT='5:w+,40:w-',BOTW_HOUR='11',
            BOTW_WEATHER='clear',ROUND77_CLOSE='1',SLOPPY_FRAMES='100'))
    else:
        assert variant in ('0','1','2','3')
        for name in ('combat','camp'):
            flags,frame = base.VIEWS[name]
            base.render(phase,f'{name}-variant-{variant}',base.OUT/phase/'variants',dict(
                flags,BOTW_HOUR='11',BOTW_WEATHER='clear',ROUND77_VARIANT=variant,SLOPPY_FRAMES=str(frame)))


def pairs():
    names = list(base.VIEWS) + [f'head-{v}-{a}' for v in range(4) for a in ('0','0.65')]
    names += ['oldman-4m', 'guardian-front'] + [f'{view}-variant-{v}' for view in ('combat','camp') for v in range(4)]
    boxes = {'oldman': (487,205), 'oldman-sit': (487,205), 'oldman-4m': (490,210), 'guardian-front': (490,210),
             'combat': (730,125), 'blue-camp': (490,180), 'guardian': (430,280), 'camp': (820,360)}
    for name in names:
        paths = [base.OUT/phase/f'{name}.png' for phase in ('before','after')]
        if not all(p.exists() for p in paths):
            continue
        images = [Image.open(p).convert('RGB') for p in paths]
        assert all(im.size == (1280,720) for im in images)
        x,y = (490,185) if name.startswith('head-') else boxes[name.split('-variant-')[0]]
        pair = Image.new('RGB',(600,324),(24,28,29))
        full = Image.new('RGB',(1280,1488),(24,28,29))
        for i,(phase,im) in enumerate(zip(('before','after'),images)):
            crop = im.crop((x,y,x+300,y+300))
            crop.save(base.OUT/phase/f'{name}-head-300.png')
            pair.paste(crop,(i*300,24))
            full.paste(im,(0,i*744+24))
            label = f'{phase.upper()} / {name} / native pixels'
            ImageDraw.Draw(pair).text((i*300+6,6),label,fill='white')
            ImageDraw.Draw(full).text((8,i*744+6),label,fill='white')
        pair.save(base.OUT/f'{name}-heads-pair.png')
        full.save(base.OUT/f'{name}-full-pair.png')
        print('paired',name)


if __name__ == '__main__':
    os.chdir(base.ROOT)
    if len(sys.argv)>1 and sys.argv[1]=='pairs':
        pairs()
    elif len(sys.argv)>=3 and sys.argv[2] in ('before','after'):
        action,phase = sys.argv[1:3]
        if action=='prepare': prepare(phase)
        elif action=='capture': base.capture(phase,sys.argv[3:])
        elif action=='heads': heads(phase)
        elif action=='variant' and len(sys.argv)>=4: variants(phase,sys.argv[3])
        elif action=='oldman-close': variants(phase)
        else: raise SystemExit(__doc__)
    else: raise SystemExit(__doc__)
