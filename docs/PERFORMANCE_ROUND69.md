# Round 69 — startup, sunken tower and resting stamina

Measured on 2026-10-14, unmodified Sloppy 0.6.0, i7-6700 / GTX 1070 on a shared
loaded desktop. All render/window runs own the shared render lock in bounded
batches. The final fixed critic pack is `build/task69-sol/final-v3-pack/`.

## Native startup

Exact canonical SPIR-V digests select 44 program recipes covering 50 observed
pipeline states. The default Vulkan cache retains its UUID/device checks.
Game-owned create-info storage stays alive while a tiny C helper compiles on up
to four real pthreads; only the calling Sloppy thread inserts returned handles.
The release Linux pool uses raw clone workers without independent libc TLS, so
it is unsuitable for driver calls. The rejected experiment and diagnostic logs
remain under `build/task69-sol/`. Sloppy itself is untouched.

Sky, mist, dome, character and post constructors queue alongside loaded programs before the
first warmup draw. Their geometry, materials and simulation are unchanged.
Existing upload-time handles are retained. Later warmup shader creation flushes
its own pending variants. Runtime draw lookup functions remain untouched.
Warm shared-cache hits take the
release runtime path without pthread preparation. Missing helpers and changed
shader digests fall back to normal pipeline creation. `BOTW_SERIAL_PIPELINES=1`
disables preparation. `tools/play.sh` and `tools/prepare_assets.sh` build the helper
atomically; Linux packages include it and need no compiler at play time.

1280×720, X11/Vulkan, full scene scale, prepared assets; fresh local Vulkan/NVIDIA
caches for cold, then the same directories for warm and changed-executable runs.
Page/system caches are not flushed. Lock wait is excluded.

| Launch | In-game load, s | Render warmup, s | Complete process, s |
|---|---:|---:|---:|
| Cold | 8.30 | 6.303 | 9.22 |
| Warm 1 | 2.30 | 0.238 | 3.20 |
| Warm 2 | 1.95 | 0.241 | 2.81 |
| Warm 3 | 2.77 | 0.354 | 3.73 |
| New executable, identical shaders | 2.26 | 0.460 | 3.10 |

The cold target is met. Warm median is 2.30 s; 1.5 s remains unmet. CPU contention
is retained rather than filtered (startup load averages around 14–15 on eight
hardware threads). Logs report each prepared-load stage, cache hit and shader
digest. Evidence: `final-v3-pack/startup/summary.json`, `recipe-summary.json`.

## Browser startup

Two isolated T3 browser tabs, local HTTP, 1280×800 viewport, production browser
scene scale 0.80/0.65. Browser/driver/page caches are not deliberately flushed.
First-frame readiness measures the producer's completed callback.

| Measurement | Before | After |
|---|---:|---:|
| First completed frame, s | 70.162 | 31.726 |
| Asset loading, s | 7.152 | 4.077 |
| Main wasm memory at readiness, MiB | 1113.688 | 974.375 |
| Reported errors | 0 | 0 |

The same Sloppy piano generator runs in a dedicated wasm worker while the main
thread builds the world and initializes graphics. All dynamics, registers and
cues are installed before frames begin. The worker transfers an exact compact
pack once and terminates. Foley directory entries/stamps preserve the common
audio fingerprint without moving Foley sample data. The independent CPU check
generates a fresh native reference under build and compares **all 154,190,108
bytes**, including its validation key. Main-wasm size is not total browser or
worker peak memory. Single loaded-machine repeats establish these observations,
not an isolated hardware speed guarantee.

The prepared world avoids the roughly eight-second baseline world-finalization
stage. Complete site size grows from 104.87 to 121.20 MB; compressed archives from
95.64 to 111.49 MB (seven archives). The 0.46 MB worker retains the compact mono
WAV downloads. Shipping the full stereo bank would add 101.82 MB compressed;
that option was rejected. Evidence: `browser-{before,after}.json`,
`web-{before,final}-package.json`, `worker-piano-summary.json`.

## Tower and HUD

The unraised crown protrudes above its buried collision courses; Jo can be
**grounded** inside its render-only skirt. Climb-only clearance missed that case.
A local body corridor clears the sunken crown and nearby world-chunk rubble,
retaining geometry beyond Jo and outside the ruin. Color clearance never removes
shadow casters. The matched route keeps the same weather seed 31, hour 11,
position, camera and production movement inputs.

The stamina wheel now has an explicit use/recovery/full-rest visibility gate.
Recent use keeps its brief return; full rest suppresses residual interpolation.
Climbing, gliding, sprinting and incomplete recovery keep the wheel visible.
No new in-game text was added.

## CPU and producer timing

Final fixed-dt pairs use the baseline at `cb21e87` and frozen `final-v3` sources.
Two adjacent before/after pairs per scene reverse order in the second pair.
1280×720, X11/Vulkan, scale 1.00, hour 11, clear weather, weather seed 31,
production inputs and 1/60 s simulation. Frames 361–720 supply **720 samples per
version/scene**. Every later tail is retained; manual captures occur at frames
120/300, before the measurement window. Binary hashes and exact frame sequences
are checked against each run's settings.

| Scene | CPU thread p99 before → after, ms | Producer p99 before → after, ms |
|---|---:|---:|
| Forest | 7.032 → 6.579 | 10.513 → 12.141 |
| Sunken tower | 5.444 → 5.321 | 12.713 → 13.403 |

CPU non-regression passes in both scenes. Producer intervals are worse in these
pairs; these observations do not establish improved delivery or scanout.
`pairs/summary.json` retains the final pooled values, and each scene directory
contains raw logs, settings, full PNGs and downscaled `compare-{120,300}.jpg`.

An earlier candidate retained a four-repeat tower CPU regression, 4.343 →
4.782 ms. It temporarily replaced the runtime pipeline lookup during warmup.
The final design prepares newly created shaders directly and never replaces
that draw lookup. Earlier candidate measurements remain under build; they are
not pooled into the final source comparison.

## Final verification

All **45 final fixed captures are byte-identical to master**. Every shot was
viewed downscaled, side by side; no new grid, dither, card edge, aliasing, black
blob, colour cast or repetition was introduced. The separate final tower route
was also viewed at frames 120 and 300. Evidence:
`visual-comparison-v3/{summary.json,page-01.jpg…page-15.jpg}` and
`pairs/tower/compare-{120,300}.jpg`.

The complete two-minute native route uses managed **2133×1200** output and the
production dynamic scene-scale policy, Vulkan immediate (driver mailbox fallback).
After the first 240 frames, all **9,587 samples** remain: producer/present-return
interval p99 **15.456 ms**, worst **33.549 ms**, **four intervals over 25 ms**;
callback thread CPU p99 **7.321 ms**. The route traversed **428.444 m** in
120.004 s. These are producer handoff measurements, not delivered scanout.
Evidence: `final-v3-pack/performance/{summary.json,route.log,route.jpg}`.

The **complete pack passed**: 45 verified captures, 120 s pacing, 13 audio clips
with dispatch scores, and all eight fast checks. Commands:

```sh
python3 tools/critic_pack.py --only captures build/task69-sol/final-v3-pack --capture-batch-scenes 8
python3 tools/critic_pack.py build/task69-sol/final-v3-pack --resume
```

Additional completed checks all pass:

| Check | Result | Evidence under `build/task69-sol/` |
|---|---|---|
| Full critic pack (feel/integration/input/opening/combat/weather/music/story) | 8 PASS | `final-v3-pack/checks/` |
| Prepared asset generation and complete equivalence | PASS | `v3-prepare.log`, `v3-prepared-check.log` |
| Warmup transitions and cached resolution coverage | PASS (52 → 52 pipelines) | `v3-warmup-check.log` |
| Independent wasm-worker/native pack, including key | PASS (154,190,108 bytes) | `independent-worker-check.log` |
| Pthread transport, stride, joined results and failures | PASS | `pthread-final-check.log` |
| Sunken-tower color clearance and retained shadows | PASS | `tower-final-check.log` |
| Full-rest/active/recovering stamina HUD | PASS | `hud-final-check.log` |
| Camera, presentation, integration and complete tower-base climb | PASS | `camera_check.log`, `presentation_check.log`, `integration_test.log`, `tower_base_climb_check.log` |
| Architecture and material-paint coverage | PASS | `architecture-final-check.log`, `material-final-check.log` |
| Final site build, JS/shell syntax, C warnings and diff whitespace | PASS | `final-web-build.log` |

All added headless checks are registered, one per line, in the runner's
`cpu_checks` array. No vendored Sloppy files changed, no build evidence is tracked,
and no push or merge was performed. Raw evidence is retained under build.

Remaining limits: the 1.5 s warm-start goal is unmet (final median 2.30 s). The
site adds about 16.3 MB for world preparation/worker overlap. Producer intervals
in the small fixed pairs increased despite lower CPU p99; scanout was not
measured. The single browser before/after repeats do not isolate driver/system
cache state or shared-machine contention.
