#!/usr/bin/env python3
"""Matched critic views. Owns one render flock per process; never wrap this tool."""
import argparse, hashlib, json, os, random, subprocess
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
rng=random.Random(93)
RANDOM=sorted(rng.sample(range(301,901),30))
TIMES=','.join(map(str,sorted(random.Random(93).sample(range(54000),30))))
SCENES={
 'swirl-day':([820],dict(BOTW_TITLE='1',SLOPPY_INPUT='10:w+,300:w-',R93_TIMES=TIMES)),
 'swirl-night':([820],dict(BOTW_TITLE='1',BOTW_HOUR='22',SLOPPY_INPUT='10:w+,300:w-',R93_TIMES=TIMES)),
 'title':([820],dict(BOTW_TITLE='1',SLOPPY_INPUT='10:w+,300:w-')),
 'night':(RANDOM+[920],dict(BOTW_TITLE='1',BOTW_HOUR='22',SLOPPY_INPUT='10:w+,300:w-')),
 'rise':([400,550,700],dict(BOTW_RISE='1')),
 'combat-panorama':([90,110,155,210,330,400],dict(R93_COMBAT_CASTLE='1',BOTW_SKIP='1',BOTW_AT='-1439,1606,0',BOTW_GIVE='travelers_sword,travelers_shield',SLOPPY_INPUT='5:w+,40:w-,45:k+,100:j+,106:j-,125:j+,131:j-,150:d+,152:space+,154:space-,170:d-,300:j+,306:j-,330:j+,336:j-')),
 'combat-castle':([90,110,155,210,330,400],dict(BOTW_SKIP='1',BOTW_AT='-1439,1606,0',BOTW_GIVE='travelers_sword,travelers_shield',SLOPPY_INPUT='5:w+,40:w-,45:k+,100:j+,106:j-,125:j+,131:j-,150:d+,152:space+,154:space-,170:d-,300:j+,306:j-,330:j+,336:j-')),
 'combat':([120,230,360,480],dict(BOTW_SKIP='1',BOTW_AT='-955,1964,0',BOTW_TENTFIRE='5',SLOPPY_INPUT='100:k+,160:j+,170:j-,240:j+,250:j-,320:j+,330:j-')),
 'bolt':([299,300,301,302,303,304],dict(BOTW_SKIP='1',BOTW_AT='-1190,1665,-0.9',BOTW_WEATHER='storm',BOTW_BOLT='300')),
 'forest-bolt':([299,300,301,302,303,304],dict(BOTW_SKIP='1',BOTW_AT='-1000,1620,3.14',BOTW_WEATHER='storm',BOTW_BOLT='300')),
 'dusk':([300],dict(BOTW_SKIP='1',BOTW_AT='-1030,1805,1.57',BOTW_HOUR='18.6',BOTW_WEATHER='cloudy',R93_MASK='1')),
 'overcast':([300],dict(BOTW_SKIP='1',BOTW_AT='-1030,1805,1.57',BOTW_WEATHER='cloudy',R93_MASK='1')),
 'dark':([300],dict(BOTW_SKIP='1',BOTW_AT='-1030,1805,1.57',BOTW_HOUR='22',BOTW_WEATHER='cloudy',R93_MASK='1')),
 'wake':([330,420,520],{}),
}
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('label')
    parser.add_argument('scenes', nargs='*', choices=list(SCENES))
    parser.add_argument('--models', type=Path)
    args = parser.parse_args()
    assert args.label.replace('-', '').isalnum()
    os.chdir(ROOT)
    binary = args.binary.resolve()
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    cwd = ROOT
    if args.models:
        # Read-only asset links let the old and new meshes coexist throughout
        # capture, without swapping the working tree's production models.
        cwd = ROOT / 'build/round93' / f'{args.label}-root'
        assets = cwd / 'assets'
        models = assets / 'models'
        models.mkdir(parents=True, exist_ok=True)
        for entry in (ROOT / 'assets').iterdir():
            if entry.name != 'models' and not (assets / entry.name).exists():
                (assets / entry.name).symlink_to(entry)
        for entry in (ROOT / 'assets/models').iterdir():
            candidate = args.models.resolve() / entry.name
            target = candidate if candidate.exists() else entry
            link = models / entry.name
            if not link.exists():
                link.symlink_to(target)
            assert link.resolve() == target.resolve(), 'model set changed under an existing label'
    model_hashes = {name: hashlib.sha256((cwd / 'assets/models' / name).read_bytes()).hexdigest()
                    for name in ('hero.mdl', 'hero_bare.mdl')}
    clean = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'R93_'))}
    for name in args.scenes or SCENES:
        frames, settings = SCENES[name]
        out = ROOT / 'build/round93' / name / args.label
        out.mkdir(parents=True, exist_ok=True)
        env = clean | dict(
            BOTW_HOUR='11', BOTW_WEATHER='clear', BOTW_SCALE='1', BOTW_NOVSYNC='1',
            SLOPPY_VSYNC='0', SLOPPY_PLATFORM='x11',
            SLOPPY_WINDOW='1920x1080' if 'bolt' in name else '1280x720',
            R93_OUT=str(out), R93_FRAMES=','.join(map(str, frames)),
            SLOPPY_FRAMES=str(max(frames) + 1), SLOPPY_SCREENSHOT=str(out / 'final.png')) | settings
        (out / 'settings.json').write_text(json.dumps(dict(
            binary=str(binary), sha256=digest, models=model_hashes,
            settings={k:v for k,v in env.items() if k not in clean}), indent=2) + '\n')
        with (out / 'run.log').open('w') as log:
            subprocess.run(['flock', '/tmp/botw-render.lock', 'timeout', '240', str(binary)],
                           cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        expected = tuple(map(int, env['SLOPPY_WINDOW'].split('x')))
        images = [out / f'frame-{frame}.png' for frame in frames]
        images += [out / f'sample-{tick}.png' for tick in settings.get('R93_TIMES', '').split(',') if tick]
        for path in images:
            assert Image.open(path).size == expected, path
        assert hashlib.sha256(binary.read_bytes()).hexdigest() == digest, 'capture binary changed'
        print('PASS', name, args.label, frames, flush=True)


if __name__ == '__main__':
    main()
