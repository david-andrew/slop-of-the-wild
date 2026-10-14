#!/usr/bin/env python3
"""Round 67 material and geometry evidence. Owns one flock per render; never wrap.

Freeze a complete source copy before editing; performance reuses three alternating
full production runs through the existing CPU/draw audit. Each two-render timing pair releases the shared render lock. All evidence stays in build.
"""
import argparse, hashlib, json, math, os, shutil, statistics, subprocess, sys, time
sys.dont_write_bytecode = True
from pathlib import Path
from PIL import Image, ImageDraw
import round82_critic_capture as capture
capture.OUT = capture.ROOT / 'build/round67-sol3'
pair_deadline = 0.0
capture.SCENES = {
    'temple': (300, dict(BOTW_SKIP='1', BOTW_CAM='-802,237,1900,-2.967,-0.14')),
    'ivy-detail': (250, dict(BOTW_SKIP='1', BOTW_CAM='-819.8,225.2,1963.8,-2.967,0.0')),
    'ivy': (250, dict(BOTW_SKIP='1', BOTW_CAM='-811,230,1938,-2.967,0.1')),
    'husks': (120, dict(BOTW_SKIP='1', BOTW_CAM='-852,222,1918,2.6,-0.4')),
    'cliffs': (300, dict(BOTW_SKIP='1', BOTW_CAM='-1600,235,1815,1.2,-0.15')),
    'waterfall': (300, dict(BOTW_SKIP='1', BOTW_CAM='-1660,175,1888,1.24,-0.05')),
    'pool': (300, dict(BOTW_SKIP='1', BOTW_CAM='-1535,120,1823,1.5707963,-0.3')),
    'snow': (150, dict(BOTW_SKIP='1', BOTW_AT='-1060,2230,2.0')),
    'passage250': (250, dict(BOTW_PASSAGE='1', SLOPPY_INPUT='20:w+')),
    'passage450': (450, dict(BOTW_PASSAGE='1', SLOPPY_INPUT='20:w+')),
    'swim': (180, dict(BOTW_SKIP='1', BOTW_AT='-1161,1684,-0.9', SLOPPY_INPUT='10:w+')),
    'cliff-placement': (120, dict(BOTW_SKIP='1', BOTW_AT='-1652,1752')),
    'cliff-placement-east': (120, dict(BOTW_SKIP='1', BOTW_AT='-1625,1752')),
}

def prepare(label, revision=None):
    source = capture.OUT / label / 'game'
    source.mkdir(parents=True, exist_ok=True)
    for path in (capture.ROOT / 'game').glob('*.jo'):
        assert not path.is_symlink()
        if revision:
            (source/path.name).write_bytes(subprocess.check_output(['git','show',f'{revision}:game/{path.name}'],cwd=capture.ROOT))
        else: shutil.copy2(path, source / path.name)
    # The current entry point defines main explicitly; the legacy helper adds
    # its own pinned-X11 main. Rename only in this frozen evidence copy.
    main = source / 'main.jo'
    main.write_text(main.read_text().replace('main = ():', 'production_main = ():'))
    capture.prepare(label, source)
    (capture.OUT/f'{label}-provenance.json').write_text(json.dumps(dict(revision=revision or subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),worktree=subprocess.check_output(['git','status','--short'],text=True),seed=64),indent=2)+'\n')

def pairs():
    for scene in capture.SCENES:
        folder = capture.OUT / scene
        if not all((folder / (p+'.png')).exists() for p in ['before', 'after']): continue
        sheet = Image.new('RGB', (1920,564), (24,27,30))
        for k, label in enumerate(['before','after']):
            im=Image.open(folder/(label+'.png')); im.thumbnail((960,540))
            sheet.paste(im,(k*960,24))
            ImageDraw.Draw(sheet).text((k*960+12,6),label,fill='white')
        sheet.save(folder/'review-pair.png')

def binary_for(phase, scene):
    label = os.environ.get('R66_CANDIDATE','after') if phase=='after' else os.environ.get('R66_BASELINE','before')
    return capture.OUT/f'{label}-game'

def run(phase, scene, repeat=None, force=False, readonly=False):
    frame, flags = capture.SCENES[scene]
    folder = capture.OUT / scene if repeat is None else capture.OUT / os.environ.get('R66_TIMINGS_NAME','performance-after')
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / phase if repeat is None else folder / f'{scene}-{phase}-{repeat}'
    binary = binary_for(phase,scene)
    settings = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'ROUND82_', 'R66_'))}
    settings.update(BOTW_NO_PREPARED_ASSETS='1', BOTW_SCALE='1', BOTW_HOUR='11', BOTW_WEATHER='clear', BOTW_NOVSYNC='1', BOTW_FRAME_LOG='1', SLOPPY_VSYNC='0', SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='1280x720', SLOPPY_FRAMES=str(frame if repeat is None else 1440), SLOPPY_SCREENSHOT=str(dest.with_suffix('.png')), ROUND82_SCENE=scene)
    settings.update(flags)
    settings['R66_CONTEXT_DRAIN_SECONDS'] = '3'
    if repeat is not None:
        settings['R66_PAIR_SHA256'] = hashlib.sha256(binary_for('after',scene).read_bytes()).hexdigest()
        settings['LD_AUDIT'] = str(capture.OUT / 'draw-audit.so')
        settings['R66_CPU_CORE'] = 'all' if os.environ.get('R66_PRODUCTION_AFFINITY')=='1' else os.environ.get('R66_CPU_CORE','2')
    if os.environ.get('R66_TRACE')=='1': settings.update(BOTW_CPU='1',BOTW_CPU_TRACE_MS='2')
    window_tool='tools/performance_window.py'
    if repeat is not None and os.environ.get('R66_PRODUCTION_AFFINITY')!='1':
        # Apply affinity after the first complete production frame. Startup
        # shader/driver/audio workers then keep the inherited full CPU set.
        settings['R66_PIN_STAGE'] = 'after-first-frame'
        settings['R66_LOG'] = str(dest.with_suffix('.log'))
        window_source=(capture.ROOT/window_tool).read_text()
        anchor="        last_geometry = None"
        assert window_source.count(anchor)==1
        window_source=window_source.replace(anchor,anchor+"\n        pinned=False")
        anchor="        while proc.poll() is None:\n            root, gx, gy"
        assert window_source.count(anchor)==1
        window_source=window_source.replace(anchor,"        while proc.poll() is None:\n            if not pinned and 'first frame:' in Path(child_env['R66_LOG']).read_text():\n                core=int(child_env['R66_CPU_CORE'])\n                game_pid=owner_pid(wid)\n                os.sched_setaffinity(game_pid,{core})\n                pinned=True\n                print(f'benchmark steady main-thread affinity: PID {game_pid} core {core}',flush=True)\n            root, gx, gy")
        window_source=window_source.replace("        status = proc.wait()","        status = proc.wait()\n        if status == 0: assert pinned, 'steady-state affinity applied'")
        window_tool=str(capture.OUT/'affinity-window.py')
        Path(window_tool).write_text(window_source)
    if repeat is not None and os.environ.get('R66_PRODUCTION_AFFINITY')=='1': settings['R66_PIN_STAGE']='production-default'
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    meta = dest.with_suffix('.json')
    old = json.loads(meta.read_text()) if meta.exists() else {}
    valid = old.get('sha256') == digest and dest.with_suffix('.png').exists() and all(old.get('settings',{}).get(k)==v for k,v in settings.items() if k.startswith(('BOTW_', 'SLOPPY_', 'ROUND82_', 'LD_AUDIT','R66_')))
    if readonly: assert valid, f'{scene} {phase} {repeat}: finish current paired sample first'
    if not valid or force:
        if meta.exists():
            archive=folder/'history'/f'{dest.name}-{time.time_ns()}'
            archive.mkdir(parents=True,exist_ok=True)
            for suffix in ['.png','.json','.log']:
                if dest.with_suffix(suffix).exists(): shutil.copy2(dest.with_suffix(suffix),archive/(dest.name+suffix))
        # Give the previous context's deferred driver allocations time to retire.
        time.sleep(3)
        with dest.with_suffix('.log').open('w') as log:
            subprocess.run(['timeout',str(max(1,int(pair_deadline-time.monotonic()))),'python3', window_tool, '1280x720', 'timeout', '180', str(binary)], env=settings, stdout=log, stderr=subprocess.STDOUT, check=True)
        assert Image.open(dest.with_suffix('.png')).size==(1280,720)
        meta.write_text(json.dumps(dict(sha256=digest,settings={k:v for k,v in settings.items() if k.startswith(('BOTW_', 'SLOPPY_', 'ROUND82_', 'LD_AUDIT','R66_'))}),indent=2))
    assert hashlib.sha256(binary.read_bytes()).hexdigest()==digest
    print('PASS', scene, phase, repeat, 'retained' if valid and not force else 'rendered', flush=True)
    if repeat is None: return
    rows = [list(map(float,line.split()[2:])) for line in dest.with_suffix('.log').read_text().splitlines() if line.startswith('frame sample:')]
    assert len(rows)==1440
    selected=[r for r in rows if r[0]>=361]
    p99=lambda col: sorted(r[col] for r in selected)[math.ceil(len(selected)*.99)-1]
    draws=[int(line.split()[3]) for line in dest.with_suffix('.log').read_text().splitlines() if line.startswith('draw sample:')]
    assert len(draws)>=1440 and max(draws)>100, 'measure full production draw workload'
    return dict(thread_p99_ms=p99(4),wall_p99_ms=p99(2),frame_p99_ms=p99(1),samples=len(selected),draws_min=min(draws[-1080:]),draws_max=max(draws[-1080:]))

def compare(scene, benchmark=False, repeats=3):
    global pair_deadline
    if not benchmark: assert os.environ.get('R66_LOCKED')=='1', 'internal pair requires parent render lock'
    if pair_deadline == 0.0: pair_deadline = time.monotonic()+145
    if not benchmark:
        for phase in ['before','after']: run(phase,scene)
        pairs()
        return
    runs={p:[] for p in ['before','after']}
    # Every baseline metadata record also carries the paired candidate hash.
    # A changed candidate therefore invalidates both halves of each pair.
    # Aggregation is read-only; each two-render pair owns a separate short lock.
    for repeat in range(repeats):
        for phase in ['before','after']:
            runs[phase].append(run(phase,scene,repeat,readonly=True))
    report={p:{k:statistics.median(r[k] for r in runs[p]) for k in runs[p][0]} for p in runs}
    report.update(runs=runs,protocol=f'1440 fixed production frames; 360 warmup; {repeats} alternating paired run(s); {"production CPU affinity" if os.environ.get("R66_PRODUCTION_AFFINITY")=="1" else "main thread pinned to core 2 after first production frame"}; nearest-rank CPU p99; tolerance 3% + 0.10 ms',binary_sha256={p:hashlib.sha256(binary_for(p,scene).read_bytes()).hexdigest() for p in runs})
    report['passed']=report['after']['thread_p99_ms']<=report['before']['thread_p99_ms']*1.03+.1
    (capture.OUT/os.environ.get('R66_TIMINGS_NAME','performance-after')/f'{scene}-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS' if report['passed'] else 'FAIL',scene,'CPU p99',report['before']['thread_p99_ms'],report['after']['thread_p99_ms'],flush=True)
    assert report['passed'], 'paired CPU p99 budget'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['prepare','capture','performance','pairs','compare','profile','_pair','_bench','_bench_pair','_profile'])
    p.add_argument('label',nargs='?',default='after',type=capture.label_name)
    p.add_argument('scenes',nargs='*')
    p.add_argument('--ref',help='freeze a historical game tree, e.g. ac429c6 for the baseline')
    p.add_argument('--batch-scenes',type=int,choices=[1,2,3],default=2)
    p.add_argument('--baseline',default='before',type=capture.label_name)
    p.add_argument('--production-affinity',action='store_true',help='use normal scheduler placement instead of the diagnostic core-2 pin')
    p.add_argument('--timings-name',default='performance-after',type=capture.label_name)
    p.add_argument('--repeats',type=int,choices=[1,3,5],default=3)
    p.add_argument('--repeat',type=int,choices=range(5),default=0)
    a=p.parse_args()
    if a.mode=='prepare': prepare(a.label,a.ref)
    elif a.mode=='capture': capture.capture(a.label,a.scenes or list(capture.SCENES))
    elif a.mode=='pairs': pairs()
    elif a.mode=='_profile':
        pair_deadline=time.monotonic()+145
        for phase in ['before','after']: run(phase,a.label,99,force=True)
    elif a.mode=='_bench_pair':
        assert os.environ.get('R66_LOCKED')=='1'
        pair_deadline=time.monotonic()+85
        for phase in (['before','after'] if a.repeat%2==0 else ['after','before']): run(phase,a.label,a.repeat)
    elif a.mode in ['_pair','_bench']:
        for scene in [a.label]+a.scenes: compare(scene,a.mode=='_bench')
    else:
        os.environ['R66_BASELINE'] = a.baseline
        os.environ['R66_CANDIDATE'] = a.label
        os.environ['R66_TIMINGS_NAME'] = a.timings_name
        os.environ['R66_PRODUCTION_AFFINITY'] = '1' if a.production_affinity else '0'
        scenes=a.scenes or (['temple','ivy-detail','husks','cliffs','waterfall','pool','snow','passage250','passage450','swim','cliff-placement','cliff-placement-east'] if a.mode=='performance' else list(capture.SCENES))
        if a.mode in ['performance','profile']: batches=[[s] for s in scenes]
        else:
            pending=[]
            for scene in scenes:
                valid=True
                for phase in ['before','after']:
                    meta=capture.OUT/scene/(phase+'.json')
                    data=json.loads(meta.read_text()) if meta.exists() else {}
                    digest=hashlib.sha256(binary_for(phase,scene).read_bytes()).hexdigest()
                    valid = valid and data.get('sha256')==digest and (capture.OUT/scene/(phase+'.png')).exists()
                if not valid: pending.append(scene)
            batches=[pending[i:i+a.batch_scenes] for i in range(0,len(pending),a.batch_scenes)]
        failed=[]
        for batch in batches:
            settings=os.environ|dict(R66_LOCKED='1',R66_TRACE='1' if a.mode=='profile' else '0')
            if a.mode=='performance':
                for repeat in range(a.repeats):
                    try:
                        for phase in ['before','after']: run(phase,batch[0],repeat,readonly=True)
                    except AssertionError:
                        subprocess.run(['flock','/tmp/botw-render.lock','timeout','90',sys.executable,__file__,'_bench_pair',batch[0],'--repeat',str(repeat)],env=settings,check=True)
                try: compare(batch[0],True,a.repeats)
                except AssertionError:
                    failed.append(batch[0])
            else:
                subprocess.run(['flock','/tmp/botw-render.lock','timeout','150',sys.executable,__file__,'_profile' if a.mode=='profile' else '_pair',*batch],env=settings,check=True)
        if failed: raise SystemExit('CPU budgets need investigation: '+', '.join(failed))
