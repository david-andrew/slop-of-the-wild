#!/bin/bash
# Requested cliff/cave views plus a sunlit shadow check, under one render lock.
# Invoke this script directly, never under another render flock.
# Usage: tools/cliff_visual_check.sh [output-dir] [already-built-game]
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ${1:-} != --locked ]]; then
    exec flock /tmp/botw-render.lock "$PWD/tools/cliff_visual_check.sh" --locked "$@"
fi
shift
out=${1:-build/cliff-visual}
mkdir -p "$out"
exe=${2:-$out/game}
if [[ $# -lt 2 ]]; then
    sloppy/bin/sloppy build game/main.jo -o "$exe"
fi
python3 - "$out" "$exe" <<'PY'
import os
import hashlib
import json
from pathlib import Path
from PIL import Image
import subprocess
import sys

out, exe = map(Path, sys.argv[1:])
views = {
    'cliffs': {'BOTW_SKIP': '1', 'BOTW_CAM': '-1600,235,1815,1.2,-0.15'},
    'overlook': {'BOTW_SKIP': '1', 'BOTW_AT': '-1030,1805,1.57',
                 'BOTW_CAM': '-1030,256,1805,-1.57,-0.08'},
    'snow': {'BOTW_SKIP': '1', 'BOTW_CAM': '-1560,320,1850,2.6,-0.35'},
    'top': {'BOTW_SKIP': '1', 'BOTW_CAM': '-1501,282,1740,-1.57,-0.75'},
    'waterfall': {'BOTW_SKIP': '1', 'BOTW_CAM': '-1660,175,1888,1.24,-0.05'},
    'climbing': {'BOTW_SKIP': '1', 'BOTW_AT': os.environ.get('CLIFF_CLIMB_AT', '-1530.537,1777.210,0.79650,207.335'),
                 'SLOPPY_INPUT': '1:w+', 'BOTW_CAMDBG': '1'},
    'passage600': {'BOTW_PASSAGE': '1', 'SLOPPY_INPUT': '20:w+'},
    'overlook-control': {'BOTW_SKIP': '1', 'BOTW_AT': '-1030,1805,1.57'},
    'cliffs-afternoon': {'BOTW_SKIP': '1', 'BOTW_CAM': '-1600,235,1815,1.2,-0.15',
                         'BOTW_HOUR': '15'},
}
binary_hash = hashlib.sha256(exe.read_bytes()).hexdigest()
captures = {}
clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
for name, flags in views.items():
    target = out / f'{name}.png'
    target.unlink(missing_ok=True)
    settings = dict(clean, **flags, SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='1600x900' if name == 'snow' else '1280x720',
                    BOTW_NOVSYNC='1', BOTW_GPU='1', BOTW_SCALE='1.0',
                    SLOPPY_FRAMES='600' if name == 'passage600' else '360',
                    SLOPPY_SCREENSHOT=str(target))
    with (out / f'{name}.log').open('w') as log:
        subprocess.run(['python3', 'tools/cliff_capture_window.py', settings['SLOPPY_WINDOW'],
                        'timeout', '300', str(exe.resolve())],
                       env=settings, stdout=log, stderr=subprocess.STDOUT, check=True)
    assert target.is_file(), f'missing capture: {target}'
    expected = (1600, 900) if name == 'snow' else (1280, 720)
    assert Image.open(target).size == expected, f'incorrect capture dimensions: {target}'
    if name == 'climbing':
        trail = [line for line in (out / f'{name}.log').read_text().splitlines() if line.startswith('cam ')]
        assert trail and ' st=climb ' in trail[-1], 'climbing capture must end attached to the wall'
    captures[name] = {k: v for k, v in settings.items() if k.startswith(('BOTW_', 'SLOPPY_'))}
    print(f'PASS capture {name}: {target}', flush=True)
assert hashlib.sha256(exe.read_bytes()).hexdigest() == binary_hash, 'capture binary changed during the batch'
(out / 'capture.json').write_text(json.dumps(dict(binary_sha256=binary_hash, views=captures), indent=2) + '\n')
PY
