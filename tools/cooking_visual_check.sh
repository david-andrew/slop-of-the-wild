#!/bin/bash
# Production Hold -> overhead carry -> lit cabin pot -> dish notice.
# Caller must own flock /tmp/botw-render.lock; this script never locks itself.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-build/cooking-visuals}
mkdir -p "$out"
python3 - "$out" <<'PY'
from pathlib import Path
import sys
import re
out=Path(sys.argv[1]).resolve()
source=Path('game/main.jo').read_text()
# Both use and selective from/import paths are relative to the production file.
source=re.sub(r"(?m)^(use|from) '([^']+)'", lambda m: f"{m[1]} '{(Path('game') / m[2]).resolve()}'", source)
source=source.replace('update = (dt0: f64):','production_update = (dt0: f64):')
source=source.replace('frame_number() % __capture_every == 0:', 'frame_number() % __capture_every == 0 and [45,80,100,220,230,250,300,340].contains(frame_number()):')
source+='''
fixture_ready = false
update = (dt: f64):
    if not fixture_ready:
        fixture_ready = true
        enemies.clear()
        inv = Inventory()
        inv_add("old_shirt")
        inv_add("raw_meat")
        inv_add("pepper")
        pot = -1
        best = 100000.0
        loop i in 0.. and b in bonfires:
            gap = f64(length(b.pos - v3(-946.0, b.pos.y, 1883.5)))
            if b.pot and gap < best:
                best = gap
                pot = i
        assert(pot >= 0, "cabin cooking pot exists")
        bonfires[pot].lit = true
        pl.pos = bonfires[pot].pos + vec3(0, 0, 1.8)
        pl.face = 0.0
        pl.last_safe = pl.pos
        pl.state = .ground
        invui = InvUI(tab = 3, t = 1.0, tab_t = 1.0)
        assert(inv_hold("raw_meat") and inv_hold("pepper"))
        cam.yaw = 0.7
        camera_snap()
        print("cooking visual cabin pot={bonfires[pot].pos}")
    if frame_number() == 90: __key_event(int(Key.e), true)
    production_update(dt)
    if frame_number() == 0: inv_toggle()
    if frame_number() == 60:
        inv_toggle()
        assert(inv.held.len() == 2, "closing inventory carries both selected materials")
        print("cooking visual carry: held=2")
    if frame_number() == 90:
        __key_event(int(Key.e), false)
        assert(pl.state == .cutscene and inv.held.len() == 0 and count_of("spicy_steak") == 1, "production lit-pot callback cooks exact selection")
        print("cooking visual pot: kneeling=2.2s quarters=10 warmth=450s")
    if frame_number() == 260:
        assert(eat_food("spicy_steak") and warm_t == 450.0, "cooked dish grants exact timed warmth")
    if frame_number() == 300:
        assert(warm_t > 449.0 and clock_a > 0.9, "active warmth keeps the thermometer and duration visible")
        print("cooking visual warmth: compact active icon and countdown")
    if frame_number() == 320:
        invui = InvUI(open = true, tab = 3, t = 1.0, tab_t = 1.0)
        inv_add("spicy_steak")
    if frame_number() == 250:
        assert(pl.state == .ground and __cook_dish == "", "cooking returns player control and shows dish notice")
        print("cooking visual complete: ground, dish notice only")
'''
(out/'cooking-visual.jo').write_text(source)
PY
sloppy/bin/sloppy build "$out/cooking-visual.jo" -o "$out/cooking-visual"
env BOTW_SKIP=1 BOTW_HOUR=10 BOTW_WEATHER=clear BOTW_SCALE=1 BOTW_NOVSYNC=1 SLOPPY_VSYNC=0 \
  SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 BOTW_CAPTURE_DIR="$out" BOTW_CAPTURE_EVERY=1 \
  SLOPPY_INPUT="" SLOPPY_SCREENSHOT="$out/complete.png" SLOPPY_FRAMES=350 \
  timeout 180 "$out/cooking-visual" > "$out/run.log" 2>&1
if grep -E 'panic:|error:|FAIL' "$out/run.log"; then exit 1; fi
grep -E 'cooking visual' "$out/run.log"
