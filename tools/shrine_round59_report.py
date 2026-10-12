#!/usr/bin/env python3
"""Round 57/58/59 matched galleries and measured display colour/contrast/GPU.
No game rendering. Masks are saved alongside the report for review.
"""
import argparse, colorsys, json, math, re, statistics
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
parser=argparse.ArgumentParser();parser.add_argument('root',nargs='?',default='build/shrine-round59');args=parser.parse_args()
root=Path(args.root).resolve()
names=['Ohman Ow','Jaba Badge','Owa Dime','Kay Nomut']
font_paths=['/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf','/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf']
font_path=next((p for p in font_paths if Path(p).exists()),None)
font=ImageFont.truetype(font_path,26) if font_path else ImageFont.load_default(size=26)
linear=[v/255/12.92 if v/255<=.04045 else ((v/255+.055)/1.055)**2.4 for v in range(256)]
def lum(rgb): return sum(c*linear[v] for c,v in zip((.2126,.7152,.0722),rgb))
def hue(pixels):
    x=y=0
    for rgb in pixels:
        h,s,v=colorsys.rgb_to_hsv(*(c/255 for c in rgb));weight=(max(rgb)-min(rgb))/255
        x+=math.cos(h*math.tau)*weight;y+=math.sin(h*math.tau)*weight
    return round(math.degrees(math.atan2(y,x))%360,1)
def gpu(path):
    txt=path.read_text();samples=re.findall(r'^gpu ms:.*buildings ([\d.]+).* = ([\d.]+)$',txt,re.M)
    assert len(samples)>=5,(path,len(samples))
    return {'median_ms':statistics.median(float(b) for a,b in samples),'buildings_ms':statistics.median(float(a) for a,b in samples),'range_ms':[min(float(b) for a,b in samples),max(float(b) for a,b in samples)],'samples':len(samples)}
def metrics(n,phase="final"):
    im=Image.open(root/phase/f'{n}-architecture.png').convert('RGB');w,h=im.size
    pix=im.load(); pools=Image.new('L',im.size);pd=ImageDraw.Draw(pools)
    # Explicit visible source footprints, measured after matching the camera.
    # Keh's default entrance pitch exposes the underwater pools hidden by the
    # ceiling-revealing gallery view; its shadow/glow samples use the gallery.
    boxes={1:[(930,566,1130,593),(365,566,510,592)],
           2:[(250,565,430,591),(870,565,1050,590)],
           3:[(40,590,200,620),(1080,590,1235,620)],
           4:[(320,340,430,385),(710,340,795,385)]}[n]
    for box in boxes: pd.rectangle(box,fill=255)
    pool_image=Image.open(root/phase/f'{n}-entrance.png').convert('RGB') if n==4 else im
    shadows=Image.new('L',im.size);sd=ImageDraw.Draw(shadows)
    # Side-wall stone between the upper fixtures and their floor footprint.
    sd.rectangle((w*.045,h*.39,w*.13,h*.65),fill=255)
    sd.rectangle((w*.87,h*.39,w*.955,h*.65),fill=255)
    # Glow pixels are excluded from material samples; save exact spatial masks.
    def blue(c):r,g,b=c;return b-r>=65 and b-g>=10 and b>=155 and g>=85
    lines=[];adjacent=[];gm=Image.new('L',im.size);gd=ImageDraw.Draw(gm)
    # Sample thin blue floor circuits only; exclude Link, the blue lift and lamps.
    for y in range(int(h*.66),int(h*.89)):
        for x in range(int(w*.035),int(w*.965)):
            if w*.38<x<w*.62:continue
            c=pix[x,y]
            if not blue(c):continue
            neighbors=[pix[x+dx,y+dy] for dx,dy in [(0,-7),(0,7),(-7,0),(7,0)] if 0<=x+dx<w and 0<=y+dy<h and not blue(pix[x+dx,y+dy])]
            if len(neighbors)<3:continue
            stone=statistics.median(lum(p) for p in neighbors)
            if stone<=.002:continue
            lines.append(c);adjacent.append(stone);gd.point((x,y),fill=255)
    # Remove thin bright emissive details from pigment/light-pool means,
    # without throwing away broad cyan-lit cistern stone just for being blue.
    def material_pixels(mask,source):
        sample=source.load()
        out=[]
        for y in range(h):
            for x in range(w):
                if not mask.getpixel((x,y)): continue
                c=sample[x,y]
                neighbors=[lum(sample[x+dx,y+dy]) for dx,dy in [(0,-7),(0,7),(-7,0),(7,0)] if 0<=x+dx<w and 0<=y+dy<h]
                emissive=max(c)-min(c)>45 and lum(c)>statistics.median(neighbors)*1.7
                if not emissive: out.append(c)
        return out
    pp=material_pixels(pools,pool_image);sp=material_pixels(shadows,im)
    assert len(lines)>30,(n,'too few blue line samples',len(lines))
    prefix=str(n) if phase=='final' else f'before-{n}'
    overlay=pool_image.copy();od=ImageDraw.Draw(overlay)
    for box in boxes: od.rectangle(box,outline='#ffa744',width=2)
    overlay.save(root/f'{prefix}-pool-regions.png')
    overlay=im.copy();od=ImageDraw.Draw(overlay)
    for box in [(w*.045,h*.39,w*.13,h*.65),(w*.87,h*.39,w*.955,h*.65)]: od.rectangle(box,outline='#ad7cff',width=2)
    overlay.save(root/f'{prefix}-shadow-regions.png')
    pools.save(root/f'{prefix}-pool-mask.png');shadows.save(root/f'{prefix}-shadow-mask.png');gm.save(root/f'{prefix}-glow-mask.png')
    return {'pool_hue_deg':hue(pp),'shadow_hue_deg':hue(sp),'pool_linear_luma':round(statistics.mean(lum(c) for c in pp),4),'shadow_linear_luma':round(statistics.mean(lum(c) for c in sp),4),'glow_hue_deg':hue(lines),'glow_luma_ratio':round(statistics.median(lum(c)/a for c,a in zip(lines,adjacent)),2),'glow_samples':len(lines),'pool_pixels':len(pp),'shadow_pixels':len(sp),'pool_boxes':boxes,'pool_view':'entrance' if n==4 else 'architecture'}
rows=[]
for n,name in enumerate(names,1):
    rows.append({'shrine':name,**metrics(n),'before_colour':metrics(n,'before'),'gpu_before':gpu(root/'before'/f'{n}-gpu.log'),'gpu_after':gpu(root/'final'/f'{n}-gpu.log')})
(root/'measurements.json').write_text(json.dumps(rows,indent=2)+'\n')
thumb=(640,360);label=42;gallery=Image.new('RGB',(2560,1206),'#101823');d=ImageDraw.Draw(gallery)
for row,phase in enumerate(['round57','round58','now']):
    folder=root/'final' if phase=='now' else root.parent/f'shrine-{phase}'/'final'
    for col,name in enumerate(names):
        x=col*640;y=row*402
        d.text((x+12,y+5),f'{name} · {phase}',font=font,fill='#e1e9ee')
        gallery.paste(Image.open(folder/f'{col+1}-architecture.png').convert('RGB').resize(thumb,Image.Resampling.LANCZOS),(x,y+label))
gallery.save(root/'entrance-4x3.png')
# Original full frames remain available at the linked paths.
title=Image.new('RGB',(1280,762),'#101823');d=ImageDraw.Draw(title)
for col,phase in enumerate(['before','final']):
    d.text((col*640+12,6),'Title · '+('before' if phase=='before' else 'after'),font=font,fill='#e1e9ee')
    title.paste(Image.open(root/phase/'title-shown.png').convert('RGB').resize((640,360),Image.Resampling.LANCZOS),(col*640,42))
    title.paste(Image.open(root/phase/'title-final.png').convert('RGB').resize((640,360),Image.Resampling.LANCZOS),(col*640,402))
title.save(root/'title-before-after.png')
# Fixed silhouette-body patches avoid the title ink and sky. Values are local
# display observations, not whole-object or monotonic distance measurements.
title_image=Image.open(root/'final/title-shown.png').convert('RGB')
title_boxes={'Castle':(170,157,280,225),'Dueling Peaks':(1090,216,1190,266),'Death Mountain':(1190,135,1269,185),'Distant ranges':(560,239,800,262),'Near forest':(380,465,700,565),'Mid field':(460,300,770,348)}
title_values=[{'name':name,'box':box,'mean_linear_luma_percent':round(statistics.mean(lum(c) for c in title_image.crop(box).get_flattened_data())*100,2)} for name,box in title_boxes.items()]
(root/'title-values.json').write_text(json.dumps(title_values,indent=2)+'\n')

lines=['# Round 59: local shrine light and title panorama','','Four shrine columns × three rounds. Matched 1280×720 architecture views; captures are unmodified apart from gallery resizing. Round 57 and round 58 are the final captures from their existing reports. Now uses the same entrance, camera input, 11:00 clear weather and render scale 1.','','![Round 57, round 58, now](entrance-4x3.png)','','Fixture irradiance is stored separately from pigment. Every shrine has the same blue-grey structural slate, cool hemisphere light and haze. The warm foundry, red blast ribs/brazier, gold brass wheel and aqua cistern keep their entrance silhouettes and local light footprints. Local character lights retain their own colour; pendants compete only within their real radius. Blue architecture traces receive a dedicated blue emissive colour.','','## Display measurements','','Circular, chroma-weighted mean hue (degrees); 0° red, 60° yellow, 180° cyan, 240° blue. Pool masks sample visible illuminated paving beneath pendants in the architecture views; Keh uses the underwater pools exposed by its default entrance pitch. Shadow masks sample side-wall masonry away from their footprint in the architecture views. Exact per-shrine pixel rectangles are recorded in [measurements.json](measurements.json); views are the same 1280×720 size. Thin bright emissive details are excluded from stone colour by local luminance contrast; broad cyan-lit stone is retained. Saved pool/shadow/glow masks make these measurements reproducible. Glow contrast is median linear Rec.709 luminance ratio to nearby non-emissive stone, using four neighbours 7 pixels away, restricted to thin visible blue floor-line cores (B ≥155, G ≥85, B−R ≥65, B−G ≥10 in 8-bit sRGB) and excluding hero/lift/fixtures. These are screen-space measurements of these entrance views, not global material averages.','','| Shrine | Lit pool hue | Shadow hue 58 → now | Blue line hue now | Glow / stone 58 → now | Blue pixels now |','|---|---:|---:|---:|---:|---:|']
for r in rows:lines.append(f"| {r['shrine']} | {r['pool_hue_deg']}° | {r['before_colour']['shadow_hue_deg']}° → {r['shadow_hue_deg']}° | {r['glow_hue_deg']}° | {r['before_colour']['glow_luma_ratio']}× → {r['glow_luma_ratio']}× | {r['glow_samples']} |")
lines+=['','## Title panorama','','Same BOTW_TITLE approach (`10:w+`), 07:00 clear weather, 1280×720. Top: first opaque title checkpoint; bottom: frame 1040 later in the crane. Full before/after images and 120-frame trail are retained in `before/` and `final/`.','','![Title before and after](title-before-after.png)','','The castle anchors the left, the paired cleft occupies the middle-right and Death Mountain sits on the outer right. Far-range haze rises with distance while the nearer cleft retains its darker value. All terrain, rivers, tree exclusions, lava and smoke use the relocated scenic anchors; the title camera and control handoff are unchanged. The [continuous opening title](checks/opening/title-shown.png) also verifies the composition on the fresh normal-input route.','','## GPU','','GTX 1070; X11 uncapped, 1280×720, scale 1. Each shrine: 720 frames, five averages of 120 completed GPU-query frames. The four-frame query ring reads asynchronously; no startup interval is explicitly discarded, so the median includes the first interval. Baseline is the merged round-58 source compiled before editing, with the same current assets. No simultaneous game renders (`flock /tmp/botw-render.lock`). Medians and full ranges are reported; differences are single-session measurements.','','| Shrine | Total before → after | Buildings before → after | Δ total | After range |','|---|---:|---:|---:|---:|']
for r in rows:
    b,a=r['gpu_before'],r['gpu_after'];lines.append(f"| {r['shrine']} | {b['median_ms']:.3f} → {a['median_ms']:.3f} ms | {b['buildings_ms']:.3f} → {a['buildings_ms']:.3f} ms | {a['median_ms']-b['median_ms']:+.3f} ms | {a['range_ms'][0]:.3f}–{a['range_ms'][1]:.3f} ms |")
at=lines.index('## GPU')
placements={'Castle':'Left; dark keep/spires','Dueling Peaks':'Middle-right; green cleft faces','Death Mountain':'Outer right; muted volcanic cone','Distant ranges':'Pale blue-grey horizon behind the field'}
title_lines=['| Title silhouette | Mean linear luminance | Placement / value group |','|---|---:|---|']
for row in title_values[:4]: title_lines.append(f"| {row['name']} | {row['mean_linear_luma_percent']:.2f}% | {placements[row['name']]} |")
title_lines+=['',f"Fixed body patches in the first opaque title frame; exact pixel rectangles are in title-values.json. Near forest: {title_values[4]['mean_linear_luma_percent']:.2f}%; sunlit mid field: {title_values[5]['mean_linear_luma_percent']:.2f}%. Atmospheric layering keeps the dark near canopy, lit middle ground, and pale distant horizon separate.",'']
lines[at:at]=title_lines
b,a=gpu(root/'before'/'title-gpu.log'),gpu(root/'final'/'title-gpu.log')
lines+=['',f"Title sequence total GPU median: {b['median_ms']:.3f} → {a['median_ms']:.3f} ms ({b['samples']} / {a['samples']} samples; sequence samples cover moving views).",'', '## Checks','','| Check | Result | Evidence |','|---|---|---|']
for test in ['shrine_route_check','shrine_discovery_check','shrine_ceremony_check','opening_check','title_handoff_check','late_story_check','feel_test','integration_test','input_check','shrine_lighting_check','title_panorama_check']:
    path=root/'checks'/f'{test}.log';txt=path.read_text();fail=bool(re.search(r'^(FAIL|panic:|.*: error:)',txt,re.M));summary=[line for line in txt.splitlines() if line.startswith(('PASS','pass','All ','Passed ','SUMMARY'))][-1:]
    if test=='opening_check': summary=[line for line in txt.splitlines() if line.startswith('PASS: continuous opening;')]
    if test=='feel_test': summary=[line for line in txt.splitlines() if line.startswith(('agreement with measured','behavioral correctness'))]
    if test in ['integration_test','input_check']: summary=[line for line in txt.splitlines() if line.startswith(('integration:','input:'))]
    if test=='shrine_route_check': summary=[line for line in txt.splitlines() if line.startswith('PASS ') and '(1)' not in line]
    markers={'shrine_route_check':r'^PASS Kay Nomut:', 'shrine_discovery_check':r'^PASS first-time discovery:', 'shrine_ceremony_check':r'PASS ceremony:', 'opening_check':r'^PASS: continuous opening;', 'title_handoff_check':r'^PASS title:', 'late_story_check':r'^PASS: ordered late story;', 'feel_test':r'^behavioral correctness: 100.0 / 100', 'integration_test':r'^integration: 1309/1309 passed', 'input_check':r'^input: 2077/2077 passed', 'shrine_lighting_check':r'^PASS lighting:','title_panorama_check':r'^PASS panorama:'}
    status='FAIL' if fail else 'PASS' if re.search(markers[test],txt,re.M) else 'PENDING'
    lines.append(f"| {test}{'.sh' if test in ['opening_check','late_story_check','shrine_route_check'] else ''} | {status} | [Full log](checks/{test}.log) {'; '.join(summary).replace('|','/')} |")
lines+=['', 'Capture note: the baseline wrapper was edited while running and its final status echo exited with a shell parsing error. All four entrance/architecture image pairs, all twenty shrine GPU samples, both title frames and the title GPU log were independently validated; the render commands themselves completed and these artifacts are used here. The corrected wrapper passes bash syntax validation.']
(root/'report.md').write_text('\n'.join(lines)+'\n')
panels=[]
preview_dir=root/'preview';preview_dir.mkdir(exist_ok=True)
for filename in ['entrance-4x3.png','title-before-after.png']:
    image=Image.open(root/filename);image.thumbnail((1280,1280),Image.Resampling.LANCZOS);image.save(preview_dir/filename)
for i,row in enumerate(rows):
    figures=[]
    for phase,label_ in [('round57','Round 57'),('round58','Round 58'),('now','Now')]:
        folder=root/'final' if phase=='now' else root.parent/f'shrine-{phase}'/'final'
        preview_image=preview_dir/f'{phase}-{i+1}.png'
        image=Image.open(folder/f'{i+1}-architecture.png');image.thumbnail((640,360),Image.Resampling.LANCZOS);image.save(preview_image)
        figures.append(f'<figure><figcaption>{label_}</figcaption><img alt="{row["shrine"]}, {label_}" src="{preview_image}"></figure>')
    stats=f'<p class="stats">Lit pool <b>{row["pool_hue_deg"]}°</b> · shadow <b>{row["shadow_hue_deg"]}°</b> · blue glow <b>{row["glow_luma_ratio"]}×</b> nearby stone · GPU <b>{row["gpu_after"]["median_ms"]:.2f} ms</b></p>'
    panels.append(f'<section id="shrine-{i}" {"hidden" if i else ""}><div class="three">'+''.join(figures)+'</div>'+stats+'</section>')
buttons=''.join(f'<button onclick="pick({i})" aria-pressed="{"true" if i==0 else "false"}">{name}</button>' for i,name in enumerate(names))
html="""<!doctype html><html><head><meta charset="utf-8"><style>
body{font-family:var(--font-sans);color:var(--foreground)}
img{width:100%;height:auto;display:block}p{color:var(--muted-foreground);line-height:1.5}
nav{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}button{font:inherit;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius);background:var(--secondary);color:var(--secondary-foreground);cursor:pointer}
button[aria-pressed=true]{background:var(--primary);color:var(--primary-foreground)}
.three{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}figure{margin:0}figcaption{font-size:13px;color:var(--muted-foreground);margin-bottom:6px}.stats{font-size:13px;margin:12px 0}
details{margin:16px 0}summary{cursor:pointer;margin-bottom:10px}
@media(max-width:500px){.three{grid-template-columns:1fr}}
</style></head><body>"""+ '<nav aria-label="Choose shrine">'+buttons+'</nav>'+''.join(panels)+f'<details><summary>Full 4×3 comparison</summary><img alt="Four shrines across rounds 57, 58 and 59" src="{preview_dir/"entrance-4x3.png"}"></details><details open><summary>Title before / after</summary><img alt="Title before and after, early and late in the crane" src="{preview_dir/"title-before-after.png"}"></details>'+"""<script>
function pick(n){document.querySelectorAll('section').forEach((s,i)=>s.hidden=i!==n);document.querySelectorAll('nav button').forEach((b,i)=>b.setAttribute('aria-pressed',i===n))}
window.addEventListener('load',()=>{const ok=[...document.images].every(i=>i.complete&&i.naturalWidth>0);console.log('All comparison images loaded:',ok);if(!ok)throw Error('Missing comparison image')});
</script></body></html>"""
(root/'comparison.html').write_text(html)
print(root/'report.md')
