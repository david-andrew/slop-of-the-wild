#!/usr/bin/env python3
"""Headless critic-manifest and real runner scheduling/CLI regression checks."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
from critic_pack import SCENES, FAST_CHECKS, note_name, percentiles
ROOT = Path(__file__).resolve().parents[1]


def main():
    shots = [(area, name, frame) for area, name, frames, _, _ in SCENES for frame, _ in frames]
    assert 38 <= len(shots) <= 46 and len(shots) == len(set(shots))
    names = {name for _, name, _ in shots}
    assert {f'shrine-{n}' for n in range(1,5)} <= names
    assert {'wake','passage','title','forest','waterfall','pool','temple','roof','husks','snow','firs','dawn','golden','night','storm','rain','camp','grass-fire','tent-fire','body-fire','boar','bird','swim','climb','glide','map','inventory','options'} <= names
    assert [f for _,n,f in shots if n=='camp'] == [300,420,640]
    assert [f for _,n,f in shots if n=='tent-fire'] == [900]
    assert note_name(60)=='C4' and note_name(61)=='C#4' and note_name(21)=='A0'
    assert percentiles([1,2,3,26]) == dict(p50=2,p99=26,worst=26,frames_over_25ms=1,samples=4)
    print(f'PASS critic manifest: {len(shots)} fixed shots, all scored areas, note conversion and nearest-rank tails')

    scratch = ROOT / 'build/tooling-check'
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as directory:
        root = Path(directory)
        source = root/'model.jo'
        game = os.path.relpath(ROOT/'game',root)
        (root/'shared.jo').write_text(f"use '{game}/items.jo'\nseed_items = (): items_init()\n")
        source.write_text(f'''use '{game}/skel.jo'
use '{game}/save.jo'
use '{game}/items.jo'
use 'shared.jo'
import '{game}/physics.jo' as ph
seed_items()
assert(idefs.len()>0 and item("apple").name=="Apple")
m=load_model("assets/models/hero.mdl")
assert(m.ok and m.parts.len()>0)
assert(__win_open and __soft and not __vk and __xdpy==null)
assert(save_allowed())
assert(ph.colliders.len()==0)
print("PASS shared module state, import aliases, CPU model data, no display/device/window, unchanged save gate")
''')
        subprocess.run([sys.executable,str(ROOT/'tools/headless_build.py'),str(source),'-o',str(root/'model')],cwd=ROOT,check=True)
        subprocess.run([str(root/'model')],cwd=ROOT,check=True)
        flags = next(s[3] for s in SCENES if s[1]=='swim')
        x,z,yaw = map(float,flags['BOTW_AT'].split(','))
        pond = root/'pond.jo'
        pond.write_text(''.join(f"use '{game}/{name}.jo'\n" for name in ['gfx','water','worldgen','structures','interiors','terrain','terrain_assets','water_render','player','camera','input'])+f'''
worldgen_load()
structures_pads()
sor_pads()
worldgen_finish()
terrain_asset_load()
water_build()
level=water_level({x},{z})!
assert(water_depth({x},{z})>1.4,"critic swim start must be deep water")
pl=Player(pos=v3({x},level-SWIM_FOOT_DEPTH,{z}),state=.swim,grounded=false,water_y=level)
cam=Cam(yaw={yaw})
cam_yaw_global={yaw}
loop frame in [0..180):
    act=Actions(move=(if frame>=10:vec2(0,1) else:vec2(0,0)))
    player_update(1.0/60.0)
    camera_update(1.0/60.0)
assert(pl.state==.swim,"critic swimming through capture frame")
print("PASS critic swim fixture: real prepared pond, production movement, swimming at frame 180")
''')
        subprocess.run([sys.executable,str(ROOT/'tools/headless_build.py'),str(pond),'-o',str(root/'pond')],cwd=ROOT,check=True)
        subprocess.run([str(root/'pond')],cwd=ROOT,env=os.environ.copy()|dict(BOTW_ASSET_CHECK='1'),check=True)
        (root/'tools').mkdir()
        (root/'bin').mkdir()
        original = (ROOT/'tools/run_all_checks.sh').read_text()
        prefix = original.split('# Headless tests;',1)[0]
        footer = original[original.rindex('\nflush_cpu\nif $list;'):]
        # Exercise the production queue/collector/CLI verbatim with cheap workers.
        calls = ''.join(f'check cpu worker_{n} python3 tools/worker.py worker_{n}\n' for n in range(8))
        calls += 'check render render_barrier python3 tools/worker.py render_barrier\n'
        (root/'tools/run_all_checks.sh').write_text(prefix+calls+footer)
        (root/'tools/run_all_checks.sh').chmod(0o755)
        (root/'tools/worker.py').write_text('''import fcntl,json,os,sys,time
from pathlib import Path
name=sys.argv[1]
def event(kind):
    with open('events.jsonl','a') as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        f.write(json.dumps(dict(name=name,event=kind,t=time.monotonic(),tmp=os.environ['TMPDIR']))+'\\n')
event('start')
time.sleep(.15 if name!='worker_0' else .25)
print('0 FAIL expected summary')
if os.environ.get('FIXTURE_FAIL')==name: print('FAIL real zero-exit failure')
event('end')
''')
        (root/'bin/git').write_text('#!/bin/bash\ncase "$1" in rev-parse) echo fixed-test-head;; status|diff) :;; *) exit 1;; esac\n')
        (root/'bin/nproc').write_text('#!/bin/bash\necho 6\n')
        # No renderer here: fake flock avoids competing for the shared render lock.
        (root/'bin/flock').write_text('#!/bin/bash\nshift\nexec "$@"\n')
        for path in (root/'bin').iterdir(): path.chmod(0o755)
        env = os.environ.copy() | dict(PATH=str(root/'bin')+':'+os.environ['PATH'])
        def run(*args, fail=None):
            if (root/'events.jsonl').exists(): (root/'events.jsonl').unlink()
            process = subprocess.run(['tools/run_all_checks.sh',*args],cwd=root,env=env|({'FIXTURE_FAIL':fail} if fail else {}),text=True,capture_output=True)
            events = [json.loads(line) for line in (root/'events.jsonl').read_text().splitlines()] if (root/'events.jsonl').exists() else []
            active, peak = set(), 0
            for event in events:
                if event['event']=='start':
                    if event['name']=='render_barrier': assert not active, 'render started with CPU work active'
                    active.add(event['name'])
                    peak=max(peak,len(active))
                else: active.remove(event['name'])
            assert not active
            return process,events,peak
        serial, _, peak = run('-j','1')
        assert serial.returncode==0 and peak==1, serial.stderr+serial.stdout
        parallel, events, peak = run('-j','3',fail='worker_3')
        assert parallel.returncode==1 and peak==3, parallel.stderr+parallel.stdout
        assert 'SUMMARY: 8 PASS, 1 FAIL, 9 total;' in parallel.stdout
        assert len({e['tmp'] for e in events})==9, 'worker scratch must be separate'
        out=Path(re.search(r'^Evidence: (.+)$',parallel.stdout,re.M)[1])
        rows=out.joinpath('results.tsv').read_text().splitlines()
        assert len(rows)==9 and 'worker_3\tFAIL\t1' in rows
        assert all((out/f'worker_{n}.log').exists() for n in range(8))
        resumed,events,peak=run('--resume',str(out),'-j','2')
        assert resumed.returncode==0 and {e['name'] for e in events}=={'worker_3'}, resumed.stderr+resumed.stdout
        assert 'SUMMARY: 9 PASS, 0 FAIL, 9 total;' in resumed.stdout
        assert len(out.joinpath('results.tsv').read_text().splitlines())==9
        default,_,peak=run()
        assert default.returncode==0 and peak==3
        listed,events,_=run('--list','-j2')
        assert listed.returncode==0 and not events and len(listed.stdout.splitlines())==9
        only,events,_=run('-j2','--only','worker_1')
        assert only.returncode==0 and {e['name'] for e in events}=={'worker_1'}
        for args in [('-j','0'),('-j','bad'),('--only','unknown'),('--only',''),('--list','--only','worker_1'),('--resume',)]:
            process,_,_=run(*args)
            assert process.returncode==2, (args,process.returncode,process.stderr)
        print('PASS runner: bounded/default/serial concurrency, render barrier, isolated logs/tmp, zero-exit failure detection, results.tsv, list/only/resume and invalid arguments')
    assert set(FAST_CHECKS) <= set(subprocess.check_output(['tools/run_all_checks.sh','--list'],cwd=ROOT,text=True).split())
    print('PASS fast check manifest entries remain registered')


if __name__=='__main__': main()
