#!/bin/bash
# CPU-only production terrain/collision/controller journey. No window, render or save I/O.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 tools/journey_check.py "$@"
