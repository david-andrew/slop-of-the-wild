#!/usr/bin/env python3
"""Round 69 foreground character evidence. Owns one flock per render; do not wrap in flock.

prepare before|after; capture before|after [views...]; poses before|after.
poses-batch before|after [--remaining] locks one pose suite; batch locks all views.
Before uses 645907d; after uses the current source. Raw evidence stays in build/.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'build/round69'
LOCKED = False
BASELINE = '645907d'
VIEWS = {f'wake{n}': ({}, n) for n in (330, 420, 520)}
VIEWS.update({
    'idle': ({'BOTW_SKIP': '1', 'BOTW_AT': '-1030,1805,1.57'}, 60),
    'run': ({'BOTW_SKIP': '1', 'BOTW_AT': '-1030,1805,1.57', 'SLOPPY_INPUT': '10:w+'}, 120),
})
for name in ('idle', 'run'):
    VIEWS['bare-' + name] = VIEWS[name]


# Same production cameras as the round-59 critic plus the normal chase camera.
VIEWS.update({
    'wake': ({}, 420),
    'chase': ({'BOTW_SKIP':'1', 'BOTW_AT':'-1030,1805,1.57'}, 120),
    'camp': ({'BOTW_SKIP':'1', 'BOTW_CAM':'-947,243,1956,-0.85,-0.45'},120),
    'combat': ({'BOTW_SKIP':'1','BOTW_AT':'-1439,1606,0',
        'BOTW_GIVE':'travelers_sword,travelers_shield',
        'SLOPPY_INPUT':'5:w+,40:w-,45:k+,100:j+,106:j-,125:j+,131:j-,150:d+,152:space+,154:space-,170:d-,300:j+,306:j-,330:j+,336:j-'},155),
})

def build(source, binary):
    with binary.with_suffix('.build.log').open('w') as log:
        subprocess.run([str(ROOT/'sloppy/bin/sloppy'), 'build', str(source), '-o', str(binary)+'.next'],
                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    Path(str(binary)+'.next').replace(binary)


def game_dir(phase):
    return OUT/'before/game' if phase == 'before' else ROOT/'game'


def prepare(phase):
    out = OUT/phase
    out.mkdir(parents=True, exist_ok=True)
    game = game_dir(phase)
    if phase == 'before':
        game.mkdir(exist_ok=True)
        names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASELINE, 'game'], cwd=ROOT, text=True)
        for name in names.splitlines():
            if name.endswith('.jo'):
                (game/Path(name).name).write_bytes(subprocess.check_output(['git', 'show', f'{BASELINE}:{name}'], cwd=ROOT))
        assets = out/'assets'
        (assets/'models').mkdir(parents=True, exist_ok=True)
        for source in (ROOT/'assets').iterdir():
            if source.name != 'models' and not (assets/source.name).exists():
                (assets/source.name).symlink_to(source, target_is_directory=source.is_dir())
        for source in (ROOT/'assets/models').iterdir():
            target = assets/'models'/source.name
            if source.name in ('hero.mdl', 'hero_bare.mdl', 'bokoblin.mdl'):
                target.write_bytes(subprocess.check_output(['git', 'show', f'{BASELINE}:assets/models/{source.name}'], cwd=ROOT))
            elif not target.exists():
                target.symlink_to(source)
    build(game/'main.jo', out/'game-bin')
    bare = f'''build:
    opt = release
use '{game/'main.jo'}'
use '{game/'items.jo'}'
use '{ROOT/'tools/performance_output.jo'}'
keys: str[]
loop id in inv.keys:
    if id!="old_shirt": keys.push(id)
inv.keys=keys
main = (): performance_output_run(update,draw)
'''
    (out/'bare.jo').write_text(bare)
    build(out/'bare.jo', out/'bare-game')
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(game.glob('*.jo'))}
    (out/'sources.json').write_text(json.dumps(manifest, indent=2)+'\n')


def render(phase, name, executable, settings, resize=False):
    out = OUT/phase
    env = {k: v for k, v in os.environ.items() if not k.startswith(('VIEW_', 'BOTW_', 'SLOPPY_'))}
    env.update(BOTW_NOVSYNC='1', BOTW_NO_PREPARED_ASSETS='1', BOTW_SCALE='1',
               SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='1280x720',
               SLOPPY_SCREENSHOT=str(out/f'{name}.png'))
    env.update(settings)
    command = [str(executable)]
    if resize:
        command = [sys.executable, str(ROOT/'tools/performance_window.py'), '1280x720', *command]
    with (out/f'{name}.log').open('w') as log:
        subprocess.run([*(() if LOCKED else ('flock', '/tmp/botw-render.lock')), 'timeout', '300', *command],
                       cwd=out if phase == 'before' else ROOT, env=env,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    assert Image.open(out/f'{name}.png').size == (1280, 720)
    (out/f'{name}.environment.json').write_text(json.dumps(settings, indent=2)+'\n')
    print(phase, name, flush=True)


def capture(phase, names):
    for name in names or VIEWS:
        flags, frame = VIEWS[name]
        settings = {'SLOPPY_FRAMES': str(frame), **flags}
        if not name.startswith('wake'):
            settings.update(BOTW_HOUR='11', BOTW_WEATHER='clear')
        render(phase, name, OUT/phase/('bare-game' if name.startswith('bare-') else 'game-bin'), settings, True)


def poses(phase):
    out, game = OUT/phase, game_dir(phase)
    source = (ROOT/'tools/model_viewer.jo').read_text()
    source = re.sub(r"'../game/([^']+)'", lambda m: repr(str(game/m[1])), source)
    source = source.replace('window("Model viewer", 1280, 720)', f'use {str(game/"clips.jo")!r}\nwindow("Hero pose seams", 1280, 720)')
    source = source.replace('load_anims("assets/models/humanoid.anim")', 'load_humanoid_anims()')
    source = re.sub(r'^add_actor\(.*$', '', source, flags=re.M)
    source = source.replace('# a crowd for performance tests:', 'add_actor("hero", env("VIEW_MODEL") ?? "hero", vec3(0,0,0), variant=2)\n# a crowd for performance tests:')
    source = source.replace('paused = false', 'paused = true')
    source = source.replace('cp = CharParams(variant = a.variant)', 'cp = CharParams(variant = a.variant, hero_material=1.0)\n        hood=part_index(a.model,"hood")\n        if hood>=0: cp.hide=1<<hood')
    source = source.replace('translation(a.pos) * rotation_y(a.yaw)', 'translation(a.pos) * rotation_y(a.yaw) * scaling((if a.model.name=="hero_bare":vec3(0.86,1,0.88) else:vec3(1,1,1)))')
    (out/'pose.jo').write_text(source)
    build(out/'pose.jo', out/'pose-game')
    for model in ('hero', 'hero_bare'):
        for clip in ('idle', 'run', 'attack', 'climb'):
            if '--remaining' in sys.argv and (out/f'pose-{model}-{clip}.png').exists(): continue
            render(phase, f'pose-{model}-{clip}', out/'pose-game', dict(VIEW_MODEL=model, VIEW_CLIP=clip,
                   VIEW_FOCUS='1', VIEW_NOPROPS='1', VIEW_DIST='2.65', VIEW_YAW='2.4',
                   VIEW_T='0.34', VIEW_HOUR='11', SLOPPY_FRAMES='4'))


if __name__ == '__main__':
    os.chdir(ROOT)
    command = sys.argv[1]
    if command in ('batch', 'poses-batch', 'capture-batch'):
        if '--locked' not in sys.argv:
            os.execvp('flock', ['flock', '/tmp/botw-render.lock', sys.executable, __file__, *sys.argv[1:], '--locked'])
        LOCKED = True
        phase = sys.argv[2]
        assert phase in ('before', 'after')
        if command == 'capture-batch': capture(phase, [a for a in sys.argv[3:] if not a.startswith('--')])
        else:
            if command == 'batch': capture(phase, [])
            poses(phase)
        raise SystemExit(0)
    if command != 'batch':
        phase = sys.argv[2]
        assert phase in ('before', 'after')
        if command == 'prepare': prepare(phase)
        elif command == 'capture': capture(phase, sys.argv[3:])
        elif command == 'poses': poses(phase)
        else: raise SystemExit('expected prepare, capture, poses, or report')
