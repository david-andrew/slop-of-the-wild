#!/usr/bin/env python3
"""Matched material views from 91809e7. Each render owns its flock; do not wrap.

prepare before|after; capture before|after [views]; gpu-prepare; gpu-run; gpu-report.
"""
import sys
from pathlib import Path
import round69_character_check as base
base.OUT = base.ROOT/'build/round71'
base.BASELINE = '91809e7'
base.VIEWS = {
    'combat': base.VIEWS['combat'],
    'night': ({'BOTW_SKIP':'1','BOTW_HOUR':'23','BOTW_AT':'-672,1535,0.8'},180),
    'blue-camp': ({'BOTW_SKIP':'1','BOTW_AT':'-982,1654,0','BOTW_CAM':'-987,190.4,1646,1.05,-0.16'},120),
    'monk': ({'BOTW_SKIP':'1','BOTW_TOWER':'1','BOTW_SHRINE':'2','BOTW_SHRINE_AT':'3.5,0,-50,-1.2'},120),
    'husks': ({'BOTW_SKIP':'1','BOTW_CAM':'-852,222,1918,2.6,-0.4'},120),
}

def capture(phase,names):
    for name in names or base.VIEWS:
        flags,frame=base.VIEWS[name]
        base.render(phase,name,base.OUT/phase/'game-bin',{'BOTW_HOUR':'11','BOTW_WEATHER':'clear','SLOPPY_FRAMES':str(frame),**flags},True)

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='prepare': base.prepare(sys.argv[2])
    elif mode=='capture': capture(sys.argv[2],sys.argv[3:])
    elif mode.startswith('gpu-'):
        import round69_gpu_check as gpu
        gpu.OUT=base.OUT
        if mode=='gpu-prepare': gpu.prepare()
        elif mode=='gpu-report':
            from round71_character_report import gpu_report
            print(gpu_report())
        elif mode=='gpu-run':
            import subprocess
            for size in ('1280x720','2133x1200'):
                for view in ('combat','husks'):
                    subprocess.run(['flock','/tmp/botw-render.lock',sys.executable,__file__,'gpu-pair',view,size],check=True)
        elif mode=='gpu-pair':
            for i in range(3): gpu.pair(sys.argv[2],sys.argv[3],i)
