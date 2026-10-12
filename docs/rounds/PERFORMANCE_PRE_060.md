# Historical pre-0.6 OpenGL performance — 2026-10-12

The following studies used the previous patched toolchain; they retain their
original protocols and are not measurements of the release Vulkan renderer.


i7-6700 / GTX 1070; `68ba705` → remaining-tail work on `sol/work`.
**2133×1200**, Wayland dma-buf **mailbox**, fixed scene scale **0.80**.
Tuples are **p50 / p99 / worst ms**; CPU is callback **thread CPU**.

| Forest, 600 s | Intervals before → after | CPU before → after | Windows >20 ms | Windows >17.5 ms |
|---|---|---|---|---|
| Untraced | 9.33 / 14.73 / 91.03 → 9.17 / 13.61 / 91.48 | 4.01 / 6.67 / 14.88 → 3.99 / 6.50 / 18.77 | 15/295 → 4/297 | 34/295 → 11/297 |
| Matched attribution | 9.16 / 13.68 / 92.38 → 9.12 / 13.31 / 88.50 | 4.15 / 6.61 / 21.98 → 4.22 / 6.53 / 10.22 | 5/297 → 4/297 | 8/297 → 8/297 |

Same continuous forest/meadow waypoint route, real production dt: **2.53 → 2.51 km**
untraced. Complete **two-second monotonic windows**, nearest rank; exclude four
seconds after first return plus the next even-second boundary. All subsequent
outliers retained. These are **present-return handoffs**, not scanout/delivery.
Fresh-before variation and profiling effects prevent assigning the entire historical
window improvement to the fixes.

**The strict all-window 17.5 ms target remains unmet.** Fresh traces retain every
**108 → 86** long interval, including **51 → 22** inside failing windows. After:
**10/22 (45%)** are inferred presentation/fence-only; **12/22** are low-CPU driver
waits (nine during far-shadow submission, one each vegetation, buildings and HUD).
No failing-window tail has measured CPU overload, GPU-pass overload or observed
shader/binding first use. These waits are outside measured game work; compositor
versus driver scheduling cannot be proved without additional platform telemetry.
Across all long traced intervals, presentation/fence-only is **39/86 (45%)**.
The historical untraced capture cannot retrospectively identify individual GPU passes.

GPU total p99 **11.39 → 11.26 ms**; after pass p99: vegetation view **4.75**,
near/middle shadow vegetation **1.88 / 2.11**, far shadow **1.13**, water **0.39**,
post/watercolour **1.14 ms**. Elapsed GPU queries also include submission/scheduling
bubbles. Cascades already alternate; no rendering cadence or LOD coverage changed.
The existing **64-cell/pass/frame** candidate rebuild retains exact visibility/order.

Distant actors now upload an unchanged older skin pose **once per frame**, reusing
its palette row across shadow/colour passes. Retained storage prevents pointer reuse;
copy-on-write edits, row wrap and next-frame texture rotation are verified on GPU.
Loading warms all vegetation species/LOD bindings and loaded character model/texture
variants. No post-load vegetation VAO allocations or shader requests were observed;
eight later plain bindings were unrelated to long intervals. Internal driver shader
specialization has no direct telemetry. The large character-shadow CPU stall did not
recur in the complete after trace; the untraced CPU worst remains visible above.

That earlier before/after study's fresh-copy startup, three source/binary processes
each, measured **1.48 / 1.49 s load medians**, binary process **1.65 s**. These are
historical figures; the Round 81 startup audit below retains today's repeats.
Prepared audio/world/mesh/collision/roof/
ownership/RNG/texture equivalence passes. Initial wake pixels, moving forest/fire/snow
and static overlook before/after RGB match exactly; four prepared/generated views
match exactly. Palette, actor skin, fauna, trees, vegetation reach/budget and draw/
shader cache checks pass. The earlier small-view fire CPU p99 **13.69 → 7.84 ms**
queue-bound result remains historical evidence in [the CPU-tail report](../performance-cpu-tails.json).

[All window rows, interval labels, flags, hashes and validation](../performance-frame-tails.json);
[full CPU/GPU/return stages](../performance-frame-tails-samples.json.gz). Raw captures and
interrupted development diagnostics remain under `build/frame-tails/`.
Helpers own one bounded render lock per run; **do not wrap them**.

```sh
python3 tools/cpu_tail_bench.py --output build/frame-tails/recheck --seconds 600 --views forest --trace
python3 tools/frame_tail_report.py --before build/frame-tails/before-trace/forest.log --after build/frame-tails/recheck/forest.log --output build/frame-tails/recheck-attribution.json
tools/run_all_checks.sh --only skin_row_check
```

## Round 81 contention audit

Four 180-second forest courses at 2133×1200, fixed 0.80 scale, native Wayland
mailbox, real production dt. `BOTW_CPU_TRACE_MS=10` retains stage wall/thread times
for CPU-heavy callbacks. All distribution figures below use complete two-second
windows after four seconds of warmup. Queue wait is excluded. "Ambient" adds no
workers but overlaps other CPU work on the shared machine; recovery is the later
no-worker run, not an artificially isolated machine.

| Run | Callback wall p50 / p99 / worst ms | Callback thread CPU p50 / p99 / worst ms | 15–26 ms wall callbacks using <8 ms CPU |
|---|---|---|---|
| Ambient | 8.99 / 16.13 / 61.11 | 4.46 / 8.29 / 17.16 | 192/247 |
| Seven CPU workers, preliminary | 10.05 / 21.65 / 63.30 | 5.58 / 7.96 / 18.52 | 1178/1252 |
| Recovery | 8.01 / 11.54 / 26.53 | 3.77 / 6.51 / 10.84 | 12/12 |
| Seven workers, identical recovery executable | 12.17 / 28.84 / 115.42 | 5.83 / 9.01 / 18.65 | 1917/2073 |

The controlled workers start only inside the game's render lock, have no window or
GPU context, and stop with the game. Interruption cleanup is verified. Thus this
experiment adds CPU contention without overlapping game renderers. The recovery
thread p99 matches the earlier idle **6.5 ms** result. The final worker run reuses
that recovery executable byte-for-byte, including recorded source hashes. With
code held constant, wall p99 rises **11.54 → 28.84 ms**, and thread CPU p99 rises
**6.51 → 9.01 ms**. CPU contention increases waiting and computation cost per
callback; slower frames also require more real-time simulation ticks.

The traces distinguish two effects. Most of the critic's 15–26 ms callback-wall
band can be reproduced while thread CPU stays below 8 ms: waiting or preemption
accounts for the excess, rather than 15–26 ms of game computation. Some real CPU
bursts remain. Every callback above 14 ms thread CPU in these four courses ran
**8–17 simulation ticks**. Ambient frame 4880 spends **70.615/15.201 ms wall/thread**
in platform event polling, then **17.454/17.160 ms** in the game callback with eleven
ticks. Its largest accumulated game stages are enemy update **1.367 ms**, enemy
animation **1.349 ms**, item elements **1.237 ms**, and camera **1.128 ms**. This is
catch-up across many small stages following the polling gap, not a single costly
asset or periodic task.

Preliminary contended frames 9837/9838 run sixteen/seventeen ticks and use **17.964/18.519 ms**
thread CPU. Item elements dominate their accumulated stages. The matched run
has three large CPU bursts with ten or fourteen ticks; accumulated enemy update
dominates, and the worst uses **18.654 ms** CPU. Recovery has no
callback above 14 ms CPU. No captured large CPU burst has an asset-loading stage.
The pinned runtime uses reference counting and per-thread free lists, rather than
a tracing GC; these traces provide no evidence of a garbage-collection pause.
They cannot prove which compositor/driver/scheduler operation caused each polling
or low-CPU wait. Raw stage totals leave 0.5–1.5 ms of callback bookkeeping and
profiling outside the named stages in the listed bursts.

[All four run distributions, source hashes and large CPU bursts](../../build/round81/cpu-diagnosis.json).
Complete logs remain in `build/round81/cpu-{idle,contended,recovery,matched-contended}/forest.log`.
The ambient probe was compiled before the coordinator's later combat additions;
camera, character and shrine source hashes differ across the preliminary probes.
Their changed paths concern combat/shrine views, while the forest route and its
timing protocol stay the same. Retained hashes make that qualification explicit.
These courses diagnose the reported contention rather than claiming a new
ten-minute performance baseline.

```sh
python3 tools/cpu_tail_bench.py --output build/round81/cpu-idle --seconds 180 --views forest --cpu-trace-ms 10
python3 tools/cpu_tail_bench.py --output build/round81/cpu-contended --seconds 180 --views forest --cpu-trace-ms 10 --cpu-workers 7
python3 tools/cpu_tail_bench.py --output build/round81/cpu-recovery --seconds 180 --views forest --cpu-trace-ms 10
python3 tools/cpu_tail_bench.py --executable build/round81/cpu-recovery/game --output build/round81/cpu-matched-contended --seconds 180 --views forest --cpu-trace-ms 10 --cpu-workers 7
```

## Round 81 startup and warmup audit

Fresh copies include all twenty ignored nature PNG inputs and run
`warm_assets.sh` before measurement. X11 1280×720, one captured frame, prepared
assets, warm local/driver caches, fresh process per repeat. Compilation, in-game
load and whole-process time are separate; lock queue wait is excluded. No shared
cache is flushed. All repeats and source hashes are retained.

| Snapshot | Repeats source / binary | Source load median (range) s | Binary load median (range) s | Source / binary process median s |
|---|---|---|---|---|
| Committed source base `db844da` | 3 / 3 | 1.86 (1.67–2.03) | 1.60 (1.58–3.80) | 3.50 / 1.79 |
| This round's presentation changes | 6 / 6 | 1.67 (1.56–3.58) | 1.71 (1.62–1.81) | 3.13 / 1.91 |
| Recheck after bounded body clearance | 3 / 3 | 1.70 (1.59–1.74) | 1.81 (1.66–2.18) | 3.22 / 2.01 |

The critic's **1.76 s median (1.63–1.94 s)** is consistent with these prepared
medians. The small before/after distributions overlap; there is no demonstrated
sustained startup regression to trim. All three snapshots pass the 3.5 s median
budget. The six-repeat snapshot has first-callback thread CPU medians
**4.076 / 4.653 ms**, independent compilation **2.145 s**. The last three-repeat
recheck has first-callback thread medians **4.904 / 5.352 ms**, compilation
**1.230 s**. Compilation timing varies independently of the in-game load metric.
The 3.80 s baseline outlier spans structures, water, vegetation and audio stages;
it is not dominated by render warmup. Later combat pose-history guards and
nearest-shoulder selection were added after these snapshots; they do not change
the opening's asset loading or warmup path. These are source-specific retained
measurements, not a claim that every final-source process was timed.

[Baseline repeats](../../build/round81/startup-before/summary.json) ·
[Six-repeat snapshot](../../build/round81/startup-final/summary.json) ·
[Bounded-clearance recheck](../../build/round81/startup-commitable/summary.json).
Prepared/generated world, audio, mesh, collision, roof, RNG and texture bytes
match. Opening, overlook, pond and shrine pixels match exactly.

A separate interleaved warmup probe reproduces the critic's long launch:
**7.10 s total, 5.531 s warmup**. Stage wall times are outdoor **3.211 s**, wet
terrain **1.492 s**, cave **0.423 s**, vegetation bindings **0.249 s**, character
bindings **0.095 s**; other warmup stages total about 0.06 s. A launch omitting
only the newer vegetation/character binding warmups still takes **7.03 s total,
5.436 s warmup**, with outdoor **3.516 s**, wet **1.487 s**, cave **0.377 s**.
Both report all **36 engine shader-cache hits** and identical first-frame pixels.
The next two interleaved pairs progressively settle: full/prior-binding totals
**6.11/5.36 s**, then **3.47/1.67 s**. By the third full run the newer bindings
cost **0.019 s combined**, while wet terrain still costs **1.477 s**.

This identifies existing outdoor/wet draws as the main observed warmup outlier,
not the newer binding loops. The probe measures wall time and shader-cache
requests; it cannot separate opaque driver specialization, GPU waiting and
scheduler contention. Sequential cache settling also prevents treating the paired
load difference as a causal cost of the added loops. Removing those loops would
sacrifice their verified protection against first-use gameplay stalls without
addressing the reproduced slow draws, so they remain. No toolchain or shader-cache
implementation is changed. [All stage rows](../../build/round81/warmup/summary.json)
and the scratch reproducer `build/round81/warmup_probe.py` retain this uncertainty.

A later 120-second forest budget recheck passes **57 complete windows**, none
above 20 or 17.5 ms. Callback wall p99 is **12.933 ms**, thread CPU p99 **7.436 ms**,
worst thread CPU **9.838 ms**. This shorter run does not supersede the historical
ten-minute all-window limitation above.

Earlier complete-input startup from 2026-10-11 measured source/binary load
**1.660/1.635 s**, process **3.120/1.830 s**, compile **1.400 s** (six per mode).
Three verified cold-local-file binary launches measured **2.910 s load / 3.140 s
process**, paired warm **1.700/1.890 s**. Only local prepared packs, shader binaries
and the executable were evicted; shared-library and driver caches remained warm.
These historical conditions differ from today's warm prepared audit and are kept
here for context, rather than repeated as the README's current startup headline.
