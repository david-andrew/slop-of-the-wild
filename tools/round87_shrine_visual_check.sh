#!/bin/bash
# Owns a lock for each individual render. Never wrap this script in flock.
# Production chase-camera samples are spaced ~23 degrees apart, including a raised pan.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-build/round87/after}
binary=${2:-build/round87/after-game}
inspector=${3:-${binary}-inspect}
mkdir -p "$out"
# Scripted input keeps the user's axis preferences. Choose keys by the desired
# boom pitch so evidence is reproducible without modifying personal options.
high_key=down
low_key=up
if [[ -f "$HOME/.botw-clone-options" ]] && rg -q '^invert_y=1(\.0+)?$' "$HOME/.botw-clone-options"; then
  high_key=up
  low_key=down
fi
for n in ${ROUND87_SHRINES:-1 2 3 4}; do
  for view in ${ROUND87_VIEWS:-pan up-pan up}; do
    frames=360
    run_binary=$binary
    capture_every=10
    input='180:right+,339:right-'
    cam=()
    start=("BOTW_SHRINE=$n")
    if [[ $view == down-pan ]]; then
      input="100:${low_key}+,160:${low_key}-,180:right+,339:right-"
      cam=("BOTW_SHRINE_AT=9,0,-1,0")
    fi
    # up-pan raises the boom and looks down; up is the vertical ceiling view.
    if [[ $view == up-pan ]]; then input="100:${high_key}+,140:${high_key}-,180:right+,339:right-"; fi
    if [[ $view == eave-high ]]; then
      input="100:${high_key}+,160:${high_key}-,180:right+,339:right-"
      cam=("BOTW_SHRINE_AT=9,0,-1,0")
    fi
    if [[ $view == descent ]]; then
      capture_every=60
      start=("BOTW_ENTER=$n")
      input=''
    fi
    if [[ $view == up ]]; then
      run_binary=$inspector
      # Exactly vertical inspection exceeds the chase camera's normal pitch.
      # A 0.01 rad tilt survives float32 world-coordinate rounding in look_at.
      case $n in
        1) pos='-681,-4.5,1501';;
        2) pos='-400,2.5,2002';;
        3) pos='-925,96.5,2321';;
        4) pos='-365,263.5,1720';;
      esac
      cam=("BOTW_CAM=$pos,0,1.5607963")
      frames=180
      capture_every=0
      input=''
    fi
    [[ -x $run_binary ]] || { echo "Build $run_binary with tools/round87_shrine_inspector.py first" >&2; exit 1; }
    mkdir -p "$out/$n-$view"
    flock /tmp/botw-render.lock env -u BOTW_ENTER -u BOTW_SHRINE -u BOTW_SHRINE_STAGE -u BOTW_SHRINE_AT -u BOTW_CAM \
      -u BOTW_SHRINE_CARRY -u BOTW_SHRINE_GIVE -u BOTW_TITLE -u BOTW_AT \
      "${start[@]}" BOTW_TOWER=1 BOTW_SKIP=1 BOTW_HOUR=11 BOTW_WEATHER=clear \
      BOTW_SCALE=1 BOTW_NOVSYNC=1 BOTW_CAMDBG=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 \
      BOTW_CAPTURE_DIR="$out/$n-$view" BOTW_CAPTURE_EVERY="$capture_every" "${cam[@]}" \
      SLOPPY_INPUT="$input" SLOPPY_FRAMES="$frames" SLOPPY_SCREENSHOT="$out/$n-$view.png" \
      timeout 180 "$run_binary" > "$out/$n-$view.log" 2>&1
    echo "captured $out/$n-$view.png"
  done
done
