#!/bin/bash
# Owns one lock per render; do not wrap.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-build/round57-visuals}
mkdir -p "$out"
python3 - "$out" <<'PY'
from pathlib import Path
import sys
out = Path(sys.argv[1]).resolve()
game = Path('game').resolve()
s = (game/'main.jo').read_text()
for p in game.glob('*.jo'): s = s.replace(f"'{p.name}'", f"'{p}'")
s = s.replace('update = (dt0: f64):', 'production_update = (dt0: f64):')
s = s.replace('frame_number() % __capture_every == 0:', 'frame_number() % __capture_every == 0 and [29,30,32,40,60,100,120,150,220,300,330].contains(frame_number()):')
s += '''
round57_case = env("ROUND57_CASE") ?? "night"
round57_ready = false
update = (dt: f64):
    if not round57_ready:
        round57_ready = true
        pl.invuln = 1000.0
        if round57_case == "rear":
            enemies.clear()
            cam.yaw = 0.65
            camera_snap()
        if round57_case == "talus":
            loop mut e in enemies:
                if e.kind != .talus: e.state = .gone
    production_update(dt)
    if round57_case == "rear" and frame_number() == 30:
        pl.invuln = 0.0
        hit_player(1, pl.pos - forward_of(pl.face) * 2.0, 4.0, .vertical)
        hero_animate(0.0, 0.0)
        print("rear hit: state={pl.state} action={fight.act} face={pl.face:.3} hp={pl.hp}")
    if round57_case == "talus" and frame_number() == 120:
        loop e in enemies:
            if e.kind == .talus:
                print("talus prewake: state={e.state} alert={e.alert:.3} hp={e.hp}")
                pl.pos = e.pos + vec3(0, 0, 6.5)
                pl.pos.y = f32(height_at(f64(pl.pos.x), f64(pl.pos.z)))
                camera_snap()
    if frame_number() == 220 or frame_number() == 300 or frame_number() == 330:
        loop i in 0.. and e in enemies:
            if length(e.pos - pl.pos) < 20.0:
                print("round57 {round57_case} frame={frame_number()} enemy={i} kind={e.kind} state={e.state} hp={e.hp}/{e.hp_max} skull={e.skull_out} gap={length(vec2(e.pos.x-pl.pos.x,e.pos.z-pl.pos.z)):.4} pos={e.pos}")
'''
(out/'round57.jo').write_text(s)
PY
sloppy/bin/sloppy build "$out/round57.jo" -o "$out/round57"
if [[ ${VISUAL_PREPARE:-0} == 1 ]]; then exit 0; fi
for scene in ${ROUND57_SCENES:-night camp rear talus}; do
  at=-672,1535,0.8; hour=23; frames=330
  input=()
  if [[ $scene == camp ]]; then
    input=(BOTW_GIVE=travelers_sword,travelers_shield SLOPPY_INPUT='1:k+,10:w+,110:w-')
  fi
  if [[ $scene == camp || $scene == rear ]]; then at=-1439,1606,0; hour=10; fi
  if [[ $scene == rear ]]; then frames=60; fi
  if [[ $scene == talus ]]; then at=-1087.75,1677.18,0; hour=10; frames=300; fi
  mkdir -p "$out/$scene-frames"
  flock /tmp/botw-render.lock env BOTW_SKIP=1 BOTW_AT="$at" BOTW_HOUR="$hour" BOTW_WEATHER=clear "${input[@]}" ROUND57_CASE="$scene" \
    BOTW_SCALE=1 BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 \
    BOTW_CAPTURE_DIR="$out/$scene-frames" BOTW_CAPTURE_EVERY=1 \
    SLOPPY_SCREENSHOT="$out/$scene.png" SLOPPY_FRAMES="$frames" \
    timeout 180 "$out/round57" > "$out/$scene.log" 2>&1
  grep -E 'round57|rear hit|talus prewake' "$out/$scene.log"
done

# Scoped renderers either self-lock or acquire one lock per process.
if [[ ${ROUND57_REGRESSION_VISUALS:-1} == 1 ]]; then
  tools/combat_visual_check.sh "$out/combat"
  flock /tmp/botw-render.lock tools/stalkoblin_visual_check.sh "$out/stalkoblin"
fi
