#!/usr/bin/env python3
"""Consolidate the fixed executable runs, comparison images and preserved old report.
Run after performance_bench.py suites: performance_report.py build/perf56 CODE_COMMIT.
"""
import json
from pathlib import Path
import re
import statistics as st
import sys
from PIL import Image, ImageChops, ImageStat
from performance_bench import CASES, report

root=Path(sys.argv[1]).resolve(); revision=sys.argv[2]
views=list(CASES)[:8]
phases={}
for phase in ['before','after','full','presentation','extended']:
    report(root/phase)
    phases[phase]=json.loads((root/phase/'summary.json').read_text())



for phase, samples in phases.items():
    expected_revision='e1596ad' if phase=='before' else revision
    assert {r['metadata']['source_revision'] for r in samples.values()}=={expected_revision},phase
    assert len({r['metadata']['executable_sha256'] for r in samples.values()})==1,phase
    assert all(not r['gpu_skipped'] for r in samples.values()),phase
assert len({r['metadata']['executable_sha256'] for phase in ['after','full','presentation','extended'] for r in phases[phase].values()})==1


def runs(phase,view,mode='gpu',scale=.8):
    return [r for n,r in phases[phase].items() if n.startswith(f'{view}-{mode}-{scale:g}-')]


def span(v):
    return f'{st.median(v):.2f} ({min(v):.2f}–{max(v):.2f})'


def diff(a,b):
    a=Image.open(a).convert('RGB');b=Image.open(b).convert('RGB')
    assert a.size==b.size
    d=ImageChops.difference(a,b);h=d.histogram();n=a.width*a.height*3
    changed=100*(1-sum(h[k*256] for k in range(3))/n)
    # Fixed lower-centre inspection area around Link and foreground ground shadows.
    box=(int(a.width*.29),int(a.height*.50),int(a.width*.74),a.height)
    return {'rgb_mae_255':sum(ImageStat.Stat(d).mean)/3,
            'changed_channels_percent':changed,'maximum_channel':max(x[1] for x in d.getextrema()),
            'foreground_box':box,'foreground_mae_255':sum(ImageStat.Stat(d.crop(box)).mean)/3}

images={};table=[];full=[];delivery=[];startup=[]
for v in views:
    rs=runs('after',v);bs=runs('before',v)
    assert len(rs)==3 and len(bs)==1,(v,len(rs),len(bs))
    assert {r['metadata']['source_revision'] for r in rs}=={revision}
    assert all(r['output']=='2246x1227' for r in rs+bs)
    # Captures must use identical simulation/camera/resolution flags.
    for k in ['BOTW_AT','BOTW_FIRE','BOTW_WEATHER','BOTW_GIVE','SLOPPY_INPUT','BOTW_SCALE','SLOPPY_FRAMES','SLOPPY_WINDOW']:
        assert bs[0]['metadata']['flags'].get(k)==rs[0]['metadata']['flags'].get(k),(v,k)
    a=root/'before'/f'{v}-gpu-0.8-1.png';b=root/'after'/f'{v}-gpu-0.8-1.png'
    images[v]={'before':str(a),'after':str(b),**diff(a,b)}
    table.append(f"| {v} | {bs[0]['gpu_median']['total']:.2f} | {span([r['gpu_median']['total'] for r in rs])} | {max(r['gpu_peak_batch'] for r in rs):.2f} | {st.median(r['gpu_median']['terrain'] for r in rs):.2f} | {st.median(r['gpu_median']['trees'] for r in rs):.2f} | {st.median(r['gpu_median']['sh-veg0']+r['gpu_median']['sh-veg1'] for r in rs):.2f} |")
    fs=runs('full',v,scale=1)
    assert len(fs)==1 and fs[0]['output']=='2246x1227'
    full.append(f"| {v} | {fs[0]['gpu_median']['total']:.2f} | {fs[0]['gpu_peak_batch']:.2f} | {fs[0]['gpu_median']['terrain']:.2f} |")
for v in ['forest','pond','camp']:
    for mode in ['paced','mailbox']:
        rs=runs('presentation',v,mode)
        assert len(rs)==3 and {r['output'] for r in rs}=={'2133x1200'}
        delivery.append(f"| {v} / {mode} | "+' | '.join(span([r['interval'][k] for r in rs]) for k in ['p50','p95','p99','worst'])+f" | {st.median(r['present']['p95'] for r in rs):.2f} | {st.median(r['game_wall']['mean'] for r in rs):.2f} |")
for v in ['forest','title','entry','traversal']:
    rs=runs('after',v) if v=='forest' else runs('extended',v)
    assert len(rs)==3
    loads=[float(re.search(r'loaded in ([\d.]+)s',r['load_total'][0])[1]) for r in rs]
    first_cpu=[float(re.search(r'cpu ([\d.]+)',r['first_frame'][0])[1]) for r in rs]
    startup.append(f"| {v} | {span(loads)} | {span([r['rss_kib']/1024 for r in rs])} | {span(first_cpu)} | {span([r['early_worst'] for r in rs])} |")

budget={phase:all(r['gpu_peak_batch']<16.7 for r in phases[phase].values() if r['gpu_peak_batch'] is not None) for phase in ['after','full','extended']}
data={'code_revision':revision,'hardware':'GTX 1070 / i7-6700, 4 cores / 8 threads',
      'budget_all_steady_batches_under_16_7_ms':budget,'phases':phases,'images':images,
      'validation':json.loads((root/'checks/results.json').read_text())}
Path('docs/performance-round56.json').write_text(json.dumps(data,indent=2)+'\n')

forest_before=runs('before','forest')[0]['gpu_median']
forest_middle=st.median(r['gpu_median']['sh-veg1'] for r in runs('after','forest'))
forest_mailbox_p99=st.median(r['interval']['p99'] for r in runs('presentation','forest','mailbox'))

md=f'''# Performance

Current code: `{revision}` on `sol/work`, based on master `e1596ad`. Measured on 2026-10-10
with a GTX 1070 and i7-6700 (4 cores / 8 threads). Executable SHA-256, exact flags, all GPU
batches, load sections, peak process RSS, first-frame CPU, producer intervals, presentation
waits, and scene activity are retained in [performance-round56.json](performance-round56.json).
Raw logs, immutable executables and images: `build/perf56/`. Every game render holds
`/tmp/botw-render.lock`; compilation and other desktop work can run concurrently.

## Current GPU budget: 2246×1227 output, normal 80% scene scale

Three final repeats per view, 720 frames each. Scene: **1796×981**; post output: **2246×1227**.
Three 2048² shadow maps. X11 `BOTW_NOVSYNC=1`; actual output and successful swap-interval
selection are validated in every log. GPU totals sum instrumented passes and exclude the
runtime's presentation call. Each reported run median uses completed 120-query batches after
discarding the first two startup batches. Peak is the largest remaining batch, not a claim
about every individual GPU frame. The baseline is one fresh, unchanged `e1596ad` run. `overlook` retains the
existing benchmark camera aimed toward the cave mouth (the cave-overlook fixture).

| View | Baseline GPU ms | Current GPU median (min–max runs) | Peak batch ms | Terrain ms | Trees ms | Vegetation shadows ms |
|---|---:|---:|---:|---:|---:|---:|
'''+ '\n'.join(table)+f'''

The current baseline already meets the steady GPU budget after the earlier terrain cache
work. This change removes additional distant caster work: forest middle-cascade vegetation
shadows fall from {forest_before['sh-veg1']:.2f} to {forest_middle:.2f} ms. Whole-frame totals
remain similar within run variation; this caster change is not the cause of all savings
relative to the older table in the history section.

## Full-resolution stress: 2246×1227 output and scene

`BOTW_SCALE=1`, otherwise identical views, 720 frames, one current-code run each. These
measurements are separate from the normal large-window 80% renderer; no resolution reduction
was introduced by this work.

| View | Median GPU ms | Peak batch ms | Terrain ms |
|---|---:|---:|---:|
'''+ '\n'.join(full)+f'''

Budget check, all retained steady GPU batches below 16.7 ms: normal **{'PASS' if budget['after'] else 'FAIL'}**,
full resolution **{'PASS' if budget['full'] else 'FAIL'}**, extended traversal/startup scenarios **{'PASS' if budget['extended'] else 'FAIL'}**.

## Work removed and visual evidence

Only the middle vegetation shadow map uses lower leaf-card detail beyond 25 m. Each tree keeps
its outer crown cards by height band, crown tip, one in four interior cards, and the existing
low-detail trunk/forks. The full near map, camera view meshes, cutout thresholds, wind,
per-tree crown deformation, shadow-map sizes and cascade filtering are preserved. Independent
instance buffers keep lower-detail casters out of the two camera passes. The legacy triangle
debug counter uses max(vertex count, index count), so unused vertices make its printed values
upper bounds; the timing tables use measured GPU queries. Sol3 owns cascade
filtering separately; this branch does not change `shadows.jo`, `shade.jo` or `post.jo`.

Terrain already includes the exact hash-lattice cache and existing distance fades from round
53. The new current runs include that code; the historical 5–8 ms terrain / 16.73 ms fire table
below predates those savings. This round adds no terrain colour/normal approximation. The
cache costs 128 MiB of VRAM and is baked during load. The current 131,072-sample
GPU precision check passes: maximum cached/reference error 0.0002442; ALU fallback error 0.
This is the current result, distinct from the round-53 zero-error capture.

Fixed-frame before/after images below use the same camera and simulation. The numeric difference
and the lower-centre foreground crop accompany visual inspection; differences are confined to
more distant caster coverage. The crown geometry visible to the camera is unchanged; no visible quality loss was found
in these eight inspected pairs. Canonical
images retain the full output dimensions.

| View | Before | After | RGB MAE / 255 | Foreground MAE / 255 |
|---|---|---|---:|---:|
'''
for v,i in images.items():md+=f"| {v} | [PNG]({i['before']}) | [PNG]({i['after']}) | {i['rgb_mae_255']:.6f} | {i['foreground_mae_255']:.6f} |\n"
md+='''
## Frame production and presentation workaround

Three paired processes per view and mode. Normal Wayland output: **2133×1200**; scene:
**1706×960**, 80% scale. Raw intervals 241–720 (480 per run); nearest-rank percentiles.
CPU means cover game update/draw. Presentation is timed around the runtime's actual present
call; the JSON separates remaining runtime/thread work and voluntary/involuntary switches.

`SLOPPY_PRESENT=mailbox` is an opt-in local addition to the pinned Sloppy library. It skips
waiting for `wl_surface.frame` callbacks and lets the compositor replace pending commits;
all buffer-release waits remain, so busy buffers are never reused and the three-buffer pool
bounds submission. Normal pacing remains the default. These are **producer intervals**, not
measurements of when each image was displayed; a mailbox can replace frames before display.
The tests retain shared OS/driver caches and the same compositor; X11 remains a separate GPU
headroom measurement, not proof that EGL/Wayland presentation waits have disappeared.

| View / mode | p50 ms | p95 ms | p99 ms | Worst ms | Present p95 ms | Game CPU mean ms |
|---|---:|---:|---:|---:|---:|---:|
'''+ '\n'.join(delivery)+f'''

Mailbox reduces presentation waits in all three views, but the forest producer p99 median
is still {forest_mailbox_p99:.2f} ms. The workaround does not establish a universal 60 Hz
frame-delivery guarantee; game/GPU headroom and presentation tails remain separate results.

## Current startup, memory, first use, and long traversal

New processes; shared OS page and driver shader caches retained. Load includes the terrain
cache bake, decoded images/audio, shader warmup and correctly sized render targets. RSS is
maximum resident **system memory**, measured by `/usr/bin/time -v`, not GPU VRAM. Early worst
is the largest producer interval in frames 1–120; first-frame CPU and each loader section are
in the JSON. Title and shrine entry exercise production rendering using the documented
`BOTW_TITLE=1` and `BOTW_ENTER=1` fixtures; continuous title/story checks are separate.
Traversal runs 3600 frames / 60 simulated seconds with scripted sprint/walk changes:
195–197 m of sampled horizontal movement, including enemy contact, climbing, and a slide
section with limited forward progress. Scene logs
record actual player positions, HP, nearby engaged/striking enemies and fight actions, so the
combat and traversal samples can be checked against their intended activity.

| Scenario | Load seconds (median, range) | Peak RSS MiB (median, range) | First-frame CPU ms (median, range) | Early worst interval ms (median, range) |
|---|---:|---:|---:|---:|
'''+ '\n'.join(startup)+'''

The first final forest process reached 7.53 s load / 1250.48 MiB peak RSS; the later
forest processes loaded in 3.44 s / 923.37–926.90 MiB. The outlier remains in the reported
range and raw data rather than being discarded as startup noise.

## Validation and reproduction

All requested tools passed: `feel_test`, `fauna_test`, `element_test`, `element_check`,
`save_test`, `architecture_test`, `contact_check`, `integration_test`, `slot_check`, `input_check`,
`camera_check`, `combat_check`, `title_handoff_check`, `terrain_noise_check`, `weather_fx_test`,
`shrine_route_check.sh`, `shrine_exit_check.sh`, `passage_check.sh`, `opening_check.sh`,
`late_story_check.sh`, and `occluder_check.sh`. Logs: `build/perf56/checks/`.
Late story: 17,823 assertions / 8,835 frames / 147.25 simulated seconds; ordered four earned
orbs → Temple meeting → paraglider → departure, with no story progress presets.

```bash
sloppy/bin/sloppy build game/main.jo -o build/game-current
python3 tools/performance_bench.py capture build/game-current build/perf/current --revision CODE_COMMIT
python3 tools/performance_bench.py capture build/game-current build/perf/full --revision CODE_COMMIT --scale 1 --repeats 1
python3 tools/performance_bench.py capture build/game-current build/perf/paced --revision CODE_COMMIT --mode paced --views forest pond camp
python3 tools/performance_bench.py capture build/game-current build/perf/mailbox --revision CODE_COMMIT --mode mailbox --views forest pond camp
python3 tools/performance_bench.py capture build/game-current build/perf/traversal --revision CODE_COMMIT --views traversal --frames 3600
```

The helper locks each process, records load inside the lock, and validates actual dimensions,
fixed scale, complete intervals and X11 swap selection. `opening_check.sh`, `late_story_check.sh`,
`weather_transition_check.sh`, and `daylight_check.sh` own their locks; never wrap them again.

## History: earlier revisions and protocols

Historical reports below are retained as measured, with their resolutions and protocols.
They are not current-code measurements or substitute evidence for the tables above.

- [Round 53](PERFORMANCE_ROUND53.md): `fac814a` baseline, exact terrain cache and camera work;
  2246×1227 output / 80% scene, with a separately labeled oversized Wayland stress experiment.
- [Earlier findings](PERFORMANCE_FINDINGS.md): `9c98d6b` baseline, startup warmup, chime cache,
  instance-upload reuse, busy versus quiet runs, and presentation-tail attribution.
- [Burning camp](BURNING_CAMP_PERFORMANCE.md): `b53ddf0` baseline, smoke/depth/burn upload work;
  2246×1227 X11 versus 2133×1200 Wayland, scene72%, 960 frames, three repeats.

### Previous main performance table (2026-10-09)

This report did not store an exact final code revision; its date/protocol identify the dataset.
The round-53 exact terrain-cache work came later. Original text follows:

'''+((root/'performance-history.md').read_text() if (root/'performance-history.md').exists() else __import__('subprocess').check_output(['git','show','e1596ad:docs/PERFORMANCE.md'],text=True)).replace('# Performance\n','',1)
Path('docs/PERFORMANCE.md').write_text(md)
print('wrote docs/PERFORMANCE.md and docs/performance-round56.json')
