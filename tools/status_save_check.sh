#!/bin/bash
# Run: tools/status_save_check.sh (headless fresh-process persistence check).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/status-save
sloppy/bin/sloppy build tools/status_save_test.jo -o build/status-save/check
fixture=$(mktemp "$PWD/build/status-save/fixture.XXXXXX")
trap 'rm -f "$fixture" "$fixture.tmp" "$fixture.gear" "$fixture.gear.tmp"' EXIT
for mode in write read; do
    if build/status-save/check "$mode" "$fixture" > "build/status-save/$mode.log" 2>&1; then
        cat "build/status-save/$mode.log"
    else
        status=$?
        cat "build/status-save/$mode.log"
        exit "$status"
    fi
    if grep -E 'panic:|error:|FAIL' "build/status-save/$mode.log"; then exit 1; fi
done
