#!/usr/bin/env python3
"""Create the local review with matched frames and retained validation logs."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from PIL import Image

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, default=Path('build/round66'))
a = p.parse_args()
root = a.output.resolve()
required = {
    'routes-final.log': [f'PASS {name}:' for name in ['Oman Au', 'Ja Baij', 'Owa Daim', 'Keh Namut']],
    'discovery-final.log': ['PASS first-time discovery: 32/32'],
    'arrival-final.log': ['PASS shrine arrival: 12576'],
    'shafts.log': ['PASS shrine descent shafts: 36'],
    'exit.log': [f'PASS: {name}:' for name in ['Oman Au', 'Ja Baij', 'Owa Daim', 'Keh Namut']],
    'passage-mesh-final.log': ['476 checks PASS'],
    'passage-walk.log': ['PASS: at'],
    'lighting.log': ['PASS lighting: 25 checks'],
    'title-panorama-final.log': ['PASS panorama: 2081160'],
}
for name, expected in required.items():
    log = (root / 'checks' / name).read_text()
    assert all(event in log for event in expected), name
    assert not any(error in log for error in ['FAIL', 'panic:', 'error:']), name
scenes = [
    ('passage/frame-750', 'Cave · frame 750', 'Relief shares the lining’s pigment and mineral finish; buried perimeters merge into the wall, with lower courses crossing the floor line.'),
    ('passage/frame-830', 'Cave · frame 830', 'The daylight threshold retains its sealed lining and original walking route.'),
]
names = ['Oman Au · foundry', 'Ja Baij · blast vault', 'Owa Daim · clockwork gallery', 'Keh Namut · flooded cistern']
notes = ['Taller, narrower hall; square forge apron, crate tracks and counterweights.', 'Lower, wider vault; octagonal blast collar, exhaust grilles and spare bomb drums.', 'Long vaulted gallery; bronze dial, toothed surround and paired wheel frames.', 'Pale quay and central walkway; water extends around the landing, with a dry valve crosswalk and recovery pier.']
for n, (name, note) in enumerate(zip(names, notes), 1):
    scenes.extend([(f'shrines/{n}-entry', name + ' · entry', note),
                   (f'shrines/{n}-arrival', name + ' · arrival', 'Arrival reveal uses the production camera. The lift shaft hangs above its themed surround.'),
                   (f'shrines/{n}-shaft', name + ' · shaft', 'An open ceiling aperture, inward shaft walls and a dark cap create actual descent depth.')])
scenes.extend([('field/overlook', 'Hyrule Field · overlook', 'Broken gate towers and wall silhouettes along the Outpost/Exchange approaches; roofless town corners farther north.'),
               ('field/title', 'Hyrule Field · title', 'Distant ruins remain restrained in value and seated on the rendered terrain. Title framing is unchanged.')])

def image_src(path, embedded):
    assert path.is_file(), path
    # Retain lossless source PNGs; smaller review copies keep the interactive
    # attachment below the renderer's 25 MiB limit at the original dimensions.
    review = root / 'review-images' / path.relative_to(root).with_suffix('.jpg')
    review.parent.mkdir(parents=True, exist_ok=True)
    if not review.is_file() or review.stat().st_mtime < path.stat().st_mtime:
        Image.open(path).convert('RGB').save(review, quality=93, subsampling=0, progressive=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(review.read_bytes()).decode() if embedded else str(review)

def document(embedded):
    pictures = [{'title': title, 'note': note, **{phase: image_src(root / phase / (key + '.png'), embedded) for phase in ['before', 'after']}} for key, title, note in scenes]
    html = '''<!doctype html><html><head><meta charset="utf-8"><style>
    body{margin:0;color:var(--foreground,#ddd);font:14px var(--font-sans,system-ui)}
    p{line-height:1.5;margin:10px 0}select{max-width:100%;padding:8px;color:inherit;background:var(--secondary,#25262a);border:1px solid var(--border,#555);border-radius:6px}
    .view{position:relative;margin-top:12px;overflow:hidden;border-radius:8px;background:#111}.view img{width:100%;display:block}.view #before{position:absolute;inset:0;clip-path:inset(0 50% 0 0)}
    .labels{position:absolute;left:8px;right:8px;top:8px;display:flex;justify-content:space-between}.labels span{padding:4px 8px;background:#111b;color:white;border-radius:4px;font-size:12px}
    .control{display:flex;align-items:center;gap:12px;margin:12px 0}.control input{flex:1;min-width:0}.checks{font-size:13px;color:var(--muted-foreground,#aaa)}
    </style></head><body>
    <p><strong>Round 66 — cave, shrine entries and distant ruins</strong></p>
    <select id="scene" aria-label="Comparison view">OPTIONS</select>
    <select id="zoom" aria-label="Detail zoom"><option value="1">1×</option><option value="2">2× detail</option><option value="4">4× detail</option></select>
    <div class="view"><img id="after" alt="After"><div id="before"><img id="before-image" alt="Before"></div><div class="labels"><span>Before · da7ebe1</span><span>After · sol2/work</span></div></div>
    <label class="control"><span>After</span><input id="reveal" type="range" min="0" max="100" value="50" aria-label="Comparison divider"><span>Before</span></label>
    <p id="note"></p><p class="checks">CHECKS</p>
    <p class="checks">Matched production captures: cave 960 × 540; shrine and field 1280 × 720. Every render holds the shared lock once. Images and full logs remain in build/round66/.</p>
    <script>const pictures=PICTURES;const scene=document.querySelector('#scene');const slider=document.querySelector('#reveal');
    function zoom(){const i=Number(scene.value);const focus=i===14?[.18,.32]:i===15?[.5,.46]:[.5,.5];const s=Number(document.querySelector('#zoom').value);const move=focus.map(p=>Math.max(1-s,Math.min(0,.5-s*p))*100);for(const img of document.querySelectorAll('.view img')){img.style.transformOrigin='0 0';img.style.transform=`translate(${move[0]}%,${move[1]}%) scale(${s})`;}}
    function update(){const p=pictures[Number(scene.value)];document.querySelector('#after').src=p.after;document.querySelector('#before-image').src=p.before;document.querySelector('#note').textContent=p.note;zoom();}
    scene.addEventListener('change',update);document.querySelector('#zoom').addEventListener('change',zoom);slider.addEventListener('input',()=>document.querySelector('#before').style.clipPath=`inset(0 ${100-Number(slider.value)}% 0 0)`);update();
    console.log('Round 66:',pictures.length,'matched views');</script></body></html>'''
    options = ''.join(f'<option value="{i}">{v[1]}</option>' for i, v in enumerate(scenes))
    checks = 'PASS: all four routes; discovery 32/32; arrival at 30/60/120 Hz; 36 shaft rays; four exits; cave mesh and walk; lighting; title panorama across five aspect ratios.'
    return html.replace('OPTIONS', options).replace('CHECKS', checks).replace('PICTURES', json.dumps(pictures))

(root / 'report.html').write_text(document(True))
(root / 'report-view.html').write_text(document(False))
sources = ['game/interiors.jo', 'game/shrines.jo', 'game/farland.jo', 'tools/shrine_arrival_check.jo', 'tools/shrine_shaft_check.jo', 'tools/round66_visual_check.py', 'tools/round66_report.py']
(root / 'implementation-sources.json').write_text(json.dumps({s: hashlib.sha256(Path(s).read_bytes()).hexdigest() for s in sources}, indent=2) + '\n')
print(root / 'report.html')
