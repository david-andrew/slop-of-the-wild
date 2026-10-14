# Round 67 continued: tree structure, uploads and cue-frame CPU

Measurements compare `983d47d` with the changes in this document. Sloppy remains
unmodified release 0.6.0. Evidence stays in `build/task67b-sol/`; no outliers are
removed. The shared desktop was not otherwise idle, so these results cannot
certify the idle-machine target.

## Changes

Trees keep full nearby geometry and the existing eight-direction atlases beyond
70 m, with the complementary 55–70 m dither band intact. The intermediate leaf
meshes now retain the existing crown envelope, top shelves and selected interior
cards instead of every interior layer. Near shadow casters switch to that mesh
beyond 16 m, and middle shadow casters use the reduced geometry. Trunks, tree
placement, collision, wind, wet lighting and cascade resolution/cadence remain
as before. The existing triangle diagnostic now follows the selected intermediate mesh.

Terrain selection now streams its nodes into immutable frame-local upload
memory. Every world frame selects before all its terrain draws. Updating the
previous persistent device buffer inserted transfer barriers against its prior
readers; the streamed path avoids those barriers without changing node selection.

Held piano notes previously allocated, faded, peak-scanned and repacked three
whole dynamic samples on their onset frame, including inaudible layers. They now
retain the immutable PCM16 source and apply the source-clock damper inside the
existing bounded voice ring. Only audible layers receive a voice. The release
shape, pitched lifetime, gain ramps, stereo source and score timing are retained;
removing the second PCM16 quantization changes samples only within its rounding
precision. This addresses the traced `jingles_update` spikes without changing
the live mixer or vendored runtime.

## Matched CPU and producer intervals

Final results are recorded in `paired/summary.json`. Each adjacent AB/BA pair
uses a visible managed X11 Vulkan client at **1920×1080, full scale**, immediate
presentation fallback, fixed world/hour/weather/input and 1/60 s simulation.
Three pairs per scene retain 1,440 steady samples per version after frame 240.
Swimming releases forward at frame 150; its separate moving window, frames
61–150, retains 270 samples per version. PNG readback happens after measurement.
Every repeat, environment, executable hash, load average and raw row is retained.

| Fixed workload | Callback CPU p99 before → after, ms | Producer p99 before → after, ms |
|---|---:|---:|
| Forest | 12.321 → 11.715 | 20.044 → 20.297 |
| Camp | 11.406 → 16.864 | 17.052 → 19.093 |
| Moving swim | 18.021 → 7.486 | 22.338 → 18.101 |
| Stationary tread | 9.155 → 9.428 | 18.310 → 17.909 |

**CPU non-regression: FAIL.** The camp and stationary-tread deltas remain
positive in the pooled final comparison. Moving-swim CPU improves substantially;
that does not turn the other scenes into passes. Run-level variation is retained
in every AB/BA pair rather than discarded or used to waive the failure.

**Fixed-scene 16.7 ms producer budget: FAIL.** The real-time route measurements
below are the direct forest/camp route results; neither is replaced by a GPU
percentile or a faster individual fixed-view repeat.


The fixed forest view is a rendering workload; the camp replay includes
production approach, locking and strikes. Independent **120-second real-dt
forest and combat routes** are retained in `routes/`, with source manifests,
route activity and every present return. The combat route's 40–80 s phase is
reported separately from its field phases. Its existing test controller raises
health and teleports only at phase boundaries; fixed replays retain ordinary
health and combat behavior.

| Real-dt workload | Producer p99 before → after, ms | Callback CPU p99 before → after, ms |
|---|---:|---:|
| Forest, 120 s | 22.297 → 21.479 | 13.859 → 12.948 |
| Combat controller, 120 s | 22.658 → 23.373 | 14.690 → 14.538 |
| Camp phase, 40–80 s | 20.905 → 25.959 | 15.626 → 15.840 |

The **16.7 ms route target fails in both final workloads**. Camp-phase CPU p99
also regresses **15.626 → 15.840 ms**, so this route does not pass CPU
non-regression. Faster mean throughput does not override that failure.

The forest traverses **424.214 → 424.533 m**, with callback thread worst
**52.741 → 22.292 ms**. Combat activity differs with real dt: cumulative engaged
frames are **1,038 → 787**, and cumulative swing frames **1,778 → 2,001**. These
are production route runs, not identical frame-by-frame combat states. Camp
producer mean improves **12.999 → 11.883 ms**, but its worst interval worsens
**34.121 → 69.624 ms**; every tail is retained.


## Vulkan GPU zones and waiting

GPU diagnostics are separate from the uninstrumented CPU comparisons. Available
native timestamp results are read four frames later without a blocking query.
Conditional cascade zones contribute zero on frames where they are skipped.
Matched AB/BA GPU pairs and all zone totals are in `paired-gpu/summary.json`.

| Full-1080p scene | GPU mean before → after, ms | GPU p99 before → after, ms |
|---|---:|---:|
| forest | 15.350 → 14.457 | 17.076 → 16.564 |
| camp | 12.670 → 12.659 | 14.294 → 14.364 |

Two reversed-order pairs retain **950 available GPU samples per version per scene**.

| Forest zone | Mean before → after, ms |
|---|---:|
| trees | 4.380 → 4.058 |
| sh-veg0 | 2.519 → 2.055 |
| sh-veg1 | 0.981 → 0.866 |
| terrain | 2.357 → 2.337 |
| post | 1.379 → 1.354 |

Forest GPU mean improves by **0.894 ms/frame**; the structural tree/shadow
zones account for most of that difference. GPU p99 below 16.7 ms does not
establish producer p99 below that budget.


`native-attribution.json` retains two earlier instrumented forest controls,
including neighboring native calls and game stages for every selected tail.
During frames 241–720 the original records **468 fence waits over 2 ms**, totaling
**4.390 s**, worst **13.421 ms**; the reduced-canopy candidate records **480**,
**4.240 s**, worst **11.190 ms**. Neither control records acquire or queue-present
calls over 2 ms in that interval. No graphics pipeline, buffer, image or memory
allocation is created in that steady window. These controls predate the final
terrain streaming change and are diagnostic attribution, not the final CPU
comparison.

The frame fence is waited by runtime `__vk_begin_frame`, reached through the
first terrain upload. Consequently the game profiler attributes that blocked
wall time to `terrain_select`. A long producer frame can also contain several
milliseconds of actual CPU submission/simulation work after the fence, plus
submit/present/poll/audio work outside the callback. GPU-zone p99 excludes these
CPU and WSI intervals. Subtracting separately pooled p99 values does not measure
a missing stage: the percentiles can describe different frames. CPU tails in
the diagnostic controls also span wildlife/vegetation submission and posed
combat geometry; they are not all acquisition stalls or all terrain math.

Instance uploads are small in the fixed forest (about **15 KB/frame**) and camp
(about **45 KB/frame**, p99 about **125 KB**). These counters exclude uniforms and
other runtime arena writes. Native tracing finds no periodic steady allocation
or pipeline compilation to explain the gap. Screenshot readbacks are outside
the measured windows. Remaining runtime telemetry needs are documented in
[SLOPPY_UPSTREAM.md](SLOPPY_UPSTREAM.md).

## Startup, visuals and verification

The final critic pack includes one fresh local cache run, three warm runs and an
entry-point-only rebuilt executable with identical shader digests. Pack evidence:
`critic-final/startup/summary.json`. This is the existing bounded startup protocol;
system/page caches are not flushed and lock queue time is excluded.

| Launch | In-game load, s | Render warmup, s | Process, s |
|---|---:|---:|---:|
| cold | 10.35 | 8.970 | 11.04 |
| warm-1 | 1.59 | 0.213 | 2.24 |
| warm-2 | 1.58 | 0.209 | 2.27 |
| warm-3 | 1.54 | 0.195 | 2.21 |
| new-build | 1.71 | 0.317 | 2.37 |

Warm median **1.58 s** is unchanged from the previous final pack and still
misses **1.5 s**. Every warm launch and the changed executable hits the shared
pipeline cache. This change does not claim a startup win.

Matched full-resolution PNGs and downscaled inspection copies are in `paired/`.
`forest-final-pair.jpg`, `camp-final-pair.jpg` and `swim-final-pair.jpg` are the
viewed final matched comparisons. Earlier candidate comparisons are retained too. The final required `critic_pack.py --only captures` output, including
forest, firs, snow, wet weather, combat and swimming, is `critic-final/`.

**PASS:** `tools/prepare_assets.sh`, `tools/prepared_assets_check.sh`, and all
10 targeted checks: `piano_hold_check`, `piano_storage_check`, `piano_test`,
`music_transition_check`, `vegetation_lod_check`, `vegetation_reach_check`,
`vegetation_tail_check`, `tree_test`, `fir_bough_check`, and
`renderer_structure_check`. Runner logs and evidence-directory pointers are in
`checks/`; preparation logs are `prepare-final.log` / `prepared-final.log`.
`git diff --check` also passes.

The final capture pack passes its requested capture section with **45 shots**. Its forest,
fir/snow, rain/storm, camp and swimming JPEGs were viewed at reduced size,
along with matched before/after forest, camp and swimming comparisons. Nearby
canopies, terrain detail, combat framing and swim appearance remain readable.
This is implementation visual review, not a new critic score.

The final fixed camp CPU regression is **+5.458 ms** and tread **+0.273 ms**;
these are unresolved failures. Earlier instrumented camp tails are dominated
by posed skinning/clearance work, but this pass has not established why the final
uncontrolled paired camp tail differs so much. A further pre-sized-buffer probe
preserves 10,041,120 vertices byte for byte but measures **222.652 → 225.401 ms**
in its isolated kernel, so it is not shipped. The probe and every failed budget
remain visible in `build/task67b-sol/`; no hardware-isolation or non-regression
waiver is claimed.


The new `piano_hold_check` compares **12,644,352** ring samples with the former
whole-note bake, including zero/short/2.75 s holds, fractional pitches, source
exhaustion, ring wraps, interrupted gain ramps, exact voice lifetimes, immutable
banks and audible dynamic counts. Differences remain within the old sample's
half-quantum rounding plus float arithmetic tolerance. `vegetation_lod_check`
covers 90 distance-boundary/view/cascade/bare/felled-tree cases. Both are in
`cpu_checks=(...)`, one per line.

Reproduce the final repeated fixed-frame comparisons:

```sh
sloppy/bin/sloppy build tools/performance_game.jo -o build/task67b-sol/after
python3 tools/round67b_performance.py build/task67b-sol/before build/task67b-sol/after build/task67b-sol/paired --repeats 3
python3 tools/round67b_performance.py build/task67b-sol/before build/task67b-sol/after build/task67b-sol/paired-gpu --scenes forest camp --repeats 2 --gpu
python3 build/task67b-sol/routes.py build
python3 build/task67b-sol/routes.py run
python3 tools/critic_pack.py --only captures build/task67b-sol/critic-final
```

The before executable is frozen from `983d47d`; final source hashes are beside
`after` and both real-time route fixtures. Render helpers own bounded locks;
do not wrap them in another flock. Earlier instrumented variations remain in the evidence folder and do not
replace the final comparisons above.
