#!/bin/bash
# CPU only: two fresh processes, real generated and real prepared startup paths.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/shrine-obstruction
# Refresh the dependency-checked pack before requiring a prepared cache hit.
tools/prepare_assets.sh > build/shrine-obstruction/prepare.log 2>&1
sloppy/bin/sloppy build tools/shrine_obstruction_check.jo -o build/shrine-obstruction/check
for mode in generated prepared; do
    if [[ $mode == generated ]]; then
        BOTW_ASSET_CHECK=1 BOTW_NO_PREPARED_ASSETS=1 build/shrine-obstruction/check
    else
        env -u BOTW_NO_PREPARED_ASSETS BOTW_ASSET_CHECK=1 build/shrine-obstruction/check
    fi
done
