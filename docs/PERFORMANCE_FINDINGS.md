# Performance findings

Current burning-tent follow-up (three repeats, frames 241–900):
[BURNING_CAMP_PERFORMANCE.md](BURNING_CAMP_PERFORMANCE.md). The measurements below retain
the earlier ten-view runs and their original protocol.

Measured on 2026-10-09 in `sol/work`, from master `9c98d6b`, with the pinned Sloppy runtime
unchanged. [PERFORMANCE.md](PERFORMANCE.md) gives three-repeat ranges for all ten views;
[benchmarks.json](benchmarks.json) retains the quieter rerun;
[benchmarks-busy.json](benchmarks-busy.json) retains the initial shared-load suite
with per-run resolution, load, CPU wall/thread time,
GPU passes, loader/first-frame measurements and concurrent process names. The instrumented
baseline is in [performance-before.json](performance-before.json).

## What caused the hitches

**First-use asset/sound work was ours.** An instrumented forest's first frame cost
252.7–964.5 ms (three processes, including the first driver-cache use). A shrine-entry run
had a 71.0 ms effects section and a 197.3 ms section labelled `post`. Investigation separated
the actual render passes from the HUD: the latter was the large place-name PNG atlas decoding
and uploading, rather than post-processing. A later split timing measured the atlas at **182 ms decoding / 2 ms upload**, so decoding dominated.
Title art was also lazy; trees built their spatial
cell index on the first cull. Representative outdoor/shrine/cave render paths and the title
sprite now run during loading, before presenting gameplay. Atlas/title uploads and cell building
happen during load. Warmup waits for the compositor's configured dimensions and the runtime's
initialized 2D batch, so it allocates the correctly sized targets once. Total load includes this
work; it has not been hidden from the measurements.

After those fixes a 17–18 ms `shrines_update` section remained when a lift was used. The pinned
library's `sfx_chime()` synthesizes a full 1.2-second sound on *every* call. `audio_cache.jo` builds
that exact sample at load and shrine/story calls reuse it. This fixes lift/activation/plate
chimes, preserving their sound and pitch.

**CPU wall spikes include waiting and scheduling.** For example, baseline forest sample 269
had 12.649 ms of update/draw wall time but 5.667 ms of main-thread CPU; sample 422 in uncapped X11
had 19.157 ms wall but 5.709 ms thread CPU. The high-load machine can preempt the game, and GL calls
can wait on the driver/GPU. These numbers rule out 12–19 ms of continuous main-thread computation,
but do not separate driver blocking from scheduler preemption alone. Later diagnostic runs also
record voluntary/involuntary thread context switches: forest repeat 3, frame 349 had 12.926 ms
wall / 5.779 ms thread CPU, zero voluntary and three involuntary switches. This directly confirms
scheduler preemption in that outlier. Sloppy has reference-counted
storage and allocation/free lists, **no tracing GC**. Slow sections moved between vegetation,
characters, props and post; there was no consistent simulation hotspot accounting for those
spikes. Concurrent load is retained per run, not described as an idle-machine result.

**Presentation spikes remain outside measured game work.** Baseline forest sample 438 had a
33.580 ms real interval, 5.814 ms game CPU, and 27.766 ms in the remaining interval. The runtime
reported long presentation waits independently (one original run: 44.2 ms interval, 5.4 ms CPU,
38.8 ms presentation). Its Wayland backend waits for compositor frame callbacks and free
buffers. A missed display deadline, compositor delay, GPU/driver wait or scheduling can create
that pattern. Lower rendering cost adds GPU headroom, but these logs cannot identify every
present wait as a GPU deadline miss. They are not attributed to streaming or GC without evidence.
A separate no-stdlib-statistics comparison checks that the remaining long intervals are not
caused solely by the runtime's per-frame median calculation/logging.

**Profiling could itself block.** GPU results used to be fetched after three frames on the
assumption that they must be ready. The game now checks all `GL_QUERY_RESULT_AVAILABLE` flags
first and drops unfinished samples instead of doing a blocking result read. `gpu skipped:` logs
count drops; none were reported in the final suite. This affects profiling runs, not ordinary gameplay.

## Steady-state rendering changes

Vegetation culling previously issued about 55 buffer uploads / 114 kB per forest frame even with
unchanged static transforms/tints. `draw_static` was already correctly using GPU-resident buffers;
the repeated calls came from `vegetation_cull`. It now compares each bucket with its retained last
payload (exact bytes, including burn tint), uploading only changes. Stable-frame totals fall to
about five uploads / 12 kB for terrain/grass; moving views and changing cull lists still upload.
View/near-shadow/middle-shadow buffers remain independent.

Separate vegetation shadow/depth fragment shaders preserve the previous alpha cutouts. In the
view, the depth pass resolves alpha, dither and camera/player dissolve; the shaded pass uses
`GL_EQUAL` and does not redo coverage. Both use identical uniforms, including wind/time, so they
also agree during normal wall-clock play. Tree meshes, LOD thresholds and all three 2048² shadow
maps are unchanged. The middle/far cascades were already alternating before this work; there
was no once-per-120-frame cascade update to fix.

The forest's first paired uncapped comparison at **2246×1227 output, 80% scene scale** reduced
trees **4.14 → 3.59 ms**, vegetation shadows **1.21 → 0.92 ms**, and total GPU time
**14.89 → 13.89 ms**. That is about 13%, 24% and 7% respectively. The final three-repeat ranges
below supersede this single pair for headroom claims. Older ~16.5 ms vsync-bound GPU totals cannot
serve as an uncapped before/after comparison.

## Visual verification

Compared same-size, same-camera forest screenshots at frame 480: `/tmp/botw-sol-perf/before-2-paced.png`
and `/tmp/botw-sol-perf/after-paced.png` (2133×1200). Crowns, leaf edges, player-camera dissolve,
trunks, ground shadows and undergrowth retain their appearance. Whole-image RGB mean absolute
difference is **0.046%** of full scale; moving characters account for the readily visible
changed pixels. The screenshots were inspected as well as compared numerically. Final benchmark
renders also cover open land, pond, fire, snow, storm, shrine and moving views. No label/text was
added to gameplay.

## Measurement protocol

`tools/bench.sh` holds `/tmp/botw-render.lock` for the entire suite, not just individual renders,
and records start/end `/proc/loadavg` plus process-name CPU snapshots for every run. Three repeats
per view/backend use frames 241–480 (240 intervals/run). Nearest-rank p50/p95/p99/worst are computed
from raw real update-to-update times; fixed-step simulation `dt` is never used as timing evidence.
`BOTW_SCALE=0.8` fixes scene resolution instead of allowing adaptive reallocations. GPU runs use
`BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11`; the report validates the X11 backend and swap-interval errors.
Actual output is **2133×1200 paced Wayland**, **2246×1227 uncapped X11** here, as the window manager
resizes the requested 2133×1200 X11 window. Scene sizes are **1706×960** and **1796×981** respectively.
The X11 pixel count and aspect ratio differ from the paced run. GPU headroom applies to the
reported X11 workload; these are not equal-resolution fps comparisons.

Game CPU is update + draw, excluding runtime final submission/audio. `gap` includes those,
statistics output, polling and presentation. Main-thread CPU comes from Linux
`CLOCK_THREAD_CPUTIME_ID`; it excludes time waiting/preempted. Raw rows associate CPU/uploads with
the preceding update/draw frame and the interval containing that work. Percentiles from the game
log use 120-sample batches; the benchmark recomputes them across the complete 240-frame window.
The first presented interval and loader warmup are reported separately, outside steady-state rows.
A short game frame can still have a long early presentation interval. Offscreen warmup does not
exercise the runtime's actual dma-buf presentation path, which creates swap buffers on first use
and waits for compositor callbacks. One sprint-open run had **123.769 ms at interval 2**, with
**3.322 ms game CPU / 120.447 ms remaining interval**. These startup presentation waits remain;
the log does not distinguish allocation, first swap-shader use, GPU/compositor startup and
scheduling sufficiently to assign all that time to one cause. GPU pass numbers use the last complete
120-query-frame batch after startup (usually frames 240–359 for a 480-frame run; unavailable
query frames are excluded), rather than attributing presentation waits to the final GPU pass.

Each cold-load run starts a **new process**. Shared filesystem/driver caches are retained: deleting
them would perturb other agents. These are process-cold measurements, not claims of a cold OS
page cache or guaranteed cold GPU shader cache. First-use tests cover the title camera/card and
entry into Ohman Ow using `BOTW_ENTER=1`; all four exit transitions are covered by regression checks.

## Verification

Passed `feel_test`, `fauna_test`, `contact_check`, `element_test`, `element_check`, `save_test` and
`architecture_test`; passage and four shrine exits were checked after the first benchmark under the
same render lock. Both passed: passage reaches 4.8 m from the cave mouth; all four shrine exits
end on the ground at the entrance with the camera 5.2 m outside the hood. Scripts/type checking
and whitespace validation passed. See below for repeated startup/presentation numbers.

## Before/after comparison under shared load

The first **60 runs** completed (three repeats × ten views × two backends), each with 240 verified
steady-state samples. One-minute load ranged **6.93–12.30** on the i7-6700 (4 cores / 8 threads);
this first suite was a shared, busy-machine comparison, with the render lock held throughout the suite. Other agents'
compilation and desktop/browser work continued; no other game render could overlap the suite.

Forest figures are medians across three runs, followed by the min–max range:

| measurement | baseline | final |
|---|---|---|
| paced p50 | 16.731 (16.629–16.746) ms | 16.704 (16.660–16.746) ms |
| paced p95 | 19.727 (19.414–20.878) ms | 19.885 (18.986–19.949) ms |
| paced p99 | 33.580 (23.139–34.324) ms | 21.360 (21.162–22.494) ms |
| paced worst | 35.348 (28.276–50.816) ms | 22.005 (21.946–23.702) ms |
| CPU wall average | 6.942 (6.826–7.902) ms | 6.608 (6.561–7.187) ms |
| main-thread CPU average | 5.287 (5.215–5.677) ms | 5.048 (4.980–5.127) ms |
| instance uploads per frame | 55 / 113,613 bytes | 5 / 11,502 bytes |
| trees, uncapped GPU | 4.14 (4.12–4.14) ms | 3.64 (3.63–3.66) ms |
| near vegetation shadows, GPU | 0.69 (0.69–0.70) ms | 0.51 (0.51–0.51) ms |
| middle vegetation shadows, GPU | 0.52 (0.51–0.52) ms | 0.42 (0.41–0.42) ms |
| total uncapped GPU | 14.86 (14.84–14.86) ms | 13.97 (13.96–14.09) ms |

Both before/after GPU comparisons use the same 2246×1227 output and 80% scene scale.
The final forest GPU total leaves **2.70 ms** against a 16.67 ms budget at that pixel count.
There were zero steady-state paced long frames in those three forest runs (threshold
1.5× median + 1 ms). This is measured improvement under these loads, not a guarantee that all
presentation/scheduling hitches disappeared. Uncapped X11 interval p99 actually varied more:
**24.60 (21.40–37.78) ms** versus **23.27 (22.48–24.07) ms** before, although GPU rendering
became cheaper. The shared machine's frame-delivery variability remains visible.

Across all views, paced p99 run medians range **20.93–33.65 ms**. Worst-frame medians range
**21.85–51.84 ms**, with a single **79.71 ms** a shrine interval retained in the table. Grass fire's
uncapped GPU median is **16.69 (16.52–16.73) ms**, so it has effectively no 60 Hz GPU margin at the
larger X11 pixel count. Terrain is now the largest measured pass in most views. The table reports
those limitations rather than claiming uniformly stutter-free 60 Hz.

## Cold process load and first use

Three paired title tests use **`BOTW_TITLE=1 BOTW_AT=-1024,1799,0`**, which starts at the actual
trigger. `BOTW_TITLE` alone positions Jo outside the trigger and did not exercise the card;
those preliminary runs were replaced for title claims. Baseline files were archived from
`9c98d6b` under ignored `build/perf-baseline`, with measurement instrumentation only. Every run
used the shared render lock. Details and slow samples are in
[performance-startup.json](performance-startup.json).

The title first-use sample (interval 362, containing draw/update frame 361) changed as follows:

| measurement | baseline, three runs | final, three runs |
|---|---|---|
| game CPU | 45.540 (39.616–50.065) ms | 4.686 (3.460–6.379) ms |
| real interval | 46.421 (40.601–50.363) ms | 16.641 (16.537–16.649) ms |
| process load, including warmup | 3.15 (3.13–4.47) s | 3.27 (3.23–3.55) s |
| first game frame CPU | 39.930 (36.572–272.358) ms | 3.618 (3.464–4.051) ms |

Title warmup itself was **0.232 (0.225–0.238) s**, including title decode **33–35 ms**, names decode
**122–129 ms**, and about **1 ms** for the names texture upload in this quieter phase. Cold driver
cache use made the initial baseline first frame much slower than later baseline processes.
All load time includes the warmup; first-game-frame timing begins afterwards. Shared OS/driver
caches remain in place. The first-use stall has been moved into load, not silently excluded from
both load and frame statistics.

The title-camera window (intervals 345–420) still contained occasional CPU outliers up to
**17.934 ms** in a final run, versus the specific texture first-use event above. Some of these
inflate thread CPU as well as wall time across several sections; they are not all attributable
to preemption. The logs do not uniquely distinguish frequency/SMT/driver contention and changes
in visible work there. No atlas reload, instance-upload burst, tracing GC or synchronized
three-cascade refresh accounts for the texture event after the fix.

For Ohman Ow entry (`BOTW_SKIP=1 BOTW_TOWER=1 BOTW_ENTER=1`, 720 frames), the baseline had
**73.5 ms effects** and **198.9 ms CPU / 216.6 ms interval** as the shrine name appeared. After
warming effects and preloading the atlas, shader/texture first-use spikes did not recur in the
entry window (intervals 30–130): maximum game CPU per run was **9.729 / 10.317 / 15.443 ms**;
maximum thread CPU was **4.989 / 4.900 / 6.083 ms**, and the 15.443 ms wall sample had four
involuntary switches. Once the chime was cached, first-game-frame CPU was
**5.001 (4.908–5.269) ms**, compared with **79.240 ms** in the original entry run and about
22 ms with rendering/textures warm but the chime still uncached. Process loads were
**4.75 (4.59–4.76) s**. Final entry steady-state p99 was **21.971 (20.512–22.767) ms**, with
worst **29.764 (28.456–34.224) ms**: presentation variation persists even in the cheap indoor view.

Three forest comparisons with **`BOTW_FRAME_LOG=1` and no `SLOPPY_STATS`** retained long intervals.
P99 was **21.523 (21.487–21.979) ms**, worst **41.980 (31.687–48.589) ms**. This excludes the
stdlib's per-frame median/logger as the sole source; game-side buffered diagnostics remain enabled,
so it is not a claim about a completely uninstrumented game. Full render regression checks passed.

## Quieter rerun

After the other heavy jobs finished, the complete 60-run suite was repeated under the same
render lock, from **16:49–17:02 EDT**. Start/end one-minute load averages were **1.11–2.27**
on the same 4-core / 8-thread machine. This is the quieter dataset in
[PERFORMANCE.md](PERFORMANCE.md) and [benchmarks.json](benchmarks.json); the earlier shared-load
dataset remains in [benchmarks-busy.json](benchmarks-busy.json). All 60 logs have the expected
240 steady-state interval samples. Resolutions, render scale and GPU measurement protocol are
identical to the busy suite.

Forest results (median and min–max across three runs):

| measurement | quieter final |
|---|---|
| paced p50 | 16.675 (16.657–16.686) ms |
| paced p95 | 18.204 (17.777–18.459) ms |
| paced p99 | 23.585 (20.422–25.897) ms |
| paced worst | 40.841 (35.003–45.642) ms |
| CPU wall average | 6.618 (6.233–6.778) ms |
| main-thread CPU average | 6.528 (6.129–6.684) ms |
| trees, uncapped GPU | 3.64 (3.64–3.67) ms |
| near vegetation shadows, GPU | 0.51 (0.51–0.52) ms |
| middle vegetation shadows, GPU | 0.43 (0.43–0.44) ms |
| total uncapped GPU | 14.07 (14.07–14.13) ms |

That forest workload leaves **2.60 ms** against a 16.67 ms GPU budget at **2246×1227 / 80%**.
The shading savings repeated under lower load, but frame-delivery tails did not improve
consistently: quiet forest repeat 2, interval 408 was **45.642 ms**, containing **6.828 ms game
CPU / 38.814 ms remaining interval**, with zero main-thread context switches during game work.
Across the ten views, median paced p99 ranges **19.05–23.59 ms** and median worst ranges
**26.41–51.32 ms**; the largest individual paced interval is **52.33 ms** in the camp.
Grass fire remains GPU-limited at **16.73 (16.65–16.74) ms** for the measured X11 workload.

CPU spikes also persist with low aggregate load. Forest paced CPU-wall p99 is
**14.781 (13.005–15.201) ms**, and thread-CPU p99 is **14.509 (12.797–14.534) ms**.
In later user/system diagnostics, fire GPU run 3, frame 119 used **12.588 ms wall / 12.343 ms
thread CPU**, all **12.343 ms userspace**, with zero voluntary/involuntary switches. This is
actual thread work inflation, unlike the confirmed preempted example above. The CPU governor
was `powersave`; frequency/SMT/driver effects are possible, but no sampling profiler was available
to prove them. These traces do not justify assigning every all-section slowdown to contention
or claiming that all hitches are fixed. Lower GPU cost, first-use warmup and caching address
the measured game-owned costs; presentation tails and unexplained CPU inflation remain.

## Round 50 art comparison (2026-10-09)

Baseline `99912bc`, compared on `astra/work`; GTX 1070, 1280×720, `BOTW_GPU=1 BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11`. Every game render was wrapped in `flock /tmp/botw-render.lock`. Values below are the last complete 120-frame GPU timer window, with identical fixed-frame inputs before and after. These are single-run comparisons, not confidence intervals.

Trees use derivative-sized cutout coverage in the depth and color passes, five baked crown habits and branch openings, flatter lateral boughs, less distance swelling, and low-detail branch forks. Grass density and blade geometry are unchanged. The cave has a continuous layered overhang/lining and a matching terrain cut. Hylia restores the source actors’ 417 m summit (the baked ground was 349 m there), with spurs, exposed snow bands and an altitude-dependent treeline. Existing temple-road rock/debris actors are made more legible, with sheltered flower beds.

| View | Trees ms | Terrain ms | Buildings ms | Grass ms | Total GPU ms |
|---|---:|---:|---:|---:|---:|
| Glide | 4.17 → 3.73 | 3.75 → 3.74 | 0.29 → 0.32 | 0.40 → 0.40 | 11.04 → 10.55 |
| Plateau overview | 6.61 → 5.86 | 4.83 → 4.84 | 0.38 → 0.38 | 0.00 → 0.00 | 14.02 → 13.28 |
| Title panorama | 5.09 → 4.63 | 3.33 → 3.33 | 0.08 → 0.21 | 0.55 → 0.60 | 11.68 → 11.41 |
| Cave exterior | 0.18 → 0.16 | 6.05 → 6.37 | 0.80 → 0.94 | 0.29 → 0.29 | 9.58 → 10.01 |
| Cave overlook | 0.21 → 0.19 | 4.93 → 4.99 | 0.38 → 0.44 | 0.96 → 0.97 | 8.71 → 8.80 |
| Snow approach | 0.34 → 0.33 | 4.63 → 4.76 | 0.10 → 0.15 | 0.28 → 0.29 | 7.82 → 8.01 |
| Mount Jolia | 0.23 → 0.19 | 3.32 → 3.63 | 0.04 → 0.10 | 0.00 → 0.00 | 5.73 → 5.99 |
| Temple road | 1.25 → 1.09 | 3.19 → 3.26 | 0.32 → 0.32 | 0.39 → 0.39 | 7.31 → 7.19 |
| Walk-out · frame 700 | 4.20 → 3.56 | 1.77 → 1.76 | 1.14 → 1.21 | 0.12 → 0.13 | 9.65 → 9.04 |
| Walk-out · frame 830 | 4.26 → 3.66 | 2.19 → 2.19 | 1.03 → 1.22 | 0.21 → 0.23 | 10.15 → 9.75 |

All individual passes, frame counts and image paths: [art-round50-gpu.json](art-round50-gpu.json). Local screenshots/logs: `build/round50/before/` and `build/round50/after/`, named `glide`, `overview`, `title`, `cave`, `overlook`, `snow`, `mountain`, `meadow`, `passage700`, and `passage830` (`.png`/`.log`). Local comparison viewer: `build/round50/art-comparison.html`. Frame 830 retains the existing story’s bright exit transition in both captures.

Validation: `feel_test` **99.0**; `fauna_test`, `element_test`, `element_check` (19 checks), `save_test`, `architecture_test`, and `passage_check.sh` pass. Passage ends at (-1071.9, 246.8, 1847.8), 4.8 m from the mouth at frame 760. Baked models have finite vertices, valid indices, unchanged vertex counts, and fewer leaf triangles. Terrain probe: summit 417.32 m; old man’s summit anchor 417.20 m.
