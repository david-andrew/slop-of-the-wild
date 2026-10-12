#!/usr/bin/env python3
"""Presentation comparison; owns one batch lock (do not wrap) and verifies physical output/samples."""
import os,subprocess,sys,json,math,hashlib,re
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];os.chdir(ROOT)
out=ROOT/'build/round71/pacing';out.mkdir(parents=True,exist_ok=True)
source=f'''build:
    opt = release
use '{ROOT}/game/main.jo'
use '{ROOT}/tools/performance_output.jo'
main=():
    if (env("SLOPPY_PLATFORM")??"")=="wayland": __game_run(update,draw)
    else: performance_output_run(update,draw)
'''
if '--locked' not in sys.argv:
 (out/'pacing.jo').write_text(source)
 subprocess.run(['sloppy/bin/sloppy','build',str(out/'pacing.jo'),'-o',str(out/'pacing')],check=True)
 os.execvp('flock',['flock','/tmp/botw-render.lock',sys.executable,__file__,'--locked'])
summary={'binary_sha256':hashlib.sha256((out/'pacing').read_bytes()).hexdigest(),'runs':[],
 'protocol':'forest, fixed scale 1; nearest-rank producer intervals >=241; all samples retained. These are not scanout timestamps.'}
for size in ('1280x720','2133x1200'):
 for platform,mode in [('wayland','fifo'),('wayland','mailbox'),('x11','fifo'),('x11','uncapped')]:
  for repeat in range(1,3):
   name=f'{platform}-{mode}-{size}-{repeat}'
   e={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_'))}
   e.update(BOTW_SKIP='1',BOTW_AT='-1000,1620,3.14',BOTW_HOUR='11',BOTW_WEATHER='clear',BOTW_SCALE='1',BOTW_FRAME_LOG='1',BOTW_LOADTIME='1',BOTW_SCENE_LOG='1',SLOPPY_FRAME_STATS='1',SLOPPY_PLATFORM=platform,SLOPPY_VSYNC=('1' if mode=='fifo' else '0'),SLOPPY_WINDOW=('768x432' if size=='1280x720' else '1280x720') if platform=='wayland' else size,SLOPPY_FRAMES='1440',SLOPPY_SCREENSHOT=str(out/(name+'.png')))
   if mode=='uncapped':e['BOTW_NOVSYNC']='1'
   cmd=['timeout','180',str(out/'pacing')]
   if platform=='x11':cmd=['python3','tools/performance_window.py',size,*cmd]
   meta={'platform':platform,'mode':mode,'requested_output':size,'repeat':repeat,'flags':{k:v for k,v in e.items() if k.startswith(('BOTW_','SLOPPY_'))}}
   (out/(name+'.environment.json')).write_text(json.dumps(meta,indent=2)+'\n')
   with (out/(name+'.log')).open('w') as log:
    subprocess.run(cmd,env=e,stdout=log,stderr=subprocess.STDOUT,check=True)
   text=(out/(name+'.log')).read_text()
   dimensions=Image.open(out/(name+'.png')).size
   meta['actual_output']='x'.join(map(str,dimensions))
   meta['load_s']=re.search(r'loaded in ([0-9.]+)s',text)[1]
   meta['load_end']=Path('/proc/loadavg').read_text().strip()
   rows=[[float(v) for v in line.split()[2:]] for line in text.splitlines() if line.startswith('frame sample:')]
   rows=[r for r in rows if r[0]>=241]
   assert len(rows)==1200,(name,len(rows))
   dims=re.findall(r'; (\d+x\d+) scale ([\d.]+)',text)
   assert dims and all(d==size and scale=='1.00' for d,scale in dims),(name,dims)
   positions=re.findall(r'perf scene: frame \d+ pos (\S+) hp',text)
   assert positions and all(p=='-1000.0,188.0,1620.0' for p in positions),(name,positions)
   assert platform!='wayland' or 'vulkan (' in text,'native Wayland mode unconfirmed'
   def metrics(column):
    a=sorted(r[column] for r in rows)
    return {'p50':a[math.ceil(len(a)*.5)-1],'p99':a[math.ceil(len(a)*.99)-1],'worst':a[-1]}
   meta['interval_ms']=metrics(1)
   meta['present_ms']=metrics(11)
   meta['size_match']=meta['actual_output']==size
   summary['runs'].append(meta)
   (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
   print(name,meta['actual_output'],meta['interval_ms'],flush=True)
   if not meta['size_match']:raise RuntimeError('Compositor output differs from requested size; retain evidence and correct the sizing protocol.')

summary['pooled']=[]
for size in ('1280x720','2133x1200'):
 for platform,mode in [('wayland','fifo'),('wayland','mailbox'),('x11','fifo'),('x11','uncapped')]:
  rows=[]
  for repeat in range(1,3):
   text=(out/f'{platform}-{mode}-{size}-{repeat}.log').read_text()
   rows.extend([r for r in [[float(v) for v in line.split()[2:]] for line in text.splitlines() if line.startswith('frame sample:')] if r[0]>=241])
  summary['pooled'].append({'platform':platform,'mode':mode,'output':size,'samples':len(rows),'interval_ms':metrics(1),'present_ms':metrics(11)})
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
