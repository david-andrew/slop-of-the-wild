#!/bin/bash
# CPU-only terrain/upload/water/farland/architecture/physics/audio/RGBA texture preparation.
# No window, GPU context, or playback device is opened.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/asset-bake assets/prepared
sloppy/bin/sloppy build tools/bake_world.jo -o build/asset-bake/world
sloppy/bin/sloppy build tools/bake_textures.jo -o build/asset-bake/textures
sloppy/bin/sloppy build tools/bake_audio.jo -o build/asset-bake/audio
BOTW_BAKE_ASSETS=1 build/asset-bake/world
BOTW_BAKE_ASSETS=1 build/asset-bake/audio
BOTW_BAKE_ASSETS=1 build/asset-bake/textures
python3 tools/headless_build.py tools/bake_combat.jo -o build/asset-bake/combat
BOTW_BAKE_ASSETS=1 build/asset-bake/combat
