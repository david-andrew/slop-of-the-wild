#!/bin/bash
# Public runtime environment option, set before Sloppy initializes the window.
set -euo pipefail
cd "$(dirname "$0")/.."
# Measured mailbox p99 is lower than FIFO in forest, fire and overlook.
export SLOPPY_VSYNC=${SLOPPY_VSYNC-0}
if (( $# == 0 )); then
    set -- sloppy/bin/sloppy game/main.jo
fi
exec "$@"
