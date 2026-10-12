#!/bin/bash
# Self-locking: one render per lock; do not wrap this script in flock.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-build/title-rise-check}
binary=${2:-$out/game}
mkdir -p "$out/title" "$out/rise"
if [[ $# -lt 2 ]]; then sloppy/bin/sloppy build game/main.jo -o "$binary"; fi
sloppy/bin/sloppy tools/title_handoff_check.jo > "$out/title-handoff.log"
sloppy/bin/sloppy tools/title_panorama_check.jo > "$out/title-panorama.log"
sloppy/bin/sloppy tools/tower_activation_check.jo > "$out/tower-activation.log"
# Clean presets and retain display/driver preferences. Each child has its own
# environment, and each timeout begins only after obtaining the render lock.
python3 - "$out" "$binary" <<'PY'
from pathlib import Path
import os, subprocess, sys
from PIL import Image
out, binary = Path(sys.argv[1]), sys.argv[2]
env = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_'))}
env.update(BOTW_HOUR='11',BOTW_WEATHER='clear',BOTW_SCALE='1',BOTW_NOVSYNC='1',
           SLOPPY_PLATFORM='x11',SLOPPY_WINDOW='1280x720',BOTW_CAMDBG='1',BOTW_CAPTURE_EVERY='30')
for name, frames, settings in [
    ('title',850,dict(BOTW_TITLE='1',SLOPPY_INPUT='10:w+,300:w-',BOTW_OPENING_CAPTURE=str(out/'title'))),
    ('rise',810,dict(BOTW_RISE='1',BOTW_RISE_CAPTURE=str(out/'rise')))]:
    folder=out/name
    for old in folder.glob('*.png'): old.unlink()
    with (folder/'run.log').open('w') as log:
        subprocess.run(['flock','/tmp/botw-render.lock','timeout','180',binary],
            env=env|settings|dict(SLOPPY_FRAMES=str(frames),BOTW_CAPTURE_DIR=str(folder),SLOPPY_SCREENSHOT=str(folder/'final.png')),
            stdout=log,stderr=subprocess.STDOUT,check=True)
    text=(folder/'run.log').read_text()
    assert 'panic:' not in text and 'FAIL' not in text,text
    needed = ['frame-450','frame-540','frame-660','title-crane','title-shown'] if name=='title' else ['frame-300','frame-510','frame-780','tower-activation-peak']
    for stem in needed: assert (folder/(stem+'.png')).is_file(),f'missing {name}/{stem}'
    marker='opening: title-crane' if name=='title' else 'rise: tower-activation-peak'
    assert any(line.startswith(marker) and line.endswith('captured true') for line in text.splitlines()),marker
    if name == 'rise':
        # The shaft fills this normalized crop in the held production shot;
        # exclude sky and the orange shrine beacon behind it.
        im=Image.open(folder/'tower-activation-peak.png').convert('RGB')
        w,h=im.size
        shaft=im.crop((int(w*.43),int(h*.3),int(w*.55),int(h*.88)))
        blue=sum(1 for r,g,b in shaft.get_flattened_data() if b>160 and b>g*1.18 and g>r*1.25)
        assert blue > w*h*.001, f'activation blue lost in rendered shaft: {blue} pixels'
        print(f'PASS tower peak pixels: {blue} saturated blue pixels in shaft')
    print(f'PASS {name}: production captures and assertions in {folder}')
PY
