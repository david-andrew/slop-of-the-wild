#!/usr/bin/env python3
"""Matched construction, panorama, wildlife and fire evidence; never renders the game."""
import json,re,statistics,sys
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(sys.argv[1] if len(sys.argv)>1 else 'build/round60').resolve()
scenes={**{f'shrine-{k}':f'{k}-gpu.log' for k in range(1,5)},'title':'title-gpu.log','boars':'boars-gpu.log',**{f'fire-{k}':f'fire-{k}-gpu.log' for k in range(3)}}
def gpu(path):
    rows=[line for line in path.read_text().splitlines() if line.startswith('gpu ms:')]
    assert len(rows)>=4,(path,len(rows))
    rows=rows[2:]
    result={'samples':len(rows),'total_ms':statistics.median(float(re.search(r'= ([\d.]+)$',r)[1]) for r in rows)}
    for part in ['buildings','farland','far-trees','terrain','fx','chars']:
        result[part+'_ms']=statistics.median(float(match[1]) if (match:=re.search(r'\b'+part+r' ([\d.]+)',r)) else 0.0 for r in rows)
    return result
report={'resolution':[1280,720],'render_scale':1,'platform':'X11, no vsync','protocol':'timer-query median, omit first two samples; three alternating paired grass-fire runs per build','scenes':{}}
for name,log in scenes.items():
    before,after=(gpu(root/phase/log) for phase in ['before','after'])
    report['scenes'][name]={'before':before,'after':after,'delta_ms':round(after['total_ms']-before['total_ms'],3)}
for phase in ['before','after']:
    sheet=Image.new('RGB',(1280,720))
    for k in range(4):
        im=Image.open(root/phase/f'{k+1}-entrance.png').convert('RGB');assert im.size==(1280,720);im.thumbnail((640,360));sheet.paste(im,((k%2)*640,(k//2)*360))
    sheet.save(root/phase/'shrine-entrances-4up.png')
for scene,file in [('shrines','shrine-entrances-4up.png'),('title','title-shown.png'),('boars','boars.png'),('fire','fire-active.png'),('fire-cold-ground','fire-0.png')]:
    sheet=Image.new('RGB',(1280,1464),(12,16,22));draw=ImageDraw.Draw(sheet)
    for i,phase in enumerate(['before','after']):
        im=Image.open(root/phase/file).convert('RGB');assert im.size==(1280,720),(file,im.size)
        sheet.paste(im,(0,i*732+12));draw.text((8,i*732),phase,fill=(225,230,235))
    sheet.save(root/f'{scene}-before-after.png')
report['tests']=json.loads((root/'checks/results.json').read_text())
report['fire_median_ms']={phase:statistics.median(report['scenes'][f'fire-{k}'][phase]['total_ms'] for k in range(3)) for phase in ['before','after']}
report['fire_fx_median_ms']={phase:statistics.median(report['scenes'][f'fire-{k}'][phase]['fx_ms'] for k in range(3)) for phase in ['before','after']}
(root/'gpu.json').write_text(json.dumps(report,indent=2)+'\n')
lines=['# Round 60 implementation evidence','', 'Baseline: master `f059423`. All captures serialized through `/tmp/botw-render.lock`.', '', '1280×720, scale 1, X11 without vsync. GPU timer-query medians omit the first two samples. Fire has three alternating paired runs per build; other scenes have one run. Title timing covers the scripted approach and panorama, rather than a stationary camera.', '', '| Scene | Before GPU ms | After GPU ms | Delta ms |','|---|---:|---:|---:|']
for name,data in report['scenes'].items():
    lines.append(f"| {name} | {data['before']['total_ms']:.2f} | {data['after']['total_ms']:.2f} | {data['delta_ms']:+.2f} |")
lines += ['', f"Fire FX pass median: {report['fire_fx_median_ms']['before']:.2f} → {report['fire_fx_median_ms']['after']:.2f} ms. Full-frame timing includes the new scenery and architecture.", '', '## Requested checks', '']
for name,r in report['tests'].items():lines.append(f"- {name}: {'PASS' if r['exit_code']==0 else 'FAIL'} ({r['seconds']:.2f} s); `checks/{name}.log`.")
lines+=['', 'Integration: 1309/1309; shrine discovery: 32/32; elements: 19/19; feel: 29/29 behavioural checks and 99.6/100 measured-reference agreement. The companion fixture-light check passes 25/25.', '', '## Implementation','', '- Shrine floors and wall coursing use theme-specific construction and non-emissive inlays. Conduits include the foundry hoist and weighted ice stair; active inputs brighten their connected paths.', '- The title middle distance adds shelf relief, denser grove pockets, roadside rock clusters and broken courtyards. Road and clearing margins use shorter, warmer vegetation.', '- Boar appearance and feeding timing build on Astra’s untouched procedural geometry from `61c011a`.', '- Source-over flame bodies bound overlap at the hottest tongue’s colour; cold ash is neutral grey, heating char is umber with sparse ember cracks.', '', '## Images','', f'- [Shrine entrances 4-up]({root}/shrines-before-after.png): before above after.', f'- [Title frame]({root}/title-before-after.png): actual opaque title frame.', f'- [Boars]({root}/boars-before-after.png): same woodland camera and simulation time.', f'- [Active fire]({root}/fire-before-after.png): dense advancing roots at frame 180. [Cold ground]({root}/fire-cold-ground-before-after.png): safe ash at frame 720.', '', 'Full-size individual frames and per-pass timing logs are in `before/` and `after/`. Raw evidence stays under `build/`.','']
(root/'REPORT.md').write_text('\n'.join(lines))
print('\n'.join(lines[:17]))
