#!/usr/bin/env python3
"""Keep compact, reproducible round-70 measurements; complete captures required."""
from pathlib import Path
import hashlib,json,re
from performance_bench import read_run, percentile
from performance_tail_report import analyze
ROOT=Path('build/round70')
assert 'heat source differential PASS:' in (ROOT/'heat-verified.log').read_text()
for name,digest in json.loads((ROOT/'heat-verified/sources.json').read_text()).items():
 assert hashlib.sha256((Path('game')/name).read_bytes()).hexdigest()==digest,'Source changed after heat differential'
GROUPS={'fire_before':'before-720','fire_after':'final2-720',
        'forest_before':'forest-large','forest_after':'final2-forest-large',
        'probe_x11':'present-before/gpu','probe_wayland':'present-before/paced',
        'probe_mailbox':'present-before/mailbox','probe_noqueue':'present-before/gpu-noqueue'}
result={'base_revision':'645907d','protocol':'fixed scale 1; frames >=241; exact X11 output; native Wayland output verified by capture; no outliers removed','groups':{},
        'sample_columns':['sample_n','interval_ms','game_wall_ms','gap_ms','game_thread_ms','uploads','upload_bytes','game_voluntary_switches','game_involuntary_switches','game_user_ms','game_system_ms','present_ms','residual_gap_ms','runtime_thread_ms','runtime_voluntary_switches','runtime_involuntary_switches','runtime_user_ms','runtime_system_ms'],
        'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('game').glob('*.jo'))},
        'heat_source_differential':(ROOT/'heat-verified.log').read_text().strip(),
        'journey_before':json.loads((ROOT/'journey-before.json').read_text()),
        'journey_after':json.loads(Path('build/journey-check/metrics.json').read_text())}
for label,directory in GROUPS.items():
 runs={};pooled=[]
 for p in sorted((ROOT/directory).glob('*-1-*.log')):
  run=read_run(p) # requires full frame sample count and final matching pixels
  text=p.read_text();summary,raw=analyze(text,allow_trace_gaps=True)
  rows=[r for r in raw['samples'] if r[0]>=241];pooled+=rows
  keep={k:summary[k] for k in ['cpu_wall','cpu_thread','present','interval','residual_gap']}
  if 'gpu_total' in summary:keep['gpu_total']=summary['gpu_total']
  keep.update(executable_sha256=run['metadata']['executable_sha256'],flags=run['metadata']['flags'],output=run['output'],load_start=run['load_start'],load_end=run['metadata'].get('load_end'),png_sha256=hashlib.sha256(Path(str(p)[:-4]+'.png').read_bytes()).hexdigest())
  traces=raw['cpu_traces']
  def detail(r):
   n=int(r[0])-1;t=traces.get(n)
   return {'frame':n,'sample':r,'stages':t['stages'][:4] if t else None,'stage_wall_ms':float(re.search(r'^long cpu ([\d.]+)',t['line'])[1]) if t else None,'gpu':raw['gpu_frames'].get(n,{}).get('total')}
  keep['worst_intervals']=[detail(r) for r in sorted(rows,key=lambda r:-r[1])[:4]]
  keep['worst_presentations']=[detail(r) for r in sorted(rows,key=lambda r:-r[11])[:4]]
  memory=[tuple(map(int,r)) for r in re.findall(r'^probe memory: (\d+) (\d+) (\d+) (\d+)$',text,re.M)]
  if memory:
   steady=[r for r in memory if r[0]>=240]
   keep['live_allocations']={'min':min(r[1] for r in steady),'max':max(r[1] for r in steady),'first':steady[0][1],'last':steady[-1][1]}
   keep['steady_target_dimensions']=sorted(set((r[2],r[3]) for r in steady))
   keep['target_resize_events']=re.findall(r'^probe (?:scene|smoke) resize:.*$',text,re.M)
   keep['upload_waits']=[{'frame':int(n),'wall_ms':float(ms),'bytes':int(b),'previous_bytes':int(old)} for n,ms,b,old in re.findall(r'^probe upload: frame (\d+) wall ([\d.]+) bytes (\d+) previous (\d+)$',text,re.M)]
  keep['steady_shader_requests']=[int(n) for n in re.findall(r'^shader request: frame (\d+)$',text,re.M) if int(n)>=240]
  keep['queue_bound_active']='gpu queue:' in text
  runs[p.stem]=keep
 assert len(runs)==(2 if label in ('fire_before','fire_after','forest_before') else 1),(label,runs.keys())
 stats={name:{k:f([r[col] for r in pooled]) for k,f in [('p50',lambda v:percentile(v,.5)),('p95',lambda v:percentile(v,.95)),('p99',lambda v:percentile(v,.99)),('worst',max)]} for name,col in [('cpu_wall',2),('cpu_thread',4),('present',11),('interval',1)]}
 result['groups'][label]={'runs':runs,'pooled':stats}
 settings=ROOT/directory/'probe-settings.json'
 if settings.exists():result['groups'][label]['probe_settings']=json.loads(settings.read_text())
 for name,run in runs.items():print(label,name,'cpu wall/thread p99',run['cpu_wall']['p99'],run['cpu_thread']['p99'],'present worst',run['present']['worst'],'interval worst',run['interval']['worst'])
b=result['groups']['fire_before']['runs'];a=result['groups']['fire_after']['runs']
assert b.keys()==a.keys()
for k in b:
 flags=lambda r:{n:v for n,v in r['flags'].items() if n!='SLOPPY_SCREENSHOT'}
 assert flags(b[k])==flags(a[k]),'Fire capture flags differ'
for name,digest in json.loads((ROOT/'after/sources.json').read_text()).items():
 assert hashlib.sha256((Path('game')/name).read_bytes()).hexdigest()==digest,'Source changed after pose/final capture'
result['fire_pixels_equal']=all(a[k]['png_sha256']==b[k]['png_sha256'] for k in b)
assert result['fire_pixels_equal'],'Fire optimization changed matched final pixels'
assert not next(iter(result['groups']['probe_noqueue']['runs'].values()))['queue_bound_active'],'No-queue diagnostic still submitted fences'
Path('docs/ROUND70_RUNTIME_EVIDENCE.json').write_text(json.dumps(result,indent=2)+'\n')
