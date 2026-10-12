#!/bin/bash
# Run under flock /tmp/botw-render.lock; this script never acquires a nested lock.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-build/element-puzzle-visuals}
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
puzzle_case=env("PUZZLE_VISUAL") ?? "thorns-before"
puzzle_ready=false
puzzle_id=0
update = (dt: f64):
    if not puzzle_ready:
        puzzle_id=if starts_with(puzzle_case,"thorns"):0 else:1
        p=element_puzzles[puzzle_id]
        pl=Player(pos=p.pos+vec3(0,0,(if contains(puzzle_case,"after"):12.0 else:4.5)),face=0.0,hp=40,hp_max=40)
        pl.pos.y=f32(height_at(f64(pl.pos.x),f64(pl.pos.z)))
        inv_add("warm_doublet")
        inv_add("torch")
        fight.weapon_out=true
        loop mut e in enemies: e.state=.gone
        if contains(puzzle_case,"after"):
            if p.thorn: arrows=[Arrow(pos=p.pos+vec3(0,0.85,0.3),prev=p.pos+vec3(0,0.85,0.3),fire=true,stuck=20.0)]
            else:
                loop mut b in barrels:
                    if length(b.pos-p.pos)<4.0: b.fuse=0.01
        puzzle_ready=true
    production_update(dt)
    p=element_puzzles[puzzle_id]
    cam.override=true
    cam.blend=1.0
    cam.o_pos=p.pos+vec3(3.5,3.2,7.5)
    cam.o_target=p.pos+vec3(0,1,-1)
    cam.o_fov=43.0
    if frame_number()==(if contains(puzzle_case,"after"):1200 else:300):
        expected=contains(puzzle_case,"after")
        assert(p.opened==expected,"production element source changes field barrier")
        assert(usables[chests[p.chest].usable].enabled==expected,"chest enabled only after opening")
        print("puzzle visual {puzzle_case}: open={p.opened} reward={chests[p.chest].content} count={chests[p.chest].count} pos={p.pos}")
'''
(out/'puzzle-visual.jo').write_text(s)
PY
sloppy/bin/sloppy build "$out/puzzle-visual.jo" -o "$out/puzzle-visual"
for scene in ${PUZZLE_SCENES:-thorns-before thorns-after cracks-before cracks-after}; do
 frames=300
 if [[ $scene == *after ]]; then frames=1200; fi
 env BOTW_SKIP=1 BOTW_HOUR=10 BOTW_WEATHER=clear BOTW_SCALE=1 BOTW_NOVSYNC=1 SLOPPY_VSYNC=0 \
  PUZZLE_VISUAL="$scene" SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 \
  SLOPPY_FRAMES="$frames" SLOPPY_SCREENSHOT="$out/$scene.png" \
  timeout 240 "$out/puzzle-visual" > "$out/$scene.log" 2>&1
 grep -E 'puzzle visual' "$out/$scene.log"
done
