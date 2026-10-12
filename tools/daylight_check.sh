#!/bin/bash
# Dawn/dusk over open turf, canopy and snow, and dawn over Hopper Pond, played through
# at twelve times the clock's speed (an hour in five seconds). Land must brighten/darken
# smoothly; the shadows may swing between moon and sun only with direct light all but out.
#   tools/daylight_check.sh      (prints PASS/FAIL; images in build/daylight-check/)
# BOTW_DAYLIGHT_OUTPUT overrides the evidence root (default build/daylight-check).
set -uo pipefail
cd "$(dirname "$0")/.."
# --dusk rerenders only the sunset views; --verify rechecks all completed captures.
verify=false
only_dusk=false
if [[ ${1:-} == --verify || ${2:-} == --verify ]]; then verify=true; fi
if [[ ${1:-} == --dusk || ${2:-} == --dusk ]]; then only_dusk=true; fi
if [[ ${1:-} != --locked ]] && ! $verify; then
    exec flock /tmp/botw-render.lock "$PWD/tools/daylight_check.sh" --locked "$@"
fi
if ! $verify; then
    root=${BOTW_DAYLIGHT_OUTPUT:-build/daylight-check}
    mkdir -p "$root"
    python3 - "$root/fixture.jo" <<'PYFIXTURE'
from pathlib import Path
import re,sys
source=Path('game/main.jo').read_text()
source=re.sub(r"(?m)^(use|from) '([^']+)'",lambda m:f"{m[1]} '{(Path('game')/m[2]).resolve()}'",source)
# Observe completed draws and preserve the lighting camera when a patrol arrives.
# Combat/damage are covered by their own probes; keep the AI and sun/moon handoff.
capture='    if __capture_dir != none and __capture_every > 0 and frame_number() > 0 and frame_number() % __capture_every == 0:\n        save_png(screenshot(), __capture_dir! + "/frame-{frame_number()}.png")\n'
assert source.count(capture)==1
source=source.replace(capture,'').replace('update = (dt0: f64):','daylight_update = (dt0: f64):').replace('\ndraw = ():','\ndaylight_draw = ():')
source+='\nupdate = (dt0: f64):\n    pl.invuln = max(pl.invuln, 1.0)\n    daylight_update(dt0)\n    assert(pl.hp > 0.0, "lighting probe stays alive")\n'
source+='\ndraw = ():\n    daylight_draw()\n    flush()\n'+capture
Path(sys.argv[1]).write_text(source)
PYFIXTURE
    sloppy/bin/sloppy build "$root/fixture.jo" -o "$root/game" || exit 1
fi
fail=0
for run in "dawn:4.4:-1030,1805,1.57" "dusk:17.6:-1030,1805,1.57" \
           "forest-dawn:4.4:-1000,1620,3.14" "forest-dusk:17.6:-1000,1620,3.14" \
           "snow-dawn:4.4:-1060,2230,2.0" "snow-dusk:17.6:-1060,2230,2.0" \
           "pond-dawn:4.4:-1190,1665,-0.9"; do
    name=${run%%:*}
    if $only_dusk && [[ $name != *dusk ]]; then continue; fi
    rest=${run#*:}
    hour=${rest%%:*}
    at=${rest#*:}
    flags=()
    if [[ $name == snow-* ]]; then flags=(BOTW_GIVE=warm_doublet); fi
    dir=${BOTW_DAYLIGHT_OUTPUT:-build/daylight-check}/$name
    mkdir -p $dir
    if ! $verify; then
        rm -f $dir/*.png
        if ! env "${flags[@]}" BOTW_SKIP=1 BOTW_AT="$at" BOTW_HOUR=$hour BOTW_TIMESCALE=12 BOTW_WEATHER=clear \
            BOTW_NOVSYNC=1 SLOPPY_VSYNC=0 SLOPPY_PLATFORM=x11 BOTW_WEATHER_LOG=1 BOTW_CAPTURE_DIR=$dir BOTW_CAPTURE_EVERY=20 SLOPPY_WINDOW=640x360 \
            SLOPPY_SCREENSHOT=$dir/final.png SLOPPY_FRAMES=960 \
            timeout 900 "$root/game" 2>&1 | tee "$dir/run.log" | grep "^wx " > "$dir/log.txt"; then
            echo "FAIL $name: render did not complete"
            fail=1
            continue
        fi
        if grep -E 'panic:|error:' "$dir/run.log"; then
            echo "FAIL $name: runtime failure"
            fail=1
            continue
        fi
    fi
    python3 - $dir $name <<'PY' || fail=1
import re, sys, glob
from pathlib import Path
from PIL import Image, ImageStat
d, name = sys.argv[1], sys.argv[2]
rows = [dict(re.findall(r"(\w+)=(\S+)", l)) for l in open(f"{d}/log.txt")]
fails = []
if len(rows) < 90: fails.append(f"logged {len(rows)} samples")
swaps = 0
for a, b in zip(rows, rows[1:]):
    la = [float(x) for x in a["light"].split(",")]
    lb = [float(x) for x in b["light"].split(",")]
    if sum((p - q) ** 2 for p, q in zip(la, lb)) ** 0.5 > 0.05:
        swaps += 1
        sun = max(float(a["sun"]), float(b["sun"]))
        if sun > 0.05: fails.append(f"shadows swung round at hour {b['hour']} with the direct light at {sun:.2f}")
if swaps != 1: fails.append(f"{swaps} moon/sun hand-overs, expected one")
frames = sorted(glob.glob(f"{d}/frame-*.png"), key=lambda p: int(re.search(r"frame-(\d+)", p).group(1)))
if len(frames) != 48 or not Path(f"{d}/final.png").is_file():
    fails.append(f"incomplete capture: {len(frames)}/48 frames")
if not frames:
    print(f"FAIL {name}: no captured frames")
    sys.exit(1)
lum = [ImageStat.Stat(Image.open(p).convert("L")).mean[0] for p in frames]
step = max(abs(a - b) for a, b in zip(lum, lum[1:]))
# (twenty frames are six game minutes: the light may change, but not leap; the pre-dawn sky
# alone brightens the view by about 6 a capture, the moon/sun hand-over had leapt 32)
if step > 10.0: fails.append(f"brightness leapt {step:.1f} between captures")
for f in fails: print(f"FAIL {name}: {f}")
if not fails: print(f"PASS {name}: {len(rows)} samples, one hand-over, brightness {lum[0]:.0f} -> {lum[-1]:.0f}, largest step {step:.1f}")
sys.exit(1 if fails else 0)
PY
done
exit $fail
