#!/usr/bin/env python3
"""Round 67 hero evidence. Owns one flock per render; do not wrap in flock.

prepare before|after; capture before|after [views...]; poses before|after; report.
batch before|after captures all game/pose views under one lock.
Before uses d46710a; after uses the current source. Raw evidence stays in build/.
"""
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'build/round67'
LOCKED = False
BASELINE = 'd46710a5934e224f0925961e7b08001087bf65f5'
VIEWS = {f'wake{n}': ({}, n) for n in (330, 420, 520)}
VIEWS.update({
    'idle': ({'BOTW_SKIP': '1', 'BOTW_AT': '-1030,1805,1.57'}, 60),
    'run': ({'BOTW_SKIP': '1', 'BOTW_AT': '-1030,1805,1.57', 'SLOPPY_INPUT': '10:w+'}, 120),
})
for name in ('idle', 'run'):
    VIEWS['bare-' + name] = VIEWS[name]


def build(source, binary):
    with binary.with_suffix('.build.log').open('w') as log:
        subprocess.run([str(ROOT/'sloppy/bin/sloppy'), 'build', str(source), '-o', str(binary)],
                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)


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
            if source.name in ('hero.mdl', 'hero_bare.mdl'):
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
        for clip in ('idle', 'run', 'climb'):
            render(phase, f'pose-{model}-{clip}', out/'pose-game', dict(VIEW_MODEL=model, VIEW_CLIP=clip,
                   VIEW_FOCUS='1', VIEW_NOPROPS='1', VIEW_DIST='2.65', VIEW_YAW='2.4',
                   VIEW_T='0.34', VIEW_HOUR='11', SLOPPY_FRAMES='4'))


def report():
    gameplay = {}
    for name in ('idle', 'run', 'bare-idle', 'bare-run',
                 *(f'pose-{model}-{clip}' for model in ('hero', 'hero_bare')
                   for clip in ('idle', 'run', 'climb'))):
        before = Image.open(OUT/'before'/f'{name}.png').convert('RGB')
        after = Image.open(OUT/'after'/f'{name}.png').convert('RGB')
        bounds = ImageChops.difference(before, after).getbbox()
        gameplay[name] = dict(identical=bounds is None, difference_bounds=bounds)
        assert bounds is None, f'non-wake pose changed: {name}'
    (OUT/'gameplay-pixel-contract.json').write_text(json.dumps(gameplay, indent=2)+'\n')
    baseline_weather = {}
    for weather in ('clear', 'cloudy', 'rain', 'storm'):
        for mode in ('visible', 'hidden', 'mask'):
            name = f'canopy-{weather}-{mode}.png'
            source = OUT/'weather-baseline-canopy'/name
            if source.exists():
                bounds = ImageChops.difference(Image.open(source).convert('RGB'),
                    Image.open(OUT/'weather-silhouette'/name).convert('RGB')).getbbox()
                baseline_weather[name] = dict(identical=bounds is None, difference_bounds=bounds)
    (OUT/'weather-baseline-comparison.json').write_text(json.dumps(baseline_weather, indent=2)+'\n')
    inherited = len(baseline_weather) == 12 and all(v['identical'] for v in baseline_weather.values())
    crops = {
        'wake330-body': ('wake330', (490, 140, 990, 475)),
        'wake420-body': ('wake420', (530, 250, 795, 585)),
        'wake520-body': ('wake520', (560, 175, 695, 625)),
        'wake330-arm': ('wake330', (575, 275, 710, 455)),
        'wake330-knees': ('wake330', (670, 235, 915, 385)),
        'wake330-ankles': ('wake330', (750, 350, 990, 445)),
        'wake420-arm': ('wake420', (590, 300, 750, 450)),
        'wake420-knees': ('wake420', (635, 405, 790, 505)),
        'wake420-ankles': ('wake420', (645, 475, 790, 580)),
        'wake520-arm': ('wake520', (580, 240, 685, 430)),
        'wake520-knees': ('wake520', (580, 430, 690, 560)),
        'wake520-ankles': ('wake520', (565, 530, 690, 625)),
    }
    for name in ('idle', 'run', 'bare-idle', 'bare-run'):
        crops[name+'-body'] = (name, (540, 315, 740, 720))
    for model in ('hero', 'hero_bare'):
        for clip in ('idle', 'run', 'climb'):
            name = f'pose-{model}-{clip}'
            crops[name+'-body'] = (name, (365, 40, 900, 720))
            crops[name+'-legs'] = (name, (365, 340, 900, 720))
    views = {name: name.replace('-', ' · ') for name in crops}
    for name in ('wake330', 'wake420', 'wake520'):
        views[name] = name+' · full frame'
    images = {}
    for phase in ('before', 'after'):
        for name, (source, box) in crops.items():
            Image.open(OUT/phase/f'{source}.png').crop(box).save(OUT/phase/f'{name}.png')
        for name in views:
            p = OUT/phase/f'{name}.png'
            images.setdefault(name, {})[phase] = 'data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()
    checks = {}
    for name in ('hero_model_check', 'hero_surface_check', 'wake_contact_check', 'opening_test', 'opening_check', 'weather_silhouette_check'):
        text = (OUT/f'{name}.log').read_text()
        assert 'PASS' in text and not re.search(r'(?m)^FAIL|panic:|Traceback|error:', text), name
        checks[name] = 'PASS'
    weather = json.loads((OUT/'weather-silhouette/contrast.json').read_text())
    minimum = min(v['contrast'] for v in weather['results'].values())
    margin_pass = len(weather['results']) == 12 and not weather['failures'] and minimum >= .12
    page = '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Round 67 hero surfaces</title><style>
body{margin:0;color:var(--foreground,#263344);font:14px system-ui}select,button{font:inherit;background:var(--background,#fff);color:inherit;border:1px solid var(--border,#ccc);padding:7px;border-radius:6px}.controls{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:8px}.pane{background:#14202b;color:white;border-radius:8px;overflow:hidden}.pane p{margin:10px}.pane img{width:100%;max-height:580px;object-fit:contain;display:block}.note{line-height:1.5;color:var(--muted-foreground,#657485)}@media(max-width:500px){.pair{grid-template-columns:1fr}}</style></head><body>
<div class="controls"><select id="view" aria-label="Pose and detail">OPTIONS</select><button id="prev">Previous</button><button id="next">Next</button></div>
<div class="pair"><div class="pane"><p>Before · d46710a</p><img id="before" alt="Before"></div><div class="pane"><p>After · round 67</p><img id="after" alt="After"></div></div>
<p class="note">Water and mist fade at their intersection with skin and cloth, softening hard cuffs while preserving the stone pool. A continuous wake-only shape lifts the right upper arm in front of the torso. Bare-leg topology is closed; shared normals and skin weights already match.</p>
<p class="note">Matched native crops: wake frames 330/420/520, production idle/run, and frozen production idle/run/climb clips for both outfits. The close-up viewer uses the Old Shirt variant and the same bare-body scale. Source models, skeleton, grips, soles and Old Shirt texels are unchanged.</p>
<p class="note">CHECKS. Weather silhouettes: 12/12 at the script's 10% floor; minimum MINIMUM. Requested 12% margin: MARGIN. All ten non-wake comparisons are pixel-identical. Raw frames, diagnostic controls and check logs accompany this page. Each render acquires the shared GPU lock once.</p>
<p class="note">BASELINE_NOTE</p>
<script>const images=IMAGES;const view=document.getElementById('view');function update(){for(const phase of ['before','after'])document.getElementById(phase).src=images[view.value][phase]}view.onchange=update;for(const [id,step]of [['prev',-1],['next',1]])document.getElementById(id).onclick=()=>{view.selectedIndex=(view.selectedIndex+step+view.options.length)%view.options.length;update()};update();console.log('comparison views',Object.keys(images).length);</script></body></html>'''
    page = page.replace('OPTIONS', ''.join(f'<option value="{n}">{html.escape(label)}</option>' for n,label in views.items()))
    page = page.replace('BASELINE_NOTE', 'Fresh baseline canopy captures are pixel-identical to this patch, including the limiting rain view. The 12% shortfall is inherited from the merged baseline; forest-floor contrast remains with Sol3\'s active pass.' if inherited and not margin_pass else '')
    page = page.replace('CHECKS', '; '.join(f'{k}: {v}' for k,v in checks.items())).replace('MINIMUM', f'{minimum:.2%}').replace('MARGIN', 'PASS' if margin_pass else 'NOT MET').replace('IMAGES', json.dumps(images))
    (OUT/'comparison.html').write_text(page)
    # Local paths keep tool calls compact; html_preview/render inline these assets.
    for name, phases in images.items():
        for phase, data in phases.items():
            page=page.replace(data, str(OUT/phase/f'{name}.png'))
    (OUT/'comparison-inline.html').write_text(page)
    (OUT/'results.json').write_text(json.dumps(dict(baseline=BASELINE, checks=checks, weather_minimum=minimum, weather_margin_pass=margin_pass, views=views), indent=2)+'\n')
    assert margin_pass, f'weather minimum {minimum:.2%} is below the requested 12%'


if __name__ == '__main__':
    os.chdir(ROOT)
    command = sys.argv[1]
    if command == 'batch':
        if '--locked' not in sys.argv:
            os.execvp('flock', ['flock', '/tmp/botw-render.lock', sys.executable, __file__, *sys.argv[1:], '--locked'])
        LOCKED = True
        phase = sys.argv[2]
        assert phase in ('before', 'after')
        capture(phase, [])
        poses(phase)
        raise SystemExit(0)
    if command == 'report': report()
    else:
        phase = sys.argv[2]
        assert phase in ('before', 'after')
        if command == 'prepare': prepare(phase)
        elif command == 'capture': capture(phase, sys.argv[3:])
        elif command == 'poses': poses(phase)
        else: raise SystemExit('expected prepare, capture, poses, or report')
