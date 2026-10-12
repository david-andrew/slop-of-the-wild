#!/bin/bash
# Complete lossless CPU equivalence, including shared audio aliases and static
# render/physics buffers. No context/device/window or render lock is required.
set -euo pipefail
cd "$(dirname "$0")/.."
tools/prepare_assets.sh
mkdir -p build/prepared-check
sloppy/bin/sloppy tools/mesh_pack_test.jo
sloppy/bin/sloppy build tools/prepared_assets_check.jo -o build/prepared-check/audio-world
sloppy/bin/sloppy build tools/prepared_mesh_check.jo -o build/prepared-check/mesh
build/prepared-check/audio-world > build/prepared-check/prepared.txt
BOTW_NO_PREPARED_ASSETS=1 build/prepared-check/audio-world > build/prepared-check/generated.txt
cmp build/prepared-check/{prepared,generated}.txt
cmp assets/prepared/textures.bin build/prepared-check/textures-prepared.bin
cmp build/prepared-check/textures-{prepared,generated}.bin
BOTW_ASSET_CHECK=1 build/prepared-check/mesh > build/prepared-check/mesh-prepared.txt
BOTW_ASSET_CHECK=1 BOTW_NO_PREPARED_ASSETS=1 build/prepared-check/mesh > build/prepared-check/mesh-generated.txt
BOTW_ASSET_CHECK=1 build/prepared-check/mesh --architecture-miss > build/prepared-check/mesh-mixed.txt
sed -n '/^physics /p' build/prepared-check/mesh-prepared.txt > build/prepared-check/physics-prepared.txt
sed -n '/^physics /p' build/prepared-check/mesh-generated.txt > build/prepared-check/physics-generated.txt
cmp build/prepared-check/physics-{prepared,generated}.txt
for mode in prepared generated mixed; do
    sed -n '/^draw named /p' "build/prepared-check/mesh-$mode.txt" > "build/prepared-check/draw-$mode.txt"
done
cmp build/prepared-check/draw-{prepared,generated}.txt
cmp build/prepared-check/draw-{prepared,mixed}.txt
for pack in terrain water farland structures; do
    cmp "assets/prepared/$pack.bin" "build/prepared-check/prepared/$pack.bin"
    cmp "build/prepared-check/generated/$pack.bin" "build/prepared-check/prepared/$pack.bin"
    cmp "build/prepared-check/mixed/$pack.bin" "build/prepared-check/prepared/$pack.bin"
done
echo 'PASS prepared assets: complete audio/world/mesh/collision/roof/ownership/RNG/texture RGBA byte equivalence and named draw order'
