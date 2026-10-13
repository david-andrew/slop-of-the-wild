#!/usr/bin/env python3
"""Matched critic views. Each game process owns one render flock; do not wrap."""
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
OUT=ROOT/'build/round82'
SCENES={
 'snow':(150,dict(BOTW_SKIP='1',BOTW_AT='-1060,2230,2.0')),
 'camp':(120,dict(BOTW_SKIP='1',BOTW_CAM='-947,243,1956,-0.85,-0.45')),
 'forest':(150,dict(BOTW_SKIP='1',BOTW_AT='-1000,1620,3.14')),
 'overlook':(720,dict(BOTW_TITLE='1',SLOPPY_INPUT='10:w+,300:w-')),
 'boar':(150,dict(BOTW_SKIP='1',BOTW_CAM='-947,188,1653,-0.717,-0.24')),
 'body-fire':(260,dict(BOTW_SKIP='1',BOTW_TENTFIRE='5',BOTW_AT='-955,1964,0')),
 'fire260':(260,dict(BOTW_SKIP='1',BOTW_FIRE='1')),
 'dry-strike':(150,dict(BOTW_SKIP='1',BOTW_CAM='-1043,242,1804,0,-0.65')),
 'options-snow':(150,dict(BOTW_SKIP='1',BOTW_AT='-1060,2230,2.0')),
 'options-grass':(150,dict(BOTW_SKIP='1',BOTW_AT='-1054,1834,0.85')),
 'options-interior':(150,dict(BOTW_SKIP='1',BOTW_SHRINE='1',BOTW_TOWER='1')),
}

def prepare(label,game_dir=None):
 OUT.mkdir(parents=True,exist_ok=True)
 game=game_dir.resolve() if game_dir else ROOT/'game'
 s=(game/'main.jo').read_text()
 for p in game.glob('*.jo'): s=s.replace(f"'{p.name}'",f"'{p}'")
 s=s.replace('update = (dt0: f64):','production_update = (dt0: f64):')
 s+=f"\nuse '{ROOT}/tools/performance_output.jo'\nuse '{game}/inventory.jo'\n"
 s+='''
r82_scene=env("ROUND82_SCENE") ?? "snow"
update=(dt:f64):
    production_update(dt)
    if starts_with(r82_scene,"options-") and (r82_scene!="options-interior" or frame_number()>=90):
        invui=InvUI(open=true,tab=6,t=1.0,tab_t=1.0)
    if r82_scene=="boar":
        animals.clear()
        p=v3(-950.64,height_at(-950.64,1649.65),1649.65)
        animal=Animal(.boar,p,p,face=3.6,seed=3.7,appearance=0.56)
        animal.idle=1.8
        animal.t=1.8
        animals.push(animal)
        fc_pos=p+vec3(2.7,1.55,3.1)
        fc_yaw=-0.717
        fc_pitch=-0.24
    if r82_scene=="dry-strike":
        impact=v3(-1043,height_at(-1043,1796),1796)
        fc_pos=impact+vec3(4,3.5,5)
        gaze=impact-fc_pos
        fc_yaw=atan2(f64(gaze.x),-f64(gaze.z))
        fc_pitch=atan2(f64(gaze.y),hypot(f64(gaze.x),f64(gaze.z)))
        if frame_number()==30:strike_at(impact+vec3(0,0.5,0))
main=():performance_output_run(update,draw)
'''
 (OUT/f'{label}.jo').write_text(s)
 with (OUT/f'{label}-build.log').open('w') as log:
  subprocess.run(['sloppy/bin/sloppy','build',str(OUT/f'{label}.jo'),'-o',str(OUT/f'{label}-game')],stdout=log,stderr=subprocess.STDOUT,check=True)
 (OUT/f'{label}-source.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in game.glob('*.jo')},indent=2))

def capture(label,names,baseline='before'):
 binary=OUT/f'{label}-game'
 digest=hashlib.sha256(binary.read_bytes()).hexdigest()
 clean={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_','ROUND82_'))}
 for name in names or SCENES:
  frames,flags=SCENES[name]
  folder=OUT/name;folder.mkdir(parents=True,exist_ok=True)
  settings=clean|dict(BOTW_NO_PREPARED_ASSETS='1',BOTW_SCALE='1',BOTW_HOUR='11',BOTW_WEATHER='clear',BOTW_NOVSYNC='1',BOTW_GPU='1',BOTW_FRAME_LOG='1',SLOPPY_VSYNC='0',SLOPPY_PLATFORM='x11',SLOPPY_WINDOW='1280x720',SLOPPY_FRAMES=str(frames),SLOPPY_SCREENSHOT=str(folder/f'{label}.png'),ROUND82_SCENE=name)|flags
  with (folder/f'{label}.log').open('w') as log:
   subprocess.run(['flock','/tmp/botw-render.lock','python3','tools/performance_window.py','1280x720','timeout','240',str(binary)],env=settings,stdout=log,stderr=subprocess.STDOUT,check=True)
  assert Image.open(folder/f'{label}.png').size==(1280,720)
  assert hashlib.sha256(binary.read_bytes()).hexdigest()==digest
  (folder/f'{label}.json').write_text(json.dumps(dict(sha256=digest,settings={k:v for k,v in settings.items() if k.startswith(('BOTW_','SLOPPY_','ROUND82_'))}),indent=2))
  if label!=baseline and (folder/f'{baseline}.png').exists():
   pair=Image.new('RGB',(2560,744),(24,27,30));d=ImageDraw.Draw(pair)
   for x,phase in [(0,baseline),(1280,label)]:
    pair.paste(Image.open(folder/f'{phase}.png'),(x,24));d.text((x+12,6),phase,fill='white')
   pair.save(folder/('pair.png' if label=='after' else f'pair-{label}.png'))
  print(f'PASS {label}/{name}',flush=True)

def performance(candidate,names,baseline='before',frames=1440,warmup=360):
 import math, statistics
 out=OUT/f'performance-{candidate}';out.mkdir(exist_ok=True)
 clean={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_','ROUND82_'))}
 binaries={'before':OUT/f'{baseline}-game','after':OUT/f'{candidate}-game'}
 digests={k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in binaries.items()}
 def samples(prefix):
  lines=prefix.with_suffix('.log').read_text().splitlines()
  rows=[[float(v) for v in line.split()[2:]] for line in lines if line.startswith('frame sample:')]
  # New master primes both Vulkan presentation slots during loading. Count only
  # game presents, after the first timed callback; retain all raw audit lines.
  started=False
  draws=[]
  for line in lines:
   if line.startswith('first frame:'):started=True
   elif started and line.startswith('draw sample:'):draws.append(list(map(int,line.split()[2:])))
  assert len(rows)==frames and len(draws)==frames and max(d[1] for d in draws)>100
  assert Image.open(prefix.with_suffix('.png')).size==(1280,720)
  return [r for r in rows if r[0]>=warmup+1],draws[warmup:]
 for name in names or ['snow','camp','forest','overlook']:
  _,flags=SCENES[name]
  runs={'before':[],'after':[]}
  workload={phase:[] for phase in runs}
  for repeat in range(3):
   for phase in (['before','after'] if repeat%2==0 else ['after','before']):
    prefix=out/f'{name}-{phase}-{repeat}'
    binary=binaries[phase]
    metadata=prefix.with_suffix('.json')
    valid=False
    if metadata.exists() and json.loads(metadata.read_text()).get('sha256')==digests[phase]:
     try:samples(prefix);valid=True
     except (OSError,AssertionError,ValueError):pass
    settings=clean|dict(BOTW_NO_PREPARED_ASSETS='1',BOTW_HOUR='11',BOTW_WEATHER='clear',BOTW_SCALE='1',BOTW_NOVSYNC='1',BOTW_FRAME_LOG='1',SLOPPY_VSYNC='0',SLOPPY_PLATFORM='x11',SLOPPY_WINDOW='1280x720',SLOPPY_FRAMES=str(frames),SLOPPY_SCREENSHOT=str(prefix.with_suffix('.png')),ROUND82_SCENE=name,LD_AUDIT=str(OUT/'draw-audit.so'))|flags
    if not valid:
     with prefix.with_suffix('.log').open('w') as log:
      subprocess.run(['flock','/tmp/botw-render.lock','python3','tools/performance_window.py','1280x720','timeout','240',str(binary)],env=settings,stdout=log,stderr=subprocess.STDOUT,check=True)
     metadata.write_text(json.dumps(dict(sha256=digests[phase],settings={k:v for k,v in settings.items() if k.startswith(('BOTW_','SLOPPY_','ROUND82_','LD_AUDIT'))}),indent=2))
    assert hashlib.sha256(binary.read_bytes()).hexdigest()==digests[phase]
    rows,draws=samples(prefix)
    workload[phase].append([d[1] for d in draws])
    percentile=lambda col:sorted(r[col] for r in rows)[math.ceil(len(rows)*.99)-1]
    row=dict(frame_p99_ms=percentile(1),wall_p99_ms=percentile(2),thread_p99_ms=percentile(4),draws_min=min(d[1] for d in draws),draws_max=max(d[1] for d in draws))
    runs[phase].append(row)
    print(name,phase,repeat,row,'retained' if valid else '',flush=True)
  report={phase:{metric:statistics.median(r[metric] for r in runs[phase]) for metric in runs[phase][0]} for phase in runs}
  report['protocol']=dict(frames=frames,warmup=warmup,order='AB/BA/AB',tolerance='3% + 0.10 ms')
  report['baseline']=baseline
  report['candidate']=candidate
  report['runs']=runs
  report['binary_sha256']=digests
  report['draw_counts_identical']=workload['before']==workload['after']
  report['passed']=report['draw_counts_identical'] and all(report['after'][m]<=report['before'][m]*1.03+.10 for m in ['frame_p99_ms','thread_p99_ms'])
  (out/f'{name}-report.json').write_text(json.dumps(report,indent=2)+'\n')
  print('PASS' if report['passed'] else 'FAIL',name,report['before'],report['after'],flush=True)
  assert report['passed'], 'paired p99/draw budget'

def label_name(value):
 if not re.fullmatch(r'[a-z][a-z0-9-]*',value):raise argparse.ArgumentTypeError('use a lowercase label with letters, digits and hyphens')
 return value

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','capture','performance']);p.add_argument('label',type=label_name);p.add_argument('scenes',nargs='*',choices=list(SCENES));p.add_argument('--game-dir',type=Path);p.add_argument('--baseline',type=label_name,default='before');p.add_argument('--frames',type=int,default=1440);p.add_argument('--warmup',type=int,default=360);a=p.parse_args()
 if a.frames<=a.warmup or a.warmup<0:p.error('frames must exceed a nonnegative warmup')
 if a.mode=='prepare':prepare(a.label,a.game_dir)
 elif a.mode=='performance':performance(a.label,a.scenes,a.baseline,a.frames,a.warmup)
 else:capture(a.label,a.scenes,a.baseline)
