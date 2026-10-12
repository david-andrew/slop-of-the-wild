#!/usr/bin/env python3
"""Round 72 fixed crops, exact material/geometry contracts and review page. No renders."""
import base64
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops
from enemy_model_check import read_model
from round71_character_report import textures
from round72_character_check import base

OUT,ROOT=base.OUT,base.ROOT
CROPS={'blue-camp':(610,277,800,535),'combat':(802,234,1090,345),
       'monk':(793,154,964,455),'husks':(398,313,907,720)}
NOTES={
 'blue-camp':'Production camp: smaller nostrils, curved dark mouth, ivory teeth and a continuous slate muzzle.',
 'combat':'Production combat: red enemies retain their existing appearance.',
 'monk':'Brighter bronze edging and cloth pigment aligned to the existing pleats. Same close-up camera and lighting.',
 'husks':'Warm weathered stone plates over dark oxidised metal, with stronger seam and circuit contrast.'}

def main():
    old=OUT/'before/assets/models/bokoblin.mdl';new=ROOT/'assets/models/bokoblin.mdl'
    a,b=map(read_model,(old,new));assert a==b,'Bokoblin vertex/index/rig/UV/grouping changed'
    for i,(x,y) in enumerate(zip(textures(old),textures(new))):
        for variant in (0,2,3):assert x[variant]==y[variant],(i,variant)
    geom=(OUT/'geometry-check.log').read_text();assert 'PASS:' in geom
    for name,marker in [('enemy_model_check','PASS Bokoblin:'),('combat_check','combat geometry PASS:')]:
        log=(OUT/f'{name}.log').read_text();assert marker in log and 'panic:' not in log
    weather=json.loads((OUT/'weather/contrast.json').read_text())
    assert not weather['failures'] and len(weather['results'])==12
    minimum=min(min(r['contrast'],r['paired_separation']) for r in weather['results'].values())
    assert minimum>=.12
    source_manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'game').glob('*.jo'))}
    assert json.loads((OUT/'after/sources.json').read_text())==source_manifest
    views=list(CROPS)
    views += [f'{view}-{variant}' for view in ('blue-camp','combat') for variant in ('red','blue','black','green')]
    images={};measurements={}
    for name in views:
        view=name if name in CROPS else name.rsplit('-',1)[0]
        crops={phase:Image.open(OUT/phase/f'{name}.png').convert('RGB').crop(CROPS[view]) for phase in ('before','after')}
        pair=Image.new('RGB',(crops['before'].width*2,crops['before'].height))
        images[name]={}
        for i,(phase,im) in enumerate(crops.items()):
            path=OUT/phase/f'{name}-crop.png';im.save(path)
            images[name][phase]=str(path)
            pair.paste(im,(i*im.width,0))
        pair.save(OUT/f'{name}-crop-pair.png')
        diff=ImageChops.difference(crops['before'],crops['after'])
        pixels=diff.get_flattened_data() if hasattr(diff,'get_flattened_data') else diff.getdata()
        changed=sum(max(p)>3 for p in pixels)
        measurements[name]={'crop':CROPS[view],'changed_pixels_rgb_gt_3':changed,'total_pixels':diff.width*diff.height}
        if name in ('blue-camp','monk','husks'):assert changed>100,name
        if name=='combat' or name.endswith(('-red','-black','-green')):assert changed==0,(name,changed)
    result={'baseline':base.BASELINE,'models':{'bokoblin':{'vertices':sum(len(p[3]) for p in b['parts']),
        'triangles':sum(len(p[4])//3 for p in b['parts']),'asset_parts':len(b['parts']),
        'exact_geometry_rig_uv_weights_vertex_colors':'unchanged','unchanged_texture_variants':['red','black','green']}},
        'procedural_geometry':geom.strip(),'weather_passed':12,'weather_minimum':minimum,
        'checks':['enemy_model_check','combat_check','weather_silhouette_check','procedural_geometry'],
        'production_variants':['red','blue'],'fixture_only_variants':['black','green'],
        'sources':source_manifest,'baker_sha256':hashlib.sha256((ROOT/'tools/bake_models.jo').read_bytes()).hexdigest(),
        'bokoblin_sha256':hashlib.sha256(new.read_bytes()).hexdigest(),'measurements':measurements}
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    page='''<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;font:14px var(--font-sans,system-ui);color:var(--foreground,#232323)}
.controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0}
select,button{font:inherit;color:inherit;background:var(--background,#fff);border:1px solid var(--border,#aaa);padding:7px;border-radius:5px}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:10px}.pair p{margin:8px 0}.pair img{display:block;width:100%;height:330px;object-fit:contain;background:var(--muted,#eee)}
.note{line-height:1.5;color:var(--muted-foreground,#626262)}@media(max-width:450px){.pair img{height:260px}}
</style></head><body><div class="controls"><select id="view" aria-label="Material comparison"></select><button id="prev">Previous</button><button id="next">Next</button></div>
<div class="pair"><div><p>Before · bcccdbb</p><img id="before" alt="Before crop"></div><div><p>After · round 72</p><img id="after" alt="After crop"></div></div>
<p id="note" class="note"></p><p class="note">Geometry and draw grouping preserved. Model/contact checks pass; weather silhouettes pass 12/12 (minimum MINIMUM). Red, black and green textures are byte-identical. Black/green are fixture-only variants.</p>
<script>const images=IMAGES,notes=NOTES;const select=document.getElementById('view');for(const name of Object.keys(images))select.add(new Option(name.replaceAll('-',' '),name));function show(){const n=select.value;for(const phase of ['before','after'])document.getElementById(phase).src=images[n][phase];document.getElementById('note').textContent=notes[n]||'Identical production camera and enemy pose with only the texture selector overridden; includes the unused variants for regression review.'}select.onchange=show;document.getElementById('prev').onclick=()=>{select.selectedIndex=(select.selectedIndex+select.length-1)%select.length;show()};document.getElementById('next').onclick=()=>{select.selectedIndex=(select.selectedIndex+1)%select.length;show()};show();console.log('12 matched crop pairs; exact mesh and 12/12 silhouette checks passed.');</script></body></html>'''
    page=page.replace('MINIMUM',f'{minimum:.2%}').replace('IMAGES',json.dumps(images)).replace('NOTES',json.dumps(NOTES))
    (OUT/'comparison-inline.html').write_text(page)
    for phases in images.values():
        for path in phases.values():page=page.replace(path,'data:image/png;base64,'+base64.b64encode(Path(path).read_bytes()).decode())
    (OUT/'comparison.html').write_text(page)
    print(json.dumps({k:v for k,v in result.items() if k not in ('sources','measurements')},indent=2))

if __name__=='__main__':main()
