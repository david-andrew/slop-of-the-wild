#!/bin/bash
# Public runtime environment option, set before Sloppy initializes the window.
set -euo pipefail
cd "$(dirname "$0")/.."
# 0.6 OpenGL Wayland frame callbacks produced more late forest windows.
# Vulkan mailbox remains the measured default; both options can be overridden.
export SLOPPY_VULKAN=${SLOPPY_VULKAN-1}
export SLOPPY_VSYNC=${SLOPPY_VSYNC-0}
if (( $# == 0 )); then
    set -- sloppy/bin/sloppy game/main.jo
fi
exec "$@"
