#!/bin/bash
# Run: tools/encounter_weather_save_check.sh (headless; no render lock needed).
set -euo pipefail
cd "$(dirname "$0")/.."
out=build/encounter-weather-save
mkdir -p "$out"
sloppy/bin/sloppy build tools/encounter_weather_save_test.jo -o "$out/check"
fixture=$(mktemp -d "$PWD/$out/fixture.XXXXXX")
trap 'python3 -c "import shutil,sys; shutil.rmtree(sys.argv[1])" "$fixture"' EXIT
for mode in write read; do
    if ! "$out/check" "$mode" "$fixture" > "$out/$mode.log" 2>&1; then
        cat "$out/$mode.log"
        exit 1
    fi
    cat "$out/$mode.log"
    if grep -E 'panic:|error:|FAIL' "$out/$mode.log"; then exit 1; fi
done
