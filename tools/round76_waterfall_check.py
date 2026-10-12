#!/usr/bin/env python3
"""West-waterfall evidence against master 52b9982 at native 1280x720.

prepare before|after; motion before|after [cliffs pool top];
perf before|after REPEAT; pairs. Each render owns one flock; never wrap.
Motion captures one run per view with three snapshots ten updates apart,
plus its final still. Perf disables snapshots and excludes 240 warmup frames.
"""
import hashlib,json,os,subprocess,sys
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'build/round76';os.chdir(ROOT)
VIEWS={'cliffs':'-1600,235,1815,1.2,-0.15','pool':'-1565,119,1858,1.22,0.22','top':'-1380,288,1837,-1.78,-0.65'}
def prepare(phase):
 out=OUT/('waterfall-'+phase);game=out/'game';game.mkdir(parents=True,exist_ok=True)
 for p in (ROOT/'game').glob('*.jo'):(game/p.name).write_bytes(subprocess.check_output(['git','show','52b9982:game/'+p.name]) if phase=='before' else p.read_bytes())
 (out/'main.jo').write_text("build:\n    opt = release\nuse '"+str(game/'main.jo')+"'\nuse '"+str(ROOT/'tools/performance_output.jo')+"'\nmain = (): performance_output_run(update, draw)\n")
 with (out/'build.log').open('w') as log:subprocess.run(['sloppy/bin/sloppy','build',str(out/'main.jo'),'-o',str(out/'game-bin')],stdout=log,stderr=subprocess.STDOUT,check=True)
 (out/'sources.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in game.glob('*.jo')},indent=2))
def capture(phase,view,frame=300,perf=False,rep=0):
 out=OUT/('waterfall-'+phase);name=f'{view}-{frame}'+(f'-perf-{rep}' if perf else ''); dest=out/name
 env={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_','ROUND'))}
 env.update(BOTW_SKIP='1',BOTW_CAM=VIEWS[view],BOTW_HOUR='11',BOTW_TIMESCALE='0',BOTW_WEATHER='clear',BOTW_NOVSYNC='1',BOTW_NO_PREPARED_ASSETS='1',BOTW_SCALE='1',SLOPPY_PLATFORM='x11',SLOPPY_WINDOW='1280x720',SLOPPY_FRAMES=str(frame),SLOPPY_SCREENSHOT=str(dest.with_suffix('.png')))
 if not perf and os.environ.get('WF_MOTION')=='1':
  frames=out/(view+'-sequence');frames.mkdir(exist_ok=True);env.update(BOTW_CAPTURE_DIR=str(frames),BOTW_CAPTURE_EVERY='10')
 if perf:env.update(BOTW_FRAME_LOG='1',BOTW_GPU='1',BOTW_GPU_FRAME_LOG='1')
 with dest.with_suffix('.log').open('w') as log:subprocess.run(['flock','/tmp/botw-render.lock','python3','tools/performance_window.py','1280x720','timeout','240',str(out/'game-bin')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 assert Image.open(dest.with_suffix('.png')).size==(1280,720)
 row={'env':{k:v for k,v in env.items() if k.startswith(('BOTW_','SLOPPY_'))},'binary':hashlib.sha256((out/'game-bin').read_bytes()).hexdigest()}
 if perf:
  txt=dest.with_suffix('.log').read_text();row['frame_rows']=[l for l in txt.splitlines() if l.startswith('frame sample:')];row['gpu_rows']=[l for l in txt.splitlines() if l.startswith('gpu frame:')]
 dest.with_suffix('.json').write_text(json.dumps(row,indent=2)+'\n');print(phase,name,flush=True)
def pairs():
 for v in VIEWS:
  for f in (300,310,320,321):
   paths=[OUT/('waterfall-'+p)/f'{v}-{f}.png' for p in ('before','after')]
   if not all(p.exists() for p in paths):continue
   im=Image.new('RGB',(1280,1488),(25,28,29));d=ImageDraw.Draw(im)
   for j,p in enumerate(paths):im.paste(Image.open(p),(0,j*744+24));d.text((10,j*744+6),('BEFORE 52b9982' if j==0 else 'AFTER')+f' / {v} / frame {f}',fill='white')
   im.save(OUT/f'waterfall-{v}-{f}-pair.png')
if len(sys.argv)<2:raise SystemExit(__doc__)
if sys.argv[1]!='pairs' and (len(sys.argv)<3 or sys.argv[2] not in ('before','after')):raise SystemExit(__doc__)
if sys.argv[1]=='prepare':prepare(sys.argv[2])
elif sys.argv[1]=='capture':
 for v in sys.argv[3:] or VIEWS:
  for f in (300,310,320):capture(sys.argv[2],v,f)
elif sys.argv[1]=='still':capture(sys.argv[2],sys.argv[3])
elif sys.argv[1]=='perf':capture(sys.argv[2],'cliffs',960,True,int(sys.argv[3]))
elif sys.argv[1]=='motion':
 import shutil
 os.environ['WF_MOTION']='1'
 for v in sys.argv[3:] or VIEWS:
  capture(sys.argv[2],v,321)
  out=OUT/('waterfall-'+sys.argv[2])
  for f in (300,310,320):shutil.copy2(out/(v+'-sequence')/f'frame-{f}.png',out/f'{v}-{f}.png')
elif sys.argv[1]=='pairs':pairs()
else:raise SystemExit(__doc__)
