#!/bin/bash
# Run under flock /tmp/botw-render.lock, OR set TALUS_CAPTURE_LOCK=1 without an
# outer lock to release between captures. Never combine the two modes.
# Actual forest actor, production reveal/climb/weapon callbacks and full renderer.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-build/talus-visuals}
mkdir -p "$out"
python3 - "$out" <<'PY'
from pathlib import Path
import sys
out = Path(sys.argv[1]).resolve()
game = Path('game').resolve()
source = (game/'main.jo').read_text()
for path in game.glob('*.jo'):
    source = source.replace(f"'{path.name}'", f"'{path}'")
source = source.replace('update = (dt0: f64):','production_update = (dt0: f64):')
source += f"\nuse '{game/'talus.jo'}'\nfrom '{game/'input.jo'}' import __scr\n"
source += '''
visual_case = env("TALUS_VISUAL") ?? "reveal"
visual_enemy = -1
visual_ready = false
visual_climbed = false
visual_mantled = false
visual_foot_error = 0.0
visual_foot_samples = 0
visual_root_error = 0.0
visual_hits = 0
visual_attacked = false
update = (dt: f64):
    if not visual_ready:
        loop i in 0.. and e in enemies:
            if e.kind == .talus: visual_enemy = i
        assert(visual_enemy >= 0, "forest actor spawns a Talus")
        loop i in [0..enemies.len()):
            if i != visual_enemy: enemies[i].state = .gone
        e = enemies[visual_enemy]
        pl = Player(pos=e.pos+vec3(0,0,(if visual_case=="dormant":10 else:6.5)), face=0.0, hp=40, hp_max=40)
        pl.pos.y = f32(height_at(f64(pl.pos.x),f64(pl.pos.z)))
        if visual_case != "reveal" and visual_case != "dormant":
            enemies[visual_enemy].state = .chase
            enemies[visual_enemy].t = 0.0
            talus_sync(enemies[visual_enemy],false)
            pl.pos = e.pos+vec3(0,0,2)
        inv_add((if visual_case=="defeat":"soldiers_broadsword" else:"travelers_sword"))
        inv_add("old_shirt")
        fight.weapon_out = true
        cam.yaw = 0.0
        cam_yaw_global = 0.0
        camera_snap()
        visual_ready = true
    production_update(dt)
    e = enemies[visual_enemy]
    if pl.state == .climb: visual_climbed = true
    if pl.state == .mantle: visual_mantled = true
    # A fixed documentary camera sees the rear ore and the climbing hero.
    cam.override = true
    cam.blend = 1.0
    cam.o_pos = e.home + vec3(10,8,13)
    cam.o_target = e.home + vec3(0,2.5,0)
    if visual_case=="front":
        cam.o_pos = e.pos+transform_dir(rotation_y(-e.face),vec3(7,6,-17))
        cam.o_target = e.pos+vec3(0,3,0)
    cam.o_fov = 43.0
    cam.yaw = 0.0
    cam_yaw_global = 0.0
    if frame_number() == 85 and visual_case == "reveal":
        assert(e.state==.notice and talus_rise(e)>0.4 and talus_rise(e)<1.0, "production proximity reveals a dormant mound")
        print("talus visual reveal: rise={talus_rise(e):.4} ore={talus_ore(e)}")
    if (visual_case=="awake" or visual_case=="front") and frame_number()==85:
        assert(talus_rise(e)==1.0,"documentary view of fully raised rock body")
        print("talus visual awake: ore={talus_ore(e)} parts={TALUS_PARTS}")
    if visual_case == "dormant" and frame_number()==85:
        assert(e.state==.sleep, "far player leaves the mound dormant")
        print("talus visual dormant: state={e.state}")
    if visual_case == "climb" and frame_number()==150:
        assert(visual_climbed and pl.state==.climb and pl.stamina<1000.0, "production inputs climb the forest Talus")
        print("talus visual climb: pos={pl.pos} stamina={pl.stamina:.2}")
    deck = talus_boulder(e,2)
    rear = transform_dir(rotation_y(deck.yaw),vec3(0,0,1))
    # Walk inward from the mantle onto the safe shoulder apron beside the ore.
    # Its low crown needs a close mining stance; the middle of the broad deck
    # leaves a sword's cutting arc above it. Keep actual controller movement.
    centered = dot(pl.pos-deck.pos,rear)<0.8
    if (visual_case=="ride" or visual_case=="weak" or visual_case=="defeat") and pl.state==.ground and talus_owns(e,pl.ground.collider) and (visual_case=="ride" or visual_attacked or centered):
        if not visual_attacked:
            __key_event(int(Key.w),false)
            # The focus-safe scripted input also owns a held-key record. Release
            # on actual shoulder arrival, independent of the scaled climb duration.
            __scr.push((frame_number(),"w",false))
            visual_attacked=true
            assert(visual_climbed and visual_mantled,"production inputs mantle onto shoulder")
            # Turn from the safe shoulder apron toward the back-mounted ore.
            pl.face=PI
            print("talus visual deck: frame={frame_number()} stamina={pl.stamina:.2} pos={pl.pos}")
        if visual_case=="ride":
            before=pl.pos
            support=colliders[pl.ground.collider]
            enemies[visual_enemy].pos.x+=f32(dt*0.6)
            enemies[visual_enemy].face+=dt*0.18
            talus_sync(enemies[visual_enemy])
            # Consume after-animation carry exactly as the production frame does.
            enemy_anim_update(0.0)
            visual_root_error=max(visual_root_error,f64(length(hero_world[3].xyz-pl.pos)))
            moved=colliders[pl.ground.collider]
            # Feet retain the support pose at hero_animate; production idle/shake
            # carry can already have moved that support before this forced turn.
            # Compare against both motions, exactly as next-frame anchor carry does.
            delta=translation(moved.pos)*rotation_y(moved.yaw-hero_motion.ground_yaw)*translation(hero_motion.ground_pos*-1.0)
            loop side in [0..2):
                if hero_motion.feet[side].planted:
                    toe=transform_point(hero_world,bone_world(hero_m,hero_skin,hero_motion.legs[side*4+3])[3].xyz)
                    anchor=transform_point(delta,hero_motion.feet[side].anchor)
                    visual_foot_error=max(visual_foot_error,f64(length(toe-anchor)))
                    visual_foot_samples+=1
        else if fight.act==.idle:
            # Idle turns and shakes move the ore's bearing; aim each new swing
            # instead of assuming the original actor heading stays fixed.
            toward_ore=talus_ore(e)-pl.pos
            toward_ore.y=0.0
            if length(toward_ore)>0.05: pl.face=yaw_of(toward_ore)
            start_swing()
    if e.hp < 300.0 and visual_hits==0:
        visual_hits=1
        print("talus visual weak: frame={frame_number()} hp={e.hp:.2}")
    if frame_number()==700 and visual_case=="ride":
        print("talus visual ride: root_error={visual_root_error:.6} planted_foot_drift={visual_foot_error:.6} samples={visual_foot_samples}")
        assert(visual_attacked and visual_root_error<0.0001 and visual_foot_samples>60 and visual_foot_error<0.01,"drawn rider root follows collider without frame lag")
    if frame_number()==900 and visual_case=="weak":
        print("talus visual weak final: hp={e.hp:.2} pos={pl.pos} state={pl.state}")
        assert(e.hp<280.0,"production shoulder swings damage ore")
    if visual_case=="defeat" and frame_number()==1800:
        assert(e.state==.gone and e.talus_drops.len()==6,"production shoulder strikes defeat Talus with ore drops")
        print("talus visual defeat: state={e.state} hp={e.hp:.2} drops={e.talus_drops.len()}")
'''
(out/'talus-visual.jo').write_text(source)
PY
sloppy/bin/sloppy build "$out/talus-visual.jo" -o "$out/talus-visual"
if [[ ${VISUAL_PREPARE:-0} == 1 ]]; then exit 0; fi
capture_runner=()
if [[ ${TALUS_CAPTURE_LOCK:-0} == 1 ]]; then capture_runner=(flock /tmp/botw-render.lock); fi
for scene in ${TALUS_SCENES:-dormant reveal awake front climb ride weak defeat}; do
 frames=85
 input=()
 if [[ $scene == climb ]]; then frames=150; input=(SLOPPY_INPUT='10:w+'); fi
 if [[ $scene == ride ]]; then frames=700; input=(SLOPPY_INPUT='10:w+'); fi
 if [[ $scene == weak ]]; then frames=900; input=(SLOPPY_INPUT='10:w+'); fi
 if [[ $scene == defeat ]]; then frames=1800; input=(SLOPPY_INPUT='10:w+'); fi
 "${capture_runner[@]}" env BOTW_SKIP=1 BOTW_AT=-1087.75,1673.18,0 BOTW_HOUR=10 BOTW_WEATHER=clear \
  "${input[@]}" TALUS_VISUAL="$scene" BOTW_SCALE=1 BOTW_NOVSYNC=1 SLOPPY_VSYNC=0 \
  SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 \
  SLOPPY_SCREENSHOT="$out/$scene.png" SLOPPY_FRAMES="$frames" \
  timeout 240 "$out/talus-visual" > "$out/$scene.log" 2>&1
 grep -E 'talus visual' "$out/$scene.log"
done
