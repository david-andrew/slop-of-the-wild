#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Build immutable executables in build/round64/{before,after}/game before
# modifying source; every capture owns the shared lock separately.
phase=${1:?before or after}
binary=$PWD/build/round64/$phase/game
out=$PWD/build/round64/$phase
capture() {
 name=$1; frames=$2; shift 2
 flock /tmp/botw-render.lock env "$@" BOTW_NO_PREPARED_ASSETS=1 BOTW_NOVSYNC=1 BOTW_GPU=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 BOTW_SCALE=1 SLOPPY_SCREENSHOT="$out/$name.png" SLOPPY_FRAMES="$frames" timeout 300 "$binary" > "$out/$name.log" 2>&1
}
capture forest 150 BOTW_SKIP=1 BOTW_AT=-1000,1620,3.14
capture boars 150 BOTW_SKIP=1 BOTW_CAM=-946,188.0,1660,-0.75,-0.12
capture golden 150 BOTW_SKIP=1 BOTW_AT=-1030,1805,1.57 BOTW_HOUR=6.4
capture overview 150 BOTW_SKIP=1 BOTW_CAM=-700,330,2150,-0.8,-0.35
capture snow 150 BOTW_SKIP=1 BOTW_AT=-1060,2230,2.0
capture hylia-pass 150 BOTW_SKIP=1 BOTW_CAM=-1300,355,2100,3.7,-0.20
mkdir -p "$out/talus"
capture talus 600 BOTW_SKIP=1 BOTW_AT=-1087.75,1673.18,0 SLOPPY_INPUT=10:w+,150:w- BOTW_CAPTURE_DIR="$out/talus" BOTW_CAPTURE_EVERY=50
