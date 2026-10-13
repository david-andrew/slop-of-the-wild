#!/bin/bash
# Builds a self-contained Linux x86-64 package of the committed game:
#   tools/package_linux.sh [output.tar.gz]
# The committed tree (HEAD) is exported to build/package/, its packs are prepared there and the
# release executable is built. The package holds the executable, the assets and the sources the
# prepared packs are keyed on (game/, sloppy/lib/, the referenced nature textures), so the game
# accepts its packs instead of rebuilding the world at every launch. Needs assets/src/ locally.
set -euo pipefail
cd "$(dirname "$0")/.."
root=$PWD
out=${1:-$root/build/slop-of-the-wild-linux-x86_64.tar.gz}
[[ -d assets/src/nature/Textures ]] || { echo "assets/src/ is missing (see docs/ASSETS.md)" >&2; exit 1; }

stage=$root/build/package/stage
pkg=$root/build/package/slop-of-the-wild
chmod -R u+w build/package 2>/dev/null || true
rm -rf build/package
mkdir -p "$stage" "$pkg/sloppy" "$pkg/assets/src/nature"
git archive HEAD | tar -x -C "$stage"
ln -s "$root/assets/src" "$stage/assets/src"
(cd "$stage" && tools/prepare_assets.sh >/dev/null && sloppy/bin/sloppy build game/main.jo -o slop-of-the-wild)

cp "$stage/slop-of-the-wild" "$pkg/"
rsync -a --exclude src "$stage/assets" "$pkg/"
rsync -a "$stage/game" "$pkg/"
rsync -a "$stage/sloppy/lib" "$pkg/sloppy/"
# Input textures may be symlinks into a local asset checkout. Materialize them
# with their target mtimes so the exported pack keys stay valid and self-contained.
mkdir -p "$pkg/assets/src/nature/Textures"
rsync -aL "$root/assets/src/nature/Textures/" "$pkg/assets/src/nature/Textures/"
cat > "$pkg/play.sh" <<'EOF'
#!/bin/bash
# Runs the game from this folder (its assets are read relative to it).
cd "$(dirname "$0")"
# Match the measured source launcher defaults.
export SLOPPY_VULKAN=${SLOPPY_VULKAN-1}
export SLOPPY_VSYNC=${SLOPPY_VSYNC-0}
exec ./slop-of-the-wild "$@"
EOF
chmod +x "$pkg/play.sh"
cat > "$pkg/README.txt" <<'EOF'
The Legend of Jo: Slop of the Wild
==================================

Linux x86-64. Run:

    ./play.sh

Vulkan mailbox presentation is the default; SLOPPY_VSYNC=1 ./play.sh selects FIFO.
SLOPPY_VULKAN=0 ./play.sh selects OpenGL (Wayland frame-callback pacing in 0.6).

The first launch prepares shaders for your GPU (up to ~30 s); later launches take a few seconds.
Progress is saved to ~/.botw-clone-save (choose "Start over" in the menu, or run
BOTW_NEWGAME=1 ./play.sh, to begin again). Options are kept in ~/.botw-clone-options.

Controls (keyboard + mouse / keyboard only / gamepad)
  move ............ WASD / WASD / left stick
  camera .......... mouse / arrow keys / right stick
  jump, glider .... Space / Space / top face button
  sprint .......... Shift / Shift / bottom face button
  attack .......... left mouse / J / left face button
  action .......... E / E / right face button
  lock on, shield . right mouse (hold) / K / left trigger
  bow ............. R / L / right trigger
  crouch .......... Ctrl or C / C / left stick press
  throw weapon .... G / G / right bumper
  item buttons .... 1 2 3 / 1 2 3 / d-pad
  inventory ....... Tab or I / Tab / start
  map ............. M or Esc / M / back

Controls can be rebound in the inventory's Options tab.
EOF
chmod -R u+w "$pkg"
# POSIX tar keeps sub-second modification times, which the packs' keys include.
tar --format=posix -C build/package -cf - slop-of-the-wild | gzip -6 > "$out"
echo "$out"
