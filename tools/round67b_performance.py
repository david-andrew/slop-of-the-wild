#!/usr/bin/env python3
"""Matched full-1080p AB/BA pairs; owns one bounded render lock per pair. Never wrap."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys

sys.dont_write_bytecode = True
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCENES = {
    'forest': dict(BOTW_AT='-1000,1620,3.14'),
    'camp': dict(BOTW_AT='-1439,1606,0', BOTW_GIVE='travelers_sword,travelers_shield', SLOPPY_INPUT='1:k+,1:w+,150:j+,151:j-,165:j+,166:j-,195:j+,196:j-,200:w-,225:j+,226:j-,255:j+,256:j-'),
    'swim': dict(BOTW_AT='-1161,1684,-0.9', SLOPPY_INPUT='10:w+,150:w-'),
}
COLUMNS = {'producer_interval': 1, 'callback_wall': 2, 'callback_thread': 4,
           'instance_uploads': 5, 'instance_bytes': 6, 'present_call': 11,
           'residual_runtime_gap': 12, 'runtime_thread': 13}


def metric(values):
    return dict(samples=len(values), mean=statistics.mean(values), p50=sorted(values)[math.ceil(len(values)*.5)-1],
                p99=sorted(values)[math.ceil(len(values)*.99)-1], worst=max(values))


def read(path):
    return [[float(x) for x in line.split()[2:]] for line in path.read_text().splitlines() if line.startswith('frame sample:')]


def pair(a):
    scene, repeat = a.scenes[0], a.repeat
    for phase in (['before', 'after'] if repeat % 2 == 0 else ['after', 'before']):
        exe = getattr(a, phase).resolve()
        folder = a.output/f'{scene}-{phase}-{repeat}'
        folder.mkdir(exist_ok=True)
        env = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'CP_', 'PROBE_')) and k != 'LD_AUDIT'}
        env.update(BOTW_SKIP='1', BOTW_HOUR='11', BOTW_TIMESCALE='0', BOTW_WEATHER='clear', BOTW_SCALE='1',
                   BOTW_FRAME_LOG='1', BOTW_LOADTIME='1', SLOPPY_VULKAN='1', SLOPPY_PLATFORM='x11', SLOPPY_VSYNC='0',
                   SLOPPY_WINDOW='1920x1080', SLOPPY_FRAMES=str(a.frames), SLOPPY_SCREENSHOT=str(folder/'final.png'))
        env.update(SCENES[scene])
        if a.gpu: env['BOTW_GPU'] = '1'
        command = [sys.executable, 'tools/performance_window.py', '--visible', '1920x1080', 'timeout', '85', str(exe)]
        (folder/'settings.json').write_text(json.dumps(dict(command=command, environment={k:v for k,v in env.items() if k.startswith(('BOTW_', 'SLOPPY_'))},
            binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(), load_start=Path('/proc/loadavg').read_text().strip()), indent=2)+'\n')
        with (folder/'run.log').open('w') as log:
            subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = read(folder/'run.log')
        assert len(rows) == a.frames and rows[-1][0] == a.frames, 'missing frame samples'
        im = Image.open(folder/'final.png').convert('RGB')
        assert im.size == (1920,1080)
        im.thumbnail((960,540)); im.save(folder/'preview.jpg')
        (folder/'load-end.txt').write_text(Path('/proc/loadavg').read_text())
        steady = [r for r in rows if r[0] > 240]
        print(scene, phase, repeat, 'CPU', metric([r[4] for r in steady])['p99'], 'producer', metric([r[1] for r in steady])['p99'], flush=True)


def report(a):
    result = dict(protocol='visible managed X11 Vulkan 1920x1080, full scale, immediate fallback, fixed world/hour/weather/input/1/60 simulation; adjacent AB/BA pairs, one short render lock per pair; nearest-rank pooled percentiles, every tail retained; steady frames241-end; moving swim61-150; screenshot only after measured windows; GPU diagnostics separate from uninstrumented CPU comparisons', gpu_instrumentation=a.gpu, scenes={})
    for scene in a.scenes:
        result['scenes'][scene] = {}
        for phase in ['before','after']:
            all_rows = [r for repeat in range(a.repeats) for r in read(a.output/f'{scene}-{phase}-{repeat}/run.log')]
            windows = {'steady': [r for r in all_rows if r[0] > 240]}
            if scene == 'swim': windows['moving'] = [r for r in all_rows if 60 < r[0] <= 150]
            result['scenes'][scene][phase] = {name: {k:metric([r[i] for r in rows]) for k,i in COLUMNS.items()} for name,rows in windows.items()}
            if a.gpu:
                gpu=[]; zones={}
                for repeat in range(a.repeats):
                    for line in (a.output/f'{scene}-{phase}-{repeat}/run.log').read_text().splitlines():
                        if not line.startswith('gpu frame:') or int(line.split()[2]) <= 240: continue
                        row=line.split(); gpu.append(float(row[-1]))
                        for i in range(3,len(row)-2,2): zones.setdefault(row[i],[]).append(float(row[i+1]))
                assert gpu
                result['scenes'][scene][phase]['gpu'] = dict(total=metric(gpu), zone_mean_ms={k:sum(v)/len(gpu) for k,v in zones.items()})
    if not a.gpu:
        cpu = {}
        producer = {}
        for scene in a.scenes:
            for window in result['scenes'][scene]['before']:
                before = result['scenes'][scene]['before'][window]['callback_thread']['p99']
                after = result['scenes'][scene]['after'][window]['callback_thread']['p99']
                cpu[f'{scene}/{window}'] = dict(delta_ms=after-before, passed=after <= before)
            if scene in ['forest','camp']:
                after = result['scenes'][scene]['after']['steady']['producer_interval']['p99']
                producer[scene] = dict(p99_ms=after, budget_ms=16.7, passed=after <= 16.7)
        result['acceptance'] = dict(cpu=cpu, producer=producer,
            cpu_nonregression_all=all(v['passed'] for v in cpu.values()),
            fixed_scene_producer_budget_all=all(v['passed'] for v in producer.values()))
    (a.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('before',type=Path); ap.add_argument('after',type=Path); ap.add_argument('output',type=Path)
    ap.add_argument('--scenes',nargs='+',choices=SCENES,default=list(SCENES))
    ap.add_argument('--repeats',type=int,default=3); ap.add_argument('--frames',type=int,default=720)
    ap.add_argument('--gpu',action='store_true'); ap.add_argument('--report-only',action='store_true')
    ap.add_argument('--locked',action='store_true',help=argparse.SUPPRESS); ap.add_argument('--repeat',type=int,default=0,help=argparse.SUPPRESS)
    a=ap.parse_args(); a.output=a.output.resolve(); a.before=a.before.resolve(); a.after=a.after.resolve()
    assert a.output.is_relative_to(ROOT/'build') and 1 <= a.repeats <= 4 and a.frames >= 360 and a.frames % 120 == 0
    a.output.mkdir(parents=True,exist_ok=True)
    if a.locked: pair(a); return
    if not a.report_only:
        for repeat in range(a.repeats):
            for scene in a.scenes:
                command=['flock','/tmp/botw-render.lock','timeout','175',sys.executable,str(Path(__file__).resolve()),str(a.before),str(a.after),str(a.output),
                         '--scenes',scene,'--repeat',str(repeat),'--repeats',str(a.repeats),'--frames',str(a.frames),'--locked']
                if a.gpu: command.append('--gpu')
                subprocess.run(command,cwd=ROOT,check=True)
    r=report(a)
    for scene in a.scenes:
        for phase in ['before','after']:
            for window,values in r['scenes'][scene][phase].items():
                if window != 'gpu': print(scene,phase,window,'CPU p99',values['callback_thread']['p99'],'producer p99',values['producer_interval']['p99'])

if __name__ == '__main__': main()
