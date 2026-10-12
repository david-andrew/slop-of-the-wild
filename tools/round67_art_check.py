#!/usr/bin/env python3
"""Matched Round 67 vegetation, landscape and title evidence. Self-locks capture batches and each paired GPU view; do not wrap in flock.

Build build/round67/{before,after}-game from the complete production entry point
plus tools/performance_output.jo. Captures and paired GPU samples use those frozen
binaries. Raw evidence stays ignored. Run capture before|after, gpu, or prepare before|after.
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
ROOT = Path('build/round67')
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
BASELINE = '645907d'

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
    source = source.replace('update = (dt0: f64):','production_update = (dt0: f64):')
    source += "\nuse '../../tools/performance_output.jo'\nupdate = (dt: f64):\n    freeze = to_int(env(\"ROUND67_FREEZE\") ?? \"0\") ?? 0\n    if freeze == 0 or frame_number() <= freeze: production_update(dt)\n    else: frame_stats_begin(post.scale)\nmain = (): performance_output_run(update, draw)\n"
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
    env = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'ROUND67_'))}
    env.update(BOTW_HOUR='11', BOTW_WEATHER='clear', BOTW_SCALE='1',
               BOTW_NOVSYNC='1', BOTW_NO_PREPARED_ASSETS='1', SLOPPY_PLATFORM='x11',
               SLOPPY_WINDOW=size, SLOPPY_FRAMES=str((discard + 4) * 120 if gpu else frame),
               SLOPPY_SCREENSHOT=str(out.with_suffix('.png').resolve()))
    env.update(flags)
    if gpu: env.update(BOTW_GPU='1', ROUND67_FREEZE=str(frame))
    with out.with_suffix('.log').open('w') as log:
        command = ['python3','tools/cliff_capture_window.py',size,'timeout','300',str(binary)]
        if not locked: command = ['flock','/tmp/botw-render.lock',*command]
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    assert Image.open(out.with_suffix('.png')).size == tuple(map(int,size.split('x')))
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == digest
    samples = [float(re.search(r'= ([\d.]+)$',line)[1]) for line in out.with_suffix('.log').read_text().splitlines() if line.startswith('gpu ms:')]
    row = dict(binary_sha256=digest, env={k:v for k,v in env.items() if k.startswith(('BOTW_', 'SLOPPY_', 'ROUND67_'))}, samples=samples)
    if gpu:
        assert len(samples) >= discard + 3, samples
        row['discard_batches'] = discard
        row['median_ms'] = statistics.median(samples[discard:])
    out.with_suffix('.json').write_text(json.dumps(row,indent=2)+'\n')
    print(phase, view, size, row.get('median_ms','captured'),flush=True)
    return row

def report():
    """Verify the complete evidence before writing the local comparison gallery."""
    import html
    weather = json.loads((ROOT / 'weather/contrast.json').read_text())
    minimum = min(min(r['contrast'], r['paired_separation']) for r in weather['results'].values())
    assert len(weather['results']) == 12 and not weather['failures'] and minimum >= .12
    gpu = json.loads((ROOT / 'gpu-summary.json').read_text())
    assert len(gpu) == len(VIEWS) * 2 and all(r['passed'] for r in gpu.values())
    checks = {
        'daylight': ('daylight-check.log', 'PASS ', 7),
        'journey': ('journey-check.log', 'PASS journey: uninterrupted field traversal', 1),
        'traversal': ('traversal-check.log', '1607/1607 checks passed', 1),
        'title panorama': ('title-panorama-check.log', 'PASS panorama: 2081160 projections', 1),
        'landscape identity': ('landscape-check.log', 'landscape:', 1),
        'prepared assets': ('prepared-assets-check.log', 'PASS prepared assets:', 1),
        'waterfall shelves': ('water-coverage-check.log', 'PASS waterfall shelves:', 1),
        'cliff mesh': ('cliff-mesh-check.log', 'cliff mesh PASS:', 1),
        'cliff climb': ('cliff-climb-check.log', 'cliff climb PASS:', 1),
    }
    for name, (log, token, count) in checks.items():
        text = (ROOT / log).read_text()
        assert text.count(token) == count and 'FAIL' not in text, name
    manifests = {}
    for phase in ('before', 'after'):
        manifests[phase] = json.loads((ROOT / f'{phase}-source.json').read_text())
        digest = hashlib.sha256((ROOT / f'{phase}-game').read_bytes()).hexdigest()
        for view in VIEWS:
            metadata = json.loads((ROOT / phase / f'{view}.json').read_text())
            assert metadata['binary_sha256'] == digest, f'{phase}/{view}: capture binary mismatch'
            flags, frame = VIEWS[view]
            assert all(metadata['env'][key] == value for key, value in flags.items()), view
            assert metadata['env']['SLOPPY_FRAMES'] == str(frame), view
            for size in ('1280x720', '2133x1200'):
                for repeat in range(3):
                    metadata = json.loads((ROOT / 'gpu' / f'{size}-{view}-{phase}-{repeat}.json').read_text())
                    assert metadata['binary_sha256'] == digest, f'{phase}/{size}/{view}/{repeat}: GPU binary mismatch'
                    assert all(metadata['env'][key] == value for key, value in flags.items()), view
                    assert metadata['env']['SLOPPY_WINDOW'] == size
                    assert metadata['env']['ROUND67_FREEZE'] == str(frame)
                    assert metadata['env']['BOTW_SCALE'] == '1'
    for name, digest in manifests['after']['modules'].items():
        assert hashlib.sha256((Path('game') / name).read_bytes()).hexdigest() == digest, name
    captions = {
        'grass': 'Mixed fine stems, bent leaves, ochre seed panicles and smaller flowers replace the repeated broad ribbons. Grass keeps the same patch, blade and LOD budgets.',
        'title': 'A continuous cloud field on the sky sphere preserves rounded cumulus lobes and broad stratus washes toward the horizon. Castle smoke has dark magenta folds and uneven, separated coils inside the existing title-safe envelope. Distant field stands now have long uneven boughs and broader pasture gaps. Rounded, eroded foothill crowns and radial volcanic ridges use muted grey-green pigment.',
        'overlook': 'Windward crags break Hylia snow faces; lee pockets retain snow. Softer crown coverage and winding woodland fingers reduce hard repeated silhouettes.',
        'waterfall': 'Real water-triangle intersections anchor ledge spray fans outside stone. Broken foam and translucent interruptions vary the falling sheet at rock contact. Crosswise warping and shorter moving marks interrupt uniform stripes; a broad scalloped foam roll softens the lip. Flow and collision are unchanged.',
        'snow': 'Matched player view of deep snow; the snow-faces and overlook views show the exposed shoulders and lee accumulation.',
        'snow-faces': 'Local mineral crags interrupt broad snow faces instead of uniform contour bands; the exposed side follows the wind direction.',
        'cliffs': 'Slanted mineral plates, stronger local pigment breakup and small shading facets roughen the pillar faces. The existing mesh, LODs and climb collision stay in place.',
        'golden': 'At the requested 06:24 location, a smooth solar-height tint shifts the rendered sky, cloud pigment and horizon haze toward ivory and apricot.',
        'camp': 'The slab is an ordinary cliff outcrop north of the west camp, traced to (-1454,1547), rendered through build.jo material 4. It now has grey mineral plates, tilted beds and small shading facets across its large cap/front faces.',
        'canopy': 'Broader derivative-sized dither coverage softens foliage rims, and distant crowns retain less dark edge pigment. Coverage still shares the existing depth pass.',
    }
    summary = dict(baseline=BASELINE, window='1280x720', weather_passed=12,
                   weather_minimum=minimum, weather_required=.12, daylight_passed=7,
                   traversal_passed=1607, title_projections=2081160,
                   journey_frames=67374, journey_metres=4851.34,
                   prepared_assets_passed=True, gpu=gpu, changes=captions)
    (ROOT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    sections = []
    for index, view in enumerate(VIEWS):
        paths = []
        for phase in ('before', 'after'):
            with Image.open(ROOT / phase / f'{view}.png') as image:
                assert image.size == (1280, 720)
                dest = ROOT / 'display' / f'{phase}-{view}.jpg'
                dest.parent.mkdir(exist_ok=True)
                image.convert('RGB').save(dest, quality=95, subsampling=0)
                paths.append(dest.resolve())
        sections.append(f'<section {"hidden" if index else ""}><div class="compare"><img src="{paths[1]}" alt="After {view}"><img class="before" src="{paths[0]}" alt="Before {view}"><span class="left">Before · {BASELINE}</span><span class="right">After</span></div><p>{html.escape(captions[view])}</p></section>')
    options = ''.join(f'<option value="{i}">{html.escape(view.replace("-", " ").title())}</option>' for i, view in enumerate(VIEWS))
    rows = ''.join(f'<tr><td>{key}</td><td>{r["before_ms"]:.2f}</td><td>{r["after_ms"]:.2f}</td><td>{r["delta_ms"]:+.2f}</td></tr>' for key,r in gpu.items())
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Round 67 landscape comparison</title>
<style>body{{margin:0;color:var(--foreground,#26362d);font:14px/1.5 var(--font-sans,system-ui)}}
.controls{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px}}
select,button{{padding:6px;border:1px solid var(--border,#abb6ae);border-radius:6px;background:var(--secondary,#e7ece8);color:inherit}}button{{cursor:pointer}}
input{{max-width:100%;width:170px}}.compare{{position:relative;aspect-ratio:16/9;overflow:hidden;border-radius:8px}}
img{{display:block;width:100%}}.before{{position:absolute;inset:0;clip-path:inset(0 50% 0 0)}}
.left,.right{{position:absolute;top:8px;padding:2px 6px;border-radius:4px;background:#17241fd9;color:white;font-size:12px}}
.left{{left:8px}}.right{{right:8px}}p{{margin:10px 0 16px}}
.checks{{padding:16px;background:var(--secondary,#e7ece8);border-radius:var(--radius,8px)}}
summary{{cursor:pointer;font-weight:600;margin:12px 0}}table{{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}}td,th{{text-align:right;padding:5px;border-bottom:1px solid var(--border,#abb6ae)}}td:first-child,th:first-child{{text-align:left}}
</style><div class="controls"><label>View <select id="view">{options}</select></label><label>Compare <input type="range" id="split" min="0" max="100" value="50" aria-label="Before and after split"></label><button id="old">Before</button><button id="new">After</button></div>
{''.join(sections)}<div class="checks">Silhouettes: 12/12 ≥12% · minimum {minimum:.1%}. Daylight: 7/7. Journey: 4.85 km, no stuck points. Traversal: 1,607/1,607. Title: 2,081,160 projections. Prepared packs: byte-equivalent. GPU: {len(gpu)}/{len(gpu)} paired budgets.</div>
<details><summary>GPU comparison · milliseconds</summary><table><thead><tr><th>View / pixels</th><th>Before</th><th>After</th><th>Δ</th></tr></thead><tbody>{rows}</tbody></table><p>Three alternating runs per immutable binary and view. Fixed scene scale 1; freeze at the reviewed frame, warm GPU timer queries. Limit: baseline × 1.03 + 0.10 ms. Both 1280×720 and 2133×1200 drawable sizes verified.</p></details>
<details><summary>Capture protocol and limits</summary><p>Baseline {BASELINE}. All images: 1280×720, clear weather, identical inputs and capture frames. Golden hour is fixed at 06:24; other views start at 11:00. Title frame 720, camp frame 260, others frame 300. Display copies are JPEG; original PNGs, executable/source hashes, environments and timer samples remain in build/round67. All renders serialize on /tmp/botw-render.lock.</p><p>Snow exposure is a material effect and ledge spray is anchored to the water surface; terrain and water collision are unchanged. Waterfall and snow refinements are modest at these fixed cameras. Distant scenery still uses low-detail crowns and procedural placement outside the three field stands. Surface-color isolation and a production-camera triangle trace identify the camp slab as a cliff outcrop using material 4 in the general building renderer. The trace, coordinates and diagnostic sources are retained beside the comparisons; the CPU asset-check trace intentionally makes no valid visual capture. This is implementation evidence, with no new critic score claimed.</p></details>
<script>const views=[...document.querySelectorAll('section')],split=document.querySelector('#split');function compare(n){{split.value=n;document.querySelectorAll('.before').forEach(v=>v.style.clipPath=`inset(0 ${{100-n}}% 0 0)`);document.querySelectorAll('.left').forEach(v=>v.hidden=Number(n)===0);document.querySelectorAll('.right').forEach(v=>v.hidden=Number(n)===100);}}document.querySelector('#view').onchange=e=>views.forEach((v,i)=>v.hidden=i!==Number(e.target.value));split.oninput=e=>compare(e.target.value);document.querySelector('#old').onclick=()=>compare(100);document.querySelector('#new').onclick=()=>compare(0);console.log('Round67 comparison: '+views.length+' matched views');</script></html>'''
    (ROOT / 'report.html').write_text(page)
    lines = ['Round 67 vegetation, map and title art', f'Baseline: {BASELINE}; branch sol3/work.', '']
    lines += [f'{view}: {caption}' for view,caption in captions.items()]
    lines += ['', f'weather_silhouette_check: 12/12 >=12%; minimum {minimum:.4%}.',
              'daylight_check: 7/7. journey_check: 67374 frames / 4851.34m / no stuck points.',
              'traversal_check: 1607/1607. title_panorama_check: 2081160 projections.',
              'Prepared assets: complete byte equivalence.', f'GPU: {len(gpu)}/{len(gpu)} paired view/resolution budgets.',
              'Limit: baseline*1.03+0.10ms; three alternating runs; scene scale 1.',
              'See report.html, summary.json and native before/after PNGs.', '',
              'Reproduce from this worktree:',
              'python3 tools/round67_art_check.py prepare before',
              'python3 tools/round67_art_check.py capture before',
              'python3 tools/round67_art_check.py prepare after',
              'python3 tools/round67_art_check.py capture after',
              'tools/prepare_assets.sh > build/round67/prepare-assets.log 2>&1',
              'tools/prepared_assets_check.sh > build/round67/prepared-assets-check.log 2>&1',
              'sloppy/bin/sloppy tools/title_panorama_check.jo > build/round67/title-panorama-check.log 2>&1',
              'sloppy/bin/sloppy tools/landscape_check.jo > build/round67/landscape-check.log 2>&1',
              'sloppy/bin/sloppy tools/cliff_mesh_check.jo > build/round67/cliff-mesh-check.log 2>&1',
              'sloppy/bin/sloppy tools/cliff_climb_check.jo > build/round67/cliff-climb-check.log 2>&1',
              'sloppy/bin/sloppy tools/water_coverage_check.jo > build/round67/water-coverage-check.log 2>&1',
              'tools/journey_check.sh > build/round67/journey-check.log 2>&1',
              'tools/traversal_check --headless --out build/round67/traversal > build/round67/traversal-check.log 2>&1',
              'python3 tools/weather_silhouette_check.py --output build/round67/weather > build/round67/weather-check.log 2>&1',
              'BOTW_DAYLIGHT_OUTPUT=build/round67/daylight tools/daylight_check.sh > build/round67/daylight-check.log 2>&1',
              'python3 tools/round67_art_check.py gpu',
              'python3 tools/round67_art_check.py report',
              'Capture and GPU modes own their render locks; do not wrap them.']
    (ROOT / 'report.txt').write_text('\n'.join(lines) + '\n')
    print('PASS round67 report: matched source/binary evidence and all requested checks verified')


if __name__ == '__main__':
    mode=sys.argv[1]
    if mode=='prepare': prepare(sys.argv[2])
    elif mode=='capture':
        result = subprocess.run(['flock','/tmp/botw-render.lock',sys.executable,__file__,'_capture',*sys.argv[2:]],
                                env={**os.environ,'ROUND67_RENDER_LOCKED':'1'})
        sys.exit(result.returncode)
    elif mode=='_capture':
        assert os.environ.get('ROUND67_RENDER_LOCKED') == '1'
        for view in sys.argv[3:] or VIEWS: run(sys.argv[2],view,'1280x720',locked=True)
    elif mode=='_gpu':
        # Internal child: the parent owns the sole flock for these six renders.
        assert os.environ.get('ROUND67_RENDER_LOCKED') == '1'
        size,view=sys.argv[2:]
        runs={p:[] for p in ['before','after']}
        for repeat in range(3):
            for phase in (['before','after'] if repeat%2==0 else ['after','before']):
                runs[phase].append(run(phase,view,size,True,repeat,locked=True)['median_ms'])
        b,a=[statistics.median(runs[p]) for p in ['before','after']]
        row=dict(before_ms=b,after_ms=a,delta_ms=a-b,limit_ms=b*1.03+.1,passed=a<=b*1.03+.1,runs=runs)
        (ROOT/'gpu'/f'{size}-{view}-summary.json').write_text(json.dumps(row,indent=2)+'\n')
        print(view,size,'PASS' if row['passed'] else 'FAIL',row,flush=True)
    elif mode=='report': report()
    elif mode=='gpu':
        # Keep only two pairs queued at once so collaborators can acquire the
        # shared renderer between views. A pair owns one lock for its six runs.
        from concurrent.futures import ThreadPoolExecutor, as_completed
        results={}
        def pair(size,view):
            summary = ROOT/'gpu'/f'{size}-{view}-summary.json'
            valid = summary.exists()
            for phase in ['before','after']:
                digest = hashlib.sha256((ROOT/f'{phase}-game').read_bytes()).hexdigest()
                for repeat in range(3):
                    metadata = ROOT/'gpu'/f'{size}-{view}-{phase}-{repeat}.json'
                    valid = valid and metadata.exists()
                    if valid:
                        row = json.loads(metadata.read_text())
                        valid = row['binary_sha256'] == digest and all(
                            row['env'][key] == value for key,value in VIEWS[view][0].items())
                        valid = valid and row['env']['SLOPPY_WINDOW'] == size and (
                            row['env']['ROUND67_FREEZE'] == str(VIEWS[view][1])) and row['env']['BOTW_SCALE'] == '1'
            if not valid:
                subprocess.run(['flock','/tmp/botw-render.lock',sys.executable,__file__,'_gpu',size,view],
                    env={**os.environ,'ROUND67_RENDER_LOCKED':'1'},check=True)
            return f'{size}/{view}',json.loads(summary.read_text())
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(pair,size,view) for size in ['1280x720','2133x1200']
                     for view in sys.argv[2:] or VIEWS]
            for future in as_completed(futures):
                key,row=future.result()
                results[key]=row
                (ROOT/'gpu-summary.json').write_text(json.dumps(results,indent=2)+'\n')
        sys.exit(any(not r['passed'] for r in results.values()))
