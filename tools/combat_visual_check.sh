#!/bin/bash
# Render production combat presentation, including a perfect-dodge flurry (no gameplay hooks).
# Owns one render lock per scene; do not wrap. Optional output directory and before/after label.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-build/combat-visuals}
label=${2:-after}
mkdir -p "$out"
python3 - "$out" <<'PY'
from pathlib import Path
import sys
import os
out = Path(sys.argv[1]).resolve()
game = Path(os.environ.get('COMBAT_GAME_DIR', 'game'))
source = (game / 'main.jo').read_text()
for path in game.glob('*.jo'):
    source = source.replace(f"'{path.name}'", f"'{path.resolve()}'")
source = source.replace('update = (dt0: f64):', 'production_update = (dt0: f64):')
source = source.replace('frame_number() % __capture_every == 0:', 'frame_number() % __capture_every == 0 and visual_capture_frame():')
source += f"use '{(game / 'enemy_contacts.jo').resolve()}'\n"
source += f"from '{(game / 'enemies.jo').resolve()}' import __take_hit\n"
source += '''
visual_case = env("COMBAT_VISUAL") ?? "windup"
visual_enemy = -1
visual_hits = 0
visual_damage = 0.0
visual_hp: f64[]
visual_swings: int[]
visual_first_hit = -1
visual_capture_frame = () -> bool:
    if visual_case == "camp_sword" or visual_case == "camp_claymore" or visual_case == "camp_spear":
        return (frame_number() >= 145 and frame_number() <= 175) or (visual_first_hit >= 0 and frame_number() <= visual_first_hit + 20) or frame_number() % 10 == 0
    [29,30,31,32,33,34,35,40,45,46,50,54,58,65,75,95,115,145,175,180].contains(frame_number())
update = (dt: f64):
    if visual_case == "camp_sword" or visual_case == "camp_claymore" or visual_case == "camp_spear":
        if visual_hp.len() == 0:
            loop e in enemies:
                visual_hp.push(e.hp)
                visual_swings.push(e.last_swing)
        production_update(dt)
        loop i in [0..enemies.len()):
            e = enemies[i]
            # Enemy HP, not merely a flash/hitstop from some unrelated event.
            if e.hp < visual_hp[i] and e.last_swing >= 0 and e.last_swing != visual_swings[i]:
                damage = visual_hp[i] - e.hp
                visual_damage += damage
                assert(hitstop > 0.0, "real camp sword damage has readable impact pause")
                print("combat visual {visual_case}: melee_damage={damage:.1} enemy={i} hp={e.hp:.1} swing={e.last_swing}")
            visual_hp[i] = e.hp
            visual_swings[i] = e.last_swing
        if hitstop > 0.0:
            visual_hits += 1
            if visual_first_hit < 0: visual_first_hit = frame_number()
            print("combat visual {visual_case}: frozen frame={frame_number()} action={fight.act} time={fight.t:.4} hitstop={hitstop:.4}")
        if frame_number() % 60 == 0:
            gap = if fight.target >= 0: f64(length(enemy_pos(fight.target) - pl.pos)) else: -1.0
            print("combat visual {visual_case}: frame={frame_number()} pos={pl.pos} target_gap={gap:.2} action={fight.act} hp={pl.hp}")
        if frame_number() >= 165 and frame_number() <= 200 and frame_number() % 5 == 0 and fight.target >= 0:
            foe = enemies[fight.target]
            print("combat visual {visual_case}: approach frame={frame_number()} gap={length(foe.pos - pl.pos):.3} hero_t={fight.t:.3} foe={foe.state} foe_t={foe.t:.3}")
        if frame_number() == 300:
            assert(visual_hits > 0 and visual_damage > 0.0, "camp production inputs deal real melee damage with readable impact pause")
            print("combat visual {visual_case}: impact_frames={visual_hits} total_melee_damage={visual_damage:.1}")
        return
    if visual_enemy < 0:
        enemies.clear()
        visual_enemy = spawn_enemy(.blue_bokoblin, pl.pos + vec3(0, 0, -2.1))
        enemies[visual_enemy].weapon = "spiked_club"
        enemies[visual_enemy].face = PI
        enemies[visual_enemy].state = .windup
        enemies[visual_enemy].t = 0.0
        enemies[visual_enemy].alert = 1.0
        inv_add("travelers_sword")
        inv_add("pot_lid")
        fight.weapon_out = true
        cam.yaw = 0.65
        camera_snap()
    production_update(dt)
    if visual_case == "stagger_front" or visual_case == "stagger_rear" or visual_case == "stagger_left" or visual_case == "stagger_right":
        enemies[visual_enemy].pos = pl.pos + vec3(0, 0, -2.1)
        if frame_number() == 30:
            dir = if visual_case == "stagger_front": vec3(0, 0, -1) else: (if visual_case == "stagger_rear": vec3(0, 0, 1) else: (if visual_case == "stagger_left": vec3(1, 0, 0) else: vec3(-1, 0, 0)))
            __take_hit(visual_enemy, 5.0, enemies[visual_enemy].pos - dir * 2.0, 4.0, false)
            play_events()
        enemy_anim_update(0.0)
        if frame_number() == 40:
            assert(enemies[visual_enemy].state == .stagger, "directional stagger persists past hit-stop")
            print("combat visual {visual_case}: recoil={enemies[visual_enemy].recoil} reaction_t={enemies[visual_enemy].t:.3}")
    if visual_case == "claymore" or visual_case == "spear" or visual_case == "sword":
        id = if visual_case == "claymore": "travelers_claymore" else: (if visual_case == "spear": "boko_spear" else: "travelers_sword")
        inv.weapons = [id]
        inv.weapon = 0
        fight = Fight(act = .swing, t = clamp(f64(frame_number() - 25) / 60.0, 0.0, swing_for(item(id), 0).dur), weapon_out = true)
        hero_animate(0.0, 0.0)
        if frame_number() == 50:
            sw = swing_for(item(id), 0)
            print("combat visual {visual_case}: windup={sw.hit0:.3} duration={sw.dur:.3} phase={attack_phase(item(id), fight.t):.3}")
    if visual_case == "thrown_spin":
        enemies[visual_enemy].state = .recover
        enemies[visual_enemy].t = 0.0
        enemies[visual_enemy].pos = pl.pos + vec3(0, 0, -6.0)
        if frame_number() == 30:
            fight = Fight(act = .throw_, weapon_out = true)
            pl.face = 0.0
        if frame_number() == 55:
            flying = false
            loop w in witems:
                if w.id == "travelers_sword" and w.thrown_by_player:
                    flying = abs(w.spin) > 10.0 and length(w.vel) > 10.0
                    print("combat visual thrown_spin: spin={w.spin:.3} speed={length(w.vel):.3}")
            assert(flying, "production throw releases a spinning weapon")
    if visual_case == "thrown_spin" and frame_number() == 180:
        dropped = false
        loop w in witems:
            if w.id == "travelers_sword" and w.alive and w.resting and not w.thrown_by_player: dropped = true
        assert(dropped and enemies[visual_enemy].hp < 72.0, "production throw damages its target then drops as a collectible")
        print("combat visual thrown_spin: target_hp={enemies[visual_enemy].hp:.1} dropped={dropped}")
    if visual_case == "guard" or visual_case == "hop" or visual_case == "backflip":
        fight.act = if visual_case == "guard": Act.guard else: (if visual_case == "hop": Act.hop else: Act.backflip)
        fight.t = max(0.0, f64(frame_number() - 30) / 60.0)
        fight.hop_dir = 1.0
        hero_animate(dt, 0.0)
    if visual_case == "windup":
        enemies[visual_enemy].state = .windup
        enemies[visual_enemy].t = 0.4
        enemy_anim_update(0.0)
    if visual_case == "strike" or visual_case == "slam" or visual_case == "shove":
        move = if visual_case == "slam": 1 else: (if visual_case == "shove": 2 else: 0)
        enemies[visual_enemy].state = .attack
        enemies[visual_enemy].move = move
        enemies[visual_enemy].t = if move == 1: 0.5 else: (if move == 2: 0.133 else: 0.18)
        enemies[visual_enemy].lift = enemy_attack_lift(move, enemies[visual_enemy].t)
        enemy_anim_update(0.0)
        if frame_number() == 50:
            e = enemies[visual_enemy]
            draw = boko_weapon_draw_transform(visual_enemy)
            contact = enemy_contact_segment(e.pos, e.face, move, e.weapon, e.t, e.contact_scale)
            error = max(f64(length(transform_point(draw, vec3(0, 0, 0)) - contact.grip)), f64(length(transform_point(draw, v3(0.0, weapon_length(item(e.weapon)), 0.0)) - contact.tip)))
            assert(error < 0.003, "rendered strike and contact share grip and tip")
            print("combat visual {visual_case}: contact error={error:.6} m")
    if visual_case == "kick":
        enemies[visual_enemy].pos = pl.pos + vec3(0, 0, -1.2)
        enemies[visual_enemy].state = .attack
        enemies[visual_enemy].move = 3
        enemies[visual_enemy].t = 0.22
        enemies[visual_enemy].last_swing = -2
        enemy_anim_update(0.0)
        if frame_number() == 50:
            e = enemies[visual_enemy]
            foot = eanims[visual_enemy].world * bone_world(boko_m, eanims[visual_enemy].skin, bone_index(boko_m, "foot_r"))
            contact = enemy_contact_segment(e.pos, e.face, 3, e.weapon, e.t, e.contact_scale)
            error = max(f64(length(foot[3].xyz - contact.grip)), f64(length(transform_point(foot, enemy_kick_toe) - contact.tip)))
            assert(error < 0.003, "drawn boot equals kick contact")
            print("combat visual kick: contact error={error:.6} m")
    if visual_case == "throw":
        enemies[visual_enemy].state = .attack
        enemies[visual_enemy].move = 4
        enemies[visual_enemy].held = "rock"
        enemies[visual_enemy].t = 0.22
        enemies[visual_enemy].last_swing = -2
        enemy_anim_update(0.0)
        if frame_number() == 50:
            e = enemies[visual_enemy]
            hand = socket_world(boko_m, eanims[visual_enemy].world, eanims[visual_enemy].skin, SOCKET_HAND_R)
            origin = enemy_contact_segment(e.pos, e.face, 4, "rock", 0.22, e.contact_scale).grip
            error = f64(length(hand[3].xyz - origin))
            assert(error < 0.003, "rock release equals drawn arm")
            print("combat visual throw: release error={error:.6} m")
    if visual_case == "waiting" or visual_case == "recover" or visual_case == "gather" or visual_case == "cheer" or visual_case == "retreat":
        enemies[visual_enemy].state = if visual_case == "waiting": EState.chase else: (if visual_case == "recover": EState.recover else: (if visual_case == "gather": EState.gather else: (if visual_case == "cheer": EState.celebrate else: EState.retreat)))
        enemies[visual_enemy].may_engage = false
        enemies[visual_enemy].speed = 0.0
        enemies[visual_enemy].t = 0.4
        enemy_anim_update(0.0)
    if visual_case == "hit" and frame_number() == 30:
        e = enemies[visual_enemy]
        assert(not enemy_health_shown(e), "lock-on does not show an undamaged enemy health bar")
        player_hits = [PHit(e.pos + vec3(0, 1, 0), pl.pos + vec3(0, 1, 0), forward_of(pl.face), 5.0, 1.0, false, 101,
            e.pos + vec3(-0.4, 1, 0), e.pos + vec3(0.4, 1, 0))]
        enemy_events.clear()
        enemies_take_hits()
        play_events()
        enemy_anim_update(0.0)
        assert(enemies[visual_enemy].flash > 0.0 and hitstop > 0.0, "landed blow flashes during hit-stop")
        crown = transform_point(eanims[visual_enemy].world * bone_world(boko_m, eanims[visual_enemy].skin, bone_index(boko_m, "head")), vec3(0,0.614364,0.266732))
        gap = f64(length(enemy_health_anchor(visual_enemy)-crown))
        assert(enemy_health_shown(enemies[visual_enemy]) and gap <= 0.3, "damage reveals a health bar within 0.3 m of the posed crown")
        print("combat visual health: crown_gap={gap:.3}m hidden_before_hit=true damaged_visible=true")
        visible_burst = false
        slash_count = 0
        loop p in particles:
            if p.kind == .glow and p.life >= 0.1 and p.color.x > 0.9 and p.color.y > 0.8 and length(p.pos-e.pos-vec3(0,1,0)) < 1.2: visible_burst = true
            if p.kind == .slash: slash_count += 1
        assert(visible_burst and slash_count >= 13, "clean hit has a bright contact flash and broad slash streak")
        print("combat visual hit: flash={enemies[visual_enemy].flash:.3} hitstop={hitstop:.3} contact_burst={visible_burst} slash_dabs={slash_count}")
    if visual_case == "hit" and frame_number() == 33:
        assert(hitstop > 0.0 and enemies[visual_enemy].t < 0.006, "three update frames retain the impact pose during hit-stop")
        print("combat visual hit: three frozen frames, reaction_t={enemies[visual_enemy].t:.4}")
    if (visual_case == "flurry" or visual_case == "flurry_flash") and frame_number() == 30:
        fight.act = .hop
        fight.t = 0.1
        fight.target = visual_enemy
        avoided = not hit_player(4, enemies[visual_enemy].pos, 4.0, .vertical)
        assert(avoided and fight.act == .flurry, "perfect side hop starts a flurry through production hit_player")
        play_events()
        blue_flash = false
        loop p in particles:
            if p.kind == .glow and p.color.z > 0.9 and p.color.x < 0.6 and length(p.pos - pl.pos) < 2.0: blue_flash = true
        assert(blue_flash, "perfect dodge creates visible blue flash particles")
        print("combat visual {visual_case}: perfect dodge blue flash frame=30")
    if visual_case == "perfect_guard" and frame_number() == 30:
        fight = Fight(act = .guard, parry_t = 0.05)
        pl.face = yaw_of(enemies[visual_enemy].pos - pl.pos)
        hp = pl.hp
        blocked = not hit_player(4, enemies[visual_enemy].pos, 4.0, .vertical)
        assert(blocked and pl.hp == hp and pl.events.contains("parry"), "production perfect guard emits its golden flash without damage")
        play_events()
        gold_flash = false
        loop p in particles:
            if p.kind == .ring and p.color.x > 0.9 and p.color.z < 0.8 and length(p.pos - pl.pos) < 2.0: gold_flash = true
        assert(gold_flash, "perfect guard creates its visible golden flash")
        print("combat visual perfect_guard: golden flash frame=30 hp={pl.hp}")
    if visual_case == "windup_heavy":
        enemies[visual_enemy].weapon = "travelers_claymore"
        enemies[visual_enemy].state = .windup
        enemies[visual_enemy].t = 0.18
        if frame_number() == 30:
            enemy_events = [EEvent("windup_heavy", enemies[visual_enemy].pos)]
            play_events()
            print("combat visual windup_heavy: tell=0.18s gain=1.0 raised weapon")
        enemy_anim_update(0.0)
    if visual_case == "flurry" and frame_number() == 50:
        assert(fight.act == .flurry and fight.time_scale < 0.5 and post_focus > 0.5 and fight.flurry_hits > 0, "flurry slows and tints the rendered world")
        print("combat visual flurry: time_scale={fight.time_scale:.3} blue_focus={post_focus:.3}")
'''
(out / 'combat-visual.jo').write_text(source)
PY
sloppy/bin/sloppy build "$out/combat-visual.jo" -o "$out/combat-visual"
if [[ ${VISUAL_PREPARE:-0} == 1 ]]; then exit 0; fi
for scene in ${COMBAT_SCENES:-windup windup_heavy strike slam shove hit flurry flurry_flash perfect_guard kick throw waiting recover gather cheer retreat stagger_front stagger_rear stagger_left stagger_right claymore spear sword thrown_spin guard hop backflip}; do
  frames=50
  if [[ $scene == hit ]]; then frames=40; fi
  if [[ $scene == flurry_flash || $scene == perfect_guard ]]; then frames=35; fi
  if [[ $scene == stagger_* ]]; then frames=40; fi
  if [[ $scene == thrown_spin ]]; then frames=180; fi
  if [[ $scene == camp_* ]]; then frames=300; fi
  capture="$out/$label-$scene-frames"
  mkdir -p "$capture"
  rm -f "$capture"/frame-*.png
  # An empty input script still enables the production fixed 1/60 s capture step.
  input=(SLOPPY_INPUT=)
  if [[ $scene == flurry || $scene == flurry_flash ]]; then input=(SLOPPY_INPUT=30:k+); fi
  if [[ $scene == perfect_guard ]]; then input=(SLOPPY_INPUT=20:k+); fi
  at=-1439,1614,0
  if [[ $scene == camp_* ]]; then
    at=-1439,1606,0
    weapon=travelers_sword
    if [[ $scene == camp_claymore ]]; then weapon=travelers_claymore; fi
    if [[ $scene == camp_spear ]]; then weapon=boko_spear; fi
    swings='1:k+,1:w+,170:j+,171:j-,180:w-,185:j+,186:j-,215:j+,216:j-,245:j+,246:j-'
    if [[ $scene == camp_sword ]]; then
      # Start before the camp guard commits; follow through into blade reach.
      # The old 170/185 presses plus 180 movement stop whiffed, then got interrupted.
      swings='1:k+,1:w+,150:j+,151:j-,165:j+,166:j-,195:j+,196:j-,200:w-,225:j+,226:j-,255:j+,256:j-'
    fi
    input=(BOTW_GIVE="$weapon,travelers_shield" SLOPPY_INPUT="$swings")
  fi
  flock /tmp/botw-render.lock env BOTW_SKIP=1 BOTW_AT="$at" BOTW_HOUR=10 BOTW_WEATHER=clear \
    "${input[@]}" COMBAT_VISUAL="$scene" BOTW_SCALE=1 BOTW_NOVSYNC=1 SLOPPY_VSYNC=0 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 \
    BOTW_CAPTURE_DIR="$capture" BOTW_CAPTURE_EVERY=1 \
    SLOPPY_SCREENSHOT="$out/$label-$scene.png" SLOPPY_FRAMES="$frames" \
    timeout 180 "$out/combat-visual" > "$out/$label-$scene.log" 2>&1
  grep 'combat visual' "$out/$label-$scene.log" || true
done

python3 - "$out" "$label" <<'PY'
from PIL import Image, ImageDraw
from pathlib import Path
import re
import sys
out, label = Path(sys.argv[1]), sys.argv[2]
for frames in out.glob(f'{label}-*-frames'):
    scene = frames.name[len(label)+1:-7]
    numbers = [30,31,34,40] if scene.startswith('stagger_') else ([46,50,54,58,75,95,145,180] if scene == 'thrown_spin' else [30,35,40,45,50])
    if scene in ('flurry_flash', 'perfect_guard'): numbers = [29,30,31,32,33,34,35]
    if scene == 'hit': numbers = [29,31,32,33,34,40]
    if scene.startswith('camp_'):
        hits = re.findall(r'frozen frame=(\d+)', (out / f'{label}-{scene}.log').read_text())
        first = int(hits[0]) if hits else 110
        prior = max((int(f.stem[6:]) for f in frames.glob('frame-*.png') if int(f.stem[6:]) <= first-2), default=first-2)
        numbers = [prior, first, first+1, first+2, first+3, first+10, first+20]
    selected = [frames / f'frame-{n}.png' for n in numbers if (frames / f'frame-{n}.png').exists()]
    final = out / f'{label}-{scene}.png'
    if final.exists(): selected.append(final)
    if not selected: continue
    strip = Image.new('RGB', (480 * len(selected), 292), '#111827')
    draw = ImageDraw.Draw(strip)
    for i, f in enumerate(selected):
        strip.paste(Image.open(f).convert('RGB').resize((480,270)), (i*480,22))
        draw.text((i*480+8,5), f'{label} {scene} {f.stem}', fill='white')
    strip.save(out / f'{label}-{scene}-strip.jpg')
PY
