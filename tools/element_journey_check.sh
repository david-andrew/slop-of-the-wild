#!/bin/bash
# Headless normal-input course. Default tests production; --proposed-support-fix
# applies the reviewable player support patch only to an isolated build copy.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - "$@" <<'PY'
from pathlib import Path
import shutil, subprocess, sys
proposed = sys.argv[1:] == ['--proposed-support-fix']
if sys.argv[1:] and not proposed:
    sys.exit('Usage: tools/element_journey_check.sh [--proposed-support-fix]')
mode = 'proposed' if proposed else 'production'
root = Path(f'build/round57/element-journey-{mode}')
shutil.copytree('game',root/'game',dirs_exist_ok=True)
(root/'tools').mkdir(exist_ok=True)
for name in ['element_journey.jo','tree_checks.jo']:
    shutil.copyfile(Path('tools')/name,root/'tools'/name)
main=Path('game/main.jo').read_text()
callback=main.split('use_slot = (k: int):',1)[1].split('# where the player is',1)[0]
p=root/'tools/element_journey.jo'
p.write_text(p.read_text()+'\nuse_slot = (k: int):'+callback)
if proposed:
    subprocess.run(['git','apply',f'--directory={root}','tools/element_journey_support.patch'],check=True)
binary=root/'element-journey'
subprocess.run(['sloppy/bin/sloppy','build',str(p),'-o',str(binary)],check=True)
log=Path(f'build/round57/element-journey-{mode}.log')
with log.open('w') as f:
    result=subprocess.run([str(binary)],stdout=f,stderr=subprocess.STDOUT)
for line in log.read_text().splitlines():
    if any(t in line for t in ['JOURNEY felled','JOURNEY crossed','JOURNEY ignition','element continuous','panic:']):
        print(line)
print(f'Full normal-input trail: {log}')
sys.exit(result.returncode)
PY
