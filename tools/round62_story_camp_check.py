#!/usr/bin/env python3
"""Matched title/aspect, HUD, inventory and camp evidence. Self-locks its entire capture batch; do not wrap with another flock.

prepare before|after|pair; capture before|after|pair [title|hud|inventory|camp|sweep|arrival|lift ...]
The before build is pinned to 4209136. Evidence and frozen sources stay in build/.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

from PIL import Image

os.chdir(Path(__file__).resolve().parent.parent)
ROOT = Path('build/round62')
BASELINE = '4209136'
SIZES = {'4x3': '1024x768', '16x10': '1280x800', '16x9': '1280x720',
         '21x9': '2560x1080', '32x9': '3840x1080'}

def prepare(phase):
    folder = Path('game')
    if phase == 'before':
        folder = ROOT / 'before-source/game'
        folder.mkdir(parents=True, exist_ok=True)
        names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASELINE, 'game'], text=True)
        for name in names.splitlines():
            if name.endswith('.jo'):
                (folder / Path(name).name).write_bytes(subprocess.check_output(['git', 'show', f'{BASELINE}:{name}']))
    folder = folder.resolve()
    source = (folder / 'main.jo').read_text()
    for p in folder.glob('*.jo'):
        source = source.replace(f"'{p.name}'", repr(str(p)))
    source = source.replace('update = (dt0: f64):', 'evidence_update = (dt0: f64):')
    source += '''
use '../../tools/performance_output.jo'
evidence_ready = false
update = (dt: f64):
    # Frame two has received the fixture's held W input. Run the normal approach
    # and crane updates before drawing the opaque title; no camera presets.
    if not evidence_ready and frame_number() >= 2:
        evidence_ready = true
        if env("BOTW_TITLE") != none and env("ROUND62_TITLE_RAW") == none:
            loop k in [0..900): evidence_update(1.0 / 60.0)
            print("title evidence: beat={story.beat} t={story.t:.3} alpha={story.title_alpha:.3} fov={view_fov():.3}")
        if env("ROUND62_HUD") != none:
            inv.slots = ["travelers_sword", "travelers_shield", "boko_bow"]
            slots_a = 1.0
            slots_t = 100.0
            clock_a = 1.0
            clock_t = 100.0
        if env("ROUND62_INVENTORY") != none:
            loop d in idefs:
                if d.kind == .food or d.kind == .material: inv_add(d.id, 7)
            tab_ = to_int(env("ROUND62_INVENTORY") ?? "3") ?? 3
            invui = InvUI(open = true, tab = tab_, t = 1.0, tab_t = 1.0)
        if env("ROUND62_CAMP_LOG") != none:
            loop i in 0.. and e in enemies:
                if length(e.pos - vec3(-955, 238, 1949)) < 35.0:
                    print("camp {i} pos={e.pos} home={e.home} weapon={e.weapon} archer={e.archer} lookout={e.lookout} camp={e.camp}")
    evidence_update(dt)
    if frame_number() == 59 or frame_number() == 79 or frame_number() == 599:
        print("evidence frame={frame_number() + 1} beat={story.beat} alpha={story.title_alpha:.4} fade={post.fade:.4} lens={view_pos()} Link={pl.pos} grounded={pl.grounded}")
        if shr_cur >= 0:
            print("lift evidence shrine={shr_cur + 1} local={pl.pos - srec[shr_cur].o} Leave={usables[srec[shr_cur].leave_u].enabled}")
main = (): performance_output_run(update, draw)
'''
    fixture = ROOT / f'{phase}-roles.jo'
    fixture.write_text(source)
    binary = ROOT / f'{phase}-roles'
    with (ROOT / f'{phase}-build.log').open('w') as log:
        subprocess.run(['sloppy/bin/sloppy', 'build', str(fixture), '-o', str(binary)], stdout=log, stderr=subprocess.STDOUT, check=True)
    (ROOT / f'{phase}-manifest.json').write_text(json.dumps({
        'baseline': BASELINE if phase == 'before' else None,
        'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
        'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.jo')}
    }, indent=2) + '\n')

def capture(phase, scene, label, size, extra):
    target = ROOT / f'{phase}-{scene}-{label}'
    settings = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'ROUND62_'))}
    settings.update(BOTW_HOUR='10', BOTW_TIMESCALE='0', BOTW_WEATHER='clear', BOTW_SCALE='1',
                    BOTW_NOVSYNC='1', SLOPPY_PLATFORM='x11', SLOPPY_WINDOW=size,
                    SLOPPY_FRAMES='60', SLOPPY_SCREENSHOT=str(target.with_suffix('.png')))
    settings.update(extra)
    binary = ROOT / f'{phase}-roles'
    png, logpath = target.with_suffix('.png'), target.with_suffix('.log')
    # Resume only verified frames produced after this exact fixture build.
    if png.exists() and logpath.exists() and png.stat().st_mtime >= binary.stat().st_mtime:
        logtext = logpath.read_text()
        if Image.open(png).size == tuple(map(int, size.split('x'))) and f'evidence frame={settings["SLOPPY_FRAMES"]} ' in logtext and (scene != 'lift' or 'beat=explore' in logtext):
            print(phase, scene, label, size, 'PASS resumed capture', flush=True)
            return
    with logpath.open('w') as log:
        subprocess.run([sys.executable, 'tools/performance_window.py', size, 'timeout', '180', str(binary)],
                       env=settings, stdout=log, stderr=subprocess.STDOUT, check=True)
    assert Image.open(target.with_suffix('.png')).size == tuple(map(int, size.split('x')))
    if scene == 'title':
        assert 'beat=title' in target.with_suffix('.log').read_text(), 'capture missed title'
    print(phase, scene, label, size, 'PASS capture', flush=True)

if __name__ == '__main__':
    ROOT.mkdir(parents=True, exist_ok=True)
    mode, phase = sys.argv[1:3]
    assert phase in ('before', 'after', 'pair')
    if mode == 'prepare':
        for label in (['before', 'after'] if phase == 'pair' else [phase]): prepare(label)
    elif mode == 'capture':
        if '--locked' not in sys.argv:
            subprocess.run(['flock', '/tmp/botw-render.lock', sys.executable, __file__, *sys.argv[1:], '--locked'], check=True)
            sys.exit(0)
        sys.argv.remove('--locked')
        scenes = sys.argv[3:] or ['title', 'hud', 'inventory', 'camp']
        for phase in (['before', 'after'] if phase == 'pair' else [phase]):
            for scene in scenes:
                if scene == 'title':
                    for label, size in SIZES.items():
                        capture(phase, scene, label, size, {'BOTW_TITLE': '1', 'SLOPPY_INPUT': '1:w+'})
                elif scene in ('hud', 'inventory'):
                    for label in ('4x3', '21x9'):
                        extra = {'BOTW_SKIP': '1', 'BOTW_AT': '-955,1964,0', 'BOTW_GIVE': 'travelers_sword,travelers_shield,boko_bow', 'ROUND62_HUD': '1'}
                        if scene == 'inventory': extra['ROUND62_INVENTORY'] = '3'
                        capture(phase, scene, label, SIZES[label], extra)
                elif scene == 'sweep':
                    for label, size in SIZES.items():
                        capture(phase, scene, label, size, {'BOTW_TITLE': '1', 'ROUND62_TITLE_RAW': '1', 'SLOPPY_INPUT': '10:w+,300:w-', 'SLOPPY_FRAMES': '600'})
                elif scene == 'arrival':
                    for shrine in range(1, 5):
                        capture(phase, scene, f'shrine{shrine}-frame80', '1280x720', {'BOTW_SKIP': '1', 'BOTW_TOWER': '1', 'BOTW_ENTER': str(shrine), 'SLOPPY_FRAMES': '80'})
                elif scene == 'lift':
                    capture(phase, scene, 'shrine2', '1280x720', {'BOTW_SKIP': '1', 'BOTW_SHRINE': '2'})
                    capture(phase, scene, 'shrine2-off', '1280x720', {'BOTW_SKIP': '1', 'BOTW_SHRINE': '2', 'BOTW_SHRINE_AT': '0,0.1,-2.3,3.14'})
                elif scene == 'camp':
                    capture(phase, scene, 'overview', '1280x720', {'BOTW_SKIP': '1', 'BOTW_CAM': '-947,243,1956,-0.85,-0.45', 'ROUND62_CAMP_LOG': '1'})
                else: raise ValueError(scene)
