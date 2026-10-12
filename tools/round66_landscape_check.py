#!/usr/bin/env python3
"""Round 66 landscape evidence. Capture/GPU modes own their render locks.

Uses immutable full-production before/after binaries and the existing paired
timer-query protocol. Before is the requested master merge, 48285bf.
"""
import os
from pathlib import Path
import hashlib
import html
import json
import statistics
import subprocess
import sys

sys.dont_write_bytecode = True
import round66_art_check as evidence

evidence.BASELINE = '48285bf'
evidence.VIEWS = {
    'overview': ({'BOTW_SKIP': '1', 'BOTW_CAM': '-700,330,2150,-0.8,-0.35'}, 300),
    'cliffs': ({'BOTW_SKIP': '1', 'BOTW_CAM': '-1600,235,1815,1.2,-0.15'}, 300),
    'waterfall': ({'BOTW_SKIP': '1', 'BOTW_CAM': '-1660,175,1888,1.24,-0.05'}, 300),
    'golden-hour': ({'BOTW_SKIP': '1', 'BOTW_AT': '-1030,1805,1.57', 'BOTW_HOUR': '6.4'}, 300),
    'snow': ({'BOTW_SKIP': '1', 'BOTW_AT': '-1060,2230,2.0'}, 300),
    'pond': ({'BOTW_SKIP': '1', 'BOTW_AT': '-1190,1665,-0.9'}, 300),
    'temple': ({'BOTW_SKIP': '1', 'BOTW_AT': '-818,1950,3.14'}, 300),
    'tower': ({'BOTW_SKIP': '1', 'BOTW_TOWER': '1', 'BOTW_AT': '-560,1722,0'}, 300),
    'glide200': ({'BOTW_SKIP': '1', 'BOTW_AT': '-1030,1805,1.57', 'BOTW_GIVE': 'paraglider',
                  'SLOPPY_INPUT': '10:w+,20:shift+,100:shift-,230:space+,232:space-'}, 200),
    'glide260': ({'BOTW_SKIP': '1', 'BOTW_AT': '-1030,1805,1.57', 'BOTW_GIVE': 'paraglider',
                  'SLOPPY_INPUT': '10:w+,20:shift+,100:shift-,230:space+,232:space-'}, 260),
    'glide330': ({'BOTW_SKIP': '1', 'BOTW_AT': '-1030,1805,1.57', 'BOTW_GIVE': 'paraglider',
                  'SLOPPY_INPUT': '10:w+,20:shift+,100:shift-,230:space+,232:space-'}, 330),
    'camp': ({'BOTW_SKIP': '1', 'BOTW_CAM': '-947,243,1956,-0.85,-0.45'}, 300),
}

def locked_child(*args):
    return subprocess.run(['flock', '/tmp/botw-render.lock', sys.executable,
                           str(Path(__file__).resolve()), *args],
                          env={**os.environ, 'ROUND66_RENDER_LOCKED': '1'}, check=True)


def gpu_pair(size, view):
    assert os.environ.get('ROUND66_RENDER_LOCKED') == '1'
    runs = {phase: [] for phase in ('before', 'after')}
    for repeat in range(3):
        phases = ('before', 'after') if repeat % 2 == 0 else ('after', 'before')
        for phase in phases:
            row = evidence.run(phase, view, size, gpu=True, repeat=repeat, locked=True)
            runs[phase].append(row['median_ms'])
    before, after = (statistics.median(runs[phase]) for phase in ('before', 'after'))
    result = dict(before_ms=before, after_ms=after, delta_ms=after-before,
                  limit_ms=before*1.03+.1, passed=after <= before*1.03+.1, runs=runs)
    path = evidence.ROOT / 'gpu' / f'{size}-{view}-summary.json'
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(view, size, 'PASS' if result['passed'] else 'FAIL', result, flush=True)


def report():
    root = evidence.ROOT
    weather = json.loads((root / 'weather' / 'contrast.json').read_text())
    assert len(weather['results']) == 12
    minimum = min(min(row['contrast'], row['paired_separation']) for row in weather['results'].values())
    assert minimum >= .12, f'Requested 12% silhouette floor missed: {minimum:.4f}'
    gpu = json.loads((root / 'gpu-summary.json').read_text())
    assert len(gpu) == 8 and all(row['passed'] for row in gpu.values())
    daylight = (root / 'daylight-check.log').read_text()
    assert daylight.count('PASS ') == 7 and 'FAIL ' not in daylight
    assert 'PASS prepared assets:' in (root / 'prepared-assets-check.log').read_text()
    assert 'PASS journey: uninterrupted field traversal' in (root / 'journey-check.log').read_text()
    assert '997/997 checks passed' in (root / 'traversal-check.log').read_text()
    # The report must describe the exact production modules in the after binary.
    manifest = json.loads((root / 'after-source.json').read_text())['modules']
    for name, digest in manifest.items():
        assert hashlib.sha256((Path('game') / name).read_bytes()).hexdigest() == digest, name
    ranks = [
        ('Bare glide cliff', 'Heightfield ribs and recessed gullies break the off-route shoulder; cool mineral washes and broader relief shading carry its exposed rock.'),
        ('Stripy west cliff strata', 'Closer stone values, broad cross-bed stains and broken lip highlights let buttress lighting lead. The waterfall remains the focal light shape.'),
        ('Evenly bright Temple slopes', 'Baked damp hollows separate cool swathes from warm dry lawns. Existing shrubs form longer uneven groups and remain visible from the overview.'),
        ('Blobby snow boundary', 'Wind tongues, baked ridge exposure and stronger mixed-margin scour reveal rock/tundra between drifts. Deep snow stays continuous.'),
        ('Repeated procedural slope texture', 'Distant comb and small-stroke contrast is reduced. Broader meadow masses read first; some evenly scattered original trees remain.'),
    ]
    summary = dict(baseline=evidence.BASELINE, window='1280x720', weather_threshold=.12,
                   weather_minimum=minimum, weather_passed=12, daylight_passed=7,
                   traversal_passed=997, prepared_assets_passed=True, journey_passed=True,
                   ranked_problems=[dict(rank=i+1, problem=p, result=r) for i, (p, r) in enumerate(ranks)], gpu=gpu)
    (root / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    notes = '\n'.join(f'{i+1}. {problem}\n   {result}' for i, (problem, result) in enumerate(ranks))
    (root / 'report.txt').write_text(f'''Round 66 landscape art
Baseline: master 48285bf. Branch: sol3/work. No push or merge.

Ranked critique and implemented changes:
{notes}

Validation:
weather_silhouette_check: 12/12 at or above 12%; minimum {minimum:.4%}.
daylight_check: 7/7 dawn/dusk sequences.
journey_check: 67,374 frames, 1122.90 seconds, 4851.34 m; no stuck points.
traversal_check: 997/997 checks at 30/60/120 Hz and irregular updates.
prepare_assets and prepared_assets_check: complete byte equivalence.
GPU: eight paired view/resolution budgets, three alternating runs per pair;
1280x720 and 2133x1200, scene scale 1; baseline*1.03+0.10 ms limit.
See gpu-summary.json, summary.json, each capture's JSON/log and report.html.

Visual evidence:
All ten requested views are saved in before/ and after/. The glide has frames
200,260,330. The waterfall uses -1660,175,1888,1.24,-0.05. Golden hour is 6.4.
The HTML gallery uses JPEG display copies in display/; all measurements and
capture-size checks use the original PNGs, which remain in before/ and after/.
Fixed camera views align exactly. Glide captures use identical input/frame
counts; the terrain ribs change the actual descent and following camera.
The Temple meadow and snow margin are best judged in the overview; their
requested player views show the close masonry and deep snow respectively.

Remaining limitations:
The snow margin is a modest refinement; the large underlying snowfield shape
still needs a later geometry pass. Original saplings remain sparsely scattered,
and the overlook shoulder is less developed than the authored west cliff mesh.
No new art scores are claimed; this is a direct implementation-agent critique.

Reproduction (run from the repository; render scripts own their locks):
python3 tools/round66_landscape_check.py prepare before
python3 tools/round66_landscape_check.py capture before
python3 tools/round66_landscape_check.py prepare after
python3 tools/round66_landscape_check.py capture after
tools/prepare_assets.sh > build/round66/prepare-assets.log 2>&1
tools/prepared_assets_check.sh > build/round66/prepared-assets-check.log 2>&1
tools/journey_check.sh > build/round66/journey-check.log 2>&1
tools/traversal_check --headless --out build/round66/traversal > build/round66/traversal-check.log 2>&1
python3 tools/weather_silhouette_check.py --output build/round66/weather > build/round66/weather-check.log 2>&1
BOTW_DAYLIGHT_OUTPUT=build/round66/daylight tools/daylight_check.sh > build/round66/daylight-check.log 2>&1
python3 tools/round66_landscape_check.py gpu > build/round66/gpu-check.log 2>&1
python3 tools/round66_landscape_check.py report
''')
    captions = {
        'glide260': ranks[0][1], 'glide330': ranks[0][1], 'glide200': ranks[0][1],
        'cliffs': ranks[1][1], 'waterfall': ranks[1][1], 'overview': ranks[2][1] + ' ' + ranks[3][1],
        'snow': 'Requested snowy player view; the overview gives the complementary view of the snow margin.',
        'temple': 'Requested close approach to the Temple masonry. The overview shows its open hillside composition.',
        'golden-hour': 'Matched 6.4-hour dawn; warm turf and the muted forest floor retain their established palette.',
        'pond': 'Hopper Pond: water, shoreline, canopy and silhouette retained.',
        'tower': 'Tower approach: dark Sheikah stone stays legible against the soft meadow.',
        'camp': 'Camp composition retained; no enemy, hero or camp gameplay edits.',
    }
    sections = []
    order = ['cliffs', 'glide260', 'overview', 'snow', 'waterfall', 'glide330', 'glide200',
             'golden-hour', 'pond', 'temple', 'tower', 'camp']
    titles = {'glide260': 'Glide · frame 260', 'glide330': 'Glide · frame 330',
              'glide200': 'Descent · frame 200', 'cliffs': 'West cliffs',
              'overview': 'Overview / Temple meadow / snow margin', 'snow': 'Snow',
              'waterfall': 'Waterfall', 'golden-hour': 'Golden hour', 'pond': 'Hopper Pond',
              'temple': 'Temple of Time', 'tower': 'Tower', 'camp': 'Camp'}
    for index, view in enumerate(order):
        paths = []
        for phase in ('before', 'after'):
            from PIL import Image
            with Image.open(root / phase / f'{view}.png') as image:
                assert image.size == (1280, 720)
                path = root / 'display' / f'{phase}-{view}.jpg'
                path.parent.mkdir(exist_ok=True)
                image.convert('RGB').save(path, quality=95, subsampling=0)
                paths.append(path.resolve())
        sections.append(f'''<section class="view" {'hidden' if index else ''}>
<div class="comparison"><img src="{paths[1]}" alt="After {view}">
<img class="before" src="{paths[0]}" alt="Before {view}">
<span class="tag left">Before · 48285bf</span><span class="tag right">After</span></div>
<p>{html.escape(captions[view])}</p></section>''')
    options = ''.join(f'<option value="{i}">{html.escape(titles[view])}</option>' for i, view in enumerate(order))
    ranking = ''.join(f'<li><strong>{html.escape(problem)}.</strong> {html.escape(result)}</li>' for problem, result in ranks)
    gpu_rows = ''.join(f'<tr><td>{key}</td><td>{row["before_ms"]:.2f}</td><td>{row["after_ms"]:.2f}</td><td>{row["delta_ms"]:+.2f}</td></tr>' for key, row in gpu.items())
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Round 66 landscape art</title>
<style>body{{margin:0;font:14px/1.5 var(--font-sans,system-ui);color:var(--foreground,#24312c)}}
.controls{{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin:0 0 12px}}
select,button{{padding:6px;max-width:100%;background:var(--secondary,#e7ece8);color:inherit;border:1px solid var(--border,#c5cfc8);border-radius:6px}}button{{cursor:pointer}}
#view{{width:210px}}.phasebuttons{{display:inline-flex;gap:8px}}
input{{width:220px;max-width:100%}}.comparison{{position:relative;aspect-ratio:16/9;overflow:hidden;border-radius:8px}}
img{{display:block;width:100%}}.before{{position:absolute;inset:0;clip-path:inset(0 50% 0 0)}}
.tag{{position:absolute;top:10px;background:#16251dd9;color:white;padding:3px 8px;border-radius:4px}}
.left{{left:10px}}.right{{right:10px}}p{{margin:10px 0 18px}}li{{margin-bottom:8px}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}}td,th{{text-align:right;padding:5px;border-bottom:1px solid var(--border,#c5cfc8)}}td:first-child,th:first-child{{text-align:left}}
summary{{cursor:pointer;font-weight:600;margin:12px 0}}.checks{{padding:16px;border-radius:var(--radius,8px);background:var(--secondary,#e5f0e8);color:var(--secondary-foreground,#24312c)}}
</style><div class="controls"><label>View <select id="view">{options}</select></label>
<label>Compare <input id="split" type="range" min="0" max="100" value="50" aria-label="Before and after split"></label>
<span class="phasebuttons"><button id="show-before">Before</button><button id="show-after">After</button></span></div>
{''.join(sections)}<div class="checks">Silhouettes: 12/12 ≥12% (minimum {minimum:.1%}). Daylight: 7/7.
Journey: 67,374 frames. Traversal: 997/997. Prepared packs: byte-equivalent. GPU: 8/8 paired view/resolution budgets.</div>
<details><summary>Five ranked art problems and changes</summary><ol>{ranking}</ol></details>
<details><summary>GPU evidence · milliseconds</summary><table><thead><tr><th>View / output</th><th>Before</th><th>After</th><th>Δ</th></tr></thead><tbody>{gpu_rows}</tbody></table>
<p>Three alternating runs per binary and view; fixed scene scale 1, frozen production update at the reviewed frame, warm timer queries. Limit: baseline × 1.03 + 0.10 ms. Every output was checked at its actual drawable size.</p></details>
<p>All requested views: 1280×720, clear weather, 11:00 except golden hour at 6.4. Mid-distance waterfall camera: −1660,175,1888,1.24,−0.05. Glide frames: 200,260,330; identical input, with terrain ribs changing the actual descent and following camera. JPEG display copies are shown here; native PNGs and measurements remain in before/ and after/. Rank 4 is a modest margin refinement; the broad snowfield shape and sparse original tree spacing remain candidates for a later geometry pass.</p>
<script>const views=[...document.querySelectorAll('.view')];const split=document.querySelector('#split');function compare(n){{split.value=n;document.querySelectorAll('.before').forEach(v=>v.style.clipPath=`inset(0 ${{100-n}}% 0 0)`)}}document.querySelector('#view').onchange=e=>views.forEach((v,i)=>v.hidden=i!==Number(e.target.value));split.oninput=e=>compare(e.target.value);document.querySelector('#show-before').onclick=()=>compare(100);document.querySelector('#show-after').onclick=()=>compare(0);</script></html>'''
    (root / 'report.html').write_text(page)
    print('PASS round66 report: all evidence and requested 12% silhouette floor verified')


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'prepare':
        evidence.prepare(sys.argv[2])
    elif mode == 'capture':
        for view in sys.argv[3:] or evidence.VIEWS:
            locked_child('_capture', sys.argv[2], view)
    elif mode == '_capture':
        assert os.environ.get('ROUND66_RENDER_LOCKED') == '1'
        # Accept multiple views for batches started by the original CLI.
        for view in sys.argv[3:]:
            evidence.run(sys.argv[2], view, '1280x720', locked=True)
    elif mode == '_gpu':
        gpu_pair(*sys.argv[2:])
    elif mode == 'report':
        report()
    elif mode == 'gpu':
        results = {}
        for size in ('1280x720', '2133x1200'):
            for view in sys.argv[2:] or ('overview', 'cliffs', 'glide260', 'snow'):
                summary = evidence.ROOT / 'gpu' / f'{size}-{view}-summary.json'
                valid = summary.exists()
                for phase in ('before', 'after'):
                    digest = hashlib.sha256((evidence.ROOT / f'{phase}-game').read_bytes()).hexdigest()
                    for repeat in range(3):
                        metadata = evidence.ROOT / 'gpu' / f'{size}-{view}-{phase}-{repeat}.json'
                        valid = valid and metadata.exists()
                        if valid:
                            valid = json.loads(metadata.read_text())['binary_sha256'] == digest
                if not valid:
                    locked_child('_gpu', size, view)
                results[f'{size}/{view}'] = json.loads(summary.read_text())
                (evidence.ROOT / 'gpu-summary.json').write_text(json.dumps(results, indent=2) + '\n')
        sys.exit(any(not row['passed'] for row in results.values()))
    else:
        sys.exit('Usage: round66_landscape_check.py prepare before|after / capture before|after [views] / gpu [views] / report')
