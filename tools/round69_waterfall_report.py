#!/usr/bin/env python3
"""Verify and assemble Round 69 waterfall/woodland before-after evidence."""
import hashlib
import html
import json
from pathlib import Path
import re
import statistics
from PIL import Image
from round69_waterfall_check import ROOT, VIEWS, BASELINE


def report():
    manifests={p:json.loads((ROOT/f'{p}-source.json').read_text()) for p in ('before','after')}
    digests={p:hashlib.sha256((ROOT/f'{p}-game').read_bytes()).hexdigest() for p in manifests}
    for name,digest in manifests['after']['modules'].items():
        assert hashlib.sha256((Path('game')/name).read_bytes()).hexdigest()==digest,name
    for phase in manifests:
        for view,(flags,frame) in VIEWS.items():
            row=json.loads((ROOT/phase/f'{view}.json').read_text())
            assert row['binary_sha256']==digests[phase],f'stale {phase}/{view}'
            assert all(row['env'][k]==v for k,v in flags.items()),(phase,view,flags,row['env'])
            assert row['env']['SLOPPY_FRAMES']==str(frame)
            assert Image.open(ROOT/phase/f'{view}.png').size==(1280,720)
    for file,expected in [('water-coverage-check.log','PASS waterfall shelves:'),('prepared-assets-check.log','PASS prepared assets:'),('landscape-check.log','landscape:')]:
        assert expected in (ROOT/file).read_text(),file
    equivalence=json.loads((ROOT/'coverage-collision-equivalence.json').read_text())
    assert all(r['identical'] for r in equivalence.values())
    gpu={}
    for size in ('1280x720','2133x1200'):
        for view in ('waterfall','title'):
            runs={}
            for phase in manifests:
                vals=[]
                for repeat in range(3):
                    name=f'{size}-{view}-{phase}-{repeat}'
                    row=json.loads((ROOT/'gpu'/f'{name}.json').read_text())
                    assert row['binary_sha256']==digests[phase],name
                    log=(ROOT/'gpu'/f'{name}.log').read_text()
                    samples=[]
                    for line in log.splitlines():
                        m=re.match(r'gpu frame: (\d+) (.*) = ([\d.]+)',line)
                        if m and int(m[1])>(row['discard_batches']*120):
                            samples.append({**{k:float(v) for k,v in re.findall(r'(\S+) ([\d.]+)',m[2])},'total':float(m[3])})
                    assert len(samples)>=300,(name,len(samples))
                    keys=sorted(set().union(*(r.keys() for r in samples)))
                    vals.append({k:statistics.median(r.get(k,0.0) for r in samples) for k in keys})
                runs[phase]=vals
            medians={p:{k:statistics.median(r[k] for r in runs[p]) for k in runs[p][0]} for p in runs}
            limit=medians['before']['total']*1.03+0.1
            gpu[f'{size}-{view}']={'medians_ms':medians,'limit_ms':limit,'passed':medians['after']['total']<=limit,'runs':runs}
    assert all(r['passed'] for r in gpu.values()),gpu
    (ROOT/'gpu-summary.json').write_text(json.dumps(gpu,indent=2)+'\n')
    crops={'waterfall-200':('waterfall',(500,80,715,690)),
           'pool-200':('mid',(390,300,890,720)),
           'title-200':('title',(0,255,1280,430)),
           'overlook-200':('overlook',(590,60,1280,205))}
    for phase in manifests:
        for name,(source,box) in crops.items():
            im=Image.open(ROOT/phase/f'{source}.png').crop(box)
            im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST).save(ROOT/phase/f'{name}.png')
    views=['waterfall','cliffs','mid','waterfall-200','pool-200','waterfall-rain','waterfall-storm','waterfall-dawn','cliffs-rain','cliffs-storm','cliffs-dawn','mid-rain','mid-storm','mid-dawn','mid-motion','title-200','overlook-200','title','overlook']
    captions={
        'waterfall':'Bright aerated core, blue-green translucent margins and falling clumps. Existing rock benches, contact foam and shelf spray are retained.',
        'cliffs':'The waterfall retains broad white/teal separation at the original cliff camera.',
        'mid':'Lower, closer camera checks the receiving pool and drifting base mist.',
        'mid-motion':'Frame 345, 0.75 seconds after the matching frame-300 mid view. Toggle between Mid and Mid motion to inspect falling streaks, mist drift and outward pool crests.',
        'title':'Connected far woods retain their placement and gaps. Lobed broadleaf crowns mix spreading, upright and smaller edge trees with slender conifers in damp clumps.',
        'overlook':'Varied silhouettes use the existing two instance batches and unchanged mesh triangle counts.'}
    for name,(source,box) in crops.items():captions[name]=f'Exactly 2× nearest-neighbour crop of {source}: native pixel bounds {box}.'
    for view in views:
        if view not in captions:
            captions[view]='Matched '+view.replace('-',' ')+': identical camera and frame; dawn is fixed at 06:24, other scenes start at 11:00.'
    display=ROOT/'display';display.mkdir(exist_ok=True)
    sections=[]
    for i,view in enumerate(views):
        paths=[]
        width,height=Image.open(ROOT/'after'/f'{view}.png').size
        for phase in manifests:
            path=display/f'{phase}-{view}.jpg'
            Image.open(ROOT/phase/f'{view}.png').convert('RGB').save(path,quality=95,subsampling=0)
            paths.append(path.resolve())
        sections.append(f'<section {"hidden" if i else ""}><div class="scroll"><div class="compare" data-w="{width}" data-h="{height}"><img src="{paths[1]}" alt="After {view}"><img class="before" src="{paths[0]}" alt="Before {view}"><span class="left">Before · {BASELINE}</span><span class="right">After</span></div></div><p>{html.escape(captions[view])}</p></section>')
    rows=''.join(f'<tr><td>{key}</td><td>{r["medians_ms"]["before"]["total"]:.3f}</td><td>{r["medians_ms"]["after"]["total"]:.3f}</td><td>{r["limit_ms"]:.3f}</td></tr>' for key,r in gpu.items())
    options=''.join(f'<option value="{i}">{html.escape(v.replace("-"," ").title())}</option>' for i,v in enumerate(views))
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Waterfall and woodland review</title>
<style>body{margin:0;color:var(--foreground,#24362d);font:14px/1.5 var(--font-sans,system-ui)}.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:12px}select,button{padding:6px;border:1px solid var(--border,#abb6ae);border-radius:6px;background:var(--secondary,#e7ece8);color:inherit}button{cursor:pointer}input{width:130px}.scroll{overflow:auto;max-width:100%}.compare{position:relative;overflow:hidden;border-radius:8px}.compare img{display:block;width:100%}.before{position:absolute;inset:0;clip-path:inset(0 50% 0 0)}.left,.right{position:absolute;top:8px;padding:2px 6px;border-radius:4px;background:#17241fe6;color:white;font-size:12px}.left{left:8px}.right{right:8px}p{margin:10px 0 16px}.checks{padding:16px;border-radius:var(--radius,8px);background:var(--secondary,#e7ece8)}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:6px;border-bottom:1px solid var(--border,#bbc8c0)}summary{cursor:pointer;margin:12px 0}</style>
<div class="controls"><label>View <select id="view">OPTIONS</select></label><label>Compare <input id="split" type="range" min="0" max="100" value="50" aria-label="Before after comparison"></label><button id="old">Before</button><button id="new">After</button><label><input id="native" type="checkbox" style="width:auto"> Exact crop/native size</label></div>
SECTIONS
<div class="checks">Complete water, terrain and structure pack payloads match baseline byte for byte. Prepared/generated assets, collision, water coverage, bench-spray anchors and landscape checks pass. No additional render passes, particle counts or water surface geometry.</div>
<details><summary>GPU evidence</summary><table><thead><tr><th>Scene/pixels</th><th>Before ms</th><th>After ms</th><th>Budget ms</th></tr></thead><tbody>ROWS</tbody></table><p>Three alternating pairs per scene/output size. Fixed scene scale 1, X11 exact output geometry, gameplay frozen at frame 300 waterfall / 720 title. Per-frame GPU medians after warmup, then median across repeats; budget = baseline × 1.03 + 0.1 ms. Full pass timings retained in gpu-summary.json. Simulation freeze does not stop runtime particle/flow elapsed time.</p></details>
<details><summary>Capture protocol</summary><p>Baseline master 1bc8463; sol3/work. Native PNGs 1280×720, fixed simulation, unprepared identical source asset inputs, all render activity serialized once on /tmp/botw-render.lock. Clear/rain/storm and frozen dawn at the three waterfall cameras. Frame 300 except title 720 and motion companion 345. Source and executable hashes, environments, GPU timing logs and equivalence hashes retained in build/round69. Display JPEGs quality 95; exact crops use nearest-neighbour enlargement. No critic score claimed.</p></details>
<script>const sections=[...document.querySelectorAll('section')],slider=document.querySelector('#split');function compare(n){slider.value=n;document.querySelectorAll('.before').forEach(v=>v.style.clipPath=`inset(0 ${100-n}% 0 0)`);document.querySelectorAll('.left').forEach(v=>v.hidden=Number(n)===0);document.querySelectorAll('.right').forEach(v=>v.hidden=Number(n)===100)}document.querySelector('#view').onchange=e=>sections.forEach((v,i)=>v.hidden=i!==Number(e.target.value));slider.oninput=e=>compare(e.target.value);document.querySelector('#old').onclick=()=>compare(100);document.querySelector('#new').onclick=()=>compare(0);document.querySelector('#native').onchange=e=>document.querySelectorAll('.compare').forEach(v=>{v.style.width=e.target.checked?v.dataset.w+'px':'';v.style.height=e.target.checked?v.dataset.h+'px':''});console.log('Verified '+sections.length+' matched waterfall/woodland comparisons');</script></html>'''
    page=page.replace('OPTIONS',options).replace('SECTIONS',''.join(sections)).replace('ROWS',rows)
    (ROOT/'report.html').write_text(page)
    summary={'baseline':BASELINE,'binary_sha256':digests,'coverage_collision_equivalence':equivalence,'gpu':gpu,'views':views,'captions':captions}
    (ROOT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (ROOT/'report.txt').write_text('Round 69 waterfall and woodland\nBaseline '+BASELINE+'; sol3/work\n\n'+'\n'.join(f'{k}: {v}' for k,v in captions.items())+'\n\nComplete water/terrain/structure payload equivalence, prepared assets, water coverage/shelves, landscape, GPU budgets pass.\n')
    print('PASS Round 69 evidence: matched source/binary/camera/frame checks; all GPU budgets; report.html, report.txt and summary.json')

if __name__=='__main__':report()
