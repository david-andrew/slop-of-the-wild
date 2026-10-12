#!/bin/bash
# The fixture uses the entire production update; this wrapper owns its render lock.
set -euo pipefail
cd "$(dirname "$0")/.."
out=build/production-loop-check
mkdir -p "$out"
python3 - "$out" <<'PY'
from pathlib import Path
import re, sys
source = Path('game/main.jo').read_text()
source = re.sub(r"(?m)^(use|from) '([^']+)'", lambda m: f"{m[1]} '{(Path('game') / m[2]).resolve()}'", source)
source = source.replace('update = (dt0: f64):', 'production_update = (dt0: f64):')
# Observe every catch-up tick before production consumes its combat/element events.
# This hook records outcomes only; all input, timing and contacts remain production.
assert source.count('    play_events()') == 1
source = source.replace('    play_events()', '    loop_probe_observe()\n    play_events()')
fixture = Path('tools/production_loop.fixture.jo').read_text()
fixture = re.sub(r"(?m)^(use|from) '([^']+)'", lambda m: f"{m[1]} '{(Path('tools') / m[2]).resolve()}'", fixture)
(Path(sys.argv[1]) / 'fixture.jo').write_text(source + '\n' + fixture)
PY
sloppy/bin/sloppy build "$out/fixture.jo" -o "$out/fixture"
status=0
flock /tmp/botw-render.lock env BOTW_SKIP=1 BOTW_AT=-1030,1805,0 BOTW_HOUR=12 BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 \
    SLOPPY_INPUT="" SLOPPY_SCREENSHOT="$out/final.png" SLOPPY_FRAMES=4 timeout 180 "$out/fixture" > "$out/run.log" 2>&1 || status=$?
cat "$out/run.log"
(( status == 0 )) || exit "$status"
if grep -E 'panic:|error:|FAIL' "$out/run.log"; then exit 1; fi
[[ $(grep -Ec '^PASS production' "$out/run.log") == 27 ]]
