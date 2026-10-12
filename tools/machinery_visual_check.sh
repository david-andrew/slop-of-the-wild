#!/bin/bash
# Caller owns flock /tmp/botw-render.lock; never acquire a nested lock.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-build/tree-visuals/machinery}
mkdir -p "$out"
python3 - "$out" <<'PY'
from pathlib import Path
import sys
out=Path(sys.argv[1]).resolve()
game=Path('game').resolve()
s=(game/'main.jo').read_text()
for p in game.glob('*.jo'): s=s.replace(f"'{p.name}'",f"'{p}'")
s=s.replace('update = (dt0: f64):','production_update = (dt0: f64):')
s+='''
update = (dt: f64):
    production_update(dt)
    o=srec[shr_cur].o
    cam.override=true
    cam.blend=1.0
    if shr_cur==OMAN:
        cam.o_pos=o+vec3(-39,5,-30)
        cam.o_target=o+vec3(-46,0.1,-39)
    else:
        cam.o_pos=o+vec3(9,7,-5)
        cam.o_target=o+vec3(0,0,-17)
    cam.o_fov=46.0
'''
(out/'machinery-visual.jo').write_text(s)
PY
sloppy/bin/sloppy build "$out/machinery-visual.jo" -o "$out/machinery-visual"
if [[ ${VISUAL_PREPARE:-0} == 1 ]]; then exit 0; fi
for shrine in 1 3; do
 env BOTW_SKIP=1 BOTW_TOWER=1 BOTW_SHRINE="$shrine" BOTW_SCALE=1 BOTW_NOVSYNC=1 \
  SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 SLOPPY_FRAMES=180 \
  SLOPPY_SCREENSHOT="$out/shrine-$shrine.png" \
  timeout 240 "$out/machinery-visual" > "$out/shrine-$shrine.log" 2>&1
 if grep -E 'panic:|error:|FAIL' "$out/shrine-$shrine.log"; then exit 1; fi
done
