#!/usr/bin/env python3
"""Build observational frozen-source probes; benchmark helper owns all render locks.

prepare PHASE: sources are build/round70/{before,after}/game (or current after).
capture PHASE: exact X11, native Wayland and mailbox diagnostics at large output.
queue PHASE: disable the queue bound in a separate exact X11 diagnostic.
"""
from pathlib import Path
import os,sys,subprocess,shutil,json,hashlib
ROOT=Path(__file__).resolve().parents[1];os.chdir(ROOT)
phase=sys.argv[2];out=ROOT/'build/round70'/('present-'+phase);out.mkdir(parents=True,exist_ok=True)
if sys.argv[1]=='prepare':
 game=out/'game'
 if game.exists():shutil.rmtree(game)
 source=ROOT/'build/round70'/phase/'game'
 if not source.exists():
  assert phase!='before','Freeze baseline first with round70_sword_check.py before'
  source=ROOT/'game'
 shutil.copytree(source,game)
 manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(game.glob('*.jo'))}
 (out/'sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
 # Timers around the actual GL instance submission, not inferred from byte counts.
 p=game/'gfx.jo';s=p.read_text();old='    glBufferData(GL_ARRAY_BUFFER, max(items.len(), 1) * size_of(I), data(items) as *u8, GL_DYNAMIC_DRAW)'
 assert s.count(old)==1
 s=s.replace(old,'''    probe_started = time()
'''+old+'''
    probe_ms = (time()-probe_started)*1000.0
    if probe_ms>1.0: eprint("probe upload: frame {frame_number()} wall {probe_ms:.3} bytes {items.len()*size_of(I)} previous {b.count*b.stride}")''')
 p.write_text(s)
 # Observe target lifetime directly where allocations occur.
 p=game/'post.jo';s=p.read_text().replace('    if w != post.w or h != post.h:', '    if w != post.w or h != post.h:\n        eprint("probe scene resize: frame {frame_number()} {post.w}x{post.h} -> {w}x{h}")',1);p.write_text(s)
 p=game/'fx.jo';s=p.read_text().replace('    if __smoke_rt.w != w or __smoke_rt.h != h:', '    if __smoke_rt.w != w or __smoke_rt.h != h:\n        eprint("probe smoke resize: frame {frame_number()} {__smoke_rt.w}x{__smoke_rt.h} -> {w}x{h}")',1);p.write_text(s)
 source=f'''build:
    opt = release
use '{game}/main.jo'
use '{game}/gpuqueue.jo'
from '{game}/gpuqueue.jo' import __gpu_queue_ok
use '{game}/gfx.jo'
use '{game}/post.jo'
use '{ROOT}/tools/performance_output.jo'
if env("PROBE_NO_QUEUE")!=none: __gpu_queue_ok=false
probe_lines=""
probe_draw=():
    draw()
    probe_lines+="probe memory: {{frame_number()}} {{alloc_count()}} {{post.w}} {{post.h}}\\n"
    if frame_number()%120==119:
        eprint(probe_lines)
        probe_lines=""
main=():
    if env("PROBE_NATIVE")!=none: __game_run(update,probe_draw)
    else: performance_output_run(update,probe_draw)
'''
 (out/'probe.jo').write_text(source)
 subprocess.run(['sloppy/bin/sloppy','build',str(out/'probe.jo'),'-o',str(out/'probe')],check=True)
else:
 queue_test=sys.argv[1]=='queue'
 assert sys.argv[1] in ('capture','queue')
 for mode in (['gpu'] if queue_test else ['gpu','paced','mailbox']):
  dest=out/(mode+'-noqueue' if queue_test else mode)
  dest.mkdir(parents=True,exist_ok=True)
  (dest/'probe-settings.json').write_text(json.dumps({'queue_disabled':queue_test,'native_loop':mode!='gpu'},indent=2)+'\n')
  # The benchmark owns one flock per render; native Wayland obtains its output
  # from the compositor. X11 probe forces and checks exact client dimensions.
  e={k:v for k,v in os.environ.items() if not k.startswith('PROBE_')}
  if queue_test:e['PROBE_NO_QUEUE']='1'
  if mode!='gpu':e['PROBE_NATIVE']='1'
  cmd=['python3','tools/performance_bench.py','capture',str(out/'probe'),str(dest),'--revision',phase,'--views','forest','--frames','2400','--repeats','1','--window','2133x1200','--scale','1','--mode',mode,'--cpu-trace','--cpu-trace-ms','6','--gpu-frame-trace']
  if mode=='gpu':cmd+=['--exact-output']
  subprocess.run(cmd,env=e,check=True)
