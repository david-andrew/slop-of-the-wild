#!/usr/bin/env python3
"""Round 68 fixed captures, AB/BA CPU comparisons, and full-pack review sheets.

Owns one render flock per run; never wrap this script in a render flock.
Frozen fixture sources and all evidence stay under this checkout's build/.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from PIL import Image, ImageDraw
import critic_pack as pack

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('TASK68_OUT', ROOT / 'build/task68-astra')).resolve()
assert OUT.is_relative_to(ROOT / 'build'), 'evidence must stay under build/'
SCENES = {name: (frames, flags, name) for _, name, frames, flags, _ in pack.SCENES
          if name in ('wake', 'golden', 'rain', 'boar', 'bird', 'bird-flight', 'swim')}
SCENES['wake'] = ([(330, 'Wake pigment'), (420, 'Wake chamber'), (520, 'Wake standing')], {}, 'wake')
SCENES['swim'] = ([(180, 'Swim'), (220, 'Submerged legs')], SCENES['swim'][1], 'swim')
SCENES['pond-rain'] = ([(300, 'Pond rain')], dict(BOTW_SKIP='1', BOTW_AT='-1190,1665,-0.9', BOTW_WEATHER='rain'), 'pond-rain')


def prepare(phase, ref):
    folder = OUT / phase
    game = folder / 'game'
    scripts = folder / 'tools'
    game.mkdir(parents=True, exist_ok=True)
    scripts.mkdir(exist_ok=True)
    for path in (ROOT / 'game').glob('*.jo'):
        content = subprocess.check_output(['git', 'show', f'{ref}:game/{path.name}'], cwd=ROOT) if ref else path.read_bytes()
        (game / path.name).write_bytes(content)
    shutil.copyfile(ROOT / 'tools/performance_output.jo', scripts / 'performance_output.jo')
    source = (game / 'main.jo').read_text()
    source = source.replace('update = (dt0: f64):', 'production_update = (dt0: f64):').replace('\ndraw = ():', '\nproduction_draw = ():')
    source = source.replace('main = (): game_run(update, draw)', '')
    extension = pack.FIXTURE.replace("'{root}/tools/performance_output.jo'", "'../tools/performance_output.jo'").replace("'{game}/", "'")
    extension = extension.replace('draw = ():\n    production_draw()', '''from 'fx.jo' import __pinst_alpha

draw = ():
    production_draw()
    if frame_number() == 300 and (cp_scene == "rain" or cp_scene == "pond-rain"):
        near = 0
        far = 0
        opacity = 0.0
        loop drop in __pinst_alpha:
            if drop.data.y != 4.0 or drop.data.w <= 0.0: continue
            clip = sc.vp * vec4(drop.pos.xyz, 1)
            if clip.w <= 0.0 or abs(clip.x) > clip.w or abs(clip.y) > clip.w: continue
            if length(drop.pos.xyz-sc.cam) < 12.0:
                near += 1
                opacity += f64(drop.color.w)
            else: far += 1
        eprint("rain visible: near={near} far={far} mean-opacity={opacity/f64(max(near,1)):.6}")''')
    fixture = game / 'main.jo'
    fixture.write_text(source + extension)
    with (folder / 'build.log').open('w') as log:
        subprocess.run(['sloppy/bin/sloppy', 'build', str(fixture), '-o', str(folder / 'capture')], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    (folder / 'sources.json').write_text(json.dumps({p.name: pack.digest(p) for p in game.glob('*.jo')}, indent=2)+'\n')


def run(phase, scene, folder, performance=False, locked=False):
    folder.mkdir(parents=True, exist_ok=True)
    frames, flags, cp_scene = SCENES[scene]
    binary = OUT / (os.environ.get('TASK68_CANDIDATE', 'after') if performance and phase=='after' else phase) / 'capture'
    total = 1440 if performance else max(f for f, _ in frames)+1
    size = '1920x1080' if performance else '1280x720'
    settings = pack.BASE | flags | dict(CP_SCENE=cp_scene, CP_FRAMES='0' if performance else ','.join(str(f) for f, _ in frames),
        CP_OUT=str(folder), SLOPPY_FRAMES=str(total), SLOPPY_WINDOW=size, SLOPPY_SCREENSHOT=str(folder/'final.png'), BOTW_FRAME_LOG='1', BOTW_LOADTIME='1')
    window_tool = 'tools/performance_window.py'
    if performance and os.environ.get('TASK68_CPU_SET'):
        # Existing round67 protocol: leave startup workers on their full set,
        # then bind the game thread once complete frames prove initialization.
        settings['TASK68_STEADY_CPU_SET']=os.environ['TASK68_CPU_SET']
        settings['TASK68_STEADY_LOG']=str(folder/'run.log')
        source=(ROOT/window_tool).read_text()
        source=source.replace('        last_geometry = None','        last_geometry = None\n        pinned = False')
        anchor='        while proc.poll() is None:\n            root, gx, gy'
        assert source.count(anchor)==1
        source=source.replace(anchor,"""        while proc.poll() is None:
            if not pinned and 'frame sample: 60 ' in Path(child_env['TASK68_STEADY_LOG']).read_text():
                cpus={int(value) for value in child_env['TASK68_STEADY_CPU_SET'].split(',')}
                pid=owner_pid(wid)
                assert cpus and cpus <= os.sched_getaffinity(pid)
                os.sched_setaffinity(pid,cpus)
                pinned=True
                print(f'benchmark steady affinity: PID {pid} CPUs {sorted(os.sched_getaffinity(pid))}',flush=True)
            root, gx, gy""")
        source=source.replace('        status = proc.wait()',"        status = proc.wait()\n        if status == 0: assert pinned, 'steady affinity applied'")
        helper=OUT/'steady-affinity-window.py';helper.write_text(source)
        window_tool=str(helper)
    command = ([] if locked else ['flock', '/tmp/botw-render.lock']) + [sys.executable, window_tool]
    if performance: command += ['--visible']
    command += [size, 'timeout', '90', str(binary)]
    (folder/'settings.json').write_text(json.dumps(dict(environment=settings, command=command, binary_sha256=pack.digest(binary)), indent=2)+'\n')
    if performance: time.sleep(3) # retire the preceding graphics context
    with (folder/'run.log').open('w') as log:
        subprocess.run(command, cwd=ROOT, env=pack.clean_env() | settings, stdout=log, stderr=subprocess.STDOUT, check=True)
    for p in folder.glob('*.png'):
        with Image.open(p) as im:
            im.convert('RGB').resize((640,360), Image.Resampling.LANCZOS).save(p.with_suffix('.jpg'), quality=92)
    print('PASS', phase, scene, folder, flush=True)


def capture(phase, scenes, locked=False):
    if not locked:
        for start in range(0,len(scenes),4):
            subprocess.run(['flock','/tmp/botw-render.lock','timeout','175',sys.executable,str(Path(__file__).resolve()),
                'capture',phase,*scenes[start:start+4],'--locked'],cwd=ROOT,check=True)
        return
    for scene in scenes:
        run(phase, scene, OUT/'captures'/phase/scene,locked=True)
        frames = SCENES[scene][0]
        for frame, _ in frames:
            a = OUT/'captures/before'/scene/f'frame-{frame}.png'
            b = OUT/'captures/after'/scene/f'frame-{frame}.png'
            if a.exists() and b.exists(): pair(a,b,OUT/'pairs'/f'{scene}-{frame}.jpg',f'{scene}-{frame}')


def pair(a, b, out, label):
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet = Image.new('RGB', (1280,384), '#161c22')
    draw = ImageDraw.Draw(sheet)
    for k,(path,name) in enumerate([(a,'before / master'),(b,'after')]):
        with Image.open(path) as im:
            sheet.paste(im.convert('RGB').resize((640,360),Image.Resampling.LANCZOS),(640*k,24))
        draw.text((640*k+6,5),f'{label}: {name}',fill='white')
    sheet.save(out,quality=92)


def performance(scenes, repeats, locked=False, repeat=0, start_repeat=0):
    folder=OUT/('performance-steady-affinity' if os.environ.get('TASK68_CPU_SET') else 'performance-steady-default');folder.mkdir(exist_ok=True)
    if locked:
        assert len(scenes)==1
        scene=scenes[0]
        for phase in (['before','after'] if repeat%2==0 else ['after','before']):
            run(phase,scene,folder/f'{scene}-{phase}-{repeat}',True,True)
        return
    for repeat in range(start_repeat,repeats):
        for scene in scenes:
            subprocess.run(['flock','/tmp/botw-render.lock','timeout','175',sys.executable,str(Path(__file__).resolve()),
                'performance','after',scene,'--locked','--repeat',str(repeat)],cwd=ROOT,check=True)
    control_path=os.environ.get('TASK68_NOISE_CONTROL')
    control=json.loads(Path(control_path).read_text()) if control_path else None
    if control is not None:
        assert not os.environ.get('TASK68_TRACE_MS'), 'control allowance requires unprofiled timing'
        assert control['candidate_phase']=='before', 'control must run the same master binary twice'
        assert control['main_thread_cpu_set']==os.environ.get('TASK68_CPU_SET'), 'control affinity mismatch'
    result=dict(candidate_phase=os.environ.get('TASK68_CANDIDATE', 'after'), main_thread_cpu_set=os.environ.get('TASK68_CPU_SET'),protocol='AB/BA, managed 1920x1080 X11 Vulkan, full scale, fixed seed 64/weather seed31/hour/weather/input and 1/60 simulation; 1440 frames per run, discard first360; three seconds of context retirement before each launch; affinity applies after frame60; pooled nearest-rank CPU callback-thread p99, every tail retained; adjacent pairs share one bounded flock (175-second maximum)', scenes={})
    for scene in scenes:
        values={}
        runs={}
        for phase in ['before','after']:
            rows=[]
            runs[phase]=[]
            for repeat in range(repeats):
                text=(folder/f'{scene}-{phase}-{repeat}/run.log').read_text()
                run_rows=[[float(x) for x in line.split()[2:]] for line in text.splitlines() if line.startswith('frame sample:') and int(line.split()[2])>360]
                assert len(run_rows)==1080
                if control is not None:
                    settings=json.loads((folder/f'{scene}-{phase}-{repeat}'/'settings.json').read_text())
                    binary_phase=os.environ.get('TASK68_CANDIDATE','after') if phase=='after' else phase
                    assert settings['binary_sha256']==pack.digest(OUT/binary_phase/'capture'), 'sample binary mismatch'
                    assert 'BOTW_CPU' not in settings['environment'], 'profiled samples cannot use a noise allowance'
                runs[phase].append(dict(repeat=repeat,order='AB' if repeat%2==0 else 'BA',**pack.percentiles([r[4] for r in run_rows])))
                rows += run_rows
            values[phase]=pack.percentiles([r[4] for r in rows])
        values['runs']=runs
        values['delta_ms']=values['after']['p99']-values['before']['p99']
        values['strict_passed']=values['delta_ms']<=0
        values['noise_ms']=0.0
        if control is not None:
            assert control['protocol']==result['protocol'], 'control protocol mismatch'
            measured=control['scenes'][scene]
            assert set(measured['runs'])=={'before','after'} and all(len(r)>=2 for r in measured['runs'].values()), 'control needs AB and BA rounds'
            # Verify the independent control really used this exact master executable.
            for phase, control_runs in measured['runs'].items():
                for row in control_runs:
                    settings=Path(control_path).parent/f'{scene}-{phase}-{row["repeat"]}'/'settings.json'
                    saved=json.loads(settings.read_text())
                    assert saved['binary_sha256']==pack.digest(OUT/'before/capture'), 'control binary mismatch'
                    assert 'BOTW_CPU' not in saved['environment'], 'profiled control cannot set a noise allowance'
            values['noise_ms']=abs(measured['delta_ms'])
        values['passed']=values['delta_ms']<=values['noise_ms']
        result['scenes'][scene]=values
    if control_path: result['noise_control']=control_path
    result['strict_passed']=all(s['strict_passed'] for s in result['scenes'].values())
    result['passed']=all(s['passed'] for s in result['scenes'].values())
    (folder/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['passed']: raise SystemExit(1)


def compare_pack(path):
    manifest=json.loads((path/'pack.json').read_text())
    folder=OUT/'full-pack-comparison'
    for shot in manifest['shots']:
        relative=Path(shot['png'])
        pair(Path('/tmp/crit68pack')/relative,path/relative,folder/f'{shot["name"]}.jpg',shot['name'])
    print(f'PASS {len(manifest["shots"])} master/candidate comparison sheets: {folder}')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['prepare','capture','performance','compare-pack'])
    parser.add_argument('phase',nargs='?',default='after')
    parser.add_argument('scenes',nargs='*',choices=list(SCENES))
    parser.add_argument('--output', type=Path, help='retain a separate evidence run under build/')
    parser.add_argument('--noise-control',type=Path,help='identical-master summary supplying an observed CPU p99 noise allowance')
    parser.add_argument('--trace-ms',type=float,help='diagnostic CPU zones; omit for acceptance timing')
    parser.add_argument('--ref');parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--locked',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--repeat',type=int,default=0,help=argparse.SUPPRESS)
    parser.add_argument('--start-repeat',type=int,default=0)
    parser.add_argument('--candidate', help='prepared candidate phase for performance (default: after)')
    parser.add_argument('--cpu-set',help='benchmark main-thread CPU affinity; same set for both binaries')
    a=parser.parse_args()
    global OUT
    if a.output:
        OUT=(ROOT/a.output).resolve()
        assert OUT.is_relative_to(ROOT/'build'), 'evidence must stay under build/'
        os.environ['TASK68_OUT']=str(OUT)
    if a.trace_ms is not None:
        os.environ['TASK68_TRACE_MS']=str(a.trace_ms)
    if os.environ.get('TASK68_TRACE_MS'):
        pack.BASE.update(BOTW_CPU='1',BOTW_CPU_TRACE_MS=os.environ['TASK68_TRACE_MS'])
    OUT.mkdir(parents=True,exist_ok=True)
    if a.noise_control: os.environ['TASK68_NOISE_CONTROL']=str((ROOT/a.noise_control).resolve())
    if a.cpu_set: os.environ['TASK68_CPU_SET']=a.cpu_set
    if a.candidate: os.environ['TASK68_CANDIDATE']=a.candidate
    if a.mode=='prepare': prepare(a.phase,a.ref)
    elif a.mode=='capture': capture(a.phase,a.scenes or list(SCENES),a.locked)
    elif a.mode=='performance': performance(a.scenes or ['rain','pond-rain','golden','wake','boar','bird-flight','swim'],a.repeats,a.locked,a.repeat,a.start_repeat)
    else: compare_pack((ROOT/a.phase).resolve())

if __name__=='__main__': main()
