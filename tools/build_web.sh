#!/bin/bash
# Produce a self-contained GitHub Pages directory; no changes to sloppy/.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/web build/web-evidence
# Bake with the same source/input stamps as the wasm compilation.
tools/prepare_assets.sh
sloppy/bin/sloppy build game/main.jo --target wasm -o build/web/raw.html
sloppy/bin/sloppy build tools/web_piano_worker.jo --target wasm -o build/web/piano-worker.html
BOTW_LOADTIME=1 WEB_PACKS= node tools/web_trace.cjs build/web/raw.html > build/web-evidence/generated.log 2>&1
python3 tools/web_package.py
