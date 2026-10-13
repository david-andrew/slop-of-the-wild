#!/usr/bin/env python3
"""Build the local review gallery and compact report from completed fir evidence."""
import base64
import html
import hashlib
import json
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/round94'
CANDIDATE = sys.argv[1] if len(sys.argv) > 1 else 'candidate7'
SCENES = {'snow':'Snow', 'camp':'Camp', 'forest':'Forest', 'forest-firs':'Forest firs', 'overlook':'Overlook'}
LABELS = ['before', 'current', 'after']
CROPS = {'snow':(20,140,585,580), 'camp':(660,0,1280,320),
         'forest':(0,0,1280,720), 'forest-firs':(265,0,970,670), 'overlook':(0,220,1280,630)}

def build():
    checks = json.loads((OUT/'checks/final-results.json').read_text())
    required = {'tree_test', 'vegetation_reach_check', 'vegetation_tail_check',
                'fir_bough_check', 'fir_surface_check', 'round82_plant_surface_check',
                'render_warmup_check', 'production-build', 'asset-warmup', 'tree-visuals'}
    assert required <= checks.keys() and all(checks[name] == 0 for name in required)
    assert json.loads((OUT/'checks/final-source.json').read_text()) == json.loads((OUT/'after-source.json').read_text())
    digest = hashlib.sha256((OUT/'after-game').read_bytes()).hexdigest()
    records, images, image_paths, repeats = {}, {}, {}, {}
    for scene in SCENES:
        paired = json.loads((OUT/f'performance-{CANDIDATE}'/f'{scene}-report.json').read_text())
        assert json.loads((OUT/scene/'after.json').read_text())['sha256'] == paired['binary_sha256']['after'], 'after image must match the measured binary'
        assert paired['binary_sha256']['after'] == digest
        assert json.loads((OUT/scene/'current.json').read_text())['sha256'] == paired['binary_sha256']['before']
        repeats[scene] = len(paired['runs']['after'])
        historical = json.loads((OUT/'rejected-candidate2/performance'/f'{scene}-report.json').read_text())
        records[scene] = dict(passed=paired['passed'], medians=dict(
            before=historical['medians']['before'], current=paired['before'], after=paired['after']))
        images[scene] = {}
        image_paths[scene] = {}
        for label in LABELS:
            images[scene][label] = {}
            image_paths[scene][label] = {}
            for detail in ['full','detail']:
                image = Image.open(OUT/scene/f'{label}.png')
                if detail == 'detail': image = image.crop(CROPS[scene])
                image.thumbnail((1000,720))
                dest = OUT/scene/f'review-{label}-{detail}.webp'
                image.save(dest, quality=90)
                image_paths[scene][label][detail] = str(dest)
                images[scene][label][detail] = 'data:image/webp;base64,' + base64.b64encode(dest.read_bytes()).decode()
    rows = []
    for scene,name in SCENES.items():
        r = records[scene]
        m = r['medians']
        rows.append('| '+name+' | '+' / '.join(f"{m[label]['frame_p99_ms']:.3f}" for label in LABELS)+' | '+
                    ' / '.join(f"{m[label]['thread_p99_ms']:.3f}" for label in LABELS)+' | '+
                    f"{m['after']['draws_min']}–{m['after']['draws_max']}"+' | '+('PASS' if r['passed'] else 'FAIL')+' |')
    report = '\n'.join(['| View | Frame p99 B / C / A (ms) | Main-thread p99 B / C / A (ms) | Draws | Current budget |',
                        '| --- | --- | --- | --- | --- |', *rows])
    (OUT/'performance-summary.md').write_text(report+'\n')
    table = ''.join('<tr><th>'+name+'</th>'+''.join(f"<td>{records[scene]['medians'][label]['frame_p99_ms']:.2f}</td>" for label in LABELS)+
                    f"<td>{records[scene]['medians']['after']['draws_min']}–{records[scene]['medians']['after']['draws_max']}</td></tr>" for scene,name in SCENES.items())
    page = '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><style>
body{font:14px/1.5 var(--font-sans,system-ui);color:var(--foreground,#dde4e1);margin:0}button{font:inherit;background:transparent;color:inherit;border:1px solid var(--border,#46524b);border-radius:7px;padding:5px 10px;cursor:pointer}button[aria-pressed=true]{background:var(--accent-surface,#294b3d);border-color:var(--accent,#83bba3)}nav{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}.row{display:flex;gap:6px;justify-content:space-between;align-items:center}.phase{display:flex;gap:6px}img{display:block;width:100%;border-radius:6px}figure{margin:12px 0}figcaption,.note{font-size:12px;color:var(--muted-foreground,#aab9b1);margin:6px 0}table{border-collapse:collapse;width:100%;font-size:12px;margin:10px 0}th,td{padding:6px 4px;border-bottom:1px solid var(--border,#46524b);text-align:right}th:first-child{text-align:left}strong{font-size:16px}.status{font-size:12px;color:var(--success,#92d1ab)}
</style></head><body>
<strong>Green fir tiers with snow on top</strong><div class="note">Compare the rounded original, the thin current crowns, and the fuller tapered revision.</div>
<nav id="scenes"></nav><div class="row"><div class="phase" id="phases"></div><button id="detail" aria-pressed="true">Detail crop</button></div>
<figure><img id="hero" alt="Matched fir rendering"><figcaption id="caption"></figcaption></figure>
<div class="status">STATUS</div>
<table><thead><tr><th>Frame p99 · ms</th><th>Before</th><th>Current</th><th>After</th><th>Draws</th></tr></thead><tbody>TABLE</tbody></table>
<div class="note">GTX 1070 · Vulkan/X11 · 1280×720 · full scene scale. REPEATS 2,880 frames each, first 720 excluded. Current/after alternate AB/BA/AB; before is retained from the earlier three-way batch. Draw sequences match frame for frame. Frame and main-thread budget: 3% + 0.10 ms against current. Older rounded crowns remain a separate comparison; see their timings above.</div>
<script>
const images=IMAGES,names=NAMES;let scene='snow',phase='after',detail=true;
const desc={before:'Before · rounded boughs from 9d9f7b9 on the c683702 game',current:'Current · c683702 thin sprays',after:'After · green tapered tiers and smaller upper snow caps'};
function render(){document.querySelectorAll('[data-scene]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.scene===scene));document.querySelectorAll('[data-phase]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.phase===phase));document.querySelector('#detail').setAttribute('aria-pressed',detail);const im=document.querySelector('#hero');im.src=images[scene][phase][detail?'detail':'full'];im.alt=names[scene]+': '+desc[phase];document.querySelector('#caption').textContent=desc[phase]+' · '+(detail?'matched detail crop':'full frame');}
for(const [key,name] of Object.entries(names)){const b=document.createElement('button');b.textContent=name;b.dataset.scene=key;b.onclick=()=>{scene=key;render()};document.querySelector('#scenes').append(b)}
for(const p of ['before','current','after']){const b=document.createElement('button');b.textContent=p[0].toUpperCase()+p.slice(1);b.dataset.phase=p;b.onclick=()=>{phase=p;render()};document.querySelector('#phases').append(b)}
document.querySelector('#detail').onclick=()=>{detail=!detail;render()};render();
console.log('Review gallery: 5 scenes, 3 phases, full/detail views.');
</script></body></html>'''
    status = 'All five visual comparisons retained · fir/tree checks pass · all five current performance budgets pass' if all(r['passed'] for r in records.values()) else 'Performance review pending: see local reports'
    repeat_note = 'Runs per version: ' + ', '.join(f'{SCENES[s]} {n}' for s,n in repeats.items()) + '.'
    page = page.replace('REPEATS',html.escape(repeat_note)).replace('STATUS',html.escape(status)).replace('TABLE',table).replace('NAMES',json.dumps(SCENES))
    (OUT/'review.html').write_text(page.replace('IMAGES',json.dumps(images)))
    (OUT/'review-inline.html').write_text(page.replace('IMAGES',json.dumps(image_paths)))
    print(report)

if __name__ == '__main__': build()
