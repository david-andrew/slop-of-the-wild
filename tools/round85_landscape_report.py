#!/usr/bin/env python3
"""Build paired images, a local review gallery and the measured p99 report.

No game is launched. Raw evidence remains under build/round85/landscape.
"""
import hashlib
import json
from pathlib import Path
import statistics
import sys
sys.dont_write_bytecode = True
from PIL import Image, ImageChops, ImageDraw
from round85_landscape_capture import OUT, ROOT, VIEWS, PERF_VIEWS, pairs

NAMES = {'cliffs':'Waterfall cliffs','pool':'Pool','close':'2 m rock','crown':'Waterfall crown',
         'overview':'Dawn overview','overview-day':'Day overview','overlook':'Cave approach','plateau-overlook':'Plateau overlook',
         'forest':'Forest edge','temple':'Temple entrance','temple-side':'Temple flank',
         's2ceil':'Jaba ceiling','s2roof-wide':'Jaba roof from floor','s2eave':'Jaba low eave','s2shaft':'Jaba lift cap','s2up-pan':'Jaba raised camera'}

def main():
    # Refuse a stale final gallery or timings from a superseded binary.
    hashes = json.loads((OUT/'after/sources.json').read_text())
    for name,digest in hashes.items():
        assert hashlib.sha256((ROOT/'game'/name).read_bytes()).hexdigest()==digest, name
    binaries = {phase:hashlib.sha256((OUT/phase/'game-bin').read_bytes()).hexdigest() for phase in ('before','after')}
    pairs()
    images = {}
    differences = {}
    for view in VIEWS:
        paths = [OUT/p/(view+'.png') for p in ('before','after')]
        assert all(p.exists() for p in paths),f'missing before/after view: {view}'
        captures=[json.loads(p.with_suffix('.json').read_text()) for p in paths]
        for phase,capture in zip(('before','after'),captures): assert capture['binary_sha256']==binaries[phase],view
        flags=[capture['env'] for capture in captures]
        for key in ('BOTW_CAM','BOTW_AT','BOTW_SHRINE','BOTW_HOUR','BOTW_WEATHER','BOTW_TIMESCALE','BOTW_SCALE','SLOPPY_INPUT','SLOPPY_FRAMES'):
            assert flags[0].get(key)==flags[1].get(key),(view,key)
        differences[view] = ImageChops.difference(Image.open(paths[0]).convert('RGB'),Image.open(paths[1]).convert('RGB')).getbbox()
        images[view] = {}
        for phase,path in zip(('before','after'),paths):
            webp = path.with_suffix('.webp')
            Image.open(path).save(webp,quality=92)
            images[view][phase] = str(webp)
    motion={}
    for view in ('cliffs','pool'):
        motion[view]={}
        for phase in ('before','after'):
            frames=[OUT/phase/(view+'-motion')/f'frame-{n}.png' for n in (300,310,320)]
            if not all(p.exists() for p in frames):continue
            # Inspect the falling sheet, excluding moving mist and scenery.
            region = (935,240,1035,550) if view=='cliffs' else (615,130,680,350)
            changed=ImageChops.difference(Image.open(frames[0]).convert('RGB').crop(region),Image.open(frames[-1]).convert('RGB').crop(region)).getbbox() is not None
            assert changed,'falling-water sequence must advance'
            motion[view][phase]={'frames':[str(p) for p in frames],'advances':changed,'sheet_region':region}
        for n in (300,310,320):
            paths=[OUT/p/(view+'-motion')/f'frame-{n}.png' for p in ('before','after')]
            if not all(p.exists() for p in paths):continue
            im=Image.new('RGB',(1280,1488),'#202629');draw=ImageDraw.Draw(im)
            for i,p in enumerate(paths):
                im.paste(Image.open(p),(0,i*744+24));draw.text((12,i*744+6),('BEFORE 500126f' if i==0 else 'AFTER')+f' / {view} / frame {n}',fill='white')
            im.save(OUT/f'{view}-motion-{n}-pair.png')
    measurements = {}
    for view in PERF_VIEWS:
        after=sorted((OUT/'after').glob(view+'-perf-*.json'))
        repetitions=[p.stem.rsplit('-',1)[1] for p in after]
        phases={phase:[json.loads((OUT/phase/(view+'-perf-'+rep+'.json')).read_text()) for rep in repetitions] for phase in ('before','after')}
        for phase,rows in phases.items():
            for row in rows: assert row['binary_sha256']==binaries[phase],(view,phase)
        if any(len(rows)<3 for rows in phases.values()): continue
        values = {phase:{key:statistics.median(r[key] for r in rows) for key in ('frame_p99_ms','cpu_p99_ms')} for phase,rows in phases.items()}
        passed = all(values['after'][key] <= values['before'][key]*1.03+0.10 for key in ('frame_p99_ms','cpu_p99_ms'))
        measurements[view] = {'runs':phases,'median':values,'passed':passed}
    report = {'baseline':'500126f','attribution':'Final build includes merged master work; see docs/rounds/ROUND85_LANDSCAPE.md.','protocol':'GTX 1070, Vulkan/X11, native 1280x720, scale 1, mailbox, fixed 1/60 simulation; scene frozen at frame 360, first 480 intervals excluded. Matched repetition IDs, alternating phase order; medians of run p99. Budget: 3% + 0.10 ms, frame interval and callback wall time. These are callback intervals, not measured scanout.',
              'image_difference_bounds':differences,'motion':motion,'performance':measurements}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    table = ''.join(f'<tr><th>{NAMES[v]}</th><td>{r["median"]["before"]["frame_p99_ms"]:.3f}</td><td>{r["median"]["after"]["frame_p99_ms"]:.3f}</td><td>{"Pass" if r["passed"] else "Review"}</td></tr>' for v,r in measurements.items())
    passed = len(measurements)==6 and all(r['passed'] for r in measurements.values())
    status = 'All six frame and callback-wall budgets pass.' if len(measurements)==6 and all(r['passed'] for r in measurements.values()) else 'Performance budget failed or measurements incomplete; inspect report.json.'
    page = '''<!doctype html><html><head><meta charset="utf-8"><style>
body{font:14px var(--font-sans,system-ui);color:var(--foreground);margin:0}nav{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 12px}button{border:1px solid var(--border);color:var(--foreground);background:var(--secondary);border-radius:6px;padding:5px 8px;cursor:pointer}button[aria-pressed=true]{background:var(--accent-surface);border-color:var(--accent)}figure{position:relative;margin:0;aspect-ratio:1280/720;overflow:hidden;border-radius:var(--radius,8px)}figure img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}#before{clip-path:inset(0 50% 0 0)}#divider{position:absolute;left:50%;height:100%;border-left:2px solid white}.tag{position:absolute;top:8px;background:#15191dcc;color:white;border-radius:4px;padding:4px 8px;font-size:12px}.old{left:8px}.new{right:8px}input{width:100%;margin:12px 0 4px;accent-color:var(--accent)}p{color:var(--muted-foreground);line-height:1.45;margin:8px 0}table{width:100%;border-collapse:collapse;font-size:12px}th,td{padding:6px 4px;border-bottom:1px solid var(--border);text-align:right}th:first-child{text-align:left}
</style></head><body><nav id="scenes"></nav><figure><img id="after" alt="Revised game render"><img id="before" alt="Baseline game render"><div id="divider"></div><span class="tag old">Before · 500126f</span><span class="tag new">After</span></figure><input aria-label="Before and after comparison" id="split" type="range" min="0" max="100" value="50"><p id="caption"></p><table><thead><tr><th>Frame p99 · ms</th><th>Before</th><th>After</th><th>Budget</th></tr></thead><tbody>TABLE</tbody></table><p>STATUS Fixed native 1280×720, full scene scale, three alternating pairs per view. First 480 frames excluded; median of each run’s p99. Callback intervals, not scanout. After includes merged master work; attribution is in docs/rounds/ROUND85_LANDSCAPE.md. Raw captures and timings remain in build/round85/landscape.</p><script>
const images=IMAGES,names=NAMES;let scene='cliffs';
const notes={cliffs:'Continuous rock normals, quieter shadow pigment, dipping strata and uneven waterfall channels.',pool:'The lower shoulders and falling sheet from pool level.',close:'Camera exactly 2 m from the unchanged rock collision surface.',crown:'Upper rock banks and waterfall roll.',overview:'More visible turf texture and clustered woodland margins at dawn.', 'overview-day':'The same terrain and forest edges in daylight.',overlook:'Production chase camera on the cave approach; a performance control.', 'plateau-overlook':'The opening overlook, facing the plateau.',forest:'Production forest view and woodland edge.',temple:'Missing facade stones, fractured entrance courses, fallen rubble and rooted ivy.', 'temple-side':'The damaged entrance from an oblique view.',s2ceil:'Close view of Jaba’s profiled ceiling.', 's2roof-wide':'Floor-level view across the blast chamber roof.', 's2eave':'Looking across the chamfered roof from its low eave.',s2shaft:'The lift cap, inspected separately from the room’s ceiling.', 's2up-pan':'Thin pink and white ceiling overlays removed; the broad structural ribs remain.'};
function render(){for(const phase of ['before','after'])document.getElementById(phase).src=images[scene][phase];document.getElementById('caption').textContent=notes[scene];document.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.scene===scene));}
for(const key of Object.keys(images)){const b=document.createElement('button');b.textContent=names[key];b.dataset.scene=key;b.onclick=()=>{scene=key;render()};document.getElementById('scenes').append(b)}
document.getElementById('split').oninput=e=>{document.getElementById('before').style.clipPath='inset(0 '+(100-e.target.value)+'% 0 0)';document.getElementById('divider').style.left=e.target.value+'%'};render();console.log('Matched landscape comparison: '+Object.keys(images).length+' scenes');
</script></body></html>'''
    page=page.replace('TABLE',table).replace('STATUS',status).replace('IMAGES',json.dumps(images)).replace('NAMES',json.dumps(NAMES))
    (OUT/'review.html').write_text(page)
    print(status)
    for view,row in measurements.items(): print(view,row['median'],row['passed'])
    if not passed: raise SystemExit(1)

if __name__=='__main__': main()
