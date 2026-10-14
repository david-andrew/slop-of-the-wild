#!/bin/bash
# One continuous run through changing weather, at the game's own pace: a clear late morning in
# the yard of the old man's cabin, a storm coming in, Link soaked and then stepping under the
# porch roof, the storm clearing. No preset weather, only when it turns.
#   tools/weather_transition_check.sh      (prints PASS/FAIL; images in build/weather-check/)
# Each game process acquires its own render lock; never wrap this script.
# BOTW_TRANSITION_OUTPUT overrides the evidence root (default build/weather-check).
set -uo pipefail
cd "$(dirname "$0")/.."
# --verify rechecks complete captures after changing an analysis rule, without rendering.
verify=false
if [[ ${1:-} == --verify || ${2:-} == --verify ]]; then verify=true; fi
root=${BOTW_TRANSITION_OUTPUT:-build/weather-check}
dir=$root
mkdir -p $dir
if ! $verify; then
    # The saved weather RNG also schedules lightning. Freeze its seed for image
    # checkpoints while exercising the production game loop and transitions.
    python3 - "$dir/fixture.jo" <<'PY'
from pathlib import Path
import re, sys
source = Path('game/main.jo').read_text()
source = re.sub(r"(?m)^(use|from) '([^']+)'", lambda m: f"{m[1]} '{(Path('game') / m[2]).resolve()}'", source)
# Sloppy imports declarations, not the entry file's loading expressions.
# Keep production loading/update/draw. Capture the current completed frame: the
# update-start hook can read an older swapped buffer whose lightning no longer
# matches this frame's weather log, creating false static-brightness failures.
capture = '    if __capture_dir != none and __capture_every > 0 and frame_number() > 0 and frame_number() % __capture_every == 0:\n        flush()\n        save_png(screenshot(), __capture_dir! + "/frame-{frame_number()}.png")\n'
assert source.count(capture) == 1
assert source.count('\ndraw = ():') == 1
source = source.replace(capture, '').replace('\ndraw = ():', '\nweather_check_draw = ():')
# Add a late open-route checkpoint before walking under the roof. The earlier
# 1200-frame image can coincide with a seeded multi-stroke lightning discharge.
capture = capture.replace('frame_number() % __capture_every == 0:',
    '(frame_number() % __capture_every == 0 or (__capture_every == 300 and frame_number() == 1290)):')
# Weather observations must finish even when an outdoor patrol reaches Link.
# Keep AI running; health and combat-camera motion are outside this assertion.
source = source.replace('update = (dt0: f64):', 'weather_check_update = (dt0: f64):')
source += '''
__weather_exit_pinned = false
update = (dt0: f64):
    pl.invuln = max(pl.invuln, 1.0)
    weather_check_update(dt0)
    if env("BOTW_WEATHER_CHECK_EXIT") != none and frame_number() >= 800 and not __weather_exit_pinned:
        __weather_exit_pinned = true
        fc_pos = view_pos()
        direction = normalize(view_target() - fc_pos)
        fc_yaw = atan2(f64(direction.x), f64(direction.z))
        fc_pitch = asin(f64(direction.y))
        free_cam = true
'''
source += '\nweather_rng_restore(rng(31))\ndraw = ():\n    weather_check_draw()\n    flush()\n' + capture
Path(sys.argv[1]).write_text(source)
PY
    sloppy/bin/sloppy build "$dir/fixture.jo" -o "$dir/game" || exit 1
fi
if ! $verify; then
    rm -f $dir/*.png
    BOTW_SKIP=1 BOTW_AT=-778.55,2267.89,-0.4 BOTW_HOUR=11 BOTW_WEATHER_SEQ="200:storm,1900:clear" \
        BOTW_WEATHER_LOG=1 BOTW_CAPTURE_DIR=$dir BOTW_CAPTURE_EVERY=300 SLOPPY_WINDOW=960x540 \
        SLOPPY_INPUT="1300:w+,1400:w-" SLOPPY_SCREENSHOT=$dir/final.png SLOPPY_FRAMES=3010 \
        flock /tmp/botw-render.lock timeout 900 "$root/game" 2>&1 | tee "$dir/run.log" | grep "^wx " > $dir/log.txt
fi
python3 - $dir <<'PY'
import re, sys, glob, statistics
from PIL import Image, ImageStat
d = sys.argv[1]
rows = []
for line in open(f"{d}/log.txt"):
    m = dict(re.findall(r"(\w+)=(\S+)", line))
    rows.append({"f": int(m["f"]), "clouds": float(m["clouds"]), "rain": float(m["rain"]),
                 "dark": float(m["dark"]), "wet": float(m["wet"]), "sun": float(m["sun"]), "sheltered": m["sheltered"] == "true"})
# The 120 Hz simulation logs twice per rendered frame. Compare completed
# frames, so a fading lightning pulse is not mistaken for a tiny sun change
# paired with a large ambient change between two substeps of the same flash.
rows = list({int(r["f"]): r for r in rows}.values())
fails = []
def check(ok, what):
    if not ok: fails.append(what)
check(len(rows) >= 290, f"logged {len(rows)} samples, expected 300")
# no step: every 10 frames the sky, rain and light move only a little
for a, b in zip(rows, rows[1:]):
    for k, lim in (("clouds", 0.02), ("rain", 0.03), ("dark", 0.03)):
        if abs(b[k] - a[k]) > lim:
            fails.append(f"{k} jumped {a[k]:.3f} -> {b[k]:.3f} at frame {b['f']}")
at = {r["f"]: r for r in rows}
check(at[200]["rain"] < 0.01 and not at[200]["sheltered"], "clear and in the open before the storm")
check(at[1300]["rain"] > 0.6 and at[1300]["dark"] > 0.4, f"storm built by frame 1300 (rain {at[1300]['rain']:.2f}, dark {at[1300]['dark']:.2f})")
check(at[1300]["wet"] > 0.3, f"soaked in the open (wet {at[1300]['wet']:.2f})")
# (from the last moment in the open: at the roof's lip he may step in and out of its cover)
last_open = max(r["f"] for r in rows if not r["sheltered"])
inside = [r for r in rows if r["f"] > last_open]
check(len(inside) > 0 and inside[0]["f"] < 1700, f"reached the roof (in the open until frame {last_open})")
if inside:
    under = inside
    check(all(b["wet"] <= a["wet"] + 1e-6 for a, b in zip(under, under[1:])), "drying, not wetting, under the roof")
    check(under[-1]["wet"] < under[0]["wet"] * 0.75, f"drying under the roof (wet {under[0]['wet']:.2f} -> {under[-1]['wet']:.2f})")
after = [r for r in rows if r["f"] >= 1910]
check(all(b["rain"] <= a["rain"] + 1e-6 and b["dark"] <= a["dark"] + 1e-6 for a, b in zip(after, after[1:])), "the storm only clears once it turns")
check(rows[-1]["rain"] < 0.3 and rows[-1]["dark"] < 0.3, f"cleared by the end (rain {rows[-1]['rain']:.2f}, dark {rows[-1]['dark']:.2f})")
# the picture as rendered: darker in the storm than before it and after it
def sky(f):
    return ImageStat.Stat(Image.open(f"{d}/frame-{f}.png").convert("L")).mean[0]
# (before the storm and at its height from the same place in the open; at its height and at
# the end from the same place under the roof)
def flash_at(frame):
    # Match the static-scene pulse rule below. Quiet windows span the whole
    # discharge; interpolation follows the normal weather ramp.
    before = [r['sun'] for f, r in at.items() if 60 <= frame-f <= 160]
    after = [r['sun'] for f, r in at.items() if 60 <= f-frame <= 160]
    if not before or not after: return False
    baseline = (statistics.median(before) + statistics.median(after)) * .5
    return at[frame]['rain'] > .6 and at[frame]['sun'] - baseline > .035
captured = [int(re.search(r'frame-(\d+)', p)[1]) for p in glob.glob(f'{d}/frame-*.png')]
quiet_storm = [f for f in captured if 300 < f < 1300 and f in at
               and at[f]['rain'] > .6 and at[f]['dark'] > .4
               and not at[f]['sheltered'] and not flash_at(f)]
check(bool(quiet_storm), "missing flash-free developed-storm capture before movement")
storm_frame = max(quiet_storm, default=None)
s300, s1800, s3000 = sky(300), sky(1800), sky(3000)
sstorm = sky(storm_frame) if storm_frame is not None else float('nan')
check(sstorm < s300 * 0.85, f"storm darker than the clear day ({sstorm:.0f} vs {s300:.0f}; frame {storm_frame})")
check(s3000 > s1800 * 1.1, f"lightening as it clears ({s3000:.0f} vs {s1800:.0f})")
if fails:
    for f in fails[:12]: print("FAIL:", f)
    sys.exit(1)
print(f"PASS weather transitions: {len(rows)} samples over {rows[-1]['f']} frames; storm in, shelter at frame {inside[0]['f']}, cleared; brightness {s300:.0f} -> {sstorm:.0f} in the open (quiet storm frame {storm_frame}), {s1800:.0f} -> {s3000:.0f} under the roof")
PY

# Continuous changes through the other lighting/material boundaries: canopy, falling
# snow, and an orb-earned shrine exit. Each stays in one continuous world run.
fail=$?
for scene in forest snow shrine-exit; do
    dir=$root/$scene
    mkdir -p "$dir"
    if ! $verify; then
        rm -f "$dir"/*.png
        flags=()
        sequence="100:storm,1400:clear"
        case $scene in
            forest) flags=(BOTW_AT=-1000,1620,3.14);;
            # Nearby blue Bokoblins can move the combat camera even with no
            # input. Pin the snow observation camera while leaving AI active.
            snow) flags=(BOTW_AT=-1060,2230,2.0 BOTW_CAM=-1065,304,2232,2.0,0.12 BOTW_GIVE=warm_doublet);;
            shrine-exit)
                flags=(BOTW_WEATHER_CHECK_EXIT=1 BOTW_TOWER=1 BOTW_SHRINE=1 BOTW_SHRINE_AT=0,3.4,-45,0 BOTW_WEATHER=storm SLOPPY_INPUT=20:e+,22:e-)
                sequence="1400:clear";;
        esac
        env BOTW_SKIP=1 BOTW_HOUR=11 SLOPPY_INPUT="0:w-" "${flags[@]}" BOTW_WEATHER_SEQ="$sequence" \
            BOTW_WEATHER_LOG=1 BOTW_CAPTURE_DIR="$dir" BOTW_CAPTURE_EVERY=100 SLOPPY_WINDOW=640x360 \
            SLOPPY_SCREENSHOT="$dir/final.png" SLOPPY_FRAMES=2700 \
            flock /tmp/botw-render.lock timeout 900 "$root/game" 2>&1 | tee "$dir/run.log" | grep "^wx " > "$dir/log.txt"
    fi
    python3 - "$dir" "$scene" <<'PY' || fail=1
import re, sys, glob, statistics
from PIL import Image, ImageStat
d, scene = sys.argv[1:]
rows = [dict(re.findall(r"(\w+)=(\S+)", l)) for l in open(f"{d}/log.txt")]
# The 120 Hz simulation logs twice per rendered frame. Compare completed
# frames, so a fading lightning pulse is not mistaken for a tiny sun change
# paired with a large ambient change between two substeps of the same flash.
rows = list({int(r["f"]): r for r in rows}.values())
fails = []
def check(ok, message):
    if not ok: fails.append(message)
check(len(rows) >= 260, f"only {len(rows)} weather samples")
for a, b in zip(rows, rows[1:]):
    # Atmosphere and precipitation are independent of the canopy/cold/indoor boundary.
    lightning = abs(float(a["sun"]) - float(b["sun"])) > .025 and max(float(a["rain"]), float(b["rain"])) > .6
    for key, limit in (("rain", .03), ("dark", .03), ("clouds", .02), ("sky", .075)):
        # The lift teleports between interiors/exteriors under the existing black fade.
        # Validate visible exterior ambient after that handoff; weather stays continuous.
        if key == "sky" and (lightning or (scene == 'shrine-exit' and int(b['f']) < 800)): continue
        check(abs(float(a[key]) - float(b[key])) <= limit, f"{key} stepped at frame {b['f']}")
if rows:
    at = {int(r['f']): r for r in rows}
    check(float(at[1300]['rain']) > .70, "storm failed to build")
    check(float(rows[-1]['rain']) < .25, "storm failed to clear")
    check(float(rows[-1]['dark']) < .3, "lighting failed to clear")
    if scene == 'shrine-exit':
        p = [float(v) for v in at[800]['pos'].split(',')]
        check(abs(p[0]) > 100 and abs(p[1]) > 100, "orb exit did not reach outdoor world")
        check(float(at[800]['sky']) > .1, "outdoor storm sky lost its ambient floor")
frames = sorted(glob.glob(f'{d}/frame-*.png'), key=lambda p: int(re.search(r'frame-(\d+)', p)[1]))
def brightness(path):
    image = Image.open(path).convert('L')
    if scene == 'snow':
        # A roaming blue Chuchu crosses the right foreground. Measure the fixed left
        # snow slope/tree stand so actor motion cannot masquerade as a lighting jump.
        w, h = image.size
        image = image.crop((int(w*.03), int(h*.08), int(w*.38), int(h*.85)))
    return ImageStat.Stat(image).mean[0]
lum = [brightness(p) for p in frames]
if scene == 'shrine-exit':
    pictured = {int(re.search(r'frame-(\d+)', p)[1]): value for p, value in zip(frames, lum)}
    check(pictured[600] < min(pictured[500], pictured[700]) * .5,
          "interior/exterior handoff must remain masked by the lift's black fade")
# Ignore the deliberate lift/camera travel, but hold all static views to smooth lighting.
start = 8 if scene == 'shrine-exit' else 0
steps = []
for index in range(start + 1, len(lum)):
    frame_a = int(re.search(r'frame-(\d+)', frames[index-1])[1])
    frame_b = int(re.search(r'frame-(\d+)', frames[index])[1])
    def flash_at(frame):
        # Detect brief direct-light pulses against neighboring weather samples; a fixed
        # sun-intensity threshold misses dim flashes and mistakes clearing sun for a bolt.
        # Multiple strokes can fill the inner window with afterglow; its median
        # then equals the flash being tested. Quiet windows on either side span
        # the whole discharge, and interpolation follows the normal weather ramp.
        before = [float(r['sun']) for f, r in at.items() if 60 <= frame-f <= 160]
        after = [float(r['sun']) for f, r in at.items() if 60 <= f-frame <= 160]
        if not before or not after: return False
        baseline = (statistics.median(before) + statistics.median(after)) * .5
        return float(at[frame]['rain']) > .6 and float(at[frame]['sun']) - baseline > .035
    flash = any(flash_at(f) for f in (frame_a, frame_b))
    if not flash: steps.append(abs(lum[index] - lum[index-1]))
step = max(steps, default=0)
check(step < 12, f"static lighting changed {step:.1f} levels per 100 frames")
for f in fails[:12]: print(f'FAIL {scene}: {f}')
if not fails: print(f'PASS {scene}: {len(rows)} transition samples; largest static brightness step {step:.1f}')
sys.exit(bool(fails))
PY
done
exit "$fail"
