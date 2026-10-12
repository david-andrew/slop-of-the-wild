#!/usr/bin/env python3
"""Frozen wake/combat GPU pairs with baseline assets. Owns each view's flock.

prepare compiles both fixtures; run measures three alternating pairs per view;
report checks cached results. No gameplay update runs after the target frame.
"""
from pathlib import Path
import hashlib, json, os, re, statistics, subprocess, sys
from round69_character_check import ROOT, OUT, VIEWS, build, game_dir
os.chdir(ROOT)

def prepare():
    for phase in ('before','after'):
        game=game_dir(phase)
        s=(game/'main.jo').read_text()
        start=s.index('    if pl.state == .ground or pl.state == .cutscene:')
        end=s.index('    # the cave mouth:',start)
        contacts=s[start:end]
        s=re.sub(r"(?m)^(use|from) '([^']+)'",lambda m:f"{m[1]} '{game/m[2]}'",s)
        s=s.replace('update = (dt0: f64):','production_update = (dt0: f64):')
        s+=f"\nuse '{ROOT/'tools/performance_output.jo'}'\n"
        s+='''update = (dt: f64):
    freeze=to_int(env("ROUND69_FREEZE") ?? "420") ?? 420
    if frame_number()<=freeze: production_update(dt)
    else:
        frame_stats_begin(post.scale)
''' + ''.join('    '+line+'\n' for line in contacts.splitlines()) + '''main = (): performance_output_run(update,draw)
'''
        source=OUT/phase/'gpu.jo';source.write_text(s)
        build(source,OUT/phase/'gpu-game')

def pair(view,size,repeat):
    (OUT/'gpu').mkdir(exist_ok=True)
    for phase in (('before','after') if repeat%2==0 else ('after','before')):
        flags,frame=VIEWS[view]
        name=f'{size}-{view}-{repeat}-{phase}'
        dest=OUT/'gpu'/name
        env={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_','ROUND69_'))}
        env.update(BOTW_HOUR='11',BOTW_WEATHER='clear',BOTW_SCALE='1',BOTW_NOVSYNC='1',
            BOTW_NO_PREPARED_ASSETS='1',BOTW_GPU='1',BOTW_GPU_FRAME_LOG='1',BOTW_FRAME_LOG='1',
            SLOPPY_PLATFORM='x11',SLOPPY_WINDOW=size,SLOPPY_FRAMES='840',
            SLOPPY_SCREENSHOT=str(dest.with_suffix('.png')),ROUND69_FREEZE=str(frame))
        env.update(flags)
        with dest.with_suffix('.log').open('w') as log:
            subprocess.run([sys.executable,str(ROOT/'tools/performance_window.py'),size,'timeout','240',str(OUT/phase/'gpu-game')],
                cwd=OUT/'before' if phase=='before' else ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        rows=[]
        for line in dest.with_suffix('.log').read_text().splitlines():
            m=re.match(r'gpu frame: (\d+) (.*) = ([\d.]+)',line)
            if m and int(m[1])>=480:
                rows.append({**{k:float(v) for k,v in re.findall(r'(\S+) ([\d.]+)',m[2])},'total':float(m[3])})
        assert len(rows)>=250,(name,len(rows))
        result={k:statistics.median(r.get(k,0.0) for r in rows) for k in rows[0]}
        result['samples']=len(rows)
        result['binary_sha256']=hashlib.sha256((OUT/phase/'gpu-game').read_bytes()).hexdigest()
        assets=OUT/'before/assets/models' if phase=='before' else ROOT/'assets/models'
        result['model_sha256']={n:hashlib.sha256((assets/f'{n}.mdl').read_bytes()).hexdigest() for n in ('hero','hero_bare','bokoblin')}
        dest.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
        print(name, 'total',result['total'],'chars',result.get('chars'),'samples',result['samples'],flush=True)

def report(quiet=False):
    results={}
    for size in ('1280x720','2133x1200'):
        for view in ('wake','combat'):
            runs={phase:[json.loads((OUT/'gpu'/f'{size}-{view}-{i}-{phase}.json').read_text()) for i in range(3)] for phase in ('before','after')}
            for phase in runs:
                assets=OUT/'before/assets/models' if phase=='before' else ROOT/'assets/models'
                expected={n:hashlib.sha256((assets/f'{n}.mdl').read_bytes()).hexdigest() for n in ('hero','hero_bare','bokoblin')}
                binary=hashlib.sha256((OUT/phase/'gpu-game').read_bytes()).hexdigest()
                assert all(r['model_sha256']==expected and r['binary_sha256']==binary for r in runs[phase]),'stale GPU evidence'
            vals={p:statistics.median(r['total'] for r in runs[p]) for p in runs}
            passed=vals['after']<=vals['before']*1.03+.1
            results[f'{size}-{view}']={'median_ms':vals,'delta_ms':vals['after']-vals['before'],'limit_ms':vals['before']*1.03+.1,'passed':passed,'runs':runs}
    (OUT/'gpu-summary.json').write_text(json.dumps(results,indent=2)+'\n')
    if not quiet: print(json.dumps(results,indent=2))
    assert all(r['passed'] for r in results.values()),'GPU budget regression'
    return results

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='prepare':prepare()
    elif mode=='_pair':pair(sys.argv[2],sys.argv[3],int(sys.argv[4]))
    elif mode=='_view':
        for i in range(3): pair(sys.argv[2],sys.argv[3],i)
    elif mode=='_batch':
        for size in ('1280x720','2133x1200'):
            for view in ('wake','combat'):
                for i in range(3): pair(view,size,i)
    elif mode=='run-batch':
        subprocess.run(['flock','/tmp/botw-render.lock',sys.executable,__file__,'_batch'],check=True)
        report()
    elif mode=='_highres':
        for view in ('wake','combat'):
            for i in range(3): pair(view,'2133x1200',i)
    elif mode=='run-highres':
        subprocess.run(['flock','/tmp/botw-render.lock',sys.executable,__file__,'_highres'],check=True)
        report()
    elif mode=='run':
        for size in ('1280x720','2133x1200'):
            for view in ('wake','combat'):
                subprocess.run(['flock','/tmp/botw-render.lock',sys.executable,__file__,'_view',view,size],check=True)
        report()
    elif mode=='report':report()
