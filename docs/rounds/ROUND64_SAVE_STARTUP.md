# Round 64: save/reload, menu HUD and fresh-copy startup


Base `705cdf0`, `sol/work`, 2026-10-10. This addresses the Round 58 fresh-process
critic findings. Raw timing logs, samples and images stay under ignored `build/`;
only this summary and reproduction/regression tools are committed.

The static-mesh follow-up below uses starting baseline `293817a`, game sources `6f76ed5`,
and the 2026-10-11 timing batch. Its 1.60 s prepared median is the current result;
the original 5.07 s reproduction is retained as a historical baseline.

## Save/reload

Ordinary encounters save defeat by monster kind and home position, preserving
identity independently of enemy array indices. Reload restores zero HP and the
`gone` state without replaying corpse animations or producing duplicate drops.
Defeat is a milestone autosave. Respawn requires ten minutes of simulation with
Link more than 80 m away; the remaining timer survives saves and reloads and
continues ticking outside the normal 220 m AI range. Stalkoblins keep their
nightly lifecycle, and the Talus keeps its existing encounter/loot records.

Weather saves retain storm intensity, gust, wind, lightning pulse and transition
RNG state (including lightning scheduling) alongside time, weather target/timer,
clouds, rain and surface wetness.
Restore recomputes darkening, sky/ground ambient, sun, haze, directions and dawn
mist with a zero-time update. That update cannot consume a weather boundary or
random lightning event. Old version-1 saves remain readable: missing defeat
records mean no recorded defeats; missing weather integrators migrate to the
saved target's settled defaults. An old save cannot recover already-lost defeats.

`tools/encounter_weather_save_check.sh` launches two separate headless processes.
It kills a red Bokoblin through production damage, saves during its death, and
loads into a reordered placement list. It verifies the survivor, no revival near
Link, remaining-time persistence, ticking 300 m away, and eventual valid respawn.
Five weather cases compare all restored atmosphere values and the first resumed
simulation frame against uninterrupted values: settled storm, building storm,
clearing, an active lightning pulse and an imminent random weather boundary.
Different global game RNG seeds in the writer and reader cannot change the
weather/strike continuation. Malformed/duplicate records are rejected.
`save_test.jo` verifies defeat triggers the production milestone autosave.

## Menu and documentation

Inventory, Map and Options suppress the combat, ordinary HUD (including prompts,
pickups and location banners), shrine and story overlay layers. Paused data stays
intact for resume. The production draw route is instrumented by the existing
`menu_pause_check.sh` fixture: every menu frame must submit zero world layers,
and closing must restore all four. Existing timer/input pause checks remain.
`PLATEAU_LAYOUT.md` now documents the integrated Talus save/element hooks.

## Prepared static world meshes (`6f76ed5`)

Measured game sources **`6f76ed5`**, starting baseline `293817a`, 2026-10-11. The documentation-only
follow-up does not change the measured game tree.
The requested **median below 3.5 s passes**. Every launch is retained:

| Launch mode | Runs | In-game load median (range), s | Whole-process median (range), s |
|---|---:|---:|---:|
| Fresh copy, source command | 18 | **1.60 (1.52–1.67)** | **2.925 (2.79–3.10)** |
| Same copy, prepared executable | 6 | **1.575 (1.55–1.64)** | **1.76 (1.74–1.82)** |

Each launch hit all four new mesh/upload packs and **all 33 shader binaries**.
The preparation frame loaded in 1.58 s. Source-launch stage medians and ranges:

| Initialization stage | Median, s | Range, s |
|---|---:|---:|
| Prepared terrain read | 0.01 | 0.00–0.01 |
| Terrain upload/context/textures | 0.29 | 0.25–0.32 |
| Water read/upload | 0.02 | 0.01–0.02 |
| Farland read/upload | 0.01 | 0.01–0.01 |
| Structures read/upload/restore | 0.26 | 0.24–0.28 |
| Render warmup/GPU completion | 0.2795 | 0.260–0.319 |
| Enemy placement | 0.185 | 0.17–0.20 |
| Prepared world finish/header validation | 0.01 | 0.01–0.01 |

Stage medians are not additive. The water/farland/structures function names in
logs remain `*_build`, but valid packs now read/upload/restore their baked data.
Enemy placement and full render warmup remain runtime work.

The one-minute machine load average was **3.42–4.39** for source launches and
**3.10–3.30** for compiled launches. Desktop contention is uncontrolled; this is
below the prior baseline's 10.07 peak (its full range was 3.47–10.07). No scheduling, CPU-frequency,
driver, page-cache or quota settings were changed. The current batch meets the
requested target at its recorded load, without asserting identical contention
or a universal launch-time promise.

Water, farland and architecture now bake their complete vertex/index buffers.
Water also stores its exact render mask and waterfall feet/cells; farland stores
all four prop meshes and instance arrays, smoke/malice placement and RNG state.
Architecture includes the castle, cave, four shrine chambers, ordinary chunks,
named/moving meshes and cliff LODs. It stores culling bounds and original chunk
order, exact cliff triangles, colliders, both broad-phase grids, roof faces and
half-meter rain maps, mutable collider/roof ownership, cave zones, shrine entries,
camp/tower indices, ground dressing and the generation RNG continuation.
Terrain normal bytes and quadtree bounds are also baked, removing that CPU scan
from the upload stage. All eight ignored CPU packs total **504.4 MiB**.

Versioned headers contain an exact total byte size and cheap dependency stamps:
source/input file sizes plus nanosecond mtimes, with exact pad bits. Launch never
hashes the large source inputs or prepared payloads. Direct Linux reads populate
final native arrays; pointer-bearing records use explicit length-bounded fields.
Decode failures leave architecture state untouched, and stale/missing/truncated
packs retain production generation. Architecture depends on both farland and
waterfall generation stamps; prepared farland plus stale architecture also
reconstructs the castle before generating the remaining structures.
Reprepare after changing or copying inputs: these are local versioned packs.

Static uploads are flushed before the remaining placement/audio initialization,
allowing queued GPU work to run during that CPU work. The complete representative
render warmup and its final GPU-completion fence remain in the load timer. All
static content is ready before the first visible frame.

`tools/warm_assets.sh` produces every pack through `tools/prepare_assets.sh`, then
builds/warm-renders the production executable. `tools/prepared_assets_check.sh`
compares complete prepared/generated audio, aliases, RNG, terrain grids and
native mesh/physics records byte for byte. It also compares a mixed fallback
(prepared terrain/water/farland, stale architecture), probes restored collision
queries, and rejects stale headers, truncation, trailing data and unbounded
counts. `tools/prepared_frame_check.py` owns its render lock and verifies all
four mesh-pack hits; prepared and generated first-frame **pixels are identical**
at verified 1280×720 for the normal opening, overlook, pond and shrine.

### Current reproduction protocol and evidence

Run `python3 tools/startup_copy_check.py --ref 6f76ed5 --max-median-load 3.5`
(or `--ref sol/work` for this final branch). The probe archives a clean revision,
adds the required ignored height/water/edge/area inputs, performs a fresh `cp -r`
into `/tmp`, and runs `tools/warm_assets.sh` **in that copy**. Source terrain
symlinks retain their read-only targets. Prior build evidence and prepared CPU/
shader packs are excluded. No cache is flushed.

After preparation, one serialized `flock /tmp/botw-render.lock` batch runs 18
fresh source-command processes followed by six executable diagnostics. Each uses
verified physical **1280×720 X11 pixels**, scene scale **1.0**, no swap interval,
normal opening and one captured frame. `/usr/bin/time` runs inside the measured
lock and excludes lock wait; the game timer includes asset initialization,
representative render warmup and GPU completion. Process time additionally
includes compilation/runtime initialization, capture and shutdown. No repeats
are discarded, and no static content is streamed after the first frame.
`warm_assets.sh`, the timing batch and self-locking capture checks acquire their
locks separately, never nested. The current probe defaults to a 3.5 s median
budget and requires every new mesh/upload pack to hit. It still supports legacy
revisions without these packs when their historical budget is supplied explicitly.

Evidence is retained under `build/round64-mesh/startup-verified/`: summary JSON, all 24
individual logs/PNGs and the warm-assets log. Source and executable hashes are
recorded there. The measured executable SHA-256 is
`77da23203ae9650d8bd5d47ddc6b52858c834221dfcb81dc44f8eb697984394d`.
The first CPU-preparation attempt failed with `/tmp` **EDQUOT** before any game
launch, despite free filesystem space. Its logs remain in
`build/round64-mesh/startup-preparation-failure/`. The previous temporary startup
copy owned by this worktree was preserved in ignored `build/round64-mesh/` to
free quota, then the same `/tmp` protocol succeeded. No other worktree or global
settings were changed. The final `6f76ed5` batch itself has no failed/omitted runs. The earlier complete
`8676ce0` 18-source/six-binary batch remains under `build/round64-mesh/startup/`,
marked invalid because of the zero normal texture. The subsequent `e3ec80b` batch
was stopped after that bug was diagnosed: all 12 completed source runs and the
partial next launch remain under `build/round64-mesh/startup-final/`, with its
owned temporary copy preserved in ignored `build/`. Neither batch supplies the
final timing claim; no outliers were removed from the corrected batch.

### Current regression results

All 26 CPU/headless check commands pass: feel, fauna, elements, saves, input,
combat, camera, title handoff, journey control, traversal, architecture/contact,
opening logic, cliff/passage meshes, water coverage/map masks, encounter/weather
reload, all four shrine routes, late story, Talus save/element integration and
prepared-asset equivalence. The final dependency-header revision reran the
complete equivalence suite, including mixed fallback and restored physics.

The corrected continuous opening, five title approaches, passage, all four
shrine exits, slots, occluders and menu pause pass. Weather silhouettes pass
**all 12 cases** at the unchanged 0.10 floor; the lowest contrast is canopy
cloudy, **0.118**. All seven daylight sequences pass with 97 samples each:
dawn/dusk, forest dawn/dusk, snow dawn/dusk and pond dawn. Their largest brightness
steps are **7.4, 4.9, 2.7, 1.9, 8.0, 7.2 and 3.2** levels respectively.

Continuous weather also passes all four scenes. The cabin run logs **302**
samples through the arriving storm, shelter at frame **1400**, drying and
clearing (brightness **101 → 78** outside, **69 → 79** under the roof). Forest,
snow and shrine-exit each log **271** samples, with largest static brightness
steps **7.3, 5.5 and 7.2**. All **26** CPU/headless commands and **nine** rendered
suites pass on the corrected revision, alongside the startup budget and exact
first-frame comparisons.

The first mesh-bake implementation accidentally copied its terrain-normal array
before filling it. Both prepared and generated paths consequently uploaded zeros,
so their roundtrip and first-frame comparisons passed while the scene was wrong.
The canopy-storm regression and comparison with the original revision exposed it.
The fix fills the owning array before storing it. The final equivalence suite
also checks upward, approximately unit normals; a separate CPU comparison with
the original `293817a` upload algorithm passes byte for byte.

Corrected generated canopy captures match the original `293817a` **pixel for
pixel** in all four weathers, in visible/hidden/mask passes. At seed 31, canopy
storm measures **0.169039** silhouette contrast and **0.296658** paired separation,
with **5,142** body pixels, exactly matching the original. This comparison is
retained in `build/round64-mesh/weather-silhouette-corrected-generated/`.

The silhouette fixture now fixes weather RNG at **31**, already used by the
continuous-weather check, before the first simulation frame. Production weather
otherwise seeds from the wall clock, making storm comparisons uncontrolled.
The frame, twelve view/weather cases, 960×540 resolution, 0.8 scale and 0.10
contrast thresholds are unchanged. Final captures and their unchanged analysis
are retained separately from the diagnostic captures.

Current CPU/render logs and per-suite exit codes remain in
`build/round64-mesh/checks-verified/`; the final silhouette captures are in
`build/round64-mesh/weather-silhouette-verified/`. Exact first-frame comparisons
and verified pack hits are in `build/round64-mesh/prepared-frame-verified/`.
The original invalid captures and timing logs remain available as evidence of
the detected bug, rather than being used for the final performance claim.

## Original fresh-copy startup baseline (`705cdf0`)

The critic's roughly five-second prepared load is reproduced. **Do not use
3.2–3.3 s as a fresh-copy startup promise.** All repeats below are retained;
none is discarded as a cold run or scheduling outlier.

| Launch mode | Runs | In-game load median (range), s | Whole-process median (range), s |
|---|---:|---:|---:|
| Fresh copy, source command | 18 | **5.07 (3.40–5.78)** | **7.15 (4.74–8.04)** |
| Same copy, prepared executable | 6 | **5.18 (4.98–5.40)** | **5.48 (5.31–5.71)** |
| Resident directory, same executable, rebuilt identical packs | 3 | **5.31 (5.09–5.33)** | **5.61 (5.40–5.64)** |

The preparation frame loaded in 3.51 s. The first five measured source launches
also loaded in 3.40–3.57 s; later launches in **the same path, with the same
executable/source/input files** became slower. Every copy launch hit **all 32
shader binaries**, and terrain shader wait was 0.000 s throughout. The prepared
world-finish stage stayed around 0.1 s. This pattern does not support a
path-keyed shader miss, cold-copy page cache, or two-second pack-hashing cost as
the explanation for this batch.

Where the extra time goes, measured stage medians for source launches 1–5 versus
6–18 (the transition run remains included in the second group and overall table):

| Initialization stage | First 5, s | Remaining 13, s | Increase, s |
|---|---:|---:|---:|
| Terrain upload/context/textures | 0.49 | 0.84 | 0.35 |
| Water build | 0.41 | 0.67 | 0.26 |
| Farland build | 0.58 | 0.90 | 0.32 |
| Structures build | 0.71 | 0.97 | 0.26 |
| Render warmup | 0.271 | 0.404 | 0.133 |
| Enemy placement | 0.20 | 0.30 | 0.10 |
| Prepared world finish/validation | 0.09 | 0.11 | 0.02 |

Those increases are spread across geometry, texture/driver initialization and
warmup. The one-minute machine load average rises from 3.47 at the first source
launch to 10.07 at the eighteenth. This is a correlation with concurrent machine
load, **not proof of a specific CPU-frequency, scheduling or driver cause**;
wall-stage timers cannot distinguish those. Stage medians are not additive.
The six compiled launches remain around five seconds, so compilation cannot
explain the extra time *inside* the game's load timer. A separate release compile
probe measured 1.08 s; compilation plus initialization outside the timer, capture
and shutdown explains why the source command's total process time is larger.
No startup speedup or three-second guarantee is claimed.

An original-directory diagnostic with the identical copied executable initially
found stale resident CPU packs: 8.68 s median (8.27–10.10 s), despite 32 shader hits.
World finish and audio each regenerated for roughly one second. It is retained
as `resident-stale-packs` and is **not** included in either prepared row above.
After rebuilding byte-identical CPU packs, resident loads return to 5.31 s
median (table above), with all 32 shader hits. Changing the working directory
does not recover a three-second load under these conditions.

Evidence: `build/round64/startup/summary.json`, individual `source-*.log`,
`binary-*.log`, PNGs, `warm-assets.log` and `compile-probe.log`. The measured
executable SHA-256 is `b29983b6f8fcff56ccf06212dc43ab37f66a3487ff73073fdc34e367c43a9116`.
The archived game sources are exactly `705cdf0`; the save/HUD fixes in this
commit do not rewrite that frozen startup baseline.

Reproduce the historical baseline with
`python3 tools/startup_copy_check.py --ref 705cdf0 --max-median-load 5.75`.
Add `--resident-repeats 3` for the original-working-directory diagnostic; that
option rebuilds its CPU packs and requires byte-for-byte equality with the copied
packs before comparison. The world, SFX, piano and chime packs match in this run
(`build/round64/startup/pack-hashes.json`).
The tool exports that revision to a clean snapshot, includes the required ignored
height/water/edge/area inputs, uses a fresh `cp -r` into `/tmp`, then runs
`warm_assets.sh` there. Terrain input symlinks are preserved as `cp -r` preserves
them; their targets are read only. Historical build evidence and shader binaries
are excluded. Preparation generates CPU packs and warms shader binaries in that
fresh path before measurement. No page cache or driver cache is flushed.

The probe runs 18 source launches and six compiled-binary diagnostic launches at
verified physical 1280×720 X11 pixels, scene scale 1.0, no swap interval, normal
opening, one frame per process. It logs both the game's `loaded in` timer (asset
initialization through render warmup/GPU completion) and process wall time
(compilation/runtime initialization/load/one-frame capture/shutdown). `/usr/bin/time`
runs inside the measured `flock /tmp/botw-render.lock` batch, excluding lock wait.
Every render runs under exactly one lock; preparation and the measured batch
acquire separate locks without nesting. `warm_assets.sh` owns its lock.
Desktop load is uncontrolled.
Logs include stage timings, shader hits and source/executable hashes. Missing
Plateau encounters fail the probe instead of producing a misleading empty-scene
timing. The baseline probe used a prepared median-load budget of 5.75 s for
each launch mode; the current default is 3.5 s, and `--max-median-load` makes a tighter target explicit. Every
repeat, including outliers, remains under `build/startup-copy-check/`.

## Original Round 64 validation

**All 28 checks pass:** the usual 20 and the eight additional checks below.

The usual 20 checks are feel, fauna, element test/check, save, integration, input,
combat, camera, title handoff, journey controller, prepared-assets equivalence,
shrine routes, late story, traversal, slots, shrine exits, passage, opening and
occluder. Additional requested checks are status-save, menu-pause and continuous
weather transitions; new fresh-process encounter/weather and startup-copy probes
are permanent regressions. Architecture, contact and integrated Talus save/element
checks are also included. Individual results are retained in `build/round64/checks/`.

Continuous weather captures run the complete production entry point with weather
RNG seed 31 and fixed 60 Hz simulation. The cabin sequence passes 302 samples
through frame 3010, including shelter and drying; rendered brightness changes
101 → 79 in the open and 70 → 79 under the roof. Forest, snow and shrine exit each
pass 271 samples, with largest static brightness steps of 7.5, 5.5 and 7.2
respectively (limit 12). The shrine exit also preserves its black lift handoff.

## Round 71: verified cold local file pages

The earlier fresh-copy launches were warm after preparation. A rootless,
`mincore`-verified eviction of all eight local prepared packs, local shader
binaries and the compiled executable now measures **2.48 s median in-game load**
(**2.48–2.53 s**, three launches), versus **1.60 s warm** (**1.57–1.61 s**).
Whole-process medians are **2.67 s cold / 1.77 s warm**, with compilation and
lock wait excluded. Prepared mesh packs hit in every valid launch. Model/texture/source-input pages, shared libraries, kernel metadata and
GPU/driver caches remain warm; this is not a
whole-machine cold-cache result. [Protocol, limitations and every retained run](ROUND71_UI_PACING.md).
