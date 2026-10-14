#!/bin/bash
# Public runtime environment option, set before Sloppy initializes the window.
set -euo pipefail
cd "$(dirname "$0")/.."
# Managed XWayland avoids the native Wayland ten-second presentation hitch.
# Keep native Wayland available explicitly and on Wayland-only desktops.
if [[ -n ${DISPLAY:-} ]]; then
    export SLOPPY_PLATFORM=${SLOPPY_PLATFORM-x11}
fi
# Request the fastest Vulkan mode: mailbox, or immediate when unavailable.
export SLOPPY_VULKAN=${SLOPPY_VULKAN-1}
export SLOPPY_VSYNC=${SLOPPY_VSYNC-0}
# A 60 cap retained acquire stalls and worsened route tails; keep it opt-in.
export BOTW_FPS=${BOTW_FPS-0}
if (( $# == 0 )); then
    set -- sloppy/bin/sloppy game/main.jo
fi
exec "$@"
