#!/bin/bash
# CPU-only decorative triangle clearance, using both real startup paths.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-build/shrine-gaps}
mkdir -p "$out"
tools/prepare_assets.sh > "$out/prepare.log" 2>&1
sloppy/bin/sloppy build tools/shrine_gap_check.jo -o "$out/check"
for mode in generated prepared; do
    if [[ $mode == generated ]]; then
        BOTW_ASSET_CHECK=1 BOTW_NO_PREPARED_ASSETS=1 "$out/check" > "$out/$mode.log" 2>&1
    else
        env -u BOTW_NO_PREPARED_ASSETS BOTW_ASSET_CHECK=1 "$out/check" > "$out/$mode.log" 2>&1
    fi
    cat "$out/$mode.log"
done
