#!/bin/bash
# Fresh lift -> all puzzles + chest + failure recovery -> monk/orb -> exterior lift.
# Headless; no game render. Optional arguments select shrine IDs (1..4).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/shrine-routes
sloppy/bin/sloppy build tools/shrine_route.jo -o build/shrine-route
python3 - "$@" <<'PY'
import os
from pathlib import Path
import re
import subprocess
import sys
import time

names = ['Ohman Ow', 'Jaba Badge', 'Owa Dime', 'Kay Nomut']
try:
    selected = [int(arg) for arg in sys.argv[1:]] or [1, 2, 3, 4]
    if any(n not in range(1, 5) for n in selected):
        raise ValueError
except ValueError:
    sys.exit('Usage: tools/shrine_route_check.sh [1|2|3|4 ...]')

# Keep test runs independent of inherited stage/position/carry/loadout and save switches.
clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
lift = 'lift, fresh puzzle'
recovered = 'checkpoint recovered (-2 HP)'
end = 'orb verified, exterior lift returned'
routes = [
    [lift, 'fell; back to the checkpoint', recovered,
     'crate 0 at 5.0,-3.0', 'crate 0 at 5.0,-5.0', 'crate 0 at 3.0,-5.0',
     'crate 0 at 1.0,-5.0', 'crate 0 at -1.0,-5.0', 'crate 0 at -3.0,-5.0',
     'crate 0 at -5.0,-5.0', 'bridge up', 'stage 1 illuminated',
     'weighted bridge crossed', 'scout destroyed', 'stage 2 illuminated',
     'chest: travelers_bow', 'chest verified travelers_bow',
     'foundry pier blocks direct push', 'crate 2 at -34.0,-37.0', 'crate 2 at -34.0,-39.0',
     'crate 2 at -36.0,-39.0', 'crate 2 at -38.0,-39.0', 'crate 2 at -40.0,-39.0',
     'foundry shuttle powered', 'crate 2 at -42.0,-39.0',
     'foundry metal delivered', 'foundry 28-second cycle verified, both directions',
     'foundry outbound ride verified', 'chest: rusty_broadsword', 'foundry high treasury reached',
     'foundry return ride verified', 'foundry shuttle returned', 'crate 1 at 4.0,-37.0', 'crate 1 at 4.0,-39.0',
     'crate 1 at 4.0,-41.0', 'crate 1 at 4.0,-43.0', 'crate ledge climbed',
     'monk 0 talks', 'orb received (1)', end],
    [lift, 'barrel picked up', 'barrel lit', 'barrel thrown',
     'wall ja_baij_crack_e broken', 'chest: travelers_claymore',
     'chest verified travelers_claymore', 'gallery barrel rolled',
     'gallery roll lit', 'rolling bomb stopped by shutter', 'closed shutter roll recovered',
     'gallery barrel rolled', 'gallery roll lit', 'rolling bomb cleared shutter',
     'wall ja_baij_crack_far broken', 'chest: arrow', 'rolling bomb treasury reached',
     'barrel picked up', 'barrel lit',
     'barrel thrown', 'wall ja_baij_crack_n broken', 'stage 1 illuminated',
     'fell; back to the checkpoint', recovered, 'barrel picked up', 'barrel lit',
     'barrel thrown', 'boom at', 'boom at', 'boom at', 'boom at',
     'pillar falls', 'pillar bridge down', 'stage 2 illuminated',
     'chain explosion bridge crossed', 'monk 1 talks', 'orb received (1)', end],
    [lift, 'fell; back to the checkpoint', recovered, 'first hub reached',
     'second hub reached', 'chest: travelers_shield', 'chest verified travelers_shield',
     'east island reached', 'clockwork first hub reached', 'gear 2 frozen',
     'clockwork brake verified stationary', 'clockwork second hub reached', 'gear 3 frozen',
     'clockwork brake verified stationary', 'chest: amber', 'frozen clockwork treasury reached',
     'clockwork return bridge deployed', 'clockwork island returned', 'second hub regained', 'stage 1 illuminated',
     'turning bars crossed', 'boulder niche 1', 'boulder niche 2', 'boulder niche 3',
     'stage 2 illuminated', 'monk 2 talks', 'orb received (1)', end],
    [lift, 'low-water failed crossing', 'shore recovered (-4 HP)', 'water rising',
     'water level -0.4', 'stage 1 illuminated', 'wall climbed to 3.6',
     'chest: travelers_spear', 'chest verified travelers_spear',
     'frost cistern rising', 'frost cistern near valve struck', 'frost cistern draining',
     'frost plate weighted, ice stair raised', 'frost cistern far valve struck',
     'chest: opal', 'ice stair treasury reached', 'frost cistern niche returned', 'water draining',
     'gate open', 'stage 2 illuminated', 'water level -2.6',
     'north crystal struck, crate settled', 'wall climbed to 4.0',
     'monk balcony climbed', 'monk 3 talks', 'orb received (1)', end],
]
failed = False
for n in selected:
    start = time.monotonic()
    try:
        run = subprocess.run(['build/shrine-route'], env={**clean, 'BOTW_SHRINE': str(n),
                            'BOTW_SHRINE_LOG': '1'}, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, timeout=60)
        output, status = run.stdout, run.returncode
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b'').decode() if isinstance(exc.stdout, bytes) else (exc.stdout or '')
        output += '\nFAIL: route exceeded 60 seconds wall time\n'
        status = 1
    elapsed = time.monotonic() - start
    Path(f'build/shrine-routes/{n}.log').write_text(output)
    errors = []
    cursor = 0
    for event in routes[n - 1]:
        at = output.find(event, cursor)
        if at < 0:
            errors.append(f'missing or out of order: {event}')
            break
        cursor = at + len(event)
    if output.count('orb received (1)') != 1:
        errors.append('expected exactly one orb award')
    if output.count('fell; back to the checkpoint') != (0 if n == 4 else 1):
        errors.append('unexpected pit recovery count')
    if n == 3 and 'boulder hit' in output:
        errors.append('boulder route took a hit')
    bonus = ['rusty_broadsword', 'arrow', 'amber', 'opal'][n - 1]
    if output.count(f'shrine: chest: {bonus}') != 1:
        errors.append('expected exactly one bonus chest award')
    duration = re.search(r'(\d+) frames, ([0-9.]+) simulated seconds', output)
    if not duration or not 120 <= float(duration[2]) <= 240:
        errors.append('route duration must be 120..240 simulated seconds')
    result = re.search(rf'^PASS {names[n-1]}: (.+)$', output, re.M)
    if status or errors or not result:
        failed = True
        print(f'FAIL {names[n-1]} ({elapsed:.2f}s wall): ' + '; '.join(errors or [f'exit {status}']))
    else:
        print(f'PASS {names[n-1]}: {result[1]}; {elapsed:.2f}s wall')
    # Preserve every puzzle event and frame-stamped route milestone, even on failure.
    for line in output.splitlines():
        if line.startswith(('shrine:', 'route:', 'FAIL', 'panic:')) and 'entrance vec3' not in line:
            print('  ' + line)
    print(f'  log: build/shrine-routes/{n}.log')
sys.exit(1 if failed else 0)
PY
