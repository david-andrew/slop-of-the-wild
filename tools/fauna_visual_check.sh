#!/bin/bash
# Production running/sneaking alerts and E catches; caller holds /tmp/botw-render.lock.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-build/fauna-visuals}
label=${2:-after}
mkdir -p "$out"
python3 - "$out" <<'PY'
from pathlib import Path
import os,sys
out=Path(sys.argv[1]).resolve()
game=Path(os.environ.get('FAUNA_GAME_DIR','game')).resolve()
source=(game/'main.jo').read_text()
for path in game.glob('*.jo'):source=source.replace(f"'{path.name}'",f"'{path}'")
source=source.replace('update = (dt0: f64):','production_update = (dt0: f64):')
source+=f"use '{game/'ui.jo'}'\nuse '{game/'wildlife.jo'}'\n"
source+='''
fauna_case = env("FAUNA_VISUAL") ?? "frog"
fauna_started = false
update = (dt: f64):
    if not fauna_started and frame_number() >= 2:
        fauna_started = true
        enemies.clear()
        animals.clear()
        critters.clear()
        bugs.clear()
        witems.clear()
        if fauna_case == "boar" or fauna_case == "fox":
            p = pl.pos + vec3(-4, 0, -4)
            p.y = f32(height_at(f64(p.x), f64(p.z)))
            animals.push(Animal((if fauna_case == "boar": WKind.boar else: WKind.fox), p, p, t = -1.0, hp = 8.0))
        else:
            p = pl.pos + vec3(0, 0, -1.2)
            p.y = f32(height_at(f64(p.x), f64(p.z)))
            if fauna_case == "firefly":
                bugs.push(Bug(p + vec3(0, 0.8, 0.4), p - vec3(0, 0, 2.6), 0.0, true))
            else: critters.push(Critter((if fauna_case == "frog": CKind.frog else: CKind.lizard), p, p, seed = 2.5))
        cam.yaw = if fauna_case == "boar" or fauna_case == "fox": 0.0 else: 0.65
        camera_snap()
    production_update(dt)
    if frame_number() == 3 and (fauna_case == "boar" or fauna_case == "fox"):
        sneak = env("FAUNA_SNEAK") != none
        assert(animals[0].danger != sneak and (animals[0].startle > 0.0) != sneak, "running alert versus quiet approach")
        print("fauna visual {fauna_case}: sneak={sneak} alert={animals[0].startle:.3} danger={animals[0].danger}")
    if frame_number() == 18 and fauna_case != "boar" and fauna_case != "fox":
        assert(ui.prompt == "Catch", "catchable critter advertises the contextual action")
        print("fauna prompt {fauna_case}: '{ui.prompt}'")
        save_png(screenshot(), (env("FAUNA_PROMPT_IMAGE") ?? "build/fauna-prompt.png"))
    if frame_number() == 30 and fauna_case != "boar" and fauna_case != "fox":
        id = if fauna_case == "frog": "hot_footed_frog" else: (if fauna_case == "lizard": "hightail_lizard" else: "sunset_firefly")
        supported = has_item_def(id)
        print("fauna catch: player={pl.pos} state={pl.state} sneak={pl.sneaking} act={fight.act} prompt={ui.prompt} interact={act.interact}")
        loop c in critters: print("fauna catch: critter={c.pos} fleeing={c.fleeing} hide={c.hide}")
        assert(count_of(id) == (if supported: 1 else: 0), "normal crouch and E catches one critter")
        if supported: assert(ui.pickup_name == item(id).name, "uses the existing pickup notice")
        print("fauna visual {fauna_case}: material={count_of(id)} pickup='{ui.pickup_name}'")
'''
(out/'fauna-visual.jo').write_text(source)
PY
sloppy/bin/sloppy build "$out/fauna-visual.jo" -o "$out/fauna-visual"
for scene in ${FAUNA_SCENES:-frog lizard firefly boar fox}; do
  hour=10; [[ $scene != firefly ]] || hour=22
  if [[ $scene == boar || $scene == fox ]]; then
    for motion in run sneak; do
      extra=(); input='1:w+'; [[ $motion != sneak ]] || { extra=(FAUNA_SNEAK=1); input='1:c+'; }
      env BOTW_SKIP=1 BOTW_AT=-1220,1675,0 BOTW_HOUR=8 BOTW_WEATHER=clear \
        FAUNA_VISUAL="$scene" "${extra[@]}" BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 \
        SLOPPY_INPUT="$input" SLOPPY_FRAMES=3 SLOPPY_SCREENSHOT="$out/$label-$scene-$motion.png" \
        timeout 180 "$out/fauna-visual" > "$out/$label-$scene-$motion.log" 2>&1
    done
  else
    env BOTW_SKIP=1 BOTW_AT=-1220,1675,0 BOTW_HOUR="$hour" BOTW_WEATHER=clear \
      FAUNA_VISUAL="$scene" FAUNA_PROMPT_IMAGE="$out/$label-$scene-prompt.png" BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 \
      SLOPPY_INPUT='1:c+,2:c-,20:e+,21:e-' SLOPPY_FRAMES=30 SLOPPY_SCREENSHOT="$out/$label-$scene.png" \
      timeout 180 "$out/fauna-visual" > "$out/$label-$scene.log" 2>&1
  fi
done
grep -E 'fauna visual' "$out/$label"*.log
