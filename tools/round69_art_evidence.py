#!/usr/bin/env python3
"""Frozen art captures, alternating CPU/frame timing pairs, and complete pack comparisons.

Each render owns one bounded flock. Evidence and generated fixtures stay in build/.
"""
import argparse
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from PIL import Image, ImageDraw
import critic_pack as pack

ROOT = pack.ROOT
OUT = ROOT / 'build/sol3-r69-art'
SCENES = {name: (frames[-1][0], flags) for _, name, frames, flags, _ in pack.SCENES}
SCENES['pond-rain'] = (300, dict(BOTW_SKIP='1', BOTW_AT='-1161,1684,-0.9', BOTW_WEATHER='rain'))
SCENES['pond-rain-wade'] = (300, dict(BOTW_SKIP='1', BOTW_AT='-1190,1665,-0.9', BOTW_WEATHER='rain'))
SCENES['meadow'] = (300, dict(BOTW_SKIP='1', BOTW_CAM='-790,249,1931,-2.75,-0.18'))
AREAS = ['meadow', 'temple', 'firs', 'snow', 'pool', 'swim', 'pond-rain', 'forest', 'rain']


def prepare(label):
    folder = OUT / label
    folder.mkdir(parents=True, exist_ok=True)
    pack.build_fixture(folder)
    (folder / 'sources.json').write_text(json.dumps({p.name: pack.digest(p) for p in (ROOT/'game').glob('*.jo')}, indent=2)+'\n')


def pinned_window():
    """Pin only the steady main thread; initialized driver/audio workers stay free."""
    source = (ROOT/'tools/performance_window.py').read_text()
    source = source.replace('        last_geometry = None', '        last_geometry = None\n        pinned = False')
    anchor = '        while proc.poll() is None:\n            root, gx, gy'
    assert source.count(anchor) == 1
    source = source.replace(anchor, '''        while proc.poll() is None:
            if not pinned and 'first frame:' in Path(child_env['R69_LOG']).read_text():
                game_pid = owner_pid(wid)
                core = int(child_env['R69_CORE'])
                os.sched_setaffinity(game_pid, {core})
                pinned = True
                print(f'benchmark steady main-thread affinity: PID {game_pid} core {core}', flush=True)
            root, gx, gy''')
    source = source.replace('        status = proc.wait()', "        status = proc.wait()\n        if status == 0: assert pinned, 'main-thread affinity was applied'")
    path = OUT/'main-thread-window.py'
    path.write_text(source)
    return str(path)


def run(label, scene, frames=None, repeat=None, warmup=240, pin_core=None):
    target, flags = SCENES[scene]
    binary = OUT / label / 'fixture/capture'
    assert binary.is_file(), 'prepare a frozen executable first'
    folder = OUT / ('captures' if repeat is None else 'performance') / (scene if pin_core is None else scene+'-controlled')
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / (label if repeat is None else f'{label}-{repeat}')
    # Frozen executables must generate their own geometry. Live prepared packs
    # use live source stamps and could otherwise feed changed geometry to A.
    env = pack.clean_env() | pack.BASE | flags | dict(BOTW_NO_PREPARED_ASSETS='1',
        CP_SCENE='swim' if scene == 'pond-rain' else scene,
        CP_FRAMES='0', CP_OUT=str(folder), BOTW_FRAME_LOG='1',
        SLOPPY_FRAMES=str(frames or target), SLOPPY_SCREENSHOT=str(dest.with_suffix('.png')))
    window = 'tools/performance_window.py'
    if pin_core is not None:
        assert pin_core in os.sched_getaffinity(0)
        env.update(R69_LOG=str(dest.with_suffix('.log')), R69_CORE=str(pin_core))
        window = pinned_window()
    command = ['flock', '/tmp/botw-render.lock', 'python3', window,
               '1280x720', 'timeout', '90', str(binary)]
    pack.command_run(command, dest.with_suffix('.log'), env, capture_batch=repeat is not None)
    (dest.with_suffix('.json')).write_text(json.dumps(dict(executable_sha256=pack.digest(binary),
        sources=json.loads((OUT/label/'sources.json').read_text()), environment={k:v for k,v in env.items() if k.startswith(pack.PREFIXES) or k.startswith('R69_')}, command=command, warmup=warmup, main_thread_core=pin_core), indent=2)+'\n')
    with Image.open(dest.with_suffix('.png')) as im:
        assert im.size == (1280, 720)
        im.convert('RGB').resize((640,360), Image.Resampling.LANCZOS).save(dest.with_suffix('.jpg'), quality=93)
    rows = [[float(v) for v in line.split()[2:]] for line in dest.with_suffix('.log').read_text().splitlines() if line.startswith('frame sample:')]
    # Production flushes its timing buffer only on each 120th frame.
    assert len(rows) == ((frames or target) // 120) * 120
    print('PASS', scene, label, repeat if repeat is not None else 'capture', flush=True)
    return [r for r in rows if r[0] > warmup]


def comparison(before, after, dest, name):
    sheet = Image.new('RGB', (1280,384), '#181d22')
    draw = ImageDraw.Draw(sheet)
    for k, (label, path) in enumerate([('before', before), ('after', after)]):
        with Image.open(path) as im:
            sheet.paste(im.convert('RGB').resize((640,360), Image.Resampling.LANCZOS), (k*640,24))
        draw.text((k*640+8,6), f'{name}: {label}', fill='white')
    sheet.save(dest, quality=93)


def performance(label, scenes, frames=720, warmup=240, repeats=3, pin_core=None):
    summary = dict(protocol=f'alternating AB/BA; {frames} fixed-dt frames/run; first {warmup} excluded; {repeats} runs/version; pooled nearest-rank p99; same 1280x720 Vulkan full-scale scene, hour/weather/seed; generated geometry from frozen sources; CPU budget 3% + 0.10 ms', scenes={})
    summary['executables'] = {phase: pack.digest(OUT/phase/'fixture/capture') for phase in ['before',label]}
    report = OUT/'performance'/('summary-controlled.json' if pin_core is not None else 'summary.json')
    if report.exists():
        previous = json.loads(report.read_text())
        if previous.get('executables') == summary['executables']:
            summary['scenes'] = previous['scenes']
    for scene in scenes:
        samples = {'before': [], label: []}
        per_run = {'before': [], label: []}
        for repeat in range(repeats):
            for phase in (['before',label] if repeat % 2 == 0 else [label,'before']):
                rows = run(phase, scene, frames, repeat, warmup, pin_core)
                samples[phase].extend(rows)
                per_run[phase].append(pack.percentiles([r[4] for r in rows]))
        pack.release_capture_lock()
        result = {phase: {metric: pack.percentiles([r[col] for r in samples[phase]]) for metric,col in [('cpu_thread_ms',4),('cpu_wall_ms',2),('frame_ms',1)]} for phase in samples}
        result['per_run_cpu'] = per_run
        result['protocol'] = dict(frames=frames, warmup=warmup, repeats=repeats, main_thread_core=pin_core, order='alternating AB/BA', samples_per_version=(frames-warmup)*repeats)
        result['passed'] = result[label]['cpu_thread_ms']['p99'] <= result['before']['cpu_thread_ms']['p99']*1.03+0.10
        summary['scenes'][scene] = result
        report.write_text(json.dumps(summary, indent=2)+'\n')
        print('PASS' if result['passed'] else 'FAIL', scene, 'CPU p99', result['before']['cpu_thread_ms']['p99'], result[label]['cpu_thread_ms']['p99'], flush=True)
    assert all(r['passed'] for r in summary['scenes'].values()), 'CPU p99 regression'


def compare_pack(folder):
    manifest = json.loads((folder/'pack.json').read_text())
    out = OUT/'review/full-pack'
    out.mkdir(parents=True, exist_ok=True)
    for shot in manifest['shots']:
        relative = Path(shot['png'])
        comparison(Path('/tmp/crit69pack')/relative, folder/relative, out/f'{shot["name"]}.jpg', shot['name'])
    print('PASS', len(manifest['shots']), 'master/final comparisons', out)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['prepare','capture','performance','compare-pack'])
    p.add_argument('label')
    p.add_argument('scenes', nargs='*')
    p.add_argument('--frames', type=int, default=720)
    p.add_argument('--warmup', type=int, default=240)
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--pin-core', type=int)
    a = p.parse_args()
    assert a.frames > a.warmup >= 0 and a.frames % 120 == 0 and a.repeats > 0
    os.chdir(ROOT)
    if a.mode == 'compare-pack':
        compare_pack((ROOT/a.label).resolve())
    else:
        assert a.label.replace('-','').isalnum()
        scenes = a.scenes or AREAS
        assert all(s in SCENES for s in scenes)
        if a.mode == 'prepare': prepare(a.label)
        elif a.mode == 'performance':
            try: performance(a.label, scenes, a.frames, a.warmup, a.repeats, a.pin_core)
            finally: pack.release_capture_lock()
        else:
            for scene in scenes:
                run(a.label, scene)
                folder = OUT/'captures'/scene
                if a.label != 'before' and (folder/'before.png').exists():
                    comparison(folder/'before.png',folder/f'{a.label}.png',folder/f'review-{a.label}.jpg',scene)
