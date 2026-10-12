#!/bin/bash
# Caller holds flock /tmp/botw-render.lock; this script never acquires it again.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:?output directory}
binary=${2:?compiled game}
mkdir -p "$out"
# Scripted inputs keep the user's camera inversion; do not change their preferences.
look=$(python3 - <<'CAMERA'
import os
from pathlib import Path
options = Path(os.environ.get('HOME', '.')) / '.botw-clone-options'
inverted = options.is_file() and any(line.startswith('invert_y=') and float(line.split('=', 1)[1]) > .5 for line in options.read_text().splitlines())
print('down' if inverted else 'up')
CAMERA
)
for shrine in 1 2 3 4; do
  if [[ ${SHRINE_VISUAL_DETAIL_ONLY:-0} != 1 && ${SHRINE_VISUAL_ARCHITECTURE_ONLY:-0} != 1 ]]; then
    env BOTW_SKIP=1 BOTW_TOWER=1 BOTW_SHRINE="$shrine" BOTW_HOUR=11 BOTW_WEATHER=clear \
      BOTW_SCALE=1 BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 BOTW_GPU=1 \
      SLOPPY_SCREENSHOT="$out/$shrine-entrance.png" SLOPPY_FRAMES=720 \
      timeout 300 "$binary" > "$out/$shrine-gpu.log" 2>&1
  fi
  env BOTW_SKIP=1 BOTW_TOWER=1 BOTW_SHRINE="$shrine" BOTW_HOUR=11 BOTW_WEATHER=clear \
    BOTW_SCALE=1 BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 \
    SLOPPY_INPUT="90:$look+,106:$look-" SLOPPY_SCREENSHOT="$out/$shrine-architecture.png" SLOPPY_FRAMES=120 \
    timeout 300 "$binary" > "$out/$shrine-architecture.log" 2>&1
  if [[ ${SHRINE_VISUAL_ARCHITECTURE_ONLY:-0} == 1 ]]; then continue; fi
  case $shrine in
    1) at='-30,0,-29,-1.57';;
    2) at='20,0,-10,1.57';;
    3) at='13,0,-28.5,1.57';;
    4) at='-18,3.6,-14,-1.57';;
  esac
  env BOTW_SKIP=1 BOTW_TOWER=1 BOTW_SHRINE="$shrine" BOTW_SHRINE_AT="$at" BOTW_HOUR=11 \
    BOTW_WEATHER=clear BOTW_SCALE=1 BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 \
    SLOPPY_SCREENSHOT="$out/$shrine-annex.png" SLOPPY_FRAMES=120 \
    timeout 300 "$binary" > "$out/$shrine-annex.log" 2>&1
done
if [[ ${SHRINE_VISUAL_DETAIL_ONLY:-0} == 1 || ${SHRINE_VISUAL_ARCHITECTURE_ONLY:-0} == 1 ]]; then exit 0; fi
mkdir -p "$out/exit"
env BOTW_SKIP=1 BOTW_TOWER=1 BOTW_SHRINE=1 BOTW_SHRINE_AT='0,3.4,-45,0' \
  BOTW_HOUR=11 BOTW_WEATHER=clear SLOPPY_INPUT='20:e+,22:e-' BOTW_CAMDBG=1 BOTW_SHRINE_LOG=1 \
  BOTW_SCALE=1 BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 \
  BOTW_CAPTURE_DIR="$out/exit" BOTW_CAPTURE_EVERY=25 \
  SLOPPY_SCREENSHOT="$out/exit.png" SLOPPY_FRAMES=750 \
  timeout 300 "$binary" > "$out/exit.log" 2>&1
