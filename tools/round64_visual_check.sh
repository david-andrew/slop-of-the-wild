#!/bin/bash
# Caller owns /tmp/botw-render.lock; this script never takes it again.
set -euo pipefail
cd "$(dirname "$0")/.."
label=${1:-after}
out=build/round64
mkdir -p "$out"
game=game
if [[ $label == before ]]; then
  if [[ ! -f "$out/before-game/main.jo" ]]; then
    mkdir -p "$out/baseline"
    git archive d325493 game | tar -x -C "$out/baseline"
    mv "$out/baseline/game" "$out/before-game"
  fi
  game="$out/before-game"
fi
export ROUND64_GAME_DIR="$game"
sloppy/bin/sloppy build "$game/main.jo" -o "$out/game-$label" > "$out/build-$label.log" 2>&1
# The critic's exact greeting, including its normal input/camera handoff.
if [[ ${ROUND64_SKIP_GREETING:-0} != 1 && ${ROUND64_PREPARE:-0} != 1 ]]; then
env BOTW_SKIP=1 BOTW_AT=-951,1876,2.5 BOTW_HOUR=7 BOTW_WEATHER=clear BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 SLOPPY_INPUT='5:w+,40:w-' SLOPPY_FRAMES=100 SLOPPY_SCREENSHOT="$out/$label-oldman.png" timeout 180 "$out/game-$label" > "$out/$label-oldman.log" 2>&1
fi
python3 - "$out" <<'PY'
from pathlib import Path
import sys,os
out=Path(sys.argv[1]).resolve(); game=Path(os.environ['ROUND64_GAME_DIR']).resolve()
s=(game/'main.jo').read_text()
for p in game.glob('*.jo'): s=s.replace(f"'{p.name}'",f"'{p}'")
s=s.replace('update = (dt0: f64):','production_update = (dt0: f64):')
s+='''
round64_started = false
round64_case = env("ROUND64_CASE") ?? "boar"
update = (dt: f64):
    if not round64_started and frame_number() >= 2:
        round64_started = true
        enemies.clear()
        animals.clear()
        bugs.clear()
        critters.clear()
        loop k in [0..3):
            p = pl.pos + v3(f64(k - 1) * 3.0, 0.0, -10.0 - f64(k % 2) * 2.0)
            p.y = f32(height_at(f64(p.x), f64(p.z)))
            assert(water_depth(f64(p.x), f64(p.z)) < 0.05, "round64 feeding patch is dry in the finished game world")
            animals.push(Animal((if round64_case == "boar": WKind.boar else: WKind.crow), p, p, seed = f64(k) * 1.73, face = 0.8 + f64(k) * 1.1, hp = 8.0, idle = f64(k) * 3.4, t = f64(k) * 1.3, flock = (if (env("ROUND64_LABEL") ?? "") == "before": -1 else: 0), appearance = f64(k) * 0.38))
        cam.yaw = 0.0
        cam.pitch = 0.13
        camera_snap()
    production_update(dt)
    if frame_number() == 60 or frame_number() == 160 or frame_number() == 300:
        save_png(screenshot(), "build/round64/{env("ROUND64_LABEL") ?? "after"}-{round64_case}-{frame_number()}.png")
        loop a in animals: print("round64 {round64_case} frame={frame_number()} state={a.state} pos={a.pos} startle={a.startle:.3}")
'''
(out/'fauna-view.jo').write_text(s)
s=(Path('tools/slate_map_view.jo')).read_text()
s+=f"\nuse '{game/'ui.jo'}'\n"
for p in game.glob('*.jo'): s=s.replace(f"use '../game/{p.name}'",f"use '{p}'").replace(f"from '../game/{p.name}'",f"from '{p}'")
s=s.replace('    inventory_draw()', '''    act.using_pad = env("ROUND64_PAD") != none
    if env("ROUND64_GLYPHS") != none:
        text("Primary controls", vec2(40, 60), 28, rgba(1, 1, 1, 1))
        loop i in [0..input_action_ids.len()):
            button_hint(input_action_label(i), input_action_names[i], 40.0 + f64(i % 4) * 300.0, 140.0 + f64(i / 4) * 72.0)
        if act.using_pad: menu_navigation_hint(40.0, 500.0)
        else: text("W S choose   A D change   E / Enter select   Tab close", vec2(40, 490), 15, rgba(1, 1, 1, 0.8))
    else: inventory_draw()''')
(out/'map-view.jo').write_text(s)
PY
sloppy/bin/sloppy build "$out/fauna-view.jo" -o "$out/fauna-$label" > "$out/build-fauna-$label.log" 2>&1
sloppy/bin/sloppy build "$out/map-view.jo" -o "$out/map-$label" > "$out/build-map-$label.log" 2>&1
if [[ ${ROUND64_PREPARE:-0} == 1 ]]; then exit 0; fi
for scene in boar crow; do
  env BOTW_SKIP=1 BOTW_AT=-1040,1825,0 BOTW_HOUR=8 BOTW_WEATHER=clear BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 ROUND64_CASE="$scene" ROUND64_LABEL="$label" SLOPPY_INPUT='100:w+,100:shift+,150:w-,150:shift-' SLOPPY_FRAMES=300 SLOPPY_SCREENSHOT="$out/$label-$scene-final.png" timeout 180 "$out/fauna-$label" > "$out/$label-$scene.log" 2>&1
done
if [[ ${ROUND64_FAUNA_ONLY:-0} == 1 ]]; then exit 0; fi
for device in keys pad; do
  extra=(); [[ $device != pad ]] || extra=(ROUND64_PAD=1)
  env "${extra[@]}" BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_FRAMES=3 SLOPPY_SCREENSHOT="$out/$label-map-$device.png" timeout 180 "$out/map-$label" > "$out/$label-map-$device.log" 2>&1
  env "${extra[@]}" ROUND64_GLYPHS=1 BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_FRAMES=3 SLOPPY_SCREENSHOT="$out/$label-glyphs-$device.png" timeout 180 "$out/map-$label" > "$out/$label-glyphs-$device.log" 2>&1
done
