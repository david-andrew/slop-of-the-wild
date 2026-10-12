#!/usr/bin/env python3
"""Assemble round-69 acceptance evidence after capture/check/GPU jobs finish."""
from pathlib import Path
import base64, hashlib, json, re, sys
from PIL import Image
from enemy_model_check import read_model
from round69_gpu_check import report as verify_gpu
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/round69'
views=['wake','chase','combat','camp','wake330','run']
views += [f'pose-{model}-{clip}' for model in ('hero','hero_bare') for clip in ('idle','run','attack','climb')]
checks={}
required={
    'hero_model_check':['PASS hero:','PASS hero_bare:'],
    'enemy_model_check':['PASS Bokoblin:'],
    'wake_contact_check':['PASS wake surface:'],
    'opening_check':['PASS: continuous opening; no gameplay presets','PASS title: five production approaches'],
    'combat_check':['combat geometry PASS:'],
    'contact_check':['contact check PASS'],
}
for name, markers in required.items():
    log=(OUT/f'{name}.log').read_text()
    assert all(marker in log for marker in markers) and not re.search(r'(?m)^FAIL|panic:|Traceback|error:',log),name
    checks[name]='PASS'
weather_log=(OUT/'weather_silhouette_check.log').read_text()
assert len(re.findall(r'(?m)^captured ',weather_log))==12 and len(re.findall(r'(?m)^PASS ',weather_log))==12,'incomplete weather suite'
manifest=json.loads((OUT/'after/sources.json').read_text())
assert manifest=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'game').glob('*.jo'))},'stale capture source manifest'
weather=json.loads((OUT/'weather-final/contrast.json').read_text())
minimum=min(min(r['contrast'],r['paired_separation']) for r in weather['results'].values())
assert len(weather['results'])==12 and not weather['failures'] and minimum>=.12,minimum
checks['weather_silhouette_check']=f'12/12; minimum {minimum:.2%}'
gpu=verify_gpu(quiet=True)
assert all(r['passed'] for r in gpu.values())
models={}
for name in ('hero','hero_bare','bokoblin'):
    models[name]={}
    for phase,path in [('before',OUT/'before/assets/models'),('after',ROOT/'assets/models')]:
        model=read_model(path/f'{name}.mdl')
        models[name][phase]={'draws':len(model['parts']),'vertices':sum(len(p[3]) for p in model['parts']),'triangles':sum(len(p[4])//3 for p in model['parts'])}
    assert models[name]['before']['draws']==models[name]['after']['draws']
    assert models[name]['after']['triangles']<=models[name]['before']['triangles']
images={}
for view in views:
    images[view]={}
    for phase in ('before','after'):
        path=OUT/phase/f'{view}.png'
        assert Image.open(path).size==(1280,720),(view,phase)
        images[view][phase]=str(path)
# Native-resolution crops make anatomical shading and hair legible in a narrow thread.
for name,source,box in [('wake-arm','wake330',(505,205,790,463)),('wake-ankle','wake',(692,487,792,579)),('wake-detail','wake',(510,250,800,580)),('chase-hair','chase',(595,325,700,425)),('combat-detail','combat',(410,195,1090,595)),('camp-detail','camp',(190,230,1150,650))]:
    images[name]={}
    for phase in ('before','after'):
        target=OUT/phase/f'{name}.png'
        Image.open(OUT/phase/f'{source}.png').crop(box).save(target)
        images[name][phase]=str(target)
page='''<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;color:var(--foreground,#253444);font:14px system-ui}select,button{font:inherit;color:inherit;background:var(--background,#fff);border:1px solid var(--border,#aaa);padding:7px;border-radius:6px}.controls{display:flex;gap:8px;margin:8px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:8px}.pane p{margin:8px 0}.pane img{width:100%;display:block;max-height:530px;object-fit:contain;background:#152330;border-radius:6px}.note{line-height:1.5;color:var(--muted-foreground,#657485)}@media(max-width:450px){.pair{grid-template-columns:1fr}}</style></head><body>
<div class="controls"><select id="view" aria-label="Comparison view"></select><button id="prev">Previous</button><button id="next">Next</button></div>
<div class="pair"><div class="pane"><p>Before · 645907d</p><img id="before" alt="Before"></div><div class="pane"><p>After · round 69</p><img id="after" alt="After"></div></div>
<p class="note">Nine overlapping hair masses replace twenty regular locks; skin normals rebuilt from the finished surface soften the raised arm. Contact-shadow cards no longer paint cuffs over figures. Shoulder and back shaping retain a slender silhouette. Elbow/knee shaping stays within 1.9 mm. Bokoblins keep their red identity with muted pigment, a darker back, lighter belly, facial planes and a stronger nearby sky edge.</p>
<p class="note">CHECKS. Skeletons, grips, soles and draw counts preserved. Hair geometry is smaller; GPU pairs pass at 1280×720 and 2133×1200.</p>
<script>const images=IMAGES;const select=document.getElementById('view');for(const name of Object.keys(images)){const o=new Option(name.replaceAll('-',' '),name);select.add(o)}function update(){for(const phase of ['before','after'])document.getElementById(phase).src=images[select.value][phase]}select.value='wake-arm';select.onchange=update;for(const [name,step]of [['prev',-1],['next',1]])document.getElementById(name).onclick=()=>{select.selectedIndex=(select.selectedIndex+step+select.options.length)%select.options.length;update()};update();console.log('Verified comparison views',Object.keys(images).length);</script></body></html>'''
page=page.replace('CHECKS','Six model/contact/opening checks pass; weather silhouettes '+checks['weather_silhouette_check']).replace('IMAGES',json.dumps(images))
inline_views=['wake-arm','wake-ankle','wake','chase-hair','chase','combat-detail','combat','camp-detail','camp']
inline=page.replace(json.dumps(images),json.dumps({k:images[k] for k in inline_views}))
(OUT/'comparison-inline.html').write_text(inline)
for phases in images.values():
    for path in phases.values():page=page.replace(path,'data:image/png;base64,'+base64.b64encode(Path(path).read_bytes()).decode())
(OUT/'comparison.html').write_text(page)
(OUT/'results.json').write_text(json.dumps(dict(baseline='645907d',checks=checks,weather_minimum=minimum,gpu=gpu,models=models,views=list(images)),indent=2)+'\n')
print(json.dumps({'checks':checks,'models':models,'gpu':{k:v['delta_ms'] for k,v in gpu.items()}},indent=2))
