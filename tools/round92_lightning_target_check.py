#!/usr/bin/env python3
"""Exercise production storm dispatch headlessly, including off-frame random bolts."""
from pathlib import Path
import os
import subprocess
import shutil

root = Path(__file__).resolve().parent.parent
out = root / 'build/round92/checks/storm-dispatch'
(out / 'tools').mkdir(parents=True, exist_ok=True)
shutil.copytree(root / 'game', out / 'game', dirs_exist_ok=True)
shutil.copyfile(root / 'tools/tree_checks.jo', out / 'tools/tree_checks.jo')
main = (root / 'game/main.jo').read_text()
body = main.split('thunder_t = -1.0\n', 1)[1].split('# the lock-on marker', 1)[0]
# Only the platform frame clock is substituted; targeting and damage stay production.
body = 'thunder_t = -1.0\n' + body.replace('frame_number()', 'test_frame')
imports = '\n'.join(f"use '{path}'" for path in [
    'tree_checks.jo', '../game/gfx.jo', '../game/camera.jo', '../game/chars.jo',
    '../game/elements.jo', '../game/env.jo', '../game/fx.jo', '../game/player.jo',
    '../game/items.jo', '../game/terrain.jo', '../game/water.jo', '../game/sfx.jo', '../game/audio_cache.jo'])
fixture = imports + "\nfrom 'tree_checks.jo' import __tree_course\n" + '''
free_cam = false
fc_pos = vec3()
fc_yaw = 0.0
fc_pitch = 0.0
__bolt_at = 300
test_frame = 0
''' + body + '''
__audio_state = 2
items_init()
__tree_course()
inv = Inventory()
pl = Player(pos=vec3(0,0.5,0))
water_grid_set(fill(f32(1.0),4096),64,-32.0,-32.0,1.0)
cam.pos = vec3(0,3.5,5)
cam.target = vec3(0,2,0)
env.rain = 1.0
# Round 96 intentionally replaced distant random targets with visible local
# contacts. Compare the actual off-frame dispatch against the same seeded
# run without the hook, rather than assuming the old 120–600 m range.
normal_targets: vec3[] = []
__bolt_at = 0
seed_random(92)
loop frame in [30,90,299,301,360]:
    test_frame = frame
    env.bolt = true
    storm_bolt(0.0)
    normal_targets.push(strike_pos)
    assert(length(strike_pos.xz-pl.pos.xz) >= 17.999 and length(strike_pos.xz-pl.pos.xz) < 48,"natural bolts keep their visible local targets outside water-shock range")
    assert(pl.hp == 12,"ordinary random bolts do not shock Jo")
    particles.clear()
__bolt_at = 300
seed_random(92)
index = 0
loop frame in [30,90,299,301,360]:
    test_frame = frame
    env.bolt = true
    storm_bolt(0.0)
    assert(length(strike_pos-normal_targets[index]) < 0.00001,"inspection hook leaves off-frame natural targets unchanged")
    assert(pl.hp == 12,"inspection setting cannot turn random bolts into repeated water hits")
    index += 1
    particles.clear()
test_frame = 300
env.bolt = true
storm_bolt(0.0)
assert(length(strike_pos.xz-pl.pos.xz) >= 4.999,"requested inspection bolt lands at least five metres away")
assert(length(strike_pos.xz-pl.pos.xz) < 16,"requested inspection bolt stays within water-shock range")
if env("BOTW_BOLT_AT") != none:
    assert(length(strike_pos.xz-vec2(0,8)) < 0.00001,"explicit target applies to the requested inspection bolt")
assert(pl.hp == 8 and player_shock_t > 0.3,"requested bolt conducts one visible, nonlethal water shock")
print("PASS storm dispatch: five off-frame targets match the hook-free run and preserve 12/12 HP; frame 300 lands 5–16m away and leaves 8/12 HP")
'''
source = out / 'tools/fixture.jo'
source.write_text(fixture)
binary = out / 'check'
subprocess.run([str(root / 'sloppy/bin/sloppy'), 'build', str(source), '-o', str(binary)], cwd=root, check=True)
settings = dict(os.environ)
settings.pop('BOTW_BOLT_AT', None)
subprocess.run([str(binary)], cwd=root, env=settings, check=True)
subprocess.run([str(binary)], cwd=root, env={**settings, 'BOTW_BOLT_AT': '0,8'}, check=True)
