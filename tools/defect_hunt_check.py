#!/usr/bin/env python3
"""Headless production transactions and native-close saves in fresh processes."""
import os
import json
import re
import statistics
import time
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
OUT = ROOT / 'build/round65-defects'
OUT.mkdir(parents=True, exist_ok=True)
source = Path('game/main.jo').read_text()

def section(start, end):
    assert source.count(start) == 1 and source.count(end) == 1, start
    return source.split(start, 1)[1].split(end, 1)[0]

cook = 'cook_at_pot =' + section('cook_at_pot =', '\n__pot_us: int[]')
pickup = section('            else if wi >= 0:\n', '\n    if act.slot >= 0: use_slot(act.slot)')
pickup = '\n'.join(line[16:] for line in pickup.splitlines())
pickup = ('field_pickup = ():\n'
          '    wi = nearest_item(pl.pos + vec3(0, 0.3, 0), 1.6)\n'
          '    if wi < 0: return\n' +
          '\n'.join('    ' + line for line in pickup.splitlines()))
harness = Path('tools/defect_hunt.jo.in').read_text()
harness = harness.replace('# @COOK_CALLBACK@', cook).replace('# @PICKUP_CALLBACK@', pickup)
(OUT / 'harness.jo').write_text(harness)
subprocess.run(['sloppy/bin/sloppy', 'build', str(OUT / 'harness.jo'), '-o', str(OUT / 'check')], check=True)
clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
failed = []

def run(label, *args):
    result = subprocess.run([str(OUT / 'check'), *args], env=clean,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
    (OUT / f'{label}.log').write_text(result.stdout)
    print(result.stdout, end='', flush=True)
    if result.returncode or any(word in result.stdout for word in ('FAIL', 'panic:', 'error:')):
        failed.append(label)
    return result.returncode == 0 and 'panic:' not in result.stdout

run('runtime', 'runtime')
with tempfile.TemporaryDirectory(prefix='save-', dir=OUT) as temp:
    for name in ['glide', 'climb', 'talus-climb', 'swim', 'held', 'held-drop', 'cook', 'drop', 'shock', 'throw', 'burning', 'loot-death', 'loot-ground', 'title', 'tower', 'orb-before', 'orb-after', 'orb-skip', 'shrine-crate', 'night', 'log-water', 'log-slope']:
        path = str(Path(temp) / name)
        if run(f'{name}-write', 'write', name, path):
            run(f'{name}-read', 'read', name, path)
assert not failed, f'Failed probes: {failed}; logs: {OUT}'
print('PASS fresh-process defect hunt')

# Permanent placement and elemental transactions, with process restart at each edge.
third = harness.split('runtime = ():', 1)[0] + Path('tools/placement_gear_save.jo.in').read_text()
(OUT / 'transactions.jo').write_text(third)
subprocess.run(['sloppy/bin/sloppy', 'build', str(OUT / 'transactions.jo'), '-o', str(OUT / 'transactions')], check=True)
with tempfile.TemporaryDirectory(prefix='transactions-', dir=OUT) as temp:
    for mode in ['write', 'read', 'repicked']:
        result = subprocess.run([str(OUT / 'transactions'), mode, temp], env=clean, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
        (OUT / f'transactions-{mode}.log').write_text(result.stdout)
        print(result.stdout, end='', flush=True)
        assert result.returncode == 0 and not any(w in result.stdout for w in ['FAIL', 'panic:', 'error:']), result.stdout
print('PASS placement/gear fresh-process transactions')

# Round 66: isolated production cross-system probes share the established fixtures.
second = harness.split('runtime = ():', 1)[0] + Path('tools/round66_session.jo.in').read_text() + Path('tools/round66_hunt.jo.in').read_text()
(OUT / 'second.jo').write_text(second)
subprocess.run(['sloppy/bin/sloppy', 'build', str(OUT / 'second.jo'), '-o', str(OUT / 'second')], check=True)
for name in ['held-gear', 'arrow-water', 'skull-water', 'skull-fire', 'item-wall', 'guardian-cover', 'warm-expiry', 'element-physics', 'enemy-edge', 'enemy-bank', 'talus-edge', 'shrine-fight', 'blast', 'wind-river', 'rate-combat', 'camera-spaces', 'camera-water', 'long-session']:
    log = OUT / f'round66-{name}.log'
    rss_samples = []
    start = time.monotonic()
    with log.open('w') as stream:
        proc = subprocess.Popen([str(OUT / 'second'), name], env=clean, stdout=stream, stderr=subprocess.STDOUT)
        while proc.poll() is None:
            try:
                status = Path(f'/proc/{proc.pid}/status').read_text()
                rss = re.search(r'^VmRSS:\s+(\d+)', status, re.M)
                if rss: rss_samples.append([time.monotonic() - start, int(rss[1])])
            except FileNotFoundError:
                pass
            if time.monotonic() - start > 600:
                proc.kill()
                proc.wait()
                raise TimeoutError(name)
            time.sleep(0.1)
    output = log.read_text()
    print(output, end='', flush=True)
    if proc.returncode or any(word in output for word in ('FAIL', 'panic:', 'error:')): failed.append(name)
    if name == 'long-session':
        (OUT / 'round66-session-rss.json').write_text(json.dumps(rss_samples))
        minutes = [float(x) for x in re.findall(r'SESSION minute=\d+ update_us=([0-9.]+)', output)]
        assert len(minutes) == 30, output
        warm = statistics.median(minutes[4:8])
        tail = statistics.median(minutes[-4:])
        # Match simulation boundaries, not a fraction of wall time (each weather/
        # shrine cycle has a very different cost). RSS includes allocator reuse
        # and transparent huge-page residency; it is not a live-object counter.
        memory = [dict(zip(('minute', 'allocations', 'wall_s', 'rss', 'virtual', 'huge'), map(float, row)))
                  for row in re.findall(r'SESSION minute=(\d+).*?allocations=(\d+) wall_s=([0-9.]+) rss_kib=(\d+) virtual_kib=(\d+) huge_kib=(\d+)', output)]
        assert len(memory) == 30, 'Missing per-minute allocation/memory evidence'
        retained = memory[7:]  # warm all four weather/shrine cycles twice
        growth = retained[-1]['rss'] - retained[0]['rss']
        virtual_growth = retained[-1]['virtual'] - retained[0]['virtual']
        live_growth = max(r['allocations'] for r in retained) - min(r['allocations'] for r in retained)
        # Retained native allocations and reserved address space catch slow leaks.
        # The allocator retains up to 64 MiB per thread in its large-block free list; keep
        # that documented bound as an RSS guard instead of an 8 MiB residency bet.
        assert live_growth <= 32, f'Live allocations drifted by {live_growth} after eight cycles'
        assert virtual_growth < 8192, f'Allocator address space grew {virtual_growth} KiB after warmup'
        assert max(r['rss'] for r in retained) - retained[0]['rss'] < 65536, f'RSS exceeds native allocator reuse budget: {growth} KiB'
        assert tail < warm * 1.8 + 200, f'Update-time drift: {warm} -> {tail} us'
        metrics = {'simulated_seconds': 1800, 'frames': 108000, 'wall_seconds': time.monotonic()-start,
                   'peak_rss_kib': max(x[1] for x in rss_samples), 'post_warmup_growth_kib': growth,
                   'post_warmup_virtual_growth_kib': virtual_growth, 'post_warmup_live_allocation_range': live_growth,
                   'post_warmup_huge_page_growth_kib': retained[-1]['huge'] - retained[0]['huge'],
                   'memory_per_minute': memory,
                   'early_update_us_median': warm, 'late_update_us_median': tail}
        (OUT / 'round66-session-metrics.json').write_text(json.dumps(metrics, indent=2))
        print('PASS session memory and update-time drift:', {k: v for k, v in metrics.items() if k != 'memory_per_minute'})
assert not failed, f'Failed second-pass probes: {failed}; logs: {OUT}'
print('PASS second-pass defect hunt')
