#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build
sloppy/bin/sloppy tools/save_test.jo
sloppy/bin/sloppy build tools/save_test.jo -o build/save-test
python3 - <<'PY'
import os
import re
import subprocess

source = open('game/save.jo').read().split('save_allowed =')[1].split('    true\n')[0]
names = re.findall(r'"((?:BOTW|SLOPPY)_[A-Z_]+)"', source)
clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
for name in names:
    subprocess.run(['build/save-test', 'isolated'], env={**clean, name: '1'}, check=True, stdout=subprocess.DEVNULL)
for mode, extra in (('interactive', {}), ('newgame', {'BOTW_NEWGAME': '1'})):
    subprocess.run(['build/save-test', mode], env={**clean, **extra}, check=True, stdout=subprocess.DEVNULL)
print(f'PASS: {len(names)} switches block save I/O; interactive and NEWGAME allow it')
PY
