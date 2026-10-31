# Performance — Sloppy 0.6.0, 2026-10-15

Unmodified official **0.6.0** (`7c8d133`), i7-6700 / GTX 1070, Wayland and XWayland,
**2133×1200 physical pixels**. Dynamic and fixed scene scales are identified per run. All outliers are
retained. These are **producer/present-return intervals, not scanout timestamps**;
the shared desktop is not an isolated hardware guarantee.

## Round 72 camera follow-up

Master `101d247` was merged into `sol/work` as `0739acc` before this follow-up.
Stone-wall climbing now eases to a 5.3 m boom, hip-height look point and 0.65 rad
downward pitch. The supplied Temple gameplay frame 180 and final frame 181
exclude the dark aisle underside and its ragged boundary; masonry stays opaque.
Natural cliffs use a 5 m oblique view with a retained shoulder chosen once from
frame-edge scenery probes. Lens clearance remains active. The cliff draw
decorator receives its existing inactive-player marker during opaque climbing,
removing the exposed fragment dither without changing the cliff shader,
mineral response, geometry or uniform layout.

The final capture-only pack passes: **50 requested frames plus 37 final PNGs**.
Every PNG was viewed downscaled beside `/tmp/crit72pack` and the previous own
`build/sol72/release-pack`; 24 are pixel-identical to each reference. Other
differences include the requested master character/weather merge and the two
camera compositions. Tent-fire frame 900 and final are pixel-identical to an
additional render of the merged baseline. The requested climb frame 180 and
final frame 181 also exactly match their independently rendered timing-fixture
counterparts, establishing the matched simulation times.

Full-frame cliff luma standard deviation improves **13.505 → 24.094** at
1280×720 (Pillow L conversion). The near held skin remains smooth and low-contrast
at five metres. **Its material is left unchanged for Astra**; the new framing
supplies the cliff silhouette, valley, terrain and sky context.

Matched timing controls use the merged baseline and final binaries, X11/Vulkan,
1280×720, fixed scene scale 1.00, 1/60 simulation, frozen 11:00 clear and weather
seed 31. Three AB/BA/AB pairs per scene run 360 frames. Each run's nearest-rank
p99 excludes frames 1–60 (300 samples); the table is the **median of three run
p99 values**, not a pooled percentile. All runs and tails are retained.

| Scene | Baseline thread p99, ms | Final thread p99, ms | Baseline wall p99, ms | Final wall p99, ms |
|---|---:|---:|---:|---:|
| Temple gameplay climb | 6.796 | 5.579 | 10.858 | 5.726 |
| Cliff gameplay climb | 5.102 | 6.488 | 6.147 | 7.103 |

**Strict cliff CPU p99 non-regression is not established.** Its thread point
estimate rises by 1.386 ms even though per-run thread p50 improves. Baseline
cliff p99 spans 3.455–6.918 ms; final spans 6.037–9.104 ms. Temple improves in
all three pairs. The shared host is not isolated; the variation does not prove
that the cliff cannot regress. No measured callback after frame 60 exceeds 25 ms.
Raw per-run settings, executable hashes, frame samples and the summary are in
[`paired-cpu-v3`](../build/sol72-followup/paired-cpu-v3/summary.json).

The complete-pack follow-up repeats the **120-second real-dt forest route at
2133×1200 physical output**, with dynamic and fixed scale 1.00 measured separately.
Both select immediate (driver mailbox fallback). Steady percentiles exclude the
first 240 frames; these are present-return intervals, not scanout. All tails and
shared-host variation remain in the raw logs.

| Route | Observed scene scale | Present p50, ms | Present p99, ms | Present worst, ms | Thread p99, ms | Intervals >25 ms |
|---|---|---:|---:|---:|---:|---:|
| Dynamic | 0.80 | 12.233 | 16.829 | 32.751 | 10.851 | 3 |
| Fixed | 1.00 | 15.200 | 20.627 | 40.166 | 11.617 | 12 |

The 720-frame diagnostic profile reduces average camera-update wall time from
about 0.095 to 0.072 ms, and its instrumented thread p99 is 3.658 → 3.158 ms.
Average wall time at terrain selection rises, a stage that also streams node
buffers. This does not locate the p99 increase in camera CPU work. Instrumented results
are diagnostic and do not replace the uninstrumented cohort above. Full stage
traces are in `build/sol72-followup/cliff-profile/`.

The **complete final pack passes**, including both forest routes, 13 audio clips
and all eight regression groups (`feel_test`, `integration_test`, `input_check`,
`opening_test`, `combat_check`, `weather_fx_test`, `music_harmony_check`,
`late_story_check`). Source and screenshot hashes were verified against the final
tree, and all 87 capture PNGs have recorded visual comparisons.

A longer 720-frame guarded cliff cohort could not obtain an accepted pair in
four attempts. The first was rejected after an Astra `final-traversal/check`
GPU context overlapped its launch. The other three failed the unchanged
pre-launch CPU/GPU activity limits (CPU <12%, GPU <5%); no thresholds were
relaxed. Samples and rejection reasons remain in
[`cliff-quiet`](../build/sol72-followup/cliff-quiet/summary.json).
**The cliff CPU p99 gate remains unresolved.**

The outer short-cohort timing session returned 143 after all 12 completed
measurement summaries and the successful tent-fire control were printed. The
cause is unknown; independent validation confirms all 12 complete 360-sample
logs and their saved summaries. This is not treated as a benchmark PASS verdict.

`camera_check`, `cliff_climb_check` (five routes, 1,800 frames),
`climb_masonry_check`, `temple_climb_camera_check`, `tower_base_climb_check`, and
`tooling_check` pass. The new Temple check is in `cpu_checks`; it covers roof
framing, the clear opaque-wall sightline and immediate manual look input.
`prepare_assets.sh` and `prepared_assets_check.sh` pass on the final tree,
including complete structure/collision/roof/RNG byte equivalence. The initial
merge-stale structure cache failure and superseded diagnostics remain available.

Evidence: [`final pack`](../build/sol72-followup/final-pack-v3/index.html),
[`Temple matched frames`](../build/sol72-followup/comparison/matched-temple-climb-gameplay.jpg),
[`cliff matched frames`](../build/sol72-followup/comparison/matched-climb.jpg),
[`all comparison results`](../build/sol72-followup/comparison/summary.json), and
[`visual review record`](../build/sol72-followup/comparison/reviewed.json).

## Round 72 — climbing camera and explicit forest scales

Climbing masonry stays opaque. If the requested lens crosses a stone face,
including Jo's held wall, the camera finds a clear back or side view on Jo's
side. The existing `BuildU` layout stays 552 bytes: a reserved value in its
keep-radius slot selects this policy, and named tower/crown behavior retains
its existing settings. Identical climb-clearance queries are reused, and an
unobstructed wall-normal view ends the search early. The cliff pack shot now
uses the gameplay camera; a Temple gameplay shot accompanies the existing
fixed wall test.

The full pack measures the same **120-second real-dt forest route** twice at
**2133×1200 physical output**: production dynamic scale and fixed **scene scale
1.00** (`BOTW_SCALE=1`). Both summaries record requested and observed scales.
Each route owns a separate bounded render lock. Nearest-rank steady percentiles
exclude the first 240 frames; raw logs retain all outliers. These are present-call
return intervals, not display scanout measurements.

| 2133×1200 route metric | Dynamic scale 0.72 / 0.80 | Fixed scale 1.00 |
|---|---:|---:|
| Present-return p50, ms | 11.581 | 15.769 |
| Present-return p99, ms | 14.710 | 19.896 |
| Present-return worst, ms | 1229.987 | 29.384 |
| CPU callback thread p99, ms | 8.426 | 11.641 |
| CPU callback wall p99, ms | 14.198 | 19.056 |
| Present-return intervals >25 ms | 1 | 2 |
| Steady samples | 9884 | 7278 |

Both runs selected **immediate (driver mailbox fallback)**. Route distance was
427.9 / 430.2 m. Full logs, scale batches,
and summaries are in `build/sol72/release-pack/performance/` and
`build/sol72/release-pack/performance-full-scale/`.

The dynamic route retains a **1,229.987 ms** present-return stall at frame
7,920 (94.614 s): callback wall/thread were 77.037/75.210 ms and the present
call itself was 0.285 ms. No competing game GPU context was observed by the
1 Hz audit. The cause of this stall remains unresolved; it is included in the
worst and >25 ms counts. Raw context is in `build/sol72/route-stall-context.json`.

Matched CPU controls use 1280×720 X11/Vulkan, scene scale 1.00, fixed 1/60
simulation, weather seed 31, frozen 11:00 clear, and production world seeds.
Three AB/BA/AB pairs each run 720 frames; pooled frames 61–720 provide 1,980
samples per version/scene. Temple movement stops at frame 300 to retain the same
face, and frame-180/720 checkpoints assert climbing. Each launch requires CPU
<12% and GPU <5% beforehand. A 1 Hz GPU-context audit rejects entire competing-game
pairs; all attempts and timing tails remain available. The measured camera and
render sources exactly match the final tree. Only a comment and the loading-only
pipeline recipe hashes changed after this cohort.

| CPU thread p99, ms | Master 7245dc7 | Candidate | Delta |
|---|---:|---:|---:|
| Temple gameplay climb/hold | 5.829 | 5.461 | -0.368 |
| Cliff gameplay climb/hold | 4.341 | 4.412 | +0.071 |
| Forest | 7.772 | 9.632 | +1.860 |

**Strict CPU p99 non-regression is not established.** The cliff and forest
point estimates above increase. Unchanged-binary cliff controls under the same
guards shifted by -1.718 ms, +0.731 ms. This demonstrates variation; it does not
prove the candidate cannot regress. Resolving this gate needs quieter or
isolated hardware. Raw medians, tails, per-run activity, rejected attempts and
binary hashes are in `quiet-layout-cpu/`, `quiet-layout-cpu-summary.json`, and
`quiet-noop-cpu/` under `build/sol72/`.

The earlier 560-byte uniform candidate was replaced by the original 552-byte
layout. Its guarded p99 results (Temple/cliff/forest: 6.353→5.786,
3.421→4.838, 7.629→8.094 ms) remain in `quiet-cpu-summary.json`; they are not
pooled into the selected candidate's cohort. Earlier non-gated/prototype runs
remain under `paired-cpu-verified/` and `probe-*`. Both baseline and candidate
experienced `vkAllocateMemory failed (-2)` during earlier runs; a separate game
was observed using the GPU while the render lock was free. Failed runs are
retained rather than treated as successful measurements.

Pure Sloppy pipeline recipes had become stale: only 18 variants entered the
control cold batch. Refreshing the canonical SPIR-V hashes puts 51 variants
into the existing batch. There are 47 program recipes / 53 observed variants;
two variants already exist during uploads. Full warmup still finishes before
play. `tools/capture_pipeline_recipes.py` creates an instrumented private fixture,
observes hashes and keys, and writes a candidate under `build/` without changing
production sources. The vendored runtime remains unchanged; no C was added.

Exact 2133×1200 startup controls use scene scale 1.00, prepared assets, one
completed frame, fresh local Vulkan/NVIDIA caches for each cold launch and the
same cache for three warm launches. Build, lock and quiet waits are excluded;
system/page caches remain intact.

| Startup metric | Master 7245dc7 | Final |
|---|---:|---:|
| Cold in-game load, s | 12.33 | 11.00 |
| Cold render warmup, s | 10.905 | 9.685 |
| Warm median load, s | 1.67 | 1.50 |
| Warm load range, s | 1.60–2.38 | 1.47–1.53 |

One cold launch per version does not establish a repeatable speedup. Every
sample and pre-launch activity measurement remains in `startup-before/` and
`startup-release/` under `build/sol72/`. Camera-only and recipe-only experiments
are retained separately in `startup-after/` and `startup-recipes/`; they are not
pooled into this final comparison. Cold load remains about eleven seconds.

Regenerate recipes after shader changes with
`python3 tools/capture_pipeline_recipes.py build/recipes-NAME`, then validate a
fresh local cache and first-use transitions before adopting the candidate.

Validation: camera and masonry headless checks, cliff/tower climb controls,
rendered tower clearance (2,600 frames), rendered occluder pixels, and tooling
checks pass. `tools/prepare_assets.sh` followed by
`tools/prepared_assets_check.sh` passes complete prepared/generated byte
equivalence. Fresh-cache warmup covers **55 → 55** pipelines; the first-weather
check passes. The final full pack passes **50 captures**, both **120-second**
routes, **13 audio clips**, and **eight checks**.

The pack GPU-process audit records 0 overlapping game-context samples;
its complete audit is retained in `release-pack-gpu-audit.json`. Every final
shot was viewed downscaled side by side with `/tmp/crit72pack/captures`:
**48 pixel-identical of 50**; the cliff gameplay camera and new
Temple gameplay view are the intentional differences. Matched before/final
climb views and the requested-orbit held-wall diagnostic were also viewed.
No new grid, dither, card edge, aliasing, black blob, colour cast or shape
repetition was observed.

Evidence stays under `build/sol72/`: `release-pack/` contains the complete pack,
`release-comparison/` the visual comparisons and review log, and
`held-wall-release-matched.jpg` the forced held-wall comparison. The capture-only
command is `python3 tools/critic_pack.py --only captures build/sol72/release-pack`;
the full run uses `python3 tools/critic_pack.py build/sol72/release-pack --resume`.
Both retained runs use `--capture-batch-scenes 8` and the existing 60-second
batch release limit. [Machine-readable aggregate](../build/sol72/performance-round72.json).

## Prior startup — pure Sloppy Vulkan batches, 2026-10-15

The game no longer builds, packages or loads a C pipeline helper. Sloppy retains
all create-info storage and calls `vkCreateGraphicsPipelines` once per queued
batch on its calling thread; the driver can parallelize internally. Sloppy's
Linux task workers are unsuitable for driver calls because they lack independent
libc TLS. Warm cache hits keep the existing runtime path. All representative
weather, combat, shrine and resolution warmup draws remain; rare variants are
not deferred into play. The vendored Sloppy release is unchanged.

Matched master **200741f** and candidate executables, exact **2133×1200** hidden
X11/Vulkan client, full scale 1.00, prepared assets, 11:00/clear outdoor start,
one captured frame per launch. Each version uses fresh local Vulkan/NVIDIA
caches for its cold run, followed by six launches reusing those caches. Build,
render-lock queue and pre-launch activity waits are excluded. System/page caches
are not flushed. Load ends before the first game draw; whole-process time
includes PNG capture and teardown.

| Metric | Master with C helper | Pure Sloppy batches |
|---|---:|---:|
| Cold in-game load, s | 10.61 | 10.85 |
| Cold render warmup, s | 9.278 | 9.523 |
| Warm median in-game load, s | 1.515 | 1.520 |
| Warm load range, s | 1.51–1.56 | 1.48–1.54 |
| Warm median render warmup, s | 0.184 | 0.181 |
| Warm median first callback end, s | 1.526 | 1.530 |
| Warm median complete process, s | 3.080 | 3.045 |

Cold increases **0.24 s (2.3%)** in this single-pair observation; it is not a
statistical cold-start estimate. Warm differs by **5 ms**, below the 10 ms
precision of individual load logs, with overlapping ranges: no measurable warm
regression in this cohort. The 1.5 s warm target remains unmet. All samples are
retained. Pre-launch GPU activity was 0–1%; CPU was 9.84–11.59% except master
warm-5 at 21.89%. These are shared-desktop observations, not hardware isolation.
Binary hashes, all timing rows and pre-launch activity are in
[the machine-readable evidence](performance-pure-sloppy-pipelines.json); logs and
screenshots are in `build/pure-sloppy-pipelines/{master,batched}-startup/`.

Validation: cold-cache pipeline coverage **54 → 54**; first weather
change **53 → 53** from the cave and **55 → 55** outdoors. Prepared assets retain
complete byte equivalence; fresh headless preparation and the wasm/web package
build pass. Master/candidate cold-start images are pixel-identical. Source grep
finds no C helper references or C compiler steps in `game/` or the launch,
prepare, web and Linux package scripts. The retired pthread transport check was
removed with the implementation it tested; real Vulkan coverage remains.

The full critic pack passes: **49 captures**, the 120-second pacing route,
**13 audio clips with scores**, and **eight checks**, in 463 s. Evidence is in
`build/pure-sloppy-pipelines/full-pack/`. Shader loading/adapter and deferred
startup-stream checks also pass. The separate fresh-copy startup check uses
1280×720 cave starts, six source and six binary launches. Its first run overlapped
package building and pack checks: binary median **3.535 s** missed the **3.5 s**
budget (source **2.465 s**). Repeating after those jobs finished passes at
**2.540 s source / 2.425 s binary**, retaining every sample in both
`startup-copy/` and `startup-copy-serial/` under the same evidence directory.
These copy-check timings do not replace the 2133×1200 matched comparison above.

The Linux package also materializes source textures into staging before baking.
Previously `git archive` already supplied `assets/src/`, so the attempted symlink
became a nested link; baking used archive timestamps, while the final package
copied working-tree texture timestamps. Fresh extraction then rejected the
texture pack and decoded 12 PNGs. The initial smoke log is retained under
`build/pure-sloppy-pipelines/linux-smoke/`; staging and shipping now use identical
texture inputs and mtimes. The rebuilt archive contains no helper library or
source. Its fresh-extract cold/warm smoke passes at exact 2133×1200, all packs
hit and zero PNG decodes: **10.62 / 1.49 s load**, **12.15 / 3.02 s complete
process** (one launch each, separate from the matched cohort). Evidence:
`build/pure-sloppy-pipelines/linux-smoke-fixed/`.

## Prior startup — 2026-10-15, Round 70

Native X11/Vulkan, **exact 2133×1200 client pixels, full scene scale 1.00**,
prepared assets, fixed 11:00/clear, `BOTW_SKIP=1`, one completed frame per launch.
The benchmark helper hides and resizes only its own X11 client. Cold uses fresh
local Vulkan/NVIDIA cache directories; warm reuses them. System/page/shared
library caches are not flushed. Compilation, render-lock queue and pre-launch
quiet waits are excluded from every launch time.

The old **8.30 s** headline described an earlier **1280×720** run, not this
protocol. The critic measured **13.75 s cold** and **2.70–2.99 s warm** over 18
launches at **2133×1200**, including about **1.03 s render warmup / 0.61 s terrain
upload**. Those observations are retained as the reported shared-desktop case;
they are not replaced by a smaller-resolution headline.

The final executable's strict low-activity control required **CPU <12% and GPU
<5%** immediately before every launch. All four final launches passed: CPU
**11.0–12.0%**, GPU **1–4%**. The original control also passed (CPU
**10.9–11.9%**, GPU **0–1%**). These are brief pre-launch observations on a shared
desktop, not isolation throughout the run.

| Metric | Original control | Final executable |
|---|---:|---:|
| Cold in-game load, s | 11.13 | 10.71 |
| Warm launches | 3 | 3 |
| Warm median in-game load, s | 1.68 | 1.61 |
| Warm range, s | 1.62–1.70 | 1.61–1.64 |
| Warm median render warmup, s | 0.267 | 0.201 |
| Warm median initial terrain upload, s | 0.190 | 0.180 |
| Warm median first callback end from process start, s | 1.692 | 1.623 |
| Warm median complete process, s | 3.35 | 3.31 |

The **1.5 s warm target remains unmet**. One cold launch per version is too small
a sample to claim a cold speedup: an earlier low-activity implementation control
measured 11.19 s cold against the original 11.13 s. The final headline uses this
exact executable's control, not the best sample from an earlier implementation.
Raw rows and binary hashes: `build/task70-sol/idle-{before-v3,final-v4}/summary.json`.

An earlier implementation (before the final camera and underground-culling
refinements) retained **all 18 warm samples per version** at the same output:
original median **1.685 s**, range **1.64–1.86 s**; implementation median
**1.540 s**, range **1.49–1.61 s**. Warm render warmup medians were
**0.273 → 0.184 s**. Cold was **13.20 → 10.36 s**, but the original cold launch
started at **33.4% CPU** versus **11.25% CPU / 1% GPU** afterward. That cold
difference cannot be attributed entirely to code. Pre-launch CPU activity across
those cohorts ranged **11.6–33.4%** before and **9.2–23.9%** afterward. These
18-run cohorts remain archived as load context, not final idle measurements.

A preceding 18-run, same-output implementation cohort retained a **1.620 s**
warm median and **1.51–4.47 s** range with CPU activity up to **84.6%**. Warm
outliers at 3.34 and 4.47 s followed high CPU activity; neither was discarded.
That superseded cohort is retained in `build/task70-sol/startup-final/`, rather
than being relabeled as idle final-tree performance. It illustrates why the
critic's busier-desktop observations and earlier smaller-resolution numbers
must keep their conditions attached.

`loaded in` ends after offscreen/presentation warmup and before the first game
draw. The first-callback marker includes update/draw and excludes presentation;
the process total includes PNG readback/write and teardown. None measures
compositor scanout. Earlier 18-run rows, exact environment, viewport validation and binary
hashes: `build/task70-sol/startup-{before-prepared,final-v3}/summary.json`.

Terrain payloads now stream during the cave opening after four visible frames,
with at most 512 KiB of texture copies or one 64-row noise tile per callback.
Height/burn maps stay available for particle roots. Outdoor starts finish the
payload in bulk before drawing; partial outdoor maps never appear. The initial
terrain-upload column therefore covers retained prerequisites, and the load
number also includes the required outdoor drain. Hidden warmup views use a
16×16 scissor, omit one redundant wet draw, and restore full coverage for both
starting-camera shadow refreshes. Full mip/noise GPU equivalence and prepared
asset byte equivalence pass. Implementation details and review evidence are in
[ROUND70_SOL.md](ROUND70_SOL.md).

## Round 70 CPU and pacing evidence

Matched fixed-step controls use the original and final executable snapshots,
1280×720 full scale, identical production seeds/positions/hour/weather/input,
and unchanged CPU affinity. Each scene runs in interleaved A B B A A B order:
three 841-frame launches per version, with 840 recorded callback samples per
launch. Camera diagnostic logging is disabled; production frame logging is on.
All samples and repeats are retained. The standard steady window excludes the
first 240 frames (1,800 samples/version/scene); the complete window retains
2,520 samples. CPU means main-thread callback time, excluding runtime gaps.

| Scene | Steady CPU p99, before → after (ms) | All-frame CPU p99 (ms) | First-120-frame CPU p99 (ms) |
|---|---:|---:|---:|
| Forest | 7.295 → 6.838 | 7.666 → 6.809 | 7.441 → 6.982 |
| Glide | 5.152 → 5.003 | 5.138 → 5.020 | 5.138 → 5.175 |
| Cave opening | 4.572 → 4.191 | 4.532 → 4.133 | 5.122 → 4.523 |

The actual gliding window, frames 60–320 (783 samples/version), improves from
**4.913 → 4.599 ms CPU p99**. The steady and complete-scene p99 comparisons pass
for all three scenes. This does not mean every narrower window improves:
glide's first-120-frame p99 is 0.037 ms higher. Streaming moves work into early
cave callbacks: their first-120-frame CPU median rises **1.484 → 2.211 ms** and
worst **7.921 → 9.034 ms**, while that window's p99 falls. These costs remain in
the measurements rather than being excluded as startup.

These fixed-step runs are **shared-load measurements**, not idle controls.
Each launch attempts a five-second quiet wait, then records actual activity and
runs regardless; pre-launch CPU activity spans **11.42–57.63%**, GPU **1–3%**.
The strict low-activity requirement applies to the startup control above.
Raw logs, every per-run activity snapshot, binary/source hashes, protocol and
all timing windows: `build/task70-sol/paired-cpu-production/`.

An earlier final-camera diagnostic control with `BOTW_CAMDBG=1` completed only
five launches before its strict quiet gate repeatedly rejected the next launch.
Its partial forest steady p99 is **6.882 → 8.578 ms** (three original versus two
final runs); that higher tail is retained in
`build/task70-sol/paired-cpu-stock/`. The trace-enabled cohort is incomplete and
is not merged with the completed production-logging controls. Together with the
variation between repeats, it limits any claim of an isolated hardware speedup.

The full critic pack's 120-second real-dt forest route uses the managed
2133×1200 client, launcher-default present mode and dynamic scene scale. Both
versions used the driver's immediate fallback for mailbox. Excluding the first
240 frames, its master/final measurements are:

| Metric, ms | Master pack | Final pack |
|---|---:|---:|
| CPU callback thread p99 | 8.116 | 6.719 |
| CPU callback wall p99 | 15.483 | 14.125 |
| Present-return interval p99 | 16.320 | 15.034 |
| Present-return intervals >25 ms | 1 | 0 |

This route compares the same timed traversal; it is not an isolated-machine
claim and its real-dt sample counts differ (9,685 / 11,809 steady frames).
Raw evidence: `/tmp/crit70pack/performance/summary.json` and
`build/task70-sol/final-v4-pack/performance/{summary.json,route.log}`. Display
scanout is not measured.

## Historical results — 2026-10-14, Round 69

Unmodified Sloppy **0.6.0**, i7-6700 / GTX 1070, shared loaded desktop.
Native startup and fixed captures: **1280×720, scale 1.00**, managed X11/Vulkan,
prepared assets. Cold uses fresh local Vulkan/NVIDIA cache directories; warm and
changed-executable runs reuse them. Kernel/page/system caches are not flushed.
Render-lock queue time is excluded. Browser measurements use isolated T3 browser
tabs, a **1280×800** viewport and production **0.80/0.65** scene-scale policy;
driver/system caches remain uncontrolled.

- Native cold load: **8.30 s**; complete one-frame process: **9.22 s**.
- Native warm median: **2.30 s** in game, **3.20 s** complete process;
  the **1.5 s warm target remains unmet**. Changed executable, identical shader
  digests: **2.26 s** in game / **3.10 s** complete process; shared cache hit.
- Browser first completed frame: **70.16 → 31.73 s**, no reported errors.
  The piano worker generates an exact compact bank alongside world initialization.
  Site size grows **104.87 → 121.20 MB** with the prepared world and worker;
  the compact mono recordings remain the download source.

Matched CPU p99 passes: forest **7.032 → 6.579 ms**, sunken tower
**5.444 → 5.321 ms**, 720 samples per version/scene. Producer p99 is worse in
these pairs; this is not a delivery improvement claim. The final 120 s route
at **2133×1200**, production dynamic scale, records **15.456 ms** producer p99
and **7.321 ms** callback thread CPU p99, retaining four >25 ms intervals.
CPU/pacing comparisons
The complete pack passes: **45 byte-identical master comparisons**, all viewed
side by side, 13 audio clips and eight fast checks. Full details are in
[PERFORMANCE_ROUND69.md](PERFORMANCE_ROUND69.md). Callback and present-return
statistics measure **producer timing**. Delivered/compositor scanout timing was
**not measured**; completed-frame/browser-ready timing is not a scanout claim.
Startup evidence: `build/task69-sol/final-v3-pack/startup/summary.json`.
Browser evidence: `build/task69-sol/browser-{before,after}.json`.

## Historical measurements

## Round 67 continued: structural canopy, upload and cue costs

The latest implementation and measurements are in
[PERFORMANCE_ROUND67B.md](PERFORMANCE_ROUND67B.md): reduced intermediate canopies
and shadow casters, frame-local terrain nodes, and bounded held-note releases.
It retains all matched CPU/GPU repeats, two-minute forest/camp routes, final
critic captures and the remaining target misses. The earlier round's numbers
below are historical controls, not the final results of this continuation.

## Round 67 critic follow-up: startup, full 1080p and combat clarity

The release runtime chooses its `.vkpipelines` filename from the **executable
basename**, not a binary-content hash. The serialized `SLPC` wrapper checks its
length/hash; Vulkan checks vendor/device and pipeline-cache UUID. A renamed pack
executable therefore starts cold even when it contains the same shaders.
Shader debug names also carry compiler-global suffixes from unrelated imports.
The game now strips only nonsemantic SPIR-V debug records, then merges a shared
`slop-of-the-wild-060.vkpipelines` cache into the native cache before loading its
first shader. Shader instructions, entry points, bindings and layouts stay
intact. The driver still keys individual pipeline variants and rejects obsolete
device/driver data. `SLOPPY_VK_PIPELINE_CACHE=0` disables this path. The vendored
runtime is unchanged.

Startup additionally loads prepared enemy contact and hero blade tracks, with
source/model/animation keys and a generated fallback. All **23,050 enemy socket
matrices and 1,936 hero blade records** match generation byte for byte. Native
model reads avoid a second full-file string buffer. Preparation remains CPU-only.

The final capture pack measures one cold process, three warm processes, then an
entry-point-only rebuilt executable with different binary bytes and identical
shader digests. Managed X11, Vulkan, 1280×720, full scale, prepared assets; one
bounded render-lock batch. Cold means fresh local Vulkan and NVIDIA cache
directories; system/page caches are not flushed. Lock queue time is excluded.

| Launch | In-game load, s | Render warmup, s | Whole process, s |
|---|---:|---:|---:|
| Cold | 10.62 | 9.187 | 11.31 |
| Warm 1 | 1.58 | 0.204 | 2.30 |
| Warm 2 | 1.57 | 0.206 | 2.26 |
| Warm 3 | 1.67 | 0.203 | 2.39 |
| New executable, identical shaders | 1.75 | 0.329 | 2.45 |

Warm median **1.58 s** improves on the critic's 1.75–1.95 s, but misses the
**1.5 s target**. The shared cache hits in every warm process and the changed
executable. Cold pipeline compilation remains expensive. Pack startup evidence
is `build/task67-sol/critic-final5/startup/summary.json`, including load averages,
binary hashes, per-shader digests and all logs; its index reports these three
startup cases separately from capture timing.

### GPU zones and resolution

The pinned game previously disabled Vulkan pass timing, and the pinned runtime's
frame statistics do not provide GPU-zone timestamps. `BOTW_GPU=1` now records
game-owned native timestamp queries around the existing zones, reading available
results four frames later without waiting. Normal gameplay allocates no query
pool. The profile includes all recorded GPU-zone samples after frame 240.
It measures command-buffer zones, excluding acquire/present and CPU scheduling.

At full 1920×1080 in the forest, the original profile's largest mean costs are
**trees 4.140 ms, terrain 2.245 ms, near vegetation shadows 1.561 ms, post 1.326 ms,
grass 0.790 ms and middle vegetation shadows 0.728 ms**. Total GPU mean/p99 is
**13.600/14.614 ms**. The final shader revision measures **13.793/15.046 ms**;
its largest per-frame mean zones are **trees 4.162 ms, terrain 2.244 ms, near
vegetation shadows 1.738 ms, post 1.313 ms, grass 0.808 ms and middle vegetation
shadows 0.764 ms**. Conditional shadow passes contribute zero in skipped frames;
separate per-draw means are retained in the final summary. Skipping dry overcast
work shows no demonstrated total GPU improvement. A
terrain-noise texture lookup experiment measured **13.886 ms mean / 4.257 ms
trees**, and was reverted. GPU timestamps do not establish producer pacing.
Raw profiles and the rejected experiment remain in `build/task67-sol/`.

An adjacent matched camp GPU pair at full 1080p records **12.440 → 12.314 ms
mean / 14.158 → 14.044 ms p99**. Fully clearing foreground foliage reduces its
zone mean **0.944 → 0.831 ms**; shortening grass around the locked target reduces
grass **2.801 → 2.725 ms**. Terrain remains **2.803 → 2.817 ms** and farland
**1.679 → 1.679 ms**. These are modest measured clarity-related savings, not a
forest throughput win. Evidence: `camp-gpu-final/summary.json` and both raw logs.

Outputs through **1920×1080 start at full scale**; larger outputs retain the
80%/72% policy. Both warmed resolutions remain available to the dynamic
controller. The final default-policy 1080p forest repeat stays at **1.00** in all
six measured batches, but producer interval p99 is **22.999 ms**, with callback
thread CPU p99 **7.430 ms**. GPU-zone p99 below 16.7 ms does not establish frame
delivery below that threshold; the **16.7 ms producer target remains unmet**.
Evidence: `final-1080/{gpu,dynamic}.{log,png,settings.json}` and
`final-1080/summary.json`; the original profile is in `gpu-summary.json`.

### CPU comparison and exact contact geometry

The comparisons use adjacent before/after pairs, reversing their order on
odd repeats. Managed visible 1920×1080 X11 clients, full scale, fixed seed/hour/
weather/input and 1/60 simulation; only the initial 240 frames are excluded.
Every later tail is retained. The original game is frozen at `af74b81` with
observational GPU instrumentation; final gameplay is frozen in `clarity-game`.
Binary hashes and settings accompany each run. Final route timing is recorded in
`build/task67-sol/paired-clarity/summary.json`.

Four final-tree pairs per scene retain **1,920 samples per version**:

| Scene | CPU p99 before → after, ms | Producer interval p99 before → after, ms |
|---|---:|---:|
| Forest | 10.764 → 10.479 | 20.497 → 19.161 |
| Camp | 15.130 → 17.075 | 18.233 → 18.723 |
| Swim-to-shore route | 22.615 → 22.060 | 23.699 → 23.190 |

Forest and swim-to-shore CPU p99 improve. Camp CPU p99 is **1.945 ms worse**,
so the requested non-regression condition remains unmet. Earlier candidate
comparisons are retained in `paired-scatter/summary.json`; their different tail
values do not replace this final-tree comparison. Shared-machine variation and
diagnostic attribution do not turn a positive measured delta into a pass.

The matched Temple wall climb uses two reversed-order pairs at visible 1280×720,
full scale. It measures frames 61–360, **600 samples per version**, before the
finite climb reaches its ledge. Final CPU p99 improves **6.640 → 6.029 ms**;
producer interval p99 improves **12.978 → 12.001 ms**.
The first extended fixture attempts are retained, including the normal ledge
exit that invalidated a 720-frame climbing-only measurement. Valid evidence is
`temple-cpu-final/summary.json`. The earlier soft fade hid Jo; final image review
prompted a fully cleared corridor centre through foreground masonry near him,
with a soft radial edge and held/behind-player stone retained. Its headless
regression asserts both the clear centre and retained endpoint.

The long swimming route eventually reaches shore, as its frame-720 comparison
shows; it measures **swim-to-shore traversal**, not stationary swimming throughout.
A separate replay releases forward at frame 150 and asserts the production swim
state at every capture through frame 720. It reports moving frames 61–150 and
treading frames 241–720 independently. Three adjacent/reversed-order pairs in
one bounded batch, visible 1280×720/full scale, with no snapshots inside those
windows, retain **270 moving / 1,440 treading samples per version**:

| Swim state | CPU p99 before → after, ms | Producer interval p99 before → after, ms |
|---|---:|---:|
| Moving breaststroke | 17.385 → 19.156 | 17.894 → 19.826 |
| Stationary tread | 5.479 → 5.641 | 9.707 → 9.822 |

Moving CPU p99 is **1.771 ms worse**, and tread is **0.162 ms worse**; the
requested CPU non-regression condition remains unmet. Final evidence is
`swim-active-cpu-final/summary.json`. The earlier snapshot-bearing replay is kept
for visual review; its moving interval p99 includes observer PNG/readback stalls.
A separate moving-phase diagnostic identifies frame 90's largest stage as
unchanged `jingles_update`, **15.246 → 14.273 ms thread CPU**, with hero animation
**0.068 → 0.069 ms** across that frame's simulation ticks. This diagnosis does
not replace the uninstrumented comparison: `swim-active-trace/moving-attribution.json`.

The extended route's diagnostic pair
attributes the largest spikes to unchanged **`jingles_update`**, about 13–30 ms
thread CPU, with hero animation about 0.07–0.12 ms. Instrumented diagnostics are
kept separate from percentile comparisons: `swim-trace/attribution.json`.

An initial camp CPU regression traced to posed combat surfaces. Affine actor
worlds now skip the generic homogeneous divide, transforming seam-shared source
positions once when reuse is substantial. A reference check independently
replays the original per-vertex formula: **1,338,816 vertices** match byte for
byte across three models, four clips, cached/uncached skins, actual camp world
coordinates and a projective fallback. Contact tolerances and geometry remain
unchanged.

### Clarity and traversal validation

Foreground vegetation clears completely at the lens, then returns through
opaque dither patches instead of watercolor ghost coverage (bark eases from
3 to 5.5 metres). The paint and composition passes retain solid patch colors
and exposed background. Architecture clearance returns before all fade logic
in shadow passes, including the Temple masonry corridor. Locked opponents
shorten nearby grass; smoke crossing the camera-to-target line retains 12%
core coverage. Temple masonry keeps a dithered transition
while timber and tower supports still clear fully. Daylight Keese roost and dawn
cancels a swoop; defeated enemies stay defeated. Moving swimming uses symmetric
breaststroke hand paths, with smaller alternating tread paths at rest.

The merge regression keeps the original lens half-coverage and tower shadow
assertions. `lens_plant_check` also follows both complete distance ramps;
`material_paint_check` checks all 15 partial coverage levels against sky and
ground through the enlarged paint brush and final composition, retaining
opaque colors and exact coverage. `round67_clarity_check` checks the masonry
corridor's shadow and inactive-player guards.

The final required critic captures are in `build/task67-sol/critic-final5/`.
Matched original captures are in `before/captures/` and `temple-before/` under
the same evidence root. Capture settings retain identical seed, position, hour,
weather and inputs; the Temple fixture uses a real climb and a fixed opposing
wall camera. Images are downscaled before review. The CPU swim check samples
480 stroke/tread poses in both models and retains its surface, kick, camera,
crossfade, exhaustion, shore and physics assertions. Separate clarity and GPU
occluder checks cover dusk/day/dawn Keese, smoke bounds, intermediate masonry
coverage and complete support clearance. Prepared asset equivalence passes.
`checks-summary.json` records the latest 21 named passing checks, including
combat/contact/geometry/reach/scatter, camera/input/spacing, cliff/tower climbing,
swim/clarity, shader loading/adaptation, tooling and prepared assets. Reviewed
matched final-tree images are `matched-final5-forest-150.jpg`,
`matched-final5-camp-{180,420,640}.jpg`, `matched-final5-swim-180.jpg` and
`matched-final5-temple-climb-180.jpg` under the evidence root. All six were viewed
after downscaling, including Jo's visible climb through the soft clearance.
`swim-cycle-matched.jpg`
shows two matched moving phases and stationary tread, with bent arms and a
narrow recovery; its snapshot-bearing run is visual evidence, not a pure
producer-interval benchmark.

Reproduce with fresh build evidence directories (these helpers own their locks):

```sh
tools/prepare_assets.sh
tools/prepared_assets_check.sh
python3 tools/round67_performance.py BEFORE_EXECUTABLE AFTER_EXECUTABLE build/task67-repeat --repeats 4
python3 tools/critic_pack.py --only captures build/task67-critic-repeat
```

Critic captures now share one lock for at most four scenes, releasing after
60 seconds of a batch; a 90-second child timeout bounds a slow last render to
about 150 seconds. The first process in each batch records its queue wait;
subsequent processes do not reacquire or nest the lock. Completed byte-identical
captures survive `--resume`. The earlier `critic-final4` attempt was deliberately
interrupted while pending the lock, then resumed with this protocol. Its recorded
interrupted wall time is a lower bound excluding compilation and the interrupted
pending wait; per-process startup and scene timings retain their own raw logs.
The final `critic-final5` pack starts fresh on the corrected shader.

## Round 66 critic follow-up: managed X11 launcher and swimming

`tools/round66_sol_pacing.py prepare` freezes one observational executable;
`compare` alternates native Wayland and X11 for the fast presentation preference,
then FIFO. Every run has **120 active seconds after first-frame preparation**, the
same real-dt forest waypoint/input route, seed 64, initial hour 11, clear weather,
production dynamic scene scaling and **2133×1200 verified client pixels**. The
first four active seconds are reported separately; all raw intervals remain in
`build/round66-sol/`. X11 uses a managed fixed-size dialog, with size hints and
fresh PNG/client validation; it is not an unmapped throughput-only benchmark.
`SLOPPY_VSYNC=0` requests mailbox preference: this driver exposes **immediate
(mode 0)** on X11 and **mailbox (mode 1)** on Wayland. FIFO is mode 2 on both.

| Platform / actual mode | Return p50 / p99 / worst, ms | Frames >25 ms |
|---|---|---|
| Native Wayland / mailbox | 10.57 / 16.98 / 80.00 | 26 |
| Managed X11 / immediate | 11.26 / 18.37 / 29.81 | 4 |
| Native Wayland / FIFO | 16.67 / 36.08 / 264.21 | 459 |
| Managed X11 / FIFO | 16.68 / 26.02 / 221.03 | 81 |

Select **managed X11/XWayland when DISPLAY is advertised, Vulkan, fastest
available presentation and BOTW_FPS=0** in both Linux launchers. Explicit
`SLOPPY_PLATFORM=wayland` overrides the choice; with no DISPLAY the runtime keeps
its normal platform selection. This decision reduces the large periodic tails,
not every percentile: X11's dynamic-route p99 is higher than Wayland's and still
misses 16.7 ms. The four X11 >25 ms returns are callback-dominated waits, with
6.67–7.68 ms callback thread CPU versus 21.66–25.50 ms wall time; presentation is
0.25–5.06 ms. Poll/geometry queries contribute up to 4.79 ms in two of those
frames. These measurements do not identify a particular native wait by themselves.

The initial full-scale stress pair used a remapped override-redirect X11 client.
It retained ten-second presentation stalls on **both** backends (Wayland 23
frames >25 ms, p99 21.36; X11 21, p99 21.73). Preserve those logs as a distinct
window/scale protocol; they are not evidence that ordinary managed X11 fixes
all compositor/driver loads. The later managed, dynamic-scale pair removes the
periodic X11 presentation waits. No vendored runtime code was changed.

Standalone `tools/upstream/presentation.jo`, with audio disabled, reproduces six
post-warmup native Wayland waits in 65 seconds: **46.6–49.4 ms**, roughly ten
seconds apart. Its X11 control has **zero >25 ms returns** and **13.04 ms worst**.
Those clear-only outputs are 2133×1200 on Wayland and 1280×720 on X11, so the
matched game matrix above is the size-controlled comparison. Logs are
`build/round66-sol/upstream-{wayland,x11}.log`; raw game runs, environment and
executable hashes, tail stages and PNG validation are in `pacing-summary.json`
and `pacing-*.{log,environment.json,png}` in that directory.

### Ten-minute source-launcher session

The lightweight repeat completed **600.004 active seconds / 71,386 returns** in
its ordinary managed **1280×720** X11 window, with Vulkan immediate fallback and
production dynamic scale. All-active return **p50 / p99 / worst are
8.188 / 13.826 / 82.897 ms**; **32 frames exceed 25 ms** (0.045%). The first-four-
second exclusion gives essentially the same p99, 13.830 ms, and the same 32 tails.
Thus the default-size p99 target passes, but **zero >25 ms frames does not**.
This is not a ten-minute 2133×1200 result: the size-controlled matrix above still
misses the 16.7 ms target on X11 at that size.

Every late return has a stage record: **21 callback-dominated, 6 geometry-query-
dominated, 5 presentation-dominated**. The worst frame has 78.616 ms callback wall
time versus 8.549 ms thread CPU. A 52.861 ms frame includes a 37.405 ms synchronous
XGetGeometry query in the observer; client dimensions stay constant. Only two
presentation calls exceed 25 ms, **27.241 and 26.611 ms**, without the old repeating
ten-second cadence. The lightweight run identifies callback waits/scheduling and
observer-query stalls, but does not identify the exact native cause of every wait.

A separately retained, fully traced ten-minute diagnostic has **189 >25 ms
returns**, p99 **13.835 ms**, worst **388.158 ms**. Its tail categories are 158
callback wall waits/preemption, 17 callback CPU work, 10 geometry queries and 4
presentation. **165 late frames contain more than two simulation ticks**. The
three worst callbacks have **50–61 involuntary context switches**; the worst has
370.782 ms wall / 63.937 ms CPU and 41 simulation ticks. Individual nominally tiny
stages show long wall delays with little CPU. This supports preemption followed
by catch-up simulation (the game retains its existing 0.5 s loop cap). Full trace
formatting can amplify such bursts, so use the lightweight run for default pacing,
and retain the traced run as diagnostic evidence rather than pooling them.

Both sessions preserve one game across four SIGSTOP scheduling pauses, releasing
and reacquiring the same shared flock every 120 active seconds. Game/observer
clock anchors exclude paused periods; resumed frames are retained. The final
harness additionally drains the GPU before handing off the lock; a short lifecycle
smoke test exercises that handoff. This drain was added after the recorded long
sessions and changes only scheduling handoffs, not production game code.

Evidence: `build/round66-sol/pacing-default-continuous.{log,environment.json,png}`,
`pacing-default-traced.*`, `pacing-summary.json`, and
`traced-session-attribution.json`. `session` uses lightweight timing;
`session --trace` runs the separate diagnostic. Use a fresh `--output build/<name>`
for a different executable/protocol, retaining older evidence. No strict claim of
zero-tail performance is made. Wake anatomy/hair edits were deferred while this
performance and swimming work took priority.

### Swim surface and CPU evidence

Swim clips are centered on the water surface, while collision and shore-grab
probes use a standing foot anchor **1.25 m below it**. Raise the rendered origin
by that depth, crossfade the origin correction with the animation, and lift the
breaststroke chest/neck while counter-rotating the arms to retain their sweep.
Keep the foot anchor for low-bank grabs. Exhaustion lowers the rendered lift
along the existing drowning timer. The swim camera keeps its look point 25 cm
above the surface, uses a 4.2 m boom, and settles to a 0.42 rad downward pitch.
Movement speeds, stamina, drowning damage/return rules and reference rows remain
unchanged.

A **48.8-second contiguous locked batch** interleaves three before/after repeats
at 1280×720, fixed scale 1, seed 64, initial hour 11 and clear weather. Moving
frames 61–150 provide 270 samples per version; treading frames 241–720 provide
1,440. Every sample in those windows is retained. Main-thread CPU p99 improves
**6.305→4.795 ms moving** and **6.635→4.408 ms treading**. Callback wall p99
improves **9.023→7.743 ms** and **9.348→7.733 ms**, respectively. Earlier repeats
separated by other workers had more variable CPU spikes; they remain in the
same evidence directory rather than replacing this paired batch.

Matched captures were downscaled and viewed: `cpu-matched/{before,after}-1-960.png`
(treading), and `swim-before-960.png` / `swim-after-final3-960.png` (moving).
The final normal-swim appearance is unchanged by the subsequent exhaustion-only
lift adjustment. Raw images, logs, binary hashes and batch summary are under
`build/round66-sol/`; the CPU comparison is `cpu-matched/summary.json`.
`swim_surface_check` is registered in the runner's CPU array and covers both
models, 480 stroke/tread poses, clip-origin transitions, head/shoulder clearance,
horizontal kick, float convergence, speed, camera, exhaustion/shore return,
shallow exits and a low-bank grab. Related movement, camera, contact, input,
architecture, opening and wake/title checks pass; prepared asset equivalence
also passes. `build/round66-sol/checks-summary.json` records the checks and paths.

## Round 67: game-only pacing, piano storage and final head lanes

Five-minute forest routes retain all raw intervals, real production dt and the
existing complete two-second window protocol. Initial options at 2133×1200:

| Option | Return p50 / p99 / worst, ms | Windows p99 >20 ms | >17.5 ms |
|---|---|---|---|
| Mailbox, dynamic scale, uncapped | 10.15 / 15.43 / 60.44 | 6/147 | 23/147 |
| Mailbox, fixed 80% scale | 10.69 / 18.33 / 195.25 | 24/147 | 41/147 |
| Mailbox, dynamic scale, 60 cap | 16.77 / 26.67 / 198.04 | 71/147 | 144/147 |
| FIFO, dynamic scale, 60 cap | 16.72 / 27.93 / 198.57 | 103/147 | 145/147 |

**Retain uncapped Vulkan mailbox and dynamic scale.** Linux `BOTW_FPS` adds an
optional cap before polling/dt/render, without catch-up bursts; default **0**.
`render_evidence.py` accepts `--fps`, `--scale` and a pinned `--executable`.
The two 60-cap runs share an executable. The first two precede the audio/combat
edits; a later default repeat records **10.23 / 15.41 / 196.65 ms**, **11/143**
windows over 20 ms and **19/143** over 17.5 ms. Startup changes the window count.
These shared-desktop samples establish no removal of the strict tail failures.

The hitch is a **10.00-second wall-clock cadence**, at the same absolute
monotonic-clock phase across launches, rather than a fixed ~840-frame count.
Fixed scale and both caps retain it. Native traces show **three swapchain images,
two frames in flight**, with slow acquires on **all three image indices**.
There are no in-play swapchain/image/pipeline creations or pipeline-cache flushes;
poll/resize and audio refill/write calls do not account for the periodic waits.
Both scene resolutions are warmed and retained. Acquisition already happens
late, after game recording and before native blit/submission, with infinite
runtime timeout. The evidence points to driver/compositor servicing; it cannot
identify which external component owns that cadence.

A traced **192.11 ms** outlier contains **182.20 ms present**, almost entirely
`vkAcquireNextImageKHR`, versus **9.83 ms callback wall / 5.24 ms thread CPU**.
The next callback spends **18.69 ms CPU** catching up. The historical **231 ms
(46 CPU +185 present)** frame has no raw trace in this checkout: its exact CPU
stage remains unproven. No runtime files were changed; the acquire stall remains.

Piano samples now use **per-note scaled PCM16**, retaining 48 kHz stereo reverb.
The six banks fall **211.92 → 105.96 MB**; including restrained strikes costs
**106.53 MB (101.59 MiB)**. Only active voice windows expand to floats. Prepared
packs load directly into i16 arrays; cues stay lossless f32. Prepared/generated
sample hashes agree, quantization stays within half a note's quantum, and packed
versus expanded rings agree within **0.000000001** across pitch/wrap/fade cases.
Live field/engaged/low-HP levels are **−24.0 / −21.2 / −21.3 LUFS**, worst measured
true peak **−1.3 dBTP**, with zero pre-limiter overloads. Transition, harmony,
recurrence, note-density and music-export checks pass.

Waiting chase idles change every **1.2 s**, avoid crouch, and face Jo within 45°;
a guard at its lane now decelerates instead of walking in place. Root lanes also
recognize low-alert combat states and let committed attackers yield. Final posed
head separation reuses the body solve, includes visible death poses and preserves
body/blade/world constraints. Selected unarmed windups get extra head room;
the late camp tell remains **94%** visible. The README camp inputs remain exact; frame 300
improves **39.15 → 279.21 px** separation against a **183.86 px** head width,
while retaining real posed sword contacts and readable impact pauses. The framing
trace excludes actors once the renderer removes them. A separate regression
covers simultaneous low-alert windup/attack without cancelling either attack.

Combat, reach, camera, spacing, input, music and all six final 960-frame framing
courses pass. Raw intervals, attribution, source/executable hashes, poses and
audio meters are in **`build/round67/`**; final framing is in `final5/framing/`.
Full optional texture rebaking is unavailable without `assets/src/nature/Textures`;
the compact audio pack's generated/prepared equivalence is verified independently.

## Default and ten-minute route

Both launchers explicitly select Vulkan mailbox (`SLOPPY_VULKAN=1`,
`SLOPPY_VSYNC=0`), preserving environment overrides. Release OpenGL's Wayland
path waits for frame callbacks; `SLOPPY_VSYNC=0` does not make that path mailbox.

The same forest/meadow waypoints run for 600 real seconds with production dt.
Complete monotonic two-second windows start four seconds after the first return,
rounded up to an even second. Each window uses nearest-rank p99; no tail trimming.

| Game/backend | Interval p50 / p99 / worst, ms | Windows p99 >20 ms | >17.5 ms |
|---|---|---|---|
| Before, Vulkan FIFO | 16.67 / 31.36 / 331.99 | 191/297 | 268/297 |
| Before, Vulkan mailbox | 11.32 / 17.56 / 223.17 | 45/297 | 104/297 |
| After, release OpenGL | 16.68 / 26.11 / 458.28 | 182/297 | 291/297 |
| After, Vulkan mailbox **default** | 10.83 / 16.36 / 170.84 | 33/297 | 80/297 |

The older toolchain with locally patched OpenGL mailbox recorded **4/297**
windows over 20 ms; that patched runtime is not the release OpenGL tested here.
The default improves **45 → 33/297** windows over 20 ms and worst interval
**223.17 → 170.84 ms**. OpenGL is clearly worse on this route and all three
matched scenes. The strict all-window 17.5 ms target remains **unmet**.
The default’s worst interval contains **159.44 ms in presentation** versus
11.31 ms callback wall / 5.34 ms callback thread CPU.

## Round 64: score fades and combat framing

Music now keeps a voice-owned ring sized for the release mixer's largest block.
Ordinary gain changes rewrite only the **20 ms ramp**; steady playback refills
consumed frames. New notes never copy an entire recording. Entering/leaving
silence rebuilds that bounded window once. Shared piano samples stay immutable.
`music_transition_check` asserts **p99 thread CPU <1 ms**: victory **0.130 ms**,
escape **0.096 ms**, and overlapping-note mood/duck stress **0.297 ms**. The
handoff delta remains below 0.000001, variable-block click checks pass, fractional
pitch/window-wrap error is below 0.000000004, and LUFS/true-peak checks pass.

Lock framing centres the pair's screen bearings and widens the lens as needed.
The final posed-head solve retains at least **40 px** separation at 1280×720;
its correction moves the real capsule. The framing check includes a three-foe
converging tent-fire crowd, middle-third lock assertions after acquisition,
and hero/enemy plus enemy/enemy capsule clearance. Confined views use the lens
radius when selecting a shoulder, a ceiling-safe elevated fallback, and final
posed body/weapon bounds. Core combat, reach, camera and 2,386 input assertions
pass. The optional `camp_sword` visual script's missed-hit assertion also fails
on **d05ace6**; both baseline and after logs are retained. Round 65 below resolves the stale fixture.

Both use production dynamic scale, real dt, Vulkan mailbox at 2133×1200,
and the same complete two-second windows. The combat route enters at **41.392 s**
and returns to field at **80.898 s**; both fades occur after warmup.

| Route | Return p50 / p99 / worst, ms | Windows p99 >20 ms | >17.5 ms |
|---|---|---|---|
| 600 s forest/meadow sprint | 10.59 / 16.63 / 249.79 | 28/297 | 69/297 |
| 120 s field → combat → field | 10.03 / 14.88 / 49.24 | 7/57 | 14/57 |

The historical default recorded **33/297** and **80/297** forest windows.
These shared-desktop runs retain every outlier; the all-window 17.5 ms target
remains unmet. The forest’s worst return includes **238.87 ms in presentation**,
versus **10.84 ms callback wall / 5.76 ms callback thread CPU**.

Raw logs, source/executable hashes, every two-second window, audio meters,
pose traces and critic-frame screenshots are in `build/round64/`. Python render
helpers own their locks; reproduce the routes without wrapping them:

```sh
python3 tools/render_evidence.py soak --backend vulkan --present-modes mailbox --route forest --seconds 600 --output build/round64/verified-forest
python3 tools/render_evidence.py soak --backend vulkan --present-modes mailbox --route combat --seconds 120 --output build/round64/verified-combat
```

## Round 65: real camp hits and combat entry

The camp script was stale: its original inputs leave a **0.504 m** capsule gap
(hit threshold 0.40 m), make **zero posed triangle contacts**, and lose the
follow-up to an enemy attack. Earlier attacks and movement through frame 200 land
**13 HP damage / 19 impact frames** on unchanged baseline and final code.
`run_all_checks.sh` now includes `camp_sword_visual_check`, requiring HP loss
with a new melee swing ID and impact pause; inputs are in the README.

Native tracing identifies a **17.18 ms burning-body pipeline** first used at
46.65 s. Startup now warms both scene scales: **zero pipelines during play**,
**47 → 47** in transition checks. Sparks, trails, flash, health/lock HUD and alert
FX add no cold pipelines; audio cue banks already load/filter before play.
Entry callback CPU maxima for AI/camera/events/music are **0.95/0.10/0.04/0.55 ms**,
including multiple ticks. Remaining entry tails contain posed clearance work
(**13.71 ms across three ticks**) or native image-acquire waits.

Body/head topology and scratch capacity are prepared at loading; posed triangle
bounds are reused across correction passes with unchanged tolerances.
**428,520** filtered/unfiltered queries agree. A matched three-foe cutting-pose
replay reduces clearance CPU p99 **5.18 → 4.00 ms bare / 7.20 → 4.12 ms dressed**,
retaining the same solved positions within 1 mm.

Final uninstrumented routes, same real dt/default scale/window protocol:

| Route | Return p50 / p99 / worst, ms | Windows p99 >20 ms | >17.5 ms |
|---|---|---|---|
| 600 s forest | 10.84 / 16.39 / 196.87 | 30/297 | 74/297 |
| 120 s combat | 10.40 / 19.64 / 73.32 | 12/57 | 18/57 |

The **40–80 s camp phase improves 2/20 → 0/20** windows over 20 ms; worst window
p99 falls **31.84 → 18.41 ms**. All twelve combat-route failures occur after 94 s,
back in the field. Forest **30/297 versus 28/297** establishes no forest-tail win;
its worst interval includes **186.41 ms presentation / 4.24 ms callback thread
CPU**. The all-window 17.5 ms target remains unmet.

Combat/camera/music, **27 visual scenes, five framing courses**, geometry/warmup
and live-audio/loudness checks pass. Final hashes/windows, native attribution
(`combat-entry.json`), pose replays, original/corrected camp logs and captures are
in `build/round65/`. Reuse the route commands above with Round 65 output paths;
helpers own their render locks.

## Every mailbox tail: attribution and game fixes

The historical 45/297 log contains 233 intervals over 20 ms, with callback/present
and thread timing but no draw/native-call trace; exact first-use causes cannot be
recovered retrospectively. A new complete warm-cache replay records **261/261**
intervals over 20 ms, including startup transitions, with game stages, draw timing,
resource changes and native Vulkan call boundaries. Every interval is retained in
[the attribution evidence](performance-pacing060-tails.json.gz).

* **Two missing pipelines:** instanced props and Talus rocks, both depth-only
  D32 shadow draws, color mask zero, blending disabled. First draws cost
  **14.18 / 288.30 ms**; native creation itself costs **14.13 / 288.24 ms**.
  A populated disk cache did not contain these previously unused state keys.
* **Resource churn:** 1,059 buffer and 207 image creations during that replay.
  Tail-associated creation calls were tiny (buffer ≤0.004 ms, image ≤0.005 ms,
  memory allocation ≤1.10 ms). The descriptor array is fixed at **16,384**;
  texture slot high-water growth/recycling is not descriptor-array reallocation.
  No steady swapchain recreation or descriptor-update call over 2 ms occurred.
* **Runtime waits and CPU stages:** acquire reached **155.66 ms**, frame-fence
  waits **42.17 ms**, and submission **25.58 ms**. Other tails retain their
  poll/present or named callback stages (terrain selection, music, enemies,
  vegetation and wildlife). Driver waits can consume thread CPU; a high CPU
  counter alone does not prove expensive game computation. CPU call tracing
  does not identify which GPU pass preceded a fence wait.

Warmup now draws the missing shadow states, loaded character/material variants,
all four shrines and their water, cave water, mist, rain/night values, fire/smoke
blend states and lightning's **RGBA8 output target**, without simulation or RNG
advancement. Cull buffers retain persistent storage reserved from model placement,
quadtree and grass-grid bounds. Only batches rebuilt before each draw use transient
streaming (FX, wildlife, glider cords, Talus and blade trails); empty batches skip
uploads. Both production resolutions retain post, smoke and grain targets.

The fixed native 60-second route has **no new pipelines, images or swapchains**.
It records five tiny buffer creations (including the second frame's upload arena),
rather than repeated per-frame allocation. Its remaining tails include acquire
and submission waits. Diagnostic runs are not used as uninstrumented percentile
comparisons. [Runtime work still needed](SLOPPY_SHOWCASE.md#where-sloppy-fell-short).

## Three pacing scenes

Two 720-interval captures per row, first 240 intervals excluded: **960 pooled
samples**, nearest rank, matched production scale at 2133×1200.

| Scene | Vulkan mailbox p50 / p99 / worst, ms | Release OpenGL p50 / p99 / worst, ms |
|---|---|---|
| Forest | 10.80 / 14.72 / 49.35 | 16.68 / 29.70 / 68.95 |
| Fire | 8.51 / 12.85 / 45.76 | 16.68 / 29.18 / 61.45 |
| Overlook | 7.08 / 8.58 / 59.35 | 16.68 / 24.88 / 61.03 |

## Validation and startup

Twelve relevant GPU checks pass across both backends, including streamed-instance
snapshot/empty-batch checks and target reuse. Repeating weather, shrine, effect and
resolution transitions after warmup adds **zero pipelines** (46 before/after).
The prepared-asset check passes complete byte equivalence, collision/roof/RNG and
named draw order. Ten matched views retain geometry, UI and materials: OpenGL
matches the old game pixel for pixel in nine views; storm differs by one channel
count in one pixel. An unmatched natural lightning-flash reference is retained
alongside the repeated, matching-phase storm capture. Vulkan/OpenGL mean absolute
RGB differences remain **0.05–2.66 / 255**, p99 **1–26 counts**; Vulkan still lacks
OpenGL's 8× anisotropy.

Fresh prepared-copy startup, six source and six executable processes, X11
1280×720, scale 1, one screenshot; lock wait excluded and all packs hit:

| Launch | Load median (range), s | Whole process median (range), s |
|---|---|---|
| Source | 1.485 (1.43–1.94) | 3.165 (3.10–3.65) |
| Executable | 1.380 (1.35–1.40) | 1.605 (1.58–1.63) |

This includes render warmup and meets the **3.5 s warm load median** budget.
Before: 1.475 / 1.355 s load medians. Source whole-process time includes compilation.

The rebuilt package passes fresh-extract forest startup on Wayland at 2133×1200,
with HOME pointing to an **existing empty directory**, `XDG_CACHE_HOME` absent,
and the same HOME reused for the warm launch. All packs hit, zero PNG decodes,
18,587 vegetation placements; a valid HOME `.cache/sloppy/*.vkpipelines` file is
saved. New HOME/local shader caches are cold; system page caches are not flushed.

| Package backend | Empty-cache load / whole process, s | Warm load / whole process, s |
|---|---|---|
| Vulkan mailbox | 9.62 / 11.54 | 1.83 / 3.74 |
| OpenGL | 22.73 / 24.66 | 1.92 / 3.83 |

Reproduce (Python helpers own their render locks; never wrap them):

```sh
python3 tools/render_evidence.py soak --backend opengl --route forest --seconds 600 --output build/pacing/gl
python3 tools/render_evidence.py soak --backend vulkan --present-modes mailbox --route forest --seconds 600 --output build/pacing/vk
python3 tools/render_evidence.py pacing --backend opengl --repeats 2 --frames 720 --output build/pacing/scenes-gl
python3 tools/render_evidence.py pacing --backend vulkan --present-modes mailbox --repeats 2 --frames 720 --output build/pacing/scenes-vk
# Add --stage-trace and LD_AUDIT=$PWD/build/pacing/vulkan-trace.so for attribution:
cc -shared -fPIC -O2 tools/vulkan_call_trace.c -o build/pacing/vulkan-trace.so
python3 tools/pacing_report.py build/pacing/vk/*.log --output build/pacing/tails.json.gz
python3 tools/startup_copy_check.py --ref HEAD --backend vulkan --repeats 6 --binary-repeats 6 --output build/pacing/startup
tools/prepared_assets_check.sh
tools/package_linux.sh
python3 tools/package_cache_check.py build/slop-of-the-wild-linux-x86_64.tar.gz --output build/pacing/package
```

[Current machine-readable results and hashes](performance-pacing060.json).
Raw logs, all native calls, images, unmatched flash, startup repeats and package
extracts/caches remain under `build/pacing060/`. The prior full release suite and
historical distributions remain in [release evidence](performance-sloppy060.json)
and [pre-0.6 studies](rounds/PERFORMANCE_PRE_060.md).

## Round 72 sol3 follow-up

The Temple slab/inlay/cap and opening daylight/malice corrections retain the
existing draw passes and the 67 architecture chunks / 2,186 colliders. Final
prepared-asset equivalence and ten targeted checks pass. The full critic pack
passes with 50 reviewed captures, 13 audio clips and eight integration checks.
Evidence is retained under `build/task72b-sol3/` (`REPORT.txt`, `pack-final/`,
`visual-review.json`, `cpu-960/summary.json`, `cpu-assessment.json`).

Two adjacent AB/BA pairs per scene use identical fixtures, generated assets,
1920×1080 Vulkan at full scale, fixed seed/hour/weather/input and steady thread
core 0. Each run has 960 frames, excludes the first 240 and retains all 720
steady samples. The climb ascends for 180 frames then holds the matching pose,
so the long timing run stays on its short arch fixture.

| Scene | Master CPU p99 ms | Candidate CPU p99 ms | Delta ms |
| --- | ---: | ---: | ---: |
| Passage | 5.900 | 5.695 | -0.205 |
| Title | 6.205 | 7.117 | +0.912 |
| Temple gameplay climb | 5.636 | 5.091 | -0.545 |
| Temple floor | 9.243 | 8.781 | -0.462 |

The strict pooled title screen does not pass. Its paired per-run increases
(+0.129 / +0.179 ms) lie inside identical-master paired control differences
(-0.368 / +0.403 ms). The control's pooled-label gap is 0.608 ms and its per-run
p99 span is 4.108 ms. Title median CPU improves 2.972→2.804 ms and callback-wall
p99 changes by -0.005 ms. These observations are compatible with shared-host
variation; they do not establish zero overhead or strict pooled non-regression.
A small title overhead remains a measurement uncertainty.

Both 120-second real-time forest pacing routes pass at managed 2133×1200 with
native driver mailbox fallback to immediate presentation. Present-return p99
is 15.800 ms at dynamic scale (0.72/0.8), and 20.886 ms at full scale. The latter
has nine intervals over 25 ms and a 101.182 ms worst interval; raw tails remain
in the pack. Present-return intervals are not scanout measurements.

## Round 72 sol3 cave and shrine material follow-up

The cave's mineral contrast is scoped to a continuous interior-camera volume;
its exterior ridge retains the merged-master appearance. Blue floor inlays use
an interpolation-safe material tag and a queued additive falloff submitted after
the FX reset. Castle smoke has a filled crimson core and an unequal soft crown.
The four shrine wall palettes and inset proportions vary; Jo's pendant fill stays
neutral. Architecture retains 67 chunks and 2,186 colliders.

Final evidence is under `build/task72c-sol3/`: `handoff-pack/`,
`pack-comparisons/`, `visual-review.json`, `exterior-fix-review.json`,
`glow-staging-review.json`, and `cpu-handoff/assessment.json` (raw initial
summary: `cpu-handoff/summary.json`). All 53 final captures
were viewed downscaled against the 49-frame supplied pack and four matching
master supplements. Character/flight/camera differences already merged before
this task are identified in the review notes. The exterior glide comparison
matches the prior merged master to within one RGB level at a few pixels.

Prepared audio/world/mesh/collision/texture equivalence and all eight targeted
headless checks pass; the new material check is registered in the CPU suite.
The full critic pack includes both 120-second pacing routes, audio and all eight
integration checks. Superseded candidates are explicitly excluded from delivery.

CPU comparisons use frozen e9094ec master and final handoff binaries, generated
assets for both, fixed world/weather seeds, hour, inputs and 1/60 simulation,
1920×1080 Vulkan X11 at full scale, and main-thread affinity after frame 60.
Each run retains all 720 samples after its first 240 frames. Four adjacent AB/BA pairs were predeclared for passage and two for each other
scene. The title received one fixed two-pair extension after its initial result
was inconclusive against control variation; the primary title estimate includes
all four pairs. Every original and new tail is retained. One or two adjacent pairs share a bounded render lock.

| Scene | Master CPU p99 ms | Handoff CPU p99 ms | Delta ms |
| --- | ---: | ---: | ---: |
| passage | 5.134 | 7.041 | +1.907 |
| title | 6.763 | 6.508 | -0.255 |
| shrine-1 | 3.296 | 2.907 | -0.389 |
| shrine-2 | 2.820 | 5.237 | +2.417 |
| shrine-3 | 5.843 | 3.654 | -2.189 |
| shrine-4 | 5.269 | 2.586 | -2.683 |

Strict pooled CPU p99 is unresolved for passage, shrine-2. Same-master controls demonstrate host variation but do not prove zero overhead.

passage median CPU: 3.442→3.232 ms; this does not resolve the p99 gate.
shrine-2 median CPU: 1.880→1.898 ms; this does not resolve the p99 gate.
The initial two-pair title CPU p99 was 5.162→7.036 ms; both that result and the combined result remain in the raw evidence.

Identical-master controls use the same affinity and frame protocol. Their
pooled label differences are passage -2.668 ms, title +0.053 ms.
Dynamic scale 120-second route present-return p99: 17.259 ms, worst 1853.239 ms, 3 intervals over 25 ms.
Full scale 120-second route present-return p99: 20.389 ms, worst 26.343 ms, 4 intervals over 25 ms.
Present-return timing is not scanout measurement. Raw distributions and logs remain in the pack.
