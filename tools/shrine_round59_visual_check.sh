#!/bin/bash
# Self-locking capture batch; do not wrap this script in another flock.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ${3:-} != --locked ]]; then
    exec flock /tmp/botw-render.lock "$PWD/tools/shrine_round59_visual_check.sh" "$1" "$2" --locked
fi
out=${1:?output directory}
binary=${2:?compiled game}
mkdir -p "$out" "$out/title-trail"
look=$(python3 - <<'PY'
from pathlib import Path
p = Path.home()/'.botw-clone-options'
print('down' if p.exists() and any(l.startswith('invert_y=') and float(l.split('=')[1])>.5 for l in p.read_text().splitlines()) else 'up')
PY
)
for shrine in 1 2 3 4; do
    env BOTW_SKIP=1 BOTW_TOWER=1 BOTW_SHRINE="$shrine" BOTW_HOUR=11 BOTW_WEATHER=clear \
        BOTW_SCALE=1 BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 BOTW_GPU=1 \
        SLOPPY_SCREENSHOT="$out/$shrine-entrance.png" SLOPPY_FRAMES=720 \
        timeout 300 "$binary" > "$out/$shrine-gpu.log" 2>&1
    env BOTW_SKIP=1 BOTW_TOWER=1 BOTW_SHRINE="$shrine" BOTW_HOUR=11 BOTW_WEATHER=clear \
        BOTW_SCALE=1 BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 \
        SLOPPY_INPUT="90:$look+,106:$look-" SLOPPY_SCREENSHOT="$out/$shrine-architecture.png" SLOPPY_FRAMES=120 \
        timeout 300 "$binary" > "$out/$shrine-architecture.log" 2>&1
    echo "captured $out shrine $shrine"
done
env BOTW_TITLE=1 BOTW_HOUR=7 BOTW_WEATHER=clear BOTW_SCALE=1 BOTW_NOVSYNC=1 \
    SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 SLOPPY_INPUT=10:w+ BOTW_OPENING_CAPTURE="$out" \
    BOTW_GPU=1 BOTW_CAPTURE_DIR="$out/title-trail" BOTW_CAPTURE_EVERY=120 \
    SLOPPY_SCREENSHOT="$out/title-final.png" SLOPPY_FRAMES=1040 \
    timeout 300 "$binary" > "$out/title-gpu.log" 2>&1
echo "captured $out title"
