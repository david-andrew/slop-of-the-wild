#!/bin/bash
# Verify the integrated production save/element hooks in an isolated fixture.
# The patch fallback supports historical source trees predating integration.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
from pathlib import Path
import shutil
import subprocess
root = Path('build/talus-integration-proposal').resolve()
shutil.copytree('game',root/'game',dirs_exist_ok=True)
if 's.talus = talus_records()' not in (root/'game/save.jo').read_text():
    subprocess.run(['git','apply','--directory=build/talus-integration-proposal','tools/talus_save_element_hooks.patch'],check=True)
for name in ['talus_checks.jo','talus_save_element.fixture.jo']:
    source = (Path('tools')/name).read_text().replace("'../game/",f"'{root/'game'}/")
    (root/name).write_text(source)
subprocess.run(['sloppy/bin/sloppy',str(root/'talus_save_element.fixture.jo')],check=True)
PY
