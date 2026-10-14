#!/bin/bash
# Headless tower -> four earned orbs -> Temple meeting -> paraglider -> departure.
# Production field callbacks are extracted verbatim; no rendering or save I/O.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/late-story-check
python3 - <<'PY'
import os
from pathlib import Path
import re
import subprocess
import sys

root = Path('build/late-story-check')
source = Path('game/main.jo').read_text()

def section(start, end):
    if source.count(start) != 1 or source.count(end) != 1:
        sys.exit(f'FAIL: production field action anchor changed: {start!r}')
    return source.split(start, 1)[1].split(end, 1)[0]

# Include the production cooking callback, pot registration and Give reward.
actions = section('# Cook exactly the materials selected with Hold', '\nshrines_setup()')
actions = actions[actions.index('__cook_dish ='):]
# These updates live in main's render loop, outside the imported story module.
update = section('    # cooking: kneel at the pot a moment, the prompt away until done\n', '    # a camp\'s chest opens once')
give_rule = next(line for line in source.splitlines() if line.startswith('    usables[give_u].enabled ='))
update += give_rule + '\n'
# The fixture pot's registration still goes through the real main callback.
template = Path('tools/late_story.jo.in').read_text()
actions = 'bonfires.push(Bonfire(v3(-945.0, height_at(-945.0, 1888.0), 1888.0), pot = true))\n' + actions
harness = template.replace('# @FIELD_ACTIONS@', actions)
harness = harness.replace('    # @FIELD_UPDATE@', re.sub(r'\bdt\b', 'DT', update).rstrip())
(root / 'harness.jo').write_text(harness)
subprocess.run(['python3', 'tools/headless_build.py', str(root / 'harness.jo'), '-o', str(root / 'check')], check=True)
clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
try:
    run = subprocess.run([str(root / 'check')], env={**clean, 'BOTW_SHRINE_LOG': '1'},
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=90)
    output, status = run.stdout, run.returncode
except subprocess.TimeoutExpired as exc:
    output = exc.stdout or ''
    if isinstance(output, bytes):
        output = output.decode(errors='replace')
    output += '\nFAIL: late story exceeded 90 seconds wall time\n'
    status = 1
(root / 'run.log').write_text(output)
expected = ['campfire-greeting', 'cold-unprotected', 'meal-cooked-camera-restored', 'doublet-given',
            'cold-protected', 'tower-activated', 'tower-rising', 'shrines-revealed',
            'tower-camera-restored', 'old-man-tower-arrival']
for n in range(1, 5):
    expected.extend([f'shrine-{n}-entry-camera-restored', f'orb-{n}-earned', f'shrine-{n}-exit-camera-restored'])
expected.extend(['temple-roof-offered', 'paraglider-given', 'farewell-camera-restored',
                 'plateau-left-gliding', 'leaving-title-shown', 'leaving-title-finished'])
events = re.findall(r'^late-story: (\S+) frame (\d+) beat (\w+) orbs (\d+)$', output, re.M)
errors = []
if [e[0] for e in events] != expected:
    errors.append('missing, duplicated or unordered story checkpoints')
if re.findall(r'^shrine: orb received \((\d+)\)$', output, re.M) != ['1', '2', '3', '4']:
    errors.append('expected exactly four earned orb awards, in order')
for line in output.splitlines():
    if line.startswith(('late-story:', 'PASS', 'FAIL', 'panic:')):
        print(line)
if status or errors or not re.search(r'^PASS late story:', output, re.M):
    print('FAIL: ' + '; '.join(errors or [f'exit {status}']))
else:
    print('PASS: ordered late story; no story progress presets; production cooking and Give callbacks')
print(f'Full story trail and generated production harness: {root}/')
sys.exit(1 if status or errors else 0)
PY
