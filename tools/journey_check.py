#!/usr/bin/env python3
"""Build a CPU snapshot of production world code, survey it, and steer a continuous journey.
Only GPU uploads are replaced: terrain, geometry, vegetation bounds, collision, movement,
stamina and interactions remain production code. Route planning never changes player state.
"""
import hashlib
import heapq
import json
import math
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys

keyboard = '--keyboard' in sys.argv[1:]
if any(arg != '--keyboard' for arg in sys.argv[1:]):
    raise SystemExit('Usage: tools/journey_check.sh [--keyboard]')
ROOT = Path('build/journey-keyboard-check' if keyboard else 'build/journey-check')
ROOT.mkdir(parents=True, exist_ok=True)
# Failed reruns must not leave a previous successful result or trail behind.
for name in ['metrics.json', 'sources.json', 'trace.csv']:
    (ROOT / name).unlink(missing_ok=True)
GAME = ROOT / 'game'
GAME.mkdir(exist_ok=True)
for path in Path(os.environ.get('JOURNEY_GAME_DIR', 'game')).glob('*.jo'):
    text = path.read_text()
    if path.name == 'structures.jo':
        assert text.count('    build_finish()') == 1
        text = text.replace('    build_finish()', '    pass # CPU harness: no GPU upload')
    if path.name == 'vegetation.jo':
        # The round-82 bush texture adds a branch to this upload expression.
        # Strip the whole texture selection, preserving geometry/collision below.
        text, texture_uploads = re.subn(
            r'^        t = if .*__veg_tex\(tex\).*white_tex$',
            '        t = white_tex', text, flags=re.MULTILINE)
        assert texture_uploads == 1, 'one vegetation texture upload selection'
        replacements = {
            'mesh(vs, ids)': 'Mesh()',
            'vm.low = mesh(tv, ti)': 'vm.low = Mesh()',
            '    crown_bake(vm)': '    pass # CPU harness: no crown atlas upload',
        }
        for old, new in replacements.items():
            if old == '    crown_bake(vm)' and old not in text: continue
            assert text.count(old) == 1, old
            text = text.replace(old, new)
    (GAME / path.name).write_text(text)
harness = Path('tools/journey.jo.in').read_text().replace('build/journey-check', str(ROOT))
(ROOT / 'harness.jo').write_text(harness)
subprocess.run(['sloppy/bin/sloppy', 'build', str(ROOT / 'harness.jo'), '-o', str(ROOT / 'check')], check=True)
clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'JOURNEY_'))}
if keyboard: clean['JOURNEY_KEYBOARD'] = '1'
def run(arg, log):
    with (ROOT / log).open('w') as out:
        status = subprocess.run([str(ROOT / 'check'), arg], env=clean, stdout=out,
                                stderr=subprocess.STDOUT, timeout=300).returncode
    if status:
        print("\n".join((ROOT / log).read_text().splitlines()[-25:]))
        sys.exit(status)
run('survey', 'survey.log')
cells = {}
for line in (ROOT / 'survey.csv').read_text().splitlines():
    x, z, y, slope, clear = map(float, line.split(','))
    cells[int(x), int(z)] = (y, slope, bool(clear))
unsafe_edges = {tuple(map(int, line.split(','))) for line in (ROOT / 'unsafe-edges.csv').read_text().splitlines()}
goals = [tuple(map(float, line.split(','))) for line in (ROOT / 'goals.csv').read_text().splitlines()]

def nearest(p):
    return min((q for q, v in cells.items() if v[2]), key=lambda q: math.hypot(q[0]-p[0], q[1]-p[2]))

def route(a, b):
    start, end = nearest(a), nearest(b)
    first = (*start, 0)
    queue = [(0, 0, first)]
    costs, prev = {first: 0}, {}
    labels = {start: {0: 0}}
    while queue:
        _, queued_cost, state = heapq.heappop(queue)
        if queued_cost != costs.get(state):
            continue
        q = state[:2]
        if labels[q].get(state[2]) != queued_cost:
            continue
        if q == end:
            out = [state]
            while out[-1] != first:
                out.append(prev[out[-1]])
            return [s[:2] for s in reversed(out)]
        for dx, dz in [(2, 0), (-2, 0), (0, 2), (0, -2), (2, 2), (2, -2), (-2, 2), (-2, -2)]:
            if (*q, dx, dz) in unsafe_edges:
                continue
            n = q[0]+dx, q[1]+dz
            if n not in cells or not cells[n][2]:
                continue
            if dx and dz and (not cells[q[0]+dx, q[1]][2] or not cells[q[0], q[1]+dz][2]):
                continue
            d = math.hypot(dx, dz)
            dy = cells[n][0]-cells[q][0]
            grade = abs(dy)/d
            if grade > 12.0:
                continue
            spent = state[2]
            if max(cells[n][1], cells[q][1]) > 0.78:
                # Conservative stock-wheel budget, quantized into 20-point buckets.
                drain = abs(dy)*(45 if dy > 0 else 18) + d*2
                spent += max(1, math.ceil(drain/20))
                if spent > 45:
                    continue
            if cells[n][1] < 0.77:
                spent = 0
            dest = (*n, spent)
            cost = costs[state] + d*(1 + grade*3 + cells[n][1]*2)
            if cells[n][1] > 0.68:
                cost += abs(dy)*100 + d*40
            if cost >= costs.get(dest, math.inf):
                continue
            alternatives = labels.setdefault(n, {})
            if any(s <= spent and c <= cost for s, c in alternatives.items()):
                continue
            for s, c in list(alternatives.items()):
                if s >= spent and c >= cost:
                    del alternatives[s]
            alternatives[spent] = cost
            costs[dest], prev[dest] = cost, state
            h = math.hypot(n[0]-end[0], n[1]-end[1])
            heapq.heappush(queue, (cost+h, cost, dest))
    raise RuntimeError(f'no stock-stamina field route: {a} -> {b}')

# Cave -> tower foot; tower descent -> four shrine lifts; fourth lift -> Temple front.
# All legs are executed in one process. The planner only writes steering targets.
for i, (a, b) in enumerate(zip(goals, goals[1:])):
    if i == 4:
        shelf = (-968.0, 291.6, 2322.0)
        ridge = (-1000.0, 316.77, 2302.0)
        points = route(a, shelf) + route(shelf, ridge)[1:] + route(ridge, b)[1:]
    else:
        points = route((-1048.0, 0.0, 1824.0) if i == 0 else a, b)
    # Keep bends, eliminate only collinear intermediate cells; no obstacle-cutting smoothing.
    points = [q for j, q in enumerate(points) if j in (0, len(points)-1) or
              (cells[q][1] < .77) != (cells[points[j-1]][1] < .77) or
              (q[0]-points[j-1][0], q[1]-points[j-1][1]) !=
              (points[j+1][0]-q[0], points[j+1][1]-q[1])]
    text = ''.join(f'{x},{cells[x,z][0]:.4f},{z}\n' for x, z in points)
    text += f'{b[0]},{b[1]},{b[2]}\n'
    (ROOT / f'leg-{i}.csv').write_text(text)
    print(f'planned leg {i}: {len(points)} waypoints', flush=True)
run('journey', 'run.log')
log = (ROOT / 'run.log').read_text()
pattern = re.compile(r'journey: ([\w-]+): ([\d.]+) s, ([\d.]+) m, max slope ([\d.]+) deg, climb ([\d.]+) s, stamina outs (\d+), falls (\d+), hard falls (\d+), stuck points (\d+); at (.*)')
legs = []
for match in pattern.finditer(log):
    name, seconds, metres, slope, climb, outs, falls, hard, stuck, position = match.groups()
    legs.append(dict(name=name, seconds=float(seconds), metres=float(metres),
                     max_slope_degrees=float(slope), climb_seconds=float(climb),
                     stamina_outs=int(outs), falls=int(falls), hard_falls=int(hard),
                     stuck_points=int(stuck), end_position=position))
expected = ['cave-to-tower', 'tower-climb', 'tower-descent', 'Oman-Au', 'Ja-Baij',
            'Owa-Daim', 'Keh-Namut', 'Temple-approach', 'Temple-roof-meeting']
assert [leg['name'] for leg in legs] == expected, 'missing or unordered journey checkpoint'
assert 'tower-activated through production interaction' in log, 'missing tower callback'
total = re.search(r'PASS journey: uninterrupted field traversal, (\d+) frames, ([\d.]+) simulated seconds, ([\d.]+) m', log)
assert total, 'missing continuous journey PASS'
if keyboard:
    assert 'PASS keyboard input: ' in log, 'missing production keyboard/camera input verification'
metrics = dict(input_mode='keyboard' if keyboard else 'actions', frames=int(total[1]), seconds=float(total[2]), metres=float(total[3]), legs=legs,
               stuck_locations=[line for line in log.splitlines() if line.startswith('journey: stuck')])
(ROOT / 'metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
manifest = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(Path('game').glob('*.jo'))}
manifest.update({str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in [Path('tools/journey.jo.in'), Path('tools/journey_check.py')]})
(ROOT / 'sources.json').write_text(json.dumps(manifest, indent=2) + '\n')
for line in log.splitlines():
    if line.startswith(('journey:', 'PASS', 'FAIL')):
        print(line)
assert not metrics['stuck_locations'] and all(leg['stuck_points'] == 0 for leg in legs), 'blocked progress on the production journey; inspect metrics.json and trace.csv'
assert all(leg['stamina_outs'] == 0 for leg in legs), 'stock stamina exhausted on the production journey'
assert all(leg['hard_falls'] == 0 for leg in legs), 'hard fall on the production journey; inspect metrics.json and trace.csv'
print(f'Full controller trail, metrics, source hashes, survey and waypoints: {ROOT}/')
