#!/bin/bash
# One render per lock, released between scenes; never wrap this script in flock.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-build/round85}
game=${ROUND85_GAME_DIR:-game}
label=${ROUND85_LABEL:-after}
mkdir -p "$out"
python3 - "$out" "$game" "$label" <<'PY'
from pathlib import Path
import sys
out,game,label=Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve(),sys.argv[3]
s=(game/'main.jo').read_text()
for p in game.glob('*.jo'): s=s.replace(f"'{p.name}'",f"'{p}'")
s=s.replace('update = (dt0: f64):','production_update = (dt0: f64):')
# Free-camera inspection normally omits enemy AI. This observation explicitly
# runs it, retaining real recognition, lookout scanning and state transitions.
s=s.replace('loop mut e in enemies: e.anim_t += dt', 'enemies_update(dt, env.night > 0.5)')
s=s.replace('frame_number() % __capture_every == 0:', 'frame_number() % __capture_every == 0 and (frame_number() == 1 or frame_number() % 600 == 0 or [120,132,144,156,168,180,192,210,240].contains(frame_number())):')
s+=f"\nuse '{game/'enemy_camp.jo'}'\n"
s+='''
round85_case = env("ROUND85_CASE") ?? "meadow"
round85_actions = fill(false, 5)
round85_started = false
round85_alerts = fill(-1.0, enemies.len())
update = (dt: f64):
    if not round85_started:
        round85_started = true
        pl.invuln = 1000.0
    if round85_case == "alert" and frame_number() == 120:
        # A running approach on the lookout's side, outside the seated actor's
        # close-distance trigger. No enemy state or awareness is forced.
        pl.pos = vec3(-977, 0, 1948)
        pl.pos.y = f32(height_at(f64(pl.pos.x), f64(pl.pos.z)))
        pl.vel = vec3(6, 0, 0)
        pl.noise = 5.0
    production_update(dt)
    if round85_case == "camp":
        loop e in enemies:
            if length(e.home - vec3(-955.87, 238, 1948.86)) < 20.0 and e.camp_role != .none:
                round85_actions[camp_day_activity(e)] = true
                assert(e.alert == 0.0, "minute observation stays undisturbed")
        if frame_number() == 3600:
            print("round85 camp minute: activities={round85_actions}")
            assert(round85_actions[1] and round85_actions[2] and round85_actions[3] and round85_actions[4], "four distinct camp idles in a minute")
    if round85_case == "alert" and frame_number() >= 120:
        loop i in 0.. and e in enemies:
            if length(e.home - vec3(-955.87, 238, 1948.86)) > 20.0 or e.camp_role == .none: continue
            if e.alert >= 1.0 and round85_alerts[i] < 0.0:
                round85_alerts[i] = f64(frame_number() - 120) / 60.0
                print("round85 live alert: role={e.camp_role} time={round85_alerts[i]:.4}s")
            if frame_number() == 180: assert(round85_alerts[i] >= 0.0 and round85_alerts[i] <= 1.0, "live camp reacts within one second")
    if frame_number() % 600 == 0:
        loop a in animals:
            if length(a.pos - sc.cam) < 24.0 and (a.kind == .boar or a.kind == .fox):
                print("round85 {round85_case} frame={frame_number()} kind={a.kind} state={a.state} pos={a.pos} speed={a.speed:.3} danger={a.danger}")
'''
(out/f'{label}-view.jo').write_text(s)
PY
sloppy/bin/sloppy build "$out/$label-view.jo" -o "$out/$label-view" > "$out/$label-view-build.log" 2>&1
if [[ ${ROUND85_PREPARE:-0} == 1 ]]; then exit 0; fi
for scene in ${ROUND85_SCENES:-meadow camp alert storm}; do
  cam=-946,188.0,1660,-0.75,-0.12; at=-1000,1800,0; frames=3600; hour=8; weather=clear
  if [[ $scene == camp || $scene == alert ]]; then cam=-947,243,1956,-0.85,-0.45; at=-960,1995,0; fi
  if [[ $scene == alert ]]; then frames=240; fi
  if [[ $scene == storm ]]; then frames=600; weather=storm; fi
  mkdir -p "$out/$label-$scene"
  flock /tmp/botw-render.lock env ROUND85_CASE="$scene" BOTW_SKIP=1 BOTW_AT="$at" BOTW_CAM="$cam" BOTW_HOUR="$hour" BOTW_WEATHER="$weather" BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 BOTW_CAPTURE_DIR="$out/$label-$scene" BOTW_CAPTURE_EVERY=1 SLOPPY_FRAMES="$frames" SLOPPY_SCREENSHOT="$out/$label-$scene.png" timeout 180 "$out/$label-view" > "$out/$label-$scene.log" 2>&1
  rg 'round85' "$out/$label-$scene.log" || true
done
