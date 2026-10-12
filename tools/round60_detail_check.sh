#!/bin/bash
# Matched production shrines/title/boars/fire. Own the GPU lock once for this batch.
# Expects before-game and after-game compiled under the output directory.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ${1:-} != --locked ]]; then
    exec flock /tmp/botw-render.lock "$PWD/tools/round60_detail_check.sh" --locked "$@"
fi
shift
out=$(realpath "${1:-build/round60}")
capture_active_fire() {
    # Early dense roots match the critic's advancing-front view; the 720-frame
    # samples above also retain the safe ash behind the front.
    for label in before after; do
        env BOTW_SKIP=1 BOTW_FIRE=1 BOTW_HOUR=7 BOTW_WEATHER=clear \
            BOTW_SCALE=1 BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 \
            SLOPPY_FRAMES=180 SLOPPY_SCREENSHOT="$out/$label/fire-active.png" \
            timeout 300 "$out/$label-game" > "$out/$label/fire-active.log" 2>&1
        echo "captured $label active fire"
    done
}
if [[ ${2:-} == --active-only ]]; then
    capture_active_fire
    exit 0
fi

capture_architecture() {
    local out="$1" binary="$2" look
    mkdir -p "$out/title-trail"
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
}

for label in before after; do
    binary="$out/$label-game"
    mkdir -p "$out/$label"
    # Reuse completed architecture evidence, otherwise collect the whole phase
    # under this batch's single lock. Never call another locking script.
    if [[ ! -f "$out/$label/title-shown.png" ]]; then
        capture_architecture "$out/$label" "$binary"
    fi
    for frames in 150 720; do
        picture=boars.png; log=boars-visual.log
        if [[ $frames == 720 ]]; then picture=boars-timing.png; log=boars-gpu.log; fi
        env BOTW_CAM=-946,188.0,1660,-0.75,-0.12 \
            BOTW_HOUR=10 BOTW_WEATHER=clear BOTW_SCALE=1 BOTW_NOVSYNC=1 BOTW_GPU=1 \
            SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 SLOPPY_FRAMES="$frames" \
            SLOPPY_SCREENSHOT="$out/$label/$picture" timeout 300 "$binary" > "$out/$label/$log" 2>&1
    done
    echo "captured $label boars"
done
# Alternating build order reduces drift between the three paired fire runs.
for repeat in 0 1 2; do
    labels=(before after)
    if [[ $repeat == 1 ]]; then labels=(after before); fi
    for label in "${labels[@]}"; do
        env BOTW_SKIP=1 BOTW_FIRE=1 BOTW_HOUR=7 BOTW_WEATHER=clear \
            BOTW_SCALE=1 BOTW_NOVSYNC=1 BOTW_GPU=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 \
            SLOPPY_FRAMES=720 SLOPPY_SCREENSHOT="$out/$label/fire-$repeat.png" \
            timeout 300 "$out/$label-game" > "$out/$label/fire-$repeat-gpu.log" 2>&1
        echo "captured $label fire $repeat"
    done
done
capture_active_fire
