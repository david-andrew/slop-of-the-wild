#!/usr/bin/env python3
"""Round70 matched light fixtures and CPU samples; owns bounded four-scene/60-second render-lock batches."""
import argparse
import atexit
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
from PIL import Image, ImageChops, ImageStat
from critic_pack import BASE, ROOT, FIXTURE, clean_env, command_run, percentiles, release_capture_lock
atexit.register(release_capture_lock)

SCENES = {
    'forest-rain': dict(BOTW_AT='-1000,1620,3.14', BOTW_WEATHER='rain'),
    'pond-rain': dict(BOTW_AT='-1190,1665,-0.9', BOTW_WEATHER='rain'),
    'forest-equipment': dict(BOTW_AT='-1000,1620,3.14', BOTW_WEATHER='rain', BOTW_GIVE='travelers_sword,travelers_shield'),
    'forest-held': dict(BOTW_AT='-1000,1620,3.14', BOTW_WEATHER='rain', BOTW_GIVE='travelers_sword,travelers_shield', SLOPPY_INPUT='1:k+'),
    'open-overcast': dict(BOTW_AT='-1030,1805,1.57'),
    'forest-clear': dict(BOTW_AT='-1000,1620,3.14'),
    'tower': dict(BOTW_AT='-560,1725,0'),
    'plume-clear': dict(BOTW_CAM='-700,330,2150,0.94,0.16'),
    'plume-overcast': dict(BOTW_CAM='-700,330,2150,0.94,0.16'),
    'plume-rain': dict(BOTW_CAM='-700,330,2150,0.94,0.16', BOTW_WEATHER='rain'),
}

def linear_luminance(path):
    with Image.open(path) as source:
        image = source.convert('RGB')
        count = image.width * image.height
        linear = [v/255/12.92 if v/255 <= 0.04045 else ((v/255+0.055)/1.055)**2.4 for v in range(256)]
        return sum(weight * sum(n*y for n,y in zip(channel.histogram(),linear))/count
                   for channel,weight in zip(image.split(),(0.2126,0.7152,0.0722)))

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('output', type=Path)
    ap.add_argument('--rain-reference', type=Path, help='prior matched capture directory; require 15-25%% lower rain brightness and identical clear forest')
    ap.add_argument('--resume', action='store_true', help='retain completed shots from this same frozen source')
    ap.add_argument('--baseline', action='store_true', help='freeze baseline-ref sources instead of the working tree')
    ap.add_argument('--baseline-ref', default='b73727d', help='baseline revision (round 70 starting master by default)')
    ap.add_argument('--scenes', nargs='+', choices=SCENES, default=list(SCENES))
    args = ap.parse_args()
    os.chdir(ROOT)
    out = args.output.resolve()
    assert out.is_relative_to(ROOT/'build') and (not out.exists() or args.resume), 'use a new build/ directory or --resume'
    game = out/'fixture/game'; game.mkdir(parents=True,exist_ok=True)
    scripts = out/'fixture/tools'; scripts.mkdir(exist_ok=True)
    sources = {}
    source_bytes = {}
    for p in sorted((ROOT/'game').glob('*.jo')):
        data = subprocess.check_output(['git','show',f'{args.baseline_ref}:game/{p.name}']) if args.baseline else p.read_bytes()
        source_bytes[p.name] = data
        sources[p.name] = hashlib.sha256(data).hexdigest()
    if args.resume:
        assert json.loads((out/'sources.json').read_text()) == sources, 'resume requires identical game sources'
        assert (scripts/'performance_output.jo').read_bytes() == (ROOT/'tools/performance_output.jo').read_bytes(), 'resume requires identical capture helper'
    shutil.copyfile(ROOT/'tools/performance_output.jo', scripts/'performance_output.jo')
    for name, data in source_bytes.items():
        (game/name).write_bytes(data)
    (out/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
    source = (game/'main.jo').read_text().replace('update = (dt0: f64):','production_update = (dt0: f64):').replace('\ndraw = ():','\nproduction_draw = ():').replace('main = (): game_run(update, draw)','')
    extension = FIXTURE.replace("'{root}/tools/performance_output.jo'", "'../tools/performance_output.jo'").replace("'{game}/", "'")
    extension = extension.replace('    if not cp_ready:\n', '''    if not cp_ready:
        if cp_scene=="open-overcast" or cp_scene=="plume-overcast":
            env.weather=.cloudy
            env.clouds=0.74
            env.weather_t=1e9
''', 1)
    (game/'main.jo').write_text(source+extension)
    binary = out/'fixture/capture'
    if not args.resume or not binary.exists():
        command_run(['sloppy/bin/sloppy','build',str(game/'main.jo'),'-o',str(binary)],out/'build.log')
    result = {}
    for name in args.scenes:
        folder = out/name; folder.mkdir(exist_ok=True)
        env = clean_env()|BASE|dict(BOTW_SKIP='1',BOTW_FRAME_LOG='1',CP_SCENE=name,CP_FRAMES='240,300',CP_OUT=str(folder),SLOPPY_FRAMES='901',SLOPPY_SCREENSHOT=str(folder/'final.png'))|SCENES[name]
        settings = {k:v for k,v in env.items() if k.startswith(('BOTW_','SLOPPY_','CP_'))}
        previous = json.loads((folder/'settings.json').read_text()) if (folder/'settings.json').exists() else {}
        (folder/'settings.json').write_text(json.dumps(settings,indent=2)+'\n')
        if not (args.resume and previous == settings and (folder/'final.png').exists() and all((folder/f'frame-{f}.png').exists() for f in [240,300])):
            command_run(['flock','/tmp/botw-render.lock','python3','tools/performance_window.py','1280x720','timeout','90',str(binary)],folder/'run.log',env,capture_batch=True)
        for frame in [240,300]:
            with Image.open(folder/f'frame-{frame}.png') as im:
                im.convert('RGB').resize((640,360),Image.Resampling.LANCZOS).save(folder/f'frame-{frame}.jpg')
        rows = [[float(v) for v in line.split()[2:]] for line in (folder/'run.log').read_text().splitlines() if line.startswith('frame sample:')]
        steady = [r for r in rows if r[0]>120 and int(r[0]) not in [240,300]]
        result[name] = {key:percentiles([r[col] for r in steady]) for key,col in [('callback_wall',2),('callback_thread',4)]}
        (out/'cpu.json').write_text(json.dumps(result,indent=2)+'\n')
        print('PASS',name,result[name]['callback_thread'],flush=True)
    if {'forest-rain','open-overcast'} <= set(args.scenes):
        forest = linear_luminance(out/'forest-rain/frame-300.png')
        overcast = linear_luminance(out/'open-overcast/frame-300.png')
        ratio = forest/overcast
        (out/'linear-brightness.json').write_text(json.dumps(dict(forest_rain=forest,open_overcast=overcast,ratio=ratio),indent=2)+'\n')
        # The visual review superseded the old 60% linear-light floor: it
        # washed out the rain. Retain the ratio as evidence, not an exposure target.
        print(f'Linear forest-rain/open-overcast brightness: {ratio:.3f}',flush=True)

    if args.rain_reference:
        assert {'forest-rain','forest-clear'} <= set(args.scenes)
        brightness = {}
        for frame in [240,300]:
            def shot(base, scene):
                return Image.open(base/scene/f'frame-{frame}.png').convert('RGB')
            before = shot(args.rain_reference, 'forest-rain')
            after = shot(out, 'forest-rain')
            assert before.size == after.size
            old = sum(ImageStat.Stat(before).mean)/3
            new = sum(ImageStat.Stat(after).mean)/3
            brightness[frame] = dict(before=old, after=new, reduction=1-new/old)
            assert 0.75 <= new/old <= 0.85, f'rain brightness reduction out of range: {1-new/old:.3%}'
            clear_before = shot(args.rain_reference, 'forest-clear')
            clear_after = shot(out, 'forest-clear')
            assert clear_before.size == clear_after.size
            assert ImageChops.difference(clear_before, clear_after).getbbox() is None, 'clear forest changed'
        (out/'rain-review.json').write_text(json.dumps(brightness,indent=2)+'\n')
        print('PASS rain review: 15-25% lower mean RGB and pixel-identical clear forest',flush=True)

if __name__=='__main__': main()
