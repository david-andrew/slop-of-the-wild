#!/usr/bin/env python3
"""Round-91 critic views. Owns one render flock per scene; never wrap this tool.

Supply immutable before/after executables and run once per label. Captures and
settings remain under build/. Use tower_base_climb_capture.jo for the full orbit.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from PIL import Image

SCENES = {
    'climb': (260, dict(BOTW_SKIP='1', BOTW_TOWER='1', BOTW_AT='-560,1722,0', SLOPPY_INPUT='10:w+')),
    'title': (820, dict(BOTW_TITLE='1', SLOPPY_INPUT='10:w+,300:w-')),
    'rise': (550, dict(BOTW_RISE='1')),
    'night': (820, dict(BOTW_TITLE='1', BOTW_HOUR='22', SLOPPY_INPUT='10:w+,300:w-')),
    'bolt': (300, dict(BOTW_SKIP='1', BOTW_AT='-1190,1665,-0.9', BOTW_WEATHER='storm', BOTW_BOLT='300')),
    'forest-bolt': (300, dict(BOTW_SKIP='1', BOTW_AT='-1000,1620,3.14', BOTW_WEATHER='storm', BOTW_BOLT='300')),
    'hair-rain': (300, dict(BOTW_SKIP='1', BOTW_AT='-1190,1665,-0.9', BOTW_WEATHER='rain')),
    'tent230': (230, dict(BOTW_SKIP='1', BOTW_TENTFIRE='5', BOTW_AT='-955,1964,0')),
    'fire': (400, dict(BOTW_SKIP='1', BOTW_FIRE='1')),
}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('binary', type=Path)
    ap.add_argument('label')
    ap.add_argument('--output', type=Path, default=Path('build/round91'))
    ap.add_argument('--scenes', nargs='+', choices=SCENES, default=list(SCENES))
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    out = args.output.resolve()
    assert out.is_relative_to(root / 'build'), 'keep captures under build/'
    assert args.label.isalnum() or args.label.replace('-', '').isalnum()
    binary = args.binary.resolve()
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    clean = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
    common = dict(BOTW_HOUR='11', BOTW_WEATHER='clear', BOTW_SCALE='1', BOTW_NOVSYNC='1',
                  SLOPPY_VSYNC='0', SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='1280x720', BOTW_CAMDBG='1')
    for name in args.scenes:
        frames, settings = SCENES[name]
        folder = out / name
        folder.mkdir(parents=True, exist_ok=True)
        picture = folder / f'{args.label}.png'
        env = clean | common | settings | dict(SLOPPY_FRAMES=str(frames), SLOPPY_SCREENSHOT=str(picture))
        with (folder / f'{args.label}.log').open('w') as log:
            subprocess.run(['flock', '/tmp/botw-render.lock', 'python3', 'tools/performance_window.py',
                            '1280x720', 'timeout', '180', str(binary)], env=env,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        assert Image.open(picture).size == (1280,720)
        assert hashlib.sha256(binary.read_bytes()).hexdigest() == digest, 'capture binary changed'
        (folder / f'{args.label}.json').write_text(json.dumps(dict(binary=str(binary), sha256=digest,
            settings={k:v for k,v in env.items() if k.startswith(('BOTW_', 'SLOPPY_'))}), indent=2)+'\n')
        print(f'PASS {args.label}/{name}: 1280x720 frame {frames}', flush=True)

if __name__ == '__main__':
    main()
