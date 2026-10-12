#!/bin/bash
# End to end, for each shrine: talk to the monk, take the orb, ride back up; by frame 750 Link
# stands at the entrance and the camera is on the open side of the hood, not in it.
# Owns one render lock per shrine; do not wrap.
#   tools/shrine_exit_check.sh      (PASS/FAIL per shrine; exit status 1 if any failed)
cd "$(dirname "$0")/.."
mkdir -p build/check-scratch
# where to stand in each shrine: two meters in front of its monk (shrines.jo, SRec.monk)
spots=("0,3.4,-45" "0,0,-49.5" "10,9,-78" "0,4,-41.5")
fail=0
for n in 1 2 3 4; do
  out=$(flock /tmp/botw-render.lock env BOTW_SHRINE_LOG=1 BOTW_CAMDBG=1 BOTW_SKIP=1 BOTW_TOWER=1 BOTW_SHRINE=$n BOTW_SHRINE_AT="${spots[$((n-1))]},0" SLOPPY_INPUT="20:e+,22:e-" SLOPPY_SCREENSHOT=build/check-scratch/shrine_exit_check.png SLOPPY_FRAMES=750 timeout 300 sloppy/bin/sloppy game/main.jo 2>&1)
  ent=$(echo "$out" | grep "entrance vec3" | sed -n "${n}p")
  cam=$(echo "$out" | grep "^cam " | tail -1)
  python3 - "$n" "$ent" "$cam" <<'PY' || fail=1
import sys, re, math
n, ent, cam = sys.argv[1], sys.argv[2], sys.argv[3]
name = ent.split(":")[1].strip() if ":" in ent else "shrine %s" % n
e = [float(v) for v in re.search(r"entrance vec3\(([^)]*)\)", ent).group(1).split(",")]
rot = float(re.search(r"rot (-?[0-9.]+)", ent).group(1))
pl = [float(v) for v in re.search(r"pl=vec3\(([^)]*)\)", cam).group(1).split(",")]
cp = [float(v) for v in re.search(r" pos=vec3\(([^)]*)\)", cam).group(1).split(",")]
st = re.search(r"st=(\w+)", cam).group(1)
# the hood stands on the shrine's local -z side: rotation_y(rot) * (0, 0, -1)
hx, hz = -math.sin(rot), -math.cos(rot)
side = (cp[0] - e[0]) * hx + (cp[2] - e[2]) * hz
at = math.hypot(pl[0] - e[0], pl[2] - e[2])
ok = st == "ground" and at < 3.0 and side < 0.0
print(("PASS" if ok else "FAIL") + f": {name}: {st}, {at:.1f} m from the entrance, camera {'outside' if side < 0 else 'inside'} the hood ({side:.1f})")
sys.exit(0 if ok else 1)
PY
done
rm -f build/check-scratch/shrine_exit_check.png
exit $fail
