#!/bin/bash
# Agent captures only. Owns the render lock; never wrap in another flock.
set -euo pipefail
cd "$(dirname "$0")/.."
exec flock /tmp/botw-render.lock tools/play.sh "$@"
