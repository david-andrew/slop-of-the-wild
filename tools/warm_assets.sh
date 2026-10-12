#!/bin/bash
# Bake lossless terrain/water/farland/architecture/physics/audio/RGBA texture packs, then prepare
# driver-specific shader binaries. Rendering takes the lock exactly once.
# Cache entries live in ignored build/shader-cache and validate exact GLSL + driver.
set -euo pipefail
cd "$(dirname "$0")/.."
tools/prepare_assets.sh
mkdir -p build/asset-warmup
sloppy/bin/sloppy build game/main.jo -o build/asset-warmup/game
python3 - <<'PY'
import os
import subprocess
from pathlib import Path
root = Path('build/asset-warmup')
env = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
env.update(BOTW_LOADTIME='1', BOTW_SCALE='1', SLOPPY_PLATFORM='x11',
           SLOPPY_WINDOW='1280x720', SLOPPY_FRAMES='1',
           SLOPPY_SCREENSHOT=str((root / 'first-frame.png').resolve()))
subprocess.run(['flock', '/tmp/botw-render.lock', 'python3', 'tools/performance_window.py',
                '1280x720', 'timeout', '180', str((root / 'game').resolve())],
               env=env, check=True)
PY
