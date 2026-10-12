#!/usr/bin/env python3
"""Round 71 image, material/geometry and frozen GPU evidence. No renders."""
import base64, hashlib, json, re, statistics, struct
from pathlib import Path
from PIL import Image, ImageChops
from collections import Counter
from enemy_model_check import read_model
from round71_character_check import base
ROOT,OUT=base.ROOT,base.OUT
CROPS={'combat':(480,225,690,650),'night':(580,200,728,478),'blue-camp':(610,277,800,535),'monk':(793,154,964,455),'husks':(398,313,907,720)}

def textures(path):
    data=path.read_bytes();p=8
    def u32():
        nonlocal p
        v=struct.unpack_from('<I',data,p)[0];p+=4;return v
    def string():
        nonlocal p
        n=u32();p+=n
    string();string()
    for _ in range(u32()):string();p+=113
    p+=28
    slots,variants=u32(),u32();result=[]
    for variant in range(variants):
        row=[]
        for slot in range(slots):
            w,h=u32(),u32();n=w*h*4
            row.append(hashlib.sha256(data[p:p+n]).hexdigest());p+=n
        result.append(row)
    return list(zip(*result))

def contracts():
    result={}
    for name in ('hero','hero_bare','bokoblin'):
        paths=[OUT/'before/assets/models'/f'{name}.mdl',ROOT/'assets/models'/f'{name}.mdl']
        a,b=map(read_model,paths)
        for key in ('rig','slots','variants','bones'):assert a[key]==b[key],(name,key)
        assert len(a['parts'])==len(b['parts'])
        for x,y in zip(a['parts'],b['parts']):
            assert x[:3]==y[:3] and x[4]==y[4] and len(x[3])==len(y[3])
            for v,w in zip(x[3],y[3]):assert v[:8]==w[:8] and v[12:]==w[12:],f'{name} geometry, UV or weights changed'
        ta,tb=map(textures,paths)
        for i,(x,y) in enumerate(zip(ta,tb)):
            for variant in ([0,1] if name=='hero' else [0,2,3] if name=='bokoblin' else [0]):
                assert x[variant]==y[variant],(name,i,variant,'unrelated texture changed')
        result[name]={'draws':len(b['parts']),'vertices':sum(len(p[3]) for p in b['parts']),'triangles':sum(len(p[4])//3 for p in b['parts']),'geometry_uv_rig_weights':'identical'}
    return result

def gpu_report():
    result={}
    for size in ('1280x720','2133x1200'):
        for view in ('combat','husks'):
            runs={p:[json.loads((OUT/'gpu'/f'{size}-{view}-{i}-{p}.json').read_text()) for i in range(3)] for p in ('before','after')}
            for phase,rows in runs.items():
                assets=OUT/'before/assets/models' if phase=='before' else ROOT/'assets/models'
                expected={n:hashlib.sha256((assets/f'{n}.mdl').read_bytes()).hexdigest() for n in ('hero','hero_bare','bokoblin')}
                binary=hashlib.sha256((OUT/phase/'gpu-game').read_bytes()).hexdigest()
                assert all(r['model_sha256']==expected and r['binary_sha256']==binary for r in rows),'stale GPU evidence'
                for i in range(3):
                    assert Image.open(OUT/'gpu'/f'{size}-{view}-{i}-{phase}.png').size==tuple(map(int,size.split('x'))),'wrong GPU framebuffer size'
            vals={p:statistics.median(r['total'] for r in rows) for p,rows in runs.items()}
            limit=vals['before']*1.03+.1
            result[f'{size}-{view}']={'median_ms':vals,'delta_ms':vals['after']-vals['before'],'limit_ms':limit,'passed':vals['after']<=limit}
    (OUT/'gpu-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    assert all(r['passed'] for r in result.values()),'GPU budget regression'
    return result

def metric(image,mask=None):
    colors=image.getcolors(image.width*image.height) if mask is None else [(n,rgb) for rgb,n in Counter(p for p,m in zip(image.getdata(),mask.getdata()) if m).items()]
    count=sum(n for n,_ in colors)
    values=[0]*256
    sat=value=lum=0.0
    linear=[v/255/12.92 if v/255<=.04045 else ((v/255+.055)/1.055)**2.4 for v in range(256)]
    for n,rgb in colors:
        mx,mn=max(rgb),min(rgb)
        values[mx]+=n
        sat+=n*(mx-mn)/max(mx,1)
        value+=n*mx/255
        lum+=n*sum(linear[c]*k for c,k in zip(rgb,(.2126,.7152,.0722)))
    def quantile(q):
        total=0
        for v,n in enumerate(values):
            total+=n
            if total>=count*q:return v/255
    return {'pixels':count,'saturation_mean':sat/count,'value_mean':value/count,'value_p10':quantile(.1),'value_p90':quantile(.9),'linear_Y_mean':lum/count}

def main():
    models=contracts();gpu=gpu_report()
    weather=json.loads((OUT/'weather/contrast.json').read_text())
    minimum=min(min(r['contrast'],r['paired_separation']) for r in weather['results'].values())
    assert len(weather['results'])==12 and not weather['failures'] and minimum>=.12
    checks={}
    for name,marker in [('enemy_model_check','PASS Bokoblin:'),('hero_model_check','PASS hero_bare:'),('combat_check','combat geometry PASS:')]:
        log=(OUT/f'{name}.log').read_text();assert marker in log and not re.search(r'(?m)^FAIL|panic:|Traceback',log);checks[name]='PASS'
    assert json.loads((OUT/'after/sources.json').read_text())=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'game').glob('*.jo'))},'stale source manifest'
    images={};measurements={}
    for view,box in CROPS.items():
        arrays={p:Image.open(OUT/p/f'{view}.png').convert('RGB') for p in ('before','after')}
        x0,y0,x1,y1=box
        crops={p:a.crop(box) for p,a in arrays.items()}
        # Fixed matched pixels changed by the material edit; excludes static
        # background. This is a change mask, not a complete semantic object mask.
        channels=ImageChops.difference(crops['after'],crops['before']).split()
        mask=ImageChops.lighter(ImageChops.lighter(channels[0],channels[1]),channels[2]).point(lambda v:255 if v>3 else 0)
        if view=='night':
            # Measure the unobscured distant Stalkoblin; the foreground skull
            # overlaps the changed hero shirt. Both stay in the comparison crop.
            from PIL import ImageDraw
            region=Image.new('L',mask.size)
            ImageDraw.Draw(region).rectangle((588-x0,204-y0,644-x0,269-y0),fill=255)
            mask=ImageChops.multiply(mask,region)
        assert mask.histogram()[255]>40,view
        measurements[view]={'crop_box':box,'mask_threshold_rgb':3,'measurement_region':([588,204,644,269] if view=='night' else box),'full_frame':{p:metric(a) for p,a in arrays.items()},'crop':{p:metric(a) for p,a in crops.items()},'changed_material_pixels':{p:metric(a,mask) for p,a in crops.items()}}
        for label in (view,view+'-crop'):images[label]={}
        for phase in arrays:
            full=OUT/phase/f'{view}.png';crop=OUT/phase/f'{view}-crop.png'
            crops[phase].save(crop)
            images[view][phase]=str(full);images[view+'-crop'][phase]=str(crop)
        mask.save(OUT/f'{view}-measurement-mask.png')
        for suffix in ('','-crop'):
            ims=[Image.open(images[view+suffix][p]) for p in ('before','after')]
            pair=Image.new('RGB',(ims[0].width*2,ims[0].height));pair.paste(ims[0],(0,0));pair.paste(ims[1],(ims[0].width,0));pair.save(OUT/f'{view}{suffix}-pair.png')
    result=dict(baseline=base.BASELINE,checks=checks,weather_minimum=minimum,models=models,gpu=gpu,measurements=measurements,
        baker_sha256=hashlib.sha256((ROOT/'tools/bake_models.jo').read_bytes()).hexdigest(),
        final_models_sha256={n:hashlib.sha256((ROOT/'assets/models'/f'{n}.mdl').read_bytes()).hexdigest() for n in models})
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'measurements.json').write_text(json.dumps(measurements,indent=2)+'\n')
    page='''<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;font:14px system-ui;color:var(--foreground,#233)}select,button{font:inherit;color:inherit;background:var(--background,#fff);border:1px solid var(--border,#888);padding:7px;border-radius:5px}.controls{display:flex;gap:8px;margin:8px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:8px}.pair img{display:block;width:100%;max-height:430px;object-fit:contain;background:#142331}.note{line-height:1.5;color:var(--muted-foreground,#657485)}@media(max-width:480px){.pair{grid-template-columns:1fr}}</style></head><body><div class="controls"><select id="view" aria-label="Material comparison"></select><button id="previous">Previous</button><button id="next">Next</button></div><div class="pair"><div><p>Before · 91809e7</p><img id="before" alt="Before"></div><div><p>After · round 71</p><img id="after" alt="After"></div></div><p class="note" id="metrics"></p><p class="note">CHECKS</p><script>const images=IMAGES,measurements=METRICS;const view=document.getElementById('view');for(const n of Object.keys(images))view.add(new Option(n.replaceAll('-',' '),n));function show(){for(const p of ['before','after'])document.getElementById(p).src=images[view.value][p];let m=measurements[view.value.replace('-crop','')].changed_material_pixels;let text=['saturation_mean','value_mean'].map(k=>k.replace('_mean','')+' '+(m.before[k]*100).toFixed(1)+'% → '+(m.after[k]*100).toFixed(1)+'%').join('; ');document.getElementById('metrics').textContent='Matched changed material pixels: '+text+'. HSV display values; fixed crop masks exclude unchanged background. Full-frame and crop statistics are recorded separately.'}view.onchange=show;view.value='blue-camp-crop';for(const [id,d] of [['previous',-1],['next',1]])document.getElementById(id).onclick=()=>{view.selectedIndex=(view.selectedIndex+d+view.length)%view.length;show()};show();console.log('Five views, ten verified full-frame/crop pairs.');</script></body></html>'''
    page=page.replace('CHECKS',f'Model and combat checks pass. Weather silhouettes: 12/12, minimum {minimum:.2%}. Geometry, rigs, grips and draw counts preserved. Four GPU view/resolution comparisons pass.').replace('IMAGES',json.dumps(images)).replace('METRICS',json.dumps(measurements))
    (OUT/'comparison-inline.html').write_text(page)
    for phases in images.values():
        for path in phases.values():page=page.replace(path,'data:image/png;base64,'+base64.b64encode(Path(path).read_bytes()).decode())
    (OUT/'comparison.html').write_text(page)
    print(json.dumps({k:v for k,v in result.items() if k!='measurements'},indent=2))

if __name__=='__main__':main()
