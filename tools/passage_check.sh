#!/bin/bash
# End to end: the scripted walk out of the Shrine of Resurrection reaches the cave mouth.
#   tools/passage_check.sh       (prints PASS/FAIL and where he got to)
cd "$(dirname "$0")/.."
mkdir -p build/check-scratch
out=$(BOTW_PASSAGE=1 BOTW_CAMDBG=1 SLOPPY_INPUT="20:w+" SLOPPY_SCREENSHOT=build/check-scratch/passage_check.png SLOPPY_FRAMES=760 timeout 300 sloppy/bin/sloppy game/main.jo 2>&1)
rm -f build/check-scratch/passage_check.png
last=$(echo "$out" | grep "^cam " | tail -1)
pos=$(echo "$last" | sed -E 's/.* pl=vec3\(([^)]*)\).*/\1/')
python3 - "$pos" <<'PY'
import sys, math
x, y, z = [float(v) for v in sys.argv[1].split(",")]
d = math.hypot(x + 1068.0, z - 1845.0)
print(("PASS" if d < 12.0 else "FAIL") + f": at ({x:.1f}, {y:.1f}, {z:.1f}), {d:.1f} m from the cave mouth after 760 frames")
sys.exit(0 if d < 12.0 else 1)
PY
