# Performance — Sloppy 0.6.0, 2026-10-12

Unmodified official **0.6.0** (`7c8d133`), i7-6700 / GTX 1070, Wayland,
**2133×1200 physical pixels**, production dynamic scene scale. All outliers are
retained. These are **producer/present-return intervals, not scanout timestamps**;
the shared desktop is not an isolated hardware guarantee.

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
