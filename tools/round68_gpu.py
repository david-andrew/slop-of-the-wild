#!/usr/bin/env python3
"""Paired fauna GPU budget at the critic view; owns the render lock."""
from pathlib import Path
import json, math, os, re, subprocess, sys
root=Path(__file__).resolve().parents[1];os.chdir(root)
out=root/'build/round68'
report='--report' in sys.argv
if not report and '--locked' not in sys.argv:
    os.execvp('flock',['flock','/tmp/botw-render.lock',sys.executable,__file__,'--locked'])
summary={}
for size,scale in [('1280x720','1.0'),('2133x1200','0.8')]:
    for repeat in range(1,4):
        for phase in ['before','after']:
            name=f'{phase}-gpu-{size}-{repeat}'
            env=os.environ|dict(BOTW_SKIP='1',BOTW_CAM='-946,188.0,1660,-0.75,-0.12',BOTW_HOUR='8',BOTW_WEATHER='clear',BOTW_NOVSYNC='1',BOTW_GPU='1',BOTW_GPU_FRAME_LOG='1',BOTW_FRAME_LOG='1',BOTW_SCALE=scale,SLOPPY_PLATFORM='x11',SLOPPY_WINDOW=size,SLOPPY_FRAMES='720',SLOPPY_SCREENSHOT=str(out/f'{name}.png'))
            if not report:
                (out/f'{name}.load').write_text(Path('/proc/loadavg').read_text())
                with (out/f'{name}.log').open('w') as log:
                    subprocess.run(['python3','tools/cliff_capture_window.py',size,'timeout','180',str(out/f'{phase}-game')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
            text=(out/f'{name}.log').read_text()
            rows=[]
            for line in text.splitlines():
                if not line.startswith('gpu frame:'): continue
                match=re.match(r'gpu frame: (\d+) (.*) = ([\d.]+)',line)
                if not match or int(match[1])<240: continue
                row={k:float(v) for k,v in re.findall(r'(\S+) ([\d.]+)',match[2])}
                row['total']=float(match[3]);rows.append(row)
            assert len(rows)>400,(name,len(rows))
            summary[name]=rows
            print(name,len(rows),flush=True)
def percentile(xs,p):return sorted(xs)[math.ceil(len(xs)*p)-1]
result={}
for size in ['1280x720','2133x1200']:
    result[size]={}
    for phase in ['before','after']:
        rows=sum([summary[f'{phase}-gpu-{size}-{r}'] for r in range(1,4)],[])
        result[size][phase]={key:{'p50':percentile([r.get(key,0.0) for r in rows],.5),'p99':percentile([r.get(key,0.0) for r in rows],.99)} for key in sorted(set().union(*(r.keys() for r in rows)))}
        result[size][phase]['samples']=len(rows)
(out/'gpu-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
