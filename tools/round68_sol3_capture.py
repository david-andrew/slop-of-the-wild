#!/usr/bin/env python3
"""Round 68 matched captures and alternating CPU p99 pairs; self-locking."""
import argparse
import hashlib
import json
import math
import statistics
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
import round67_sol3_capture as evidence
from PIL import Image, ImageDraw
ROOT = evidence.capture.ROOT
OUT = ROOT/'build/round68-sol3'
evidence.capture.OUT = OUT
evidence.capture.SCENES = {
    'passage90': (90, dict(BOTW_PASSAGE='1', SLOPPY_INPUT='20:w+')),
    'passage450': (450, dict(BOTW_PASSAGE='1', SLOPPY_INPUT='20:w+')),
    'passage700': (700, dict(BOTW_PASSAGE='1', SLOPPY_INPUT='20:w+')),
    'pool': (300, dict(BOTW_SKIP='1', BOTW_CAM='-1535,120,1823,1.5707963,-0.3')),
    'waterfall': (300, dict(BOTW_SKIP='1', BOTW_CAM='-1660,175,1888,1.24,-0.05')),
    'temple': (300, dict(BOTW_SKIP='1', BOTW_CAM='-802,237,1900,-2.967,-0.14')),
    'husks': (120, dict(BOTW_SKIP='1', BOTW_CAM='-852,222,1918,2.6,-0.4')),
    'snow': (150, dict(BOTW_SKIP='1', BOTW_AT='-1060,2230,2.0')),
    'firs': (150, dict(BOTW_SKIP='1', BOTW_CAM='-880,206,2273,2.60,-0.16')),
    'camp': (180, dict(BOTW_SKIP='1', BOTW_AT='-1439,1606,0', BOTW_GIVE='travelers_sword,travelers_shield', SLOPPY_INPUT='1:k+,1:w+,150:j+,151:j-,165:j+,166:j-,195:j+,196:j-,200:w-,225:j+,226:j-,255:j+,256:j-')),
}
def capture_pairs(label):
    for scene in evidence.capture.SCENES:
        folder=OUT/scene
        if not all((folder/(phase+'.json')).exists() for phase in ['before',label]): continue
        sheet=Image.new('RGB',(1280,385),(24,27,30));draw=ImageDraw.Draw(sheet)
        for k,phase in enumerate(['before',label]):
            metadata=json.loads((folder/(phase+'.json')).read_text())
            assert metadata['sha256']==hashlib.sha256((OUT/(phase+'-game')).read_bytes()).hexdigest(), 'comparison executable mismatch'
            with Image.open(folder/(phase+'.png')) as im: sheet.paste(im.convert('RGB').resize((640,360),Image.Resampling.LANCZOS),(k*640,25))
            draw.text((k*640+6,6),f'{scene}: {phase}',fill='white')
        sheet.save(folder/('review-'+label+'.jpg'),quality=93)

def summarize_bench(label, scene, repeats):
    folder=OUT/('performance-'+label)
    summary={'protocol':{'frames':720,'warmup':240,'steady_frames_per_run':480,'repeats':repeats,'order':'AB/BA alternating','main_thread_core':2,'percentile':'nearest-rank pooled steady frames; every tail retained','tolerance':'3% + 0.10 ms'},'before':{},'after':{}}
    for phase in ['before','after']:
        binary=OUT/((label if phase=='after' else 'before')+'-game')
        digest=hashlib.sha256(binary.read_bytes()).hexdigest()
        steady=[];run_p99=[]
        for repeat in range(repeats):
            prefix=folder/f'{scene}-{phase}-{repeat}'
            metadata=json.loads(prefix.with_suffix('.json').read_text())
            assert metadata['sha256']==digest and metadata['settings']['SLOPPY_FRAMES']=='720'
            rows=[[float(v) for v in line.split()[2:]] for line in prefix.with_suffix('.log').read_text().splitlines() if line.startswith('frame sample:')]
            assert len(rows)==720
            rows=[row for row in rows if row[0]>240]
            assert len(rows)==480
            steady.extend(rows)
            run_p99.append(sorted(row[4] for row in rows)[math.ceil(len(rows)*.99)-1])
        percentile=lambda col:sorted(row[col] for row in steady)[math.ceil(len(steady)*.99)-1]
        summary[phase]={'thread_p99_ms':percentile(4),'wall_p99_ms':percentile(2),'frame_p99_ms':percentile(1),'thread_p50_ms':statistics.median(row[4] for row in steady),'samples':len(steady),'per_run_thread_p99_ms':run_p99,'median_per_run_thread_p99_ms':statistics.median(run_p99),'binary_sha256':digest}
    summary['cpu_p99_delta_ms']=summary['after']['thread_p99_ms']-summary['before']['thread_p99_ms']
    summary['passed']=summary['after']['thread_p99_ms']<=summary['before']['thread_p99_ms']*1.03+0.1
    (folder/(scene+'-pooled-report.json')).write_text(json.dumps(summary,indent=2)+'\n')
    print('PASS' if summary['passed'] else 'FAIL',scene,'pooled CPU p99',summary['before']['thread_p99_ms'],summary['after']['thread_p99_ms'],flush=True)
    assert summary['passed'], 'pooled CPU p99 budget'

def compare_pack(pack):
    manifest=json.loads((pack/'pack.json').read_text())
    folder=OUT/'review/full-pack';folder.mkdir(parents=True,exist_ok=True)
    for shot in manifest['shots']:
        relative=Path(shot['png'])
        sheet=Image.new('RGB',(1280,385),(24,27,30));draw=ImageDraw.Draw(sheet)
        for k,(label,path) in enumerate([('master',Path('/tmp/crit68pack')/relative),('candidate',pack/relative)]):
            with Image.open(path) as im: sheet.paste(im.convert('RGB').resize((640,360),Image.Resampling.LANCZOS),(k*640,25))
            draw.text((k*640+6,6),f'{shot["name"]}: {label}',fill='white')
        sheet.save(folder/f'{shot["name"]}.jpg',quality=92)
    print(f'PASS {len(manifest["shots"])} downscaled full-pack comparisons: {folder}')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['prepare','capture','performance','compare-pack'])
    p.add_argument('label',nargs='?',default='after')
    p.add_argument('scenes',nargs='*')
    p.add_argument('--ref')
    p.add_argument('--repeats',type=int,choices=[3,5],default=3)
    a=p.parse_args()
    if a.mode != 'compare-pack':
        a.label = evidence.capture.label_name(a.label)
        if any(scene not in evidence.capture.SCENES for scene in a.scenes): p.error('unknown capture scene')
    assert OUT.resolve().is_relative_to(ROOT/'build') and not OUT.is_symlink()
    if a.mode=='prepare': evidence.prepare(a.label,a.ref)
    elif a.mode=='capture':
        for scene in a.scenes or evidence.capture.SCENES:
            subprocess.run(['flock','/tmp/botw-render.lock','timeout','95',sys.executable,'-c',
                'import sys,time;sys.path.insert(0,"tools");import round68_sol3_capture as r;r.evidence.binary_for=lambda phase,scene:r.OUT/(phase+"-game");r.evidence.pair_deadline=time.monotonic()+90;r.evidence.run(sys.argv[1],sys.argv[2])',a.label,scene],check=True)
        capture_pairs(a.label)
    elif a.mode=='compare-pack': compare_pack((ROOT/a.label).resolve())
    else:
        # Up to three alternating pairs share one bounded 150-second lock.
        # Frozen source trees and all 480 steady samples/run remain unchanged.
        os.environ.update(R66_BASELINE='before',R66_CANDIDATE=a.label,R66_TIMINGS_NAME='performance-'+a.label,R66_PRODUCTION_AFFINITY='0',R66_BENCH_FRAMES='720',R66_BENCH_WARMUP='240')
        audit=OUT/'draw-audit.so'
        subprocess.run(['cc','-shared','-fPIC','-O2','tools/round82_draw_audit.c','-o',str(audit)],check=True)
        for scene in a.scenes or ['passage450','pool','temple','husks','snow','firs','camp']:
            pending=[]
            for repeat in range(a.repeats):
                try:
                    for phase in ['before','after']: evidence.run(phase,scene,repeat,readonly=True)
                except AssertionError: pending.append(repeat)
            for first in range(0,len(pending),3):
                batch=pending[first:first+3]
                subprocess.run(['flock','/tmp/botw-render.lock','timeout','150',sys.executable,'-c',
                    'import sys,time;sys.path.insert(0,"tools");import round68_sol3_capture as r;r.evidence.pair_deadline=time.monotonic()+145;[(r.evidence.run(p,sys.argv[1],int(n),force=True)) for n in sys.argv[2:] for p in (["before","after"] if int(n)%2==0 else ["after","before"])]',scene,*map(str,batch)],env=os.environ|dict(R66_LOCKED='1'),check=True)
            summarize_bench(a.label,scene,a.repeats)
