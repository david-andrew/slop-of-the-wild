#!/bin/bash
# Run: tools/menu_pause_check.sh (owns the render lock; do not wrap).
set -euo pipefail
cd "$(dirname "$0")/.."
out=build/menu-pause-check
mkdir -p "$out"
python3 - "$out" <<'PY'
from pathlib import Path
import re, sys
out = Path(sys.argv[1]).resolve()
source = Path('game/main.jo').read_text()
source = re.sub(r"(?m)^(use|from) '([^']+)'", lambda m: f"{m[1]} '{(Path('game') / m[2]).resolve()}'", source)
source = source.replace('update = (dt0: f64):', 'production_update = (dt0: f64):')
source = re.sub(r'(?m)^draw = \(\):', 'production_draw = ():', source)
source = source.replace('    if not invui.open: story_draw_2d()', '    if not invui.open:\n        story_draw_2d()')
# Count actual production layer submissions while every tab is open.
for call in ['combat_hud()', 'hud_draw(slot_views(), (if len(w) > 0: item(w).name else: ""))', 'shrines_draw_2d()', 'story_draw_2d()']:
    source = re.sub(r'(?m)^( +)' + re.escape(call) + r'$', lambda m: m[1] + 'menu_world_layers += 1\n' + m[1] + call, source)

fixture = Path('tools/menu_pause.fixture.jo').read_text()
fixture = re.sub(r"(?m)^(use|from) '([^']+)'", lambda m: f"{m[1]} '{(Path('tools') / m[2]).resolve()}'", fixture)
(out / 'fixture.jo').write_text(source + '\n' + fixture)
PY
sloppy/bin/sloppy build "$out/fixture.jo" -o "$out/fixture"
if flock /tmp/botw-render.lock env BOTW_SKIP=1 BOTW_AT=-1030,1805,1.57 BOTW_HOUR=7 BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 \
    SLOPPY_INPUT="" SLOPPY_SCREENSHOT="$out/final.png" SLOPPY_FRAMES=780 timeout 180 "$out/fixture" > "$out/run.log" 2>&1; then
    if grep -E 'panic:|error:|FAIL' "$out/run.log"; then exit 1; fi
else
    status=$?
    cat "$out/run.log"
    exit "$status"
fi
grep -E 'pause|resume|menu HUD' "$out/run.log"
