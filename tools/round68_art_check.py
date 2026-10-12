#!/usr/bin/env python3
"""Matched master 0af23bf/current Round 68 art evidence.

Capture mode locks each game render itself; never wrap this script in flock.
The complete production entry point plus performance_output pins real X11 pixels.
Title-background suppresses only the atlas overlay after the world/post draw.
Commands: prepare before|after; capture before|after [views...]; negative; report.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
from PIL import Image

os.chdir(Path(__file__).resolve().parent.parent)
ROOT = Path('build/round68')
VIEWS = {
    'grass': ({'BOTW_SKIP':'1', 'BOTW_AT':'-1030,1805,1.57'}, 300),
    'title': ({'BOTW_SKIP':'1', 'BOTW_TITLE':'1', 'BOTW_AT':'-1024,1799,0'}, 720),
    'overlook': ({'BOTW_SKIP':'1', 'BOTW_CAM':'-700,330,2150,-0.8,-0.35'}, 300),
    'waterfall': ({'BOTW_SKIP':'1', 'BOTW_CAM':'-1660,175,1888,1.24,-0.05'}, 300),
    'snow': ({'BOTW_SKIP':'1', 'BOTW_AT':'-1060,2230,2.0', 'BOTW_GIVE':'warm_doublet'}, 300),
    'snow-faces': ({'BOTW_SKIP':'1', 'BOTW_CAM':'-1300,355,2100,3.7,-0.20'}, 300),
    'cliffs': ({'BOTW_SKIP':'1', 'BOTW_CAM':'-1600,235,1815,1.2,-0.15'}, 300),
    'golden': ({'BOTW_SKIP':'1', 'BOTW_AT':'-1030,1805,1.57', 'BOTW_HOUR':'6.4', 'BOTW_TIMESCALE':'0'}, 300),
    'camp': ({'BOTW_SKIP':'1', 'BOTW_AT':'-1439,1606,0', 'BOTW_GIVE':'travelers_sword,travelers_shield', 'SLOPPY_INPUT':'5:w+,40:w-,45:k+,100:j+,106:j-,125:j+,131:j-,150:d+,152:space+,154:space-,170:d-,300:j+,306:j-,330:j+,336:j-'}, 260),
    'canopy': ({'BOTW_SKIP':'1', 'BOTW_AT':'-1000,1620,3.14'}, 300),
}
VIEWS['title-background'] = ({**VIEWS['title'][0], 'ROUND68_TITLE_BACKGROUND': '1'}, VIEWS['title'][1])
BASELINE = '0af23bf'

def prepare(phase):
    ROOT.mkdir(parents=True, exist_ok=True)
    game = Path('game').resolve()
    if phase == 'before':
        game = (ROOT / 'before-source' / 'game').resolve()
        game.mkdir(parents=True, exist_ok=True)
        names = subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,'game'],text=True)
        for name in names.splitlines():
            if name.endswith('.jo'):
                (game / Path(name).name).write_bytes(subprocess.check_output(['git','show',f'{BASELINE}:{name}']))
    source = (game / 'main.jo').read_text()
    source = re.sub(r"(?m)^(use|from) '([^']+)'",lambda m:f"{m[1]} '{game / m[2]}'",source)
    # Background companion changes only the atlas overlay after world/post draw.
    source = source.replace('    if not invui.open: story_draw_2d()', """    if not invui.open:
        review_alpha = story.title_alpha
        if env("ROUND68_TITLE_BACKGROUND") != none: story.title_alpha = 0.0
        story_draw_2d()
        story.title_alpha = review_alpha""")
    source = source.replace('update = (dt0: f64):','production_update = (dt0: f64):')
    source += "\nuse '../../tools/performance_output.jo'\nupdate = (dt: f64):\n    freeze = to_int(env(\"ROUND68_FREEZE\") ?? \"0\") ?? 0\n    if freeze == 0 or frame_number() <= freeze: production_update(dt)\n    else: frame_stats_begin(post.scale)\nmain = (): performance_output_run(update, draw)\n"
    fixture = ROOT / f'{phase}.jo'
    fixture.write_text(source)
    subprocess.run(['sloppy/bin/sloppy','build',str(fixture),'-o',str(ROOT / f'{phase}-game')],check=True)
    manifest = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(game.glob('*.jo'))}
    (ROOT / f'{phase}-source.json').write_text(json.dumps(dict(baseline=BASELINE,modules=manifest),indent=2)+'\n')

def run(phase, view, size, gpu=False, repeat=0, locked=False):
    flags, frame = VIEWS[view]
    discard = max(4, frame // 120 + 1)
    out = ROOT / ('gpu' if gpu else phase) / (f'{size}-{view}-{phase}-{repeat}' if gpu else view)
    out.parent.mkdir(parents=True, exist_ok=True)
    binary = ROOT / f'{phase}-game'
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    env = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'ROUND68_'))}
    env.update(BOTW_HOUR='11', BOTW_WEATHER='clear', BOTW_SCALE='1',
               BOTW_NOVSYNC='1', BOTW_NO_PREPARED_ASSETS='1', SLOPPY_PLATFORM='x11',
               SLOPPY_WINDOW=size, SLOPPY_FRAMES=str((discard + 4) * 120 if gpu else frame),
               SLOPPY_SCREENSHOT=str(out.with_suffix('.png').resolve()))
    env.update(flags)
    if gpu: env.update(BOTW_GPU='1', ROUND68_FREEZE=str(frame))
    with out.with_suffix('.log').open('w') as log:
        command = ['python3','tools/cliff_capture_window.py',size,'timeout','300',str(binary)]
        if not locked: command = ['flock','/tmp/botw-render.lock',*command]
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    assert Image.open(out.with_suffix('.png')).size == tuple(map(int,size.split('x')))
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == digest
    samples = [float(re.search(r'= ([\d.]+)$',line)[1]) for line in out.with_suffix('.log').read_text().splitlines() if line.startswith('gpu ms:')]
    row = dict(binary_sha256=digest, env={k:v for k,v in env.items() if k.startswith(('BOTW_', 'SLOPPY_', 'ROUND68_'))}, samples=samples)
    if gpu:
        assert len(samples) >= discard + 3, samples
        row['discard_batches'] = discard
        row['median_ms'] = statistics.median(samples[discard:])
    out.with_suffix('.json').write_text(json.dumps(row,indent=2)+'\n')
    print(phase, view, size, row.get('median_ms','captured'),flush=True)
    return row

def title_contrast(phase):
    import math
    from PIL import ImageChops
    visible = Image.open(ROOT / phase / 'title.png').convert('RGB')
    background = Image.open(ROOT / phase / 'title-background.png').convert('RGB')
    atlas = Image.open('assets/title.png').convert('RGBA')
    width, height = visible.size
    aw, ah = atlas.size
    title_w = min(width * .38, 680, height * .16 * 1224 / 366)
    title_h = title_w * 366 / 1224
    left, top = (width - title_w) / 2, height * .115
    linear = lambda x: x / 255 / 12.92 if x / 255 <= .04045 else ((x / 255 + .055) / 1.055) ** 2.4
    luminance = lambda rgb: sum(linear(c) * k for c, k in zip(rgb, (.2126,.7152,.0722)))
    ratios, backgrounds = [], []
    for y in range(int(title_h)):
        for x in range(int(title_w)):
            letter = atlas.getpixel((int((x+.5)/title_w*aw), int((y+.5)/title_h*ah)))
            if letter[3] < .98 * 255: continue
            fg = luminance(letter[:3])
            bg = luminance(background.getpixel((int(left+x), int(top+y))))
            ratios.append((max(fg,bg)+.05)/(min(fg,bg)+.05))
            backgrounds.append(bg)
    difference = ImageChops.difference(visible, background)
    difference.paste((0,0,0), (math.floor(left)-2, math.floor(top)-2,
                             math.ceil(left+title_w)+2, math.ceil(top+title_h)+2))
    extrema = difference.getextrema()
    assert max(high for low,high in extrema) <= 1, f'{phase}: background companion drift {extrema}'
    row = dict(minimum_ratio=min(ratios), mean_ratio=statistics.mean(ratios),
               background_max_luminance=max(backgrounds), opaque_atlas_pixels=len(ratios),
               required_ratio=3.0, passed=min(ratios)>=3.0,
               method='sRGB decoded to linear Rec.709; (Lmax+0.05)/(Lmin+0.05) at alpha >= .98 atlas pixels',
               background_drift_max_rgb=max(high for low,high in extrema))
    (ROOT / phase / 'title-contrast.json').write_text(json.dumps(row,indent=2)+'\n')
    return row


def negative_control():
    ROOT.mkdir(parents=True, exist_ok=True)
    target = ROOT / 'title-negative-control.png'
    Image.new('RGB', (1280,720), 'white').save(target)
    log = ROOT / 'title-negative-control.log'
    with log.open('w') as output:
        result = subprocess.run(['sloppy/bin/sloppy','tools/title_panorama_check.jo'],
                    env={**os.environ,'BOTW_TITLE_BACKGROUND':str(target.resolve())},
                    stdout=output,stderr=subprocess.STDOUT)
    assert result.returncode != 0 and 'rendered background must retain 3:1' in log.read_text()
    print('PASS title negative control: white background correctly rejected')


def report():
    import html
    manifests = {p:json.loads((ROOT / f'{p}-source.json').read_text()) for p in ('before','after')}
    digests = {p:hashlib.sha256((ROOT/f'{p}-game').read_bytes()).hexdigest() for p in manifests}
    for phase in manifests:
        for view, (flags,frame) in VIEWS.items():
            row = json.loads((ROOT/phase/f'{view}.json').read_text())
            assert row['binary_sha256'] == digests[phase], f'{phase}/{view}: stale capture'
            assert all(row['env'][k] == v for k,v in flags.items())
            assert row['env']['SLOPPY_FRAMES'] == str(frame)
            assert Image.open(ROOT/phase/f'{view}.png').size == (1280,720)
    for name,digest in manifests['after']['modules'].items():
        assert hashlib.sha256((Path('game')/name).read_bytes()).hexdigest() == digest, f'changed after source: {name}'
    checks = {'camp outcrop':('camp-outcrop-check.log','PASS camp outcrop:'),
              'prepared assets':('prepared-assets-check.log','PASS prepared assets:'),
              'cliff mesh':('cliff-mesh-check.log','cliff mesh PASS:'),
              'cliff climb':('cliff-climb-check.log','cliff climb PASS:'),
              'water coverage':('water-coverage-check.log','PASS waterfall shelves:'),
              'landscape':('landscape-check.log','landscape:'),
              'title panorama':('title-panorama-check.log','PASS panorama: 2081160 projections')}
    for name,(path,token) in checks.items():
        log = (ROOT/path).read_text()
        assert token in log and 'FAIL' not in log, name
    contrast = {p:title_contrast(p) for p in ('before','after')}
    assert contrast['after']['passed']
    contrast_log = (ROOT/'title-panorama-check.log').read_text()
    assert 'title lettering contrast: minimum' in contrast_log and 'panic' not in contrast_log
    assert 'rendered background must retain 3:1' in (ROOT/'title-negative-control.log').read_text()
    views = ['waterfall','waterfall-left-200','waterfall-right-200','title','grass','camp',
             'cliffs','golden','overlook','snow','snow-faces','canopy']
    for phase in ('before','after'):
        image = Image.open(ROOT/phase/'waterfall.png')
        image.resize((2560,1440),Image.Resampling.NEAREST).save(ROOT/phase/'waterfall-200.png')
        for side,box in [('left',(60,140,560,650)),('right',(760,140,1260,650))]:
            crop = image.crop(box)
            crop.resize((crop.width*2,crop.height*2),Image.Resampling.NEAREST).save(ROOT/phase/f'waterfall-{side}-200.png')
    captions = {
        'waterfall':'Removed the Round 67 small-cell plate pigment and independent normal perturbation. The original continuous mineral wash, larger mesh forms and bedding remain. Round 67 bench foam and spray remain.',
        'waterfall-left-200':'Left cliff at exactly 200% with nearest-neighbour enlargement; the 500×510 native crop begins at (60,140).',
        'waterfall-right-200':'Right cliff at exactly 200% with nearest-neighbour enlargement; the 500×510 native crop begins at (760,140).',
        'title':f"Smaller painted cloud lobes, lit rims and grey-violet bases; feathered atlas reserve settles before the title. Worst opaque-letter contrast: master {contrast['before']['minimum_ratio']:.4f}:1 → after {contrast['after']['minimum_ratio']:.4f}:1 (required 3:1).",
        'grass':'Structured cloud pigment and firmer edges above the retained varied stems, seed heads and flowers.',
        'camp':'The slab is an ordinary cliff rib, grid (7,7), centre (-1455.48,218.41,1543.69), radii (7.41,17.60,4.44), material 4, chunk -11988. Its clipped cap was 8.7 m above terrain; lower cap from .72 to .32 puts the crown at 224.04 m, 2.1 m above its terrain sample. Rooted face and collider remain. Ordinary outcrops also receive tilted rock beds and sparse continuous joints.',
        'cliffs':'Continuous larger cliff forms retain the Round 67 grey-green palette.',
        'golden':'Retained the warmer dawn sky and vegetation.',
        'overlook':'Retained ridged muted foothills, wooded fingers and wind-scoured snow.',
        'snow':'Matched deep-snow player view.',
        'snow-faces':'Retained local crags and lee snow accumulation.',
        'canopy':'Retained softer foliage coverage and distant pasture gaps.'}
    summary = dict(baseline=BASELINE, branch='sol3/work', window='1280x720',
                   binary_sha256=digests, title_contrast=contrast, checks=list(checks),
                   negative_control='white title background rejected', changes=captions)
    (ROOT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    sections = []
    for index,view in enumerate(views):
        zoomed = view.endswith('-200')
        paths = []
        for phase in ('before','after'):
            display = ROOT / 'display' / f'{phase}-{view}.jpg'
            display.parent.mkdir(exist_ok=True)
            Image.open(ROOT/phase/f'{view}.png').convert('RGB').save(display, quality=95, subsampling=0)
            paths.append(display.resolve())
        sections.append(f'<section {"hidden" if index else ""}><div class="scroll"><div class="compare {"zoom" if zoomed else ""}"><img src="{paths[1]}" alt="After {view}"><img class="before" src="{paths[0]}" alt="Master {view}"><span class="left">Master · 0af23bf</span><span class="right">After</span></div></div><p>{html.escape(captions[view])}</p></section>')
    options = ''.join(f'<option value="{i}">{html.escape(v.replace("-"," ").title())}</option>' for i,v in enumerate(views))
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Round 68 review</title>
<style>body{{margin:0;color:var(--foreground,#26362d);font:14px/1.5 var(--font-sans,system-ui)}}
.controls{{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:12px}}select,button{{padding:6px;border:1px solid var(--border,#abb6ae);border-radius:6px;background:var(--secondary,#e7ece8);color:inherit}}button{{cursor:pointer}}input{{width:150px;max-width:100%}}
.scroll{{overflow:auto;max-width:100%}}.compare{{position:relative;overflow:hidden;border-radius:8px}}.compare img{{display:block;width:100%}}.compare.native{{width:1280px;height:720px}}.compare.native img{{width:1280px;height:720px}}.compare.zoom{{width:1000px;height:1020px}}.compare.zoom img{{width:1000px;height:1020px}}.before{{position:absolute;inset:0;clip-path:inset(0 50% 0 0)}}.left,.right{{position:absolute;top:8px;padding:2px 6px;border-radius:4px;background:#17241fe6;color:white;font-size:12px}}.left{{left:8px}}.right{{right:8px}}p{{margin:10px 0 16px}}.checks{{padding:16px;border-radius:var(--radius,8px);background:var(--secondary,#e7ece8)}}summary{{cursor:pointer;margin:12px 0}}</style>
<div class="controls"><label>View <select id="view">{options}</select></label><label>Compare <input id="split" type="range" min="0" max="100" value="50" aria-label="Master and after comparison"></label><button id="old">Master</button><button id="new">After</button><label><input id="native" type="checkbox" style="width:auto"> Native 1×</label></div>
{''.join(sections)}<div class="checks">Title lettering: {contrast['after']['minimum_ratio']:.4f}:1 minimum · {contrast['after']['opaque_atlas_pixels']:,} opaque atlas pixels · 3:1 required. Panorama: 2,081,160 projections. Cliff mesh, climbing, water coverage, landscape and complete prepared-asset equivalence pass. White-background negative control rejected.</div>
<details><summary>Capture protocol</summary><p>All ten Round 67 views re-captured from master 0af23bf and this branch. Native 1280×720, scene scale 1, identical cameras, input, weather and frame counts. Title frame 720, camp 260, others 300; 11:00 clear weather except frozen dawn 06:24. Each game render owns a single /tmp/botw-render.lock. Background companions suppress only title alpha during the 2D overlay; pixels outside the atlas bounds are identical within one RGB level. Contrast uses sRGB decoded to linear Rec.709. Full waterfall-200.png enlargements and left/right native crops are retained in each capture folder.</p><p>The baseline contains the current master character/runtime changes; the after retains all Round 67 art outside these three corrections. No critic score is claimed. Display copies are JPEG at quality 95; untouched native PNGs, source and binary hashes, capture environments and check logs remain in build/round68.</p></details>
<script>const sections=[...document.querySelectorAll('section')],slider=document.querySelector('#split');function compare(n){{slider.value=n;document.querySelectorAll('.before').forEach(v=>v.style.clipPath=`inset(0 ${{100-n}}% 0 0)`);document.querySelectorAll('.left').forEach(v=>v.hidden=Number(n)===0);document.querySelectorAll('.right').forEach(v=>v.hidden=Number(n)===100)}}document.querySelector('#view').onchange=e=>sections.forEach((v,i)=>v.hidden=i!==Number(e.target.value));slider.oninput=e=>compare(e.target.value);document.querySelector('#old').onclick=()=>compare(100);document.querySelector('#new').onclick=()=>compare(0);document.querySelector('#native').onchange=e=>document.querySelectorAll('.compare:not(.zoom)').forEach(v=>v.classList.toggle('native',e.target.checked));console.log('Round 68: '+sections.length+' comparison views, verified matched binaries and title contrast');</script></html>'''
    (ROOT/'report.html').write_text(page)
    lines = ['Round 68: cliff, cloud and camp-slab corrections',
             f'Baseline master {BASELINE}; sol3/work; native 1280x720.',
             f"Title minimum contrast: master {contrast['before']['minimum_ratio']:.4f}:1 -> after {contrast['after']['minimum_ratio']:.4f}:1; floor 3:1.",
             f"Samples: {contrast['after']['opaque_atlas_pixels']} opaque atlas pixels; matched background companion.",
             '', *[f'{view}: {captions[view]}' for view in views], '',
             'Checks: '+', '.join(checks)+'. White-background negative control correctly fails.',
             'Waterfall 200%: before/after waterfall-200.png and waterfall-{left,right}-200.png.',
             'Reproduce: python3 tools/round68_art_check.py prepare before; prepare after; capture before; capture after; report.',
             'Pixel assertion: BOTW_TITLE_BACKGROUND=build/round68/after/title-background.png sloppy/bin/sloppy tools/title_panorama_check.jo',
             'Capture mode self-locks; never wrap in flock. Build evidence remains ignored.']
    (ROOT/'report.txt').write_text('\n'.join(lines)+'\n')
    print('PASS round68 report: ten matched production views, 200% waterfall and verified lettering contrast')

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'prepare': prepare(sys.argv[2])
    elif mode == 'capture':
        for view in sys.argv[3:] or VIEWS: run(sys.argv[2], view, '1280x720')
    elif mode == 'report': report()
    elif mode == 'negative': negative_control()
