#!/usr/bin/env python3
"""Adjacent before/after runs in bounded self-locking pairs; retain every tail."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
SCENES={
    'forest':dict(BOTW_AT='-1000,1620,3.14'),
    'camp':dict(BOTW_AT='-1439,1606,0',BOTW_GIVE='travelers_sword,travelers_shield',SLOPPY_INPUT='1:k+,1:w+,150:j+,151:j-,165:j+,166:j-,195:j+,196:j-,200:w-,225:j+,226:j-,255:j+,256:j-'),
    'swim':dict(BOTW_AT='-1161,1684,-0.9',SLOPPY_INPUT='10:w+'),
}

def percentile(v,p=.99):return sorted(v)[math.ceil(len(v)*p)-1]

def samples(path):
    return [[float(x) for x in line.split()[2:]] for line in path.read_text().splitlines() if line.startswith('frame sample:') and int(line.split()[2])>240]


def run_pair(a):
    for phase in (['before','after'] if a.repeat%2==0 else ['after','before']):
        exe=getattr(a,phase).resolve()
        stem=f'{a.scene}-{phase}-{a.repeat}'
        env={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_','CP_'))}
        env.update(BOTW_SKIP='1',BOTW_HOUR='11',BOTW_TIMESCALE='0',BOTW_WEATHER='clear',BOTW_SCALE='1',BOTW_FRAME_LOG='1',BOTW_LOADTIME='1',
            SLOPPY_VULKAN='1',SLOPPY_PLATFORM='x11',SLOPPY_VSYNC='0',SLOPPY_WINDOW='1920x1080',SLOPPY_FRAMES='720',SLOPPY_SCREENSHOT=str(a.output/f'{stem}.png'))
        env.update(SCENES[a.scene])
        if a.trace:env.update(BOTW_CPU='1',BOTW_CPU_TRACE_MS='8')
        command=[sys.executable,str(ROOT/'tools/performance_window.py'),'--visible','1920x1080','timeout','90',str(exe)]
        (a.output/f'{stem}.settings.json').write_text(json.dumps(dict(command=command,environment={k:v for k,v in env.items() if k.startswith(('BOTW_','SLOPPY_'))},binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),load_start=Path('/proc/loadavg').read_text().strip()),indent=2)+'\n')
        with (a.output/f'{stem}.log').open('w') as log:subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        rows=samples(a.output/f'{stem}.log')
        assert len(rows)==480
        print(stem,'CPU p99',percentile([r[4] for r in rows]),'interval p99',percentile([r[1] for r in rows]),flush=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('before',type=Path)
    ap.add_argument('after',type=Path)
    ap.add_argument('output',type=Path)
    ap.add_argument('--scene',choices=SCENES)
    ap.add_argument('--repeat',type=int,default=0)
    ap.add_argument('--repeats',type=int,default=2)
    ap.add_argument('--start-repeat',type=int,default=0)
    ap.add_argument('--trace',action='store_true')
    ap.add_argument('--locked',action='store_true',help=argparse.SUPPRESS)
    a=ap.parse_args();a.output=a.output.resolve()
    assert a.output.is_relative_to(ROOT/'build')
    a.output.mkdir(parents=True,exist_ok=True)
    if a.locked:
        assert a.scene is not None
        run_pair(a);return
    assert 0 <= a.start_repeat < a.repeats <= 4
    for repeat in range(a.start_repeat,a.repeats):
        for scene in ([a.scene] if a.scene else SCENES):
            command=['flock','/tmp/botw-render.lock','timeout','150',sys.executable,str(Path(__file__).resolve()),str(a.before.resolve()),str(a.after.resolve()),str(a.output),'--locked','--scene',scene,'--repeat',str(repeat)]
            if a.trace:command.append('--trace')
            subprocess.run(command,cwd=ROOT,check=True)
    result={'protocol':'adjacent X11 Vulkan immediate/mailbox-preference before/after pairs, reversed in odd repeats; managed 1920x1080, full scale, fixed seeds/hour/weather/inputs and 1/60s simulation; discard only initial 240 frames; nearest-rank pooled p99; every tail retained; one render lock per bounded pair','scenes':{}}
    for scene in ([a.scene] if a.scene else SCENES):
        result['scenes'][scene]={}
        for phase in ['before','after']:
            rows=[r for n in range(a.repeats) for r in samples(a.output/f'{scene}-{phase}-{n}.log')]
            result['scenes'][scene][phase]=dict(callback_cpu_p99_ms=percentile([r[4] for r in rows]),interval_p99_ms=percentile([r[1] for r in rows]),samples=len(rows))
        b,c=(result['scenes'][scene][p] for p in ['before','after'])
        result['scenes'][scene]['cpu_p99_delta_ms']=c['callback_cpu_p99_ms']-b['callback_cpu_p99_ms']
    (a.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
