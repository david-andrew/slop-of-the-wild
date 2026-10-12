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
        env "${flags[@]}" BOTW_SKIP=1 BOTW_AT="$at" BOTW_HOUR=$hour BOTW_TIMESCALE=12 BOTW_WEATHER=clear \
            BOTW_WEATHER_LOG=1 BOTW_CAPTURE_DIR=$dir BOTW_CAPTURE_EVERY=20 SLOPPY_WINDOW=640x360 \
            SLOPPY_SCREENSHOT=$dir/final.png SLOPPY_FRAMES=960 \
            timeout 900 sloppy/bin/sloppy game/main.jo 2>&1 | grep "^wx " > $dir/log.txt
    fi
    python3 - $dir $name <<'PY' || fail=1
import re, sys, glob
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
