#!/bin/bash
# Fixed trunk between the lens and Link, using production vegetation and paint passes.
# Optional baseline game source directory; caller owns the shared render lock.
set -euo pipefail
cd "$(dirname "$0")/.."
output=${1:-build/occluder-check}
game=${2:-game}
mkdir -p "$output"
python3 - "$output" "$game" <<'PY'
from pathlib import Path
import subprocess
import sys
root, game = map(lambda x: Path(x).resolve(), sys.argv[1:])
imports = '\n'.join(f"use '{game / (name + '.jo')}'" for name in ['main', 'gfx', 'vegetation', 'player', 'camera', 'chars', 'render', 'terrain', 'env'])
source = imports + '''
fixture = vec3(0, 0, 0)
fixture_update = (dt: f64):
    env_update(dt, false)
    pl.pos = fixture + vec3(0.20, 0.0, -2.1)
    pl.state = .ground
    pl.face = PI
    veg_player = pl.pos
    hooks.grass_player = pl.pos
    hero_animate(dt, -1.0)
fixture_draw = ():
    render_world(fixture + vec3(0.05, 1.8, 3.2), pl.pos + vec3(0, 1.15, 0), 50.0)
main = ():
    best = 10000.0
    loop p in places:
        if p.height < 7.0 or not starts_with(vmodels[p.model].name, "CommonTree"): continue
        d = length(p.pos.xz - vec2(-1190, 1665))
        if f64(d) < best:
            best = f64(d)
            fixture = p.pos
    print("occluder fixture trunk {fixture}")
    __game_run(fixture_update, fixture_draw)
'''
(root / 'fixture.jo').write_text(source)
subprocess.run(['sloppy/bin/sloppy', 'build', str(root / 'fixture.jo'), '-o', str(root / 'fixture')], check=True)
PY
if [[ ${OCCLUDER_BUILD_ONLY:-} == 1 ]]; then exit 0; fi
env BOTW_SKIP=1 BOTW_HOUR=12 BOTW_WEATHER=clear BOTW_NOVSYNC=1 BOTW_GPU=1 SLOPPY_PLATFORM=x11 BOTW_SCALE=0.8 SLOPPY_WINDOW=1280x720 SLOPPY_FRAMES=360 SLOPPY_SCREENSHOT="$output/tree.png" timeout 300 "$output/fixture" > "$output/tree.log" 2>&1
