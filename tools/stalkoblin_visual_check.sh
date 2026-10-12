#!/bin/bash
# Caller holds flock /tmp/botw-render.lock; this script never acquires a second lock.
# Production rig, hit callback and draw path: skull detachment and reattachment.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-build/stalkoblin-visuals}
mkdir -p "$out"
python3 - "$out" <<'PY'
from pathlib import Path
import sys
out=Path(sys.argv[1]).resolve()
game=Path('game').resolve()
s=(game/'main.jo').read_text()
for p in game.glob('*.jo'): s=s.replace(f"'{p.name}'", f"'{p}'")
s=s.replace('update = (dt0: f64):', 'production_update = (dt0: f64):')
s=s.replace('frame_number() % __capture_every == 0:', 'frame_number() % __capture_every == 0 and [25, 45, 110, 200, 300, 380, 430].contains(frame_number()):')
s+=f"\nfrom '{game/'enemies.jo'}' import __take_hit\n"
s+='''
visual_enemy = -1
update = (dt: f64):
    if visual_enemy < 0:
        enemies.clear()
        visual_enemy = spawn_enemy(.stalkoblin, pl.pos + vec3(0, 0, -3))
        enemies[visual_enemy].weapon = "boko_club"
        enemies[visual_enemy].face = PI
        pl.invuln = 1000.0
        cam.yaw = 0.35
        camera_snap()
        assert(stalko_m.bones == boko_m.bones, "skeleton uses the exact contact rig")
        assert(stalko_m.parts.len() == 2 and part_index(stalko_m, "skull") == 1, "detachable skull is a distinct part")
        print("stalkoblin model: body={stalko_m.parts[0].tris} skull={stalko_m.parts[1].tris} triangles; bones={stalko_m.bones.len()}")
    production_update(dt)
    if frame_number() == 30:
        __take_hit(visual_enemy, 1.0, pl.pos, 2.0, false)
        enemy_anim_update(0.0)
    if frame_number() == 45:
        assert(enemies[visual_enemy].skull_out and enemies[visual_enemy].skull_age > 0.1, "hit detaches the skull through the impact")
        assert(enemies[visual_enemy].hp > 0.0, "body survives the hit")
        print("PASS skull detached: age={enemies[visual_enemy].skull_age:.3} pos={enemies[visual_enemy].skull_pos}")
    if frame_number() == 110:
        assert(enemies[visual_enemy].skull_out, "physical recovery cannot use the old 1.1s timer")
        print("PASS physical skull persists beyond old timer")
    if frame_number() % 10 == 0:
        e = enemies[visual_enemy]
        print("STALK frame={frame_number()} state={e.state} detached={e.skull_out} body={e.pos} skull={e.skull_pos} age={e.skull_age:.3}")
    if frame_number() == 380:
        assert(not enemies[visual_enemy].skull_out, "body reaches and picks up its skull")
        print("PASS skull reattached through gameplay recovery")
        __take_hit(visual_enemy, 20.0, pl.pos, 2.0, false)
    if frame_number() == 405:
        q = enemies[visual_enemy].skull_pos
        player_hits = [PHit(q, q + vec3(0, 0, 1), vec3(0, 0, -1), 2.0, 2.0, false, 900, q + vec3(-0.4, 0, 0), q + vec3(0.4, 0, 0))]
        enemies_take_hits()
        player_hits.clear()
        assert(enemies[visual_enemy].state == .dead and enemies[visual_enemy].skull_hp == 0.0, "destroying skull collapses body")
        print("PASS skull destruction collapses body")
'''
(out/'fixture.jo').write_text(s)
PY
sloppy/bin/sloppy build "$out/fixture.jo" -o "$out/fixture"
if [[ ${VISUAL_PREPARE:-0} == 1 ]]; then exit 0; fi
env BOTW_SKIP=1 BOTW_AT=-672,1535,0.8 BOTW_HOUR=23 BOTW_WEATHER=clear \
 BOTW_NOVSYNC=1 SLOPPY_VSYNC=0 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 SLOPPY_FRAMES=435 \
 BOTW_CAPTURE_DIR="$out" BOTW_CAPTURE_EVERY=5 SLOPPY_SCREENSHOT="$out/final.png" \
 timeout 180 "$out/fixture" > "$out/run.log" 2>&1
grep -E 'stalkoblin model|PASS skull' "$out/run.log"
