#!/usr/bin/env python3
"""Reproduce the critic pack's 120s route with fixed affinity and AB/BA controls.

All output and frozen sources stay under build/. Each run owns a separate flock.
Build:  ... OUTPUT build LABEL REVISION (use WORKTREE for uncommitted sources)
Run:    ... OUTPUT run NAME LABEL [--trace]
Report: ... OUTPUT report
Use master for all four control-{1-A,1-B,2-B,2-A} runs, then master/candidate
for compare-{1-A,1-B,2-B,2-A}. Never pool traced and untraced measurements.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import time

from critic_pack import (ROOT, clean_env, command_run, digest, lock_wait,
                         percentiles, performance_report)


def freeze(out, label, revision):
    folder = out / label
    assert not folder.exists(), 'frozen build already exists'
    game = folder / 'game'
    game.mkdir(parents=True)
    scripts = folder / 'tools'
    scripts.mkdir()
    hashes = {}
    for path in sorted((ROOT / 'game').glob('*.jo')):
        data = path.read_bytes() if revision == 'WORKTREE' else subprocess.check_output(
            ['git', 'show', f'{revision}:game/{path.name}'])
        (game / path.name).write_bytes(data)
        hashes[path.name] = hashlib.sha256(data).hexdigest()
    # Identical adaptation to critic_pack.performance: X11 assertion and managed
    # 2133x1200 geometry, with the original real-dt route/update/draw unchanged.
    source = (ROOT / 'tools/render_session.jo').read_text().replace(
        'assert(__wayland and not __soft)',
        'assert(not __wayland and not __soft and __xdpy != null)')
    source += '\n' + (ROOT / 'tools/performance_output.jo').read_text().split('performance_output_run =', 1)[0]
    anchor = '        __gl_screen_resize(__win_w, __win_h)'
    assert source.count(anchor) == 1
    source = source.replace(anchor, '''        root: int = 0
        x: i32 = 0
        y: i32 = 0
        w: u32 = 0
        h: u32 = 0
        border: u32 = 0
        depth: u32 = 0
        assert(__perf_geometry(__xdpy,__xwin,&root,&x,&y,&w,&h,&border,&depth)!=0)
        if w!=2133 or h!=1200:
            __perf_resize(__xdpy,__xwin,2133,1200)
            __perf_sync(__xdpy,0)
            assert(__perf_geometry(__xdpy,__xwin,&root,&x,&y,&w,&h,&border,&depth)!=0)
        assert(w==2133 and h==1200)
        __win_w=int(w)
        __win_h=int(h)
''' + anchor)
    fixture = scripts / 'route.jo'
    fixture.write_text(source)
    command_run(['sloppy/bin/sloppy', 'build', str(fixture), '-o', str(folder / 'route')], folder / 'build.log')
    (folder / 'sources.json').write_text(json.dumps(hashes, indent=2) + '\n')
    (folder / 'provenance.json').write_text(json.dumps(dict(revision=revision,
        executable_sha256=digest(folder/'route'), fixture_sha256=digest(fixture)), indent=2)+'\n')
    print('BUILT', label, flush=True)


def run(out, name, label, cpu, trace):
    folder = out / name
    assert not folder.exists(), 'retain previous measurements; choose a new name'
    folder.mkdir()
    # Link within this evidence directory only; frozen executables are immutable.
    os.link(out / label / 'route', folder / 'route')
    env = clean_env() | dict(BOTW_SKIP='1', BOTW_AT='-1140,1500,3.14', BOTW_HOUR='11',
        BOTW_TIMESCALE='0', BOTW_WEATHER='clear', BOTW_FPS='0', BOTW_FRAME_LOG='1',
        BOTW_LOADTIME='1', BOTW_SCENE_LOG='1', SLOPPY_PLATFORM='x11', SLOPPY_VULKAN='1',
        SLOPPY_VSYNC='0', SLOPPY_WINDOW='2133x1200', PROBE_ROUTE='forest', PROBE_SECONDS='120',
        PROBE_PNG=str(folder / 'route.png'))
    if trace:
        env.update(BOTW_CPU='1', BOTW_CPU_TRACE_MS='6', PROBE_STAGES='1')
    command = ['flock', '/tmp/botw-render.lock', 'taskset', '-c', str(cpu), 'python3',
        'tools/performance_window.py', '--visible', '2133x1200', 'timeout', '180',
        'tools/play.sh', str(folder / 'route')]
    settings = dict(command=command, label=label, trace=trace, affinity=[cpu],
        environment={k:v for k,v in env.items() if k.startswith(('BOTW_', 'SLOPPY_', 'PROBE_'))})
    (folder / 'settings.json').write_text(json.dumps(settings, indent=2)+'\n')
    print('QUEUED', name, label, flush=True)
    started = time.monotonic()
    wall = command_run(command, folder / 'route.log', env)
    report = performance_report(folder, command, env, 0, wall, lock_wait(folder / 'route.log', started))
    print('DONE', name, report['timing_ms'], flush=True)


def report(out):
    runs = {}
    samples = {}
    protocols = []
    for folder in sorted(out.iterdir()):
        if not (folder / 'summary.json').exists() or not (folder / 'settings.json').exists():
            continue
        summary = json.loads((folder / 'summary.json').read_text())
        settings = json.loads((folder / 'settings.json').read_text())
        if settings['trace']:
            continue
        protocols.append({k:v for k,v in settings['environment'].items() if k != 'PROBE_PNG'})
        samples[folder.name] = [float(line.split()[7]) for line in (folder/'route.log').read_text().splitlines()
                               if line.startswith('present return:') and int(line.split()[2]) > 240]
        runs[folder.name] = dict(label=settings['label'], affinity=settings['affinity'],
            sha256=summary['executable_sha256'], p99=summary['timing_ms']['callback_thread']['p99'],
            p50=summary['timing_ms']['callback_thread']['p50'], frames=summary['total_frames'],
            distance_m=summary['route_distance_m'])
    control = [runs[f'control-{n}'] for n in ('1-A', '1-B', '2-B', '2-A')]
    assert len({r['sha256'] for r in control}) == 1, 'control must be byte-identical'
    assert len({tuple(r['affinity']) for r in runs.values()}) == 1
    assert all(p == protocols[0] for p in protocols), 'route flags must match'
    spread = max(r['p99'] for r in control)-min(r['p99'] for r in control)
    result = dict(runs=runs, control_spread_ms=spread,
        control_pair_deltas_ms=[runs[f'control-{i}-B']['p99']-runs[f'control-{i}-A']['p99'] for i in (1,2)])
    for prefix in ('compare', 'final'):
        names = [f'{prefix}-{i}-{phase}' for i in (1,2) for phase in ('A','B')]
        if not all(n in runs for n in names):
            continue
        assert all(runs[f'{prefix}-{i}-A']['sha256'] == control[0]['sha256'] for i in (1,2))
        phase_values = {phase:[runs[f'{prefix}-{i}-{phase}']['p99'] for i in (1,2)] for phase in ('A','B')}
        means = {phase:statistics.mean(values) for phase,values in phase_values.items()}
        delta = means['B']-means['A']
        pooled = {phase:percentiles([v for i in (1,2) for v in samples[f'{prefix}-{i}-{phase}']]) for phase in ('A','B')}
        result[prefix] = dict(run_p99_ms=phase_values, pooled_cpu_ms=pooled, mean_run_p99_ms=means,
            delta_ms=delta, within_control_spread=abs(delta)<=spread,
            pair_deltas_ms=[runs[f'{prefix}-{i}-B']['p99']-runs[f'{prefix}-{i}-A']['p99'] for i in (1,2)])
    (out / 'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    sub = parser.add_subparsers(dest='action', required=True)
    build = sub.add_parser('build')
    build.add_argument('label')
    build.add_argument('revision')
    launch = sub.add_parser('run')
    launch.add_argument('name')
    launch.add_argument('label')
    launch.add_argument('--cpu', type=int, default=2)
    launch.add_argument('--trace', action='store_true')
    sub.add_parser('report')
    args = parser.parse_args()
    os.chdir(ROOT)
    out = args.output.resolve()
    assert out.is_relative_to(ROOT/'build')
    out.mkdir(parents=True, exist_ok=True)
    for value in (getattr(args,'name',''), getattr(args,'label','')):
        assert '/' not in value and value not in ('.','..')
    if args.action == 'build': freeze(out, args.label, args.revision)
    elif args.action == 'run': run(out, args.name, args.label, args.cpu, args.trace)
    else: report(out)


if __name__ == '__main__':
    main()
