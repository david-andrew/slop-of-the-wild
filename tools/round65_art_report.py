#!/usr/bin/env python3
"""Build the local before/after comparison and 200% crops after round65_art_check.py."""
from pathlib import Path
import json, re, statistics
from PIL import Image
root=Path(__file__).resolve().parent.parent / "build" / "round65"
# All boxes are fixed source-pixel coordinates, shared by before/after.
views={
 'wake': ('Wake · skin', (530,240,750,430), 'Fine pigment and soft contours on skin; the broad lighting wash is retained.'),
 'combat': ('Combat · cloth and grass', (470,280,750,510), 'Restrained lengthwise cloth strokes and fine figures against larger grass dabs.'),
 'cliffs': ('Cliffs · rock', (340,350,660,550), 'Broader angular marks and broken pigment in joints.'),
 'pond': ('Hopper Pond · water', (730,300,1050,500), 'Smooth water wash with intact reflection and highlight detail.'),
 'title': ('Title · sky and distant land', (950,75,1270,255), 'Grain-free sky above textured land; protected distant silhouettes.'),
 'forest': ('Forest · foliage and stone', (865,270,1185,500), 'Loose foliage dabs beside broader mineral strokes.'),
}
rows=[]
for name,(title,box,note) in views.items():
 row=dict(name=name,title=title,note=note,box=box)
 for phase in ['before','after']:
  image=Image.open(root/phase/f'{name}.png').convert('RGB')
  crop=image.crop(box);crop=crop.resize((crop.width*2,crop.height*2),Image.Resampling.NEAREST)
  crop.save(root/phase/f'{name}-200.png')
  row[phase]=str(root/phase/f'{name}.png')
  row[phase+'Crop']=str(root/phase/f'{name}-200.png')
 rows.append(row)
gpu=json.loads((root/'gpu-summary.json').read_text()) if (root/'gpu-summary.json').exists() else {}
for key,row in gpu.items():
 size,view=key.split('/')
 for phase in ['before','after']:
  runs=[]
  for repeat in range(3):
   lines=(root/'gpu'/f'{size}-{view}-{phase}-{repeat}.log').read_text().splitlines()
   values=[float(re.search(r' post ([0-9.]+)',l)[1]) for l in lines if l.startswith('gpu ms:')]
   metadata=json.loads((root/'gpu'/f'{size}-{view}-{phase}-{repeat}.json').read_text())
   runs.append(statistics.median(values[metadata.get('discard_batches',4):]))
  row[phase+'_post_ms']=statistics.median(runs)
(root/'gpu-with-post.json').write_text(json.dumps(gpu,indent=2)+'\n')
table=''.join(f'<tr><td>{k}</td><td>{r["before_ms"]:.3f}</td><td>{r["after_ms"]:.3f}</td><td>{r["delta_ms"]:+.3f}</td><td>{r["after_post_ms"]-r["before_post_ms"]:+.3f}</td><td>{"PASS" if r["passed"] else "FAIL"}</td></tr>' for k,r in gpu.items())
html='''<!doctype html><html><head><meta charset="utf-8"><title>Round 65 · material paint</title><style>
*{box-sizing:border-box}body{margin:0;color:var(--foreground,#e8e8e8);font:14px/1.5 var(--font-sans,system-ui)}button,select{font:inherit;background:var(--secondary,#303237);color:inherit;border:1px solid var(--border,#555);border-radius:6px;padding:7px 12px}button[aria-pressed=true]{background:#38634f;color:white}nav{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}.scene{position:relative}#full{width:100%;display:block}p{margin:10px 0;color:var(--muted-foreground,#b9bfc3)}.crop{overflow:auto;border:1px solid var(--border,#555)}#crop{display:block;max-width:none}small{color:var(--muted-foreground,#b9bfc3)}.gpu-table{overflow-x:auto}table{border-collapse:collapse;font-variant-numeric:tabular-nums;width:100%;font-size:12px}td,th{text-align:right;border-bottom:1px solid var(--border,#555);padding:6px}td:first-child,th:first-child{text-align:left}details{margin-top:14px}h3{font-size:15px;margin:16px 0 6px}</style></head><body>
<nav><select id="view" aria-label="Acceptance view"></select><button id="before" aria-pressed="false">Before · 8d18626</button><button id="after" aria-pressed="true">After</button></nav><p id="note"></p><div class="scene"><img id="full" alt="Full acceptance view"></div><h3>200% crop · identical source pixels</h3><small id="coords"></small><div class="crop"><img id="crop" alt="Material crop at 200 percent"></div><details><summary>GPU medians · milliseconds</summary><p>Three alternating pairs per view and output size, native resolution, scale 1. Frozen scene after the acceptance frame; at least four 120-frame GPU warmup batches discarded (seven for the later title frame). Budget: before × 1.03 + 0.1 ms.</p><div class="gpu-table"><table><thead><tr><th>View</th><th>Before</th><th>After</th><th>Δ total</th><th>Δ post</th><th>Budget</th></tr></thead><tbody>TABLE</tbody></table></div></details><p>Full PNGs, unfiltered nearest-neighbor 200% crops, capture settings and binary hashes live alongside this page. No new render target or extra paint-filter taps.</p><script>
const views=DATA;let phase='after';const sel=document.getElementById('view');views.forEach((v,i)=>sel.add(new Option(v.title,i)));function show(){const v=views[+sel.value];document.getElementById('full').src=v[phase];document.getElementById('crop').src=v[phase+'Crop'];document.getElementById('note').textContent=v.note;document.getElementById('coords').textContent='Source rectangle: '+v.box.join(', ')+' · '+phase;['before','after'].forEach(p=>document.getElementById(p).setAttribute('aria-pressed',p===phase));}sel.onchange=show;['before','after'].forEach(p=>document.getElementById(p).onclick=()=>{phase=p;show()});show();Promise.all(views.flatMap(v=>['before','after','beforeCrop','afterCrop'].map(k=>new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve([v.name,k,im.naturalWidth,im.naturalHeight]);im.onerror=()=>reject(v.name+' '+k);im.src=v[k];})))).then(rows=>console.log('Verified '+rows.length+' full views and 200% crops',rows)).catch(e=>console.error('Image load failed',e));</script></body></html>'''.replace('TABLE',table).replace('DATA',json.dumps(rows))
(root/'comparison.html').write_text(html)
(root/'crop-boxes.json').write_text(json.dumps(views,indent=2)+'\n')
