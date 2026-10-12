#!/bin/bash
# Owns one render lock per view. Never wrap this script in flock.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-build/round86/after}
binary=${2:-build/round86/after-game}
mkdir -p "$out"
for n in ${ROUND86_SHRINES:-1 2 3 4}; do
  for view in ${ROUND86_VIEWS:-arrival puzzle}; do
    input=""
    # Follow the first control from the lift: weights/barrels/near valve right,
    # or the first rotating bridge straight ahead. Same inputs before and after.
    if [[ $view == puzzle ]]; then
      input="20:d+,55:d-"
      if [[ $n == 3 ]]; then input="20:w+,55:w-"; fi
    fi
    flock /tmp/botw-render.lock env -u BOTW_ENTER -u BOTW_SHRINE_STAGE -u BOTW_SHRINE_AT -u BOTW_CAM \
      -u BOTW_SHRINE_CARRY -u BOTW_SHRINE_GIVE -u BOTW_TITLE -u BOTW_AT \
      BOTW_SHRINE="$n" BOTW_TOWER=1 BOTW_SKIP=1 BOTW_HOUR=11 BOTW_WEATHER=clear \
      BOTW_SCALE=1 BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 \
      SLOPPY_INPUT="$input" SLOPPY_FRAMES=180 SLOPPY_SCREENSHOT="$out/$n-$view.png" \
      timeout 180 "$binary" > "$out/$n-$view.log" 2>&1
    echo "captured $out/$n-$view.png"
  done
done
