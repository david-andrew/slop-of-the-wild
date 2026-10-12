# Round 53: terrain cost, frame tails, climbing camera

Baseline: `fac814a`, branch `sol/work`. Measurements: 2026-10-09, GTX 1070. Only terrain cost structure, render uniform plumbing, camera, frametime, and diagnostic tools changed. Snow/rock colours and boundaries are preserved.

## GPU results

Uncapped X11: `BOTW_GPU=1 BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 BOTW_SKIP=1 BOTW_SCALE=0.8`. Requested window 2133×1200; actual X11 pixel size 2246×1227, scene 1796×981. Both binaries used identical flags, positions and fixed 1/60 simulation steps. Every render held `/tmp/botw-render.lock`. The before executable was built from clean `fac814a` before editing.

Each main capture ran 720 frames. Values are medians of the five subsequent 120-query GPU batches after discarding the first batch. Frame-300 fire ran 300 frames and has one subsequent completed batch. Total is the sum of instrumented GPU passes, not a CPU frame interval.

| View | Terrain before → after (ms) | Reduction | GPU total before → after (ms) |
|---|---:|---:|---:|
| Grass fire, frame 300 | 2.55 → 1.67 | 34.5% | 11.32 → 10.51 |
| Grass fire, frame 720 | 2.66 → 1.77 | 33.5% | 11.52 → 10.68 |
| Snow | 5.76 → 3.20 | 44.4% | 11.20 → 8.27 |
| Camp | 1.95 → 1.35 | 30.8% | 9.46 → 8.89 |
| Hopper Pond | 2.01 → 1.39 | 31.0% | 9.29 → 8.69 |
| Overlook | 4.52 → 2.74 | 39.4% | 10.75 → 8.96 |

**Snow remains 0.20 ms above the requested 3 ms target.** The fresh baseline fire capture was 11.32 ms total at frame 300, so this comparison does not reproduce or replace the critic’s 16.73 ms capture. Shared-machine conditions and exact output dimensions matter.

## Work removed without approximating colour

Distance gates reuse the existing smooth fades: gaps stop after 60 m, individual litter leaves after 45 m, rock cracks after 90 m, snow glitter after 12 m. Their original interpolation and fade weights remain. No new visual LOD transition is introduced. Full snow or rock skips covered material layers; zero moss, paving and canopy coverage skip their unused noise. Snow colour, grass/rock rag noise, and the unperturbed face-height sample are reused instead of recomputed.

A terrain-only RGBA32F integer hash lattice replaces four ALU `hash12` evaluations per in-range `vnoise` with one `texelFetch`. It stores all four corners per texel for floor-coordinate x in [−1024,1024), y in [0,4096). Original octave coordinates, full float precision, cubic interpolation, and mix order remain. Outside the rectangle, or if the framebuffer cannot be created, the shader uses the original arithmetic. The cache stores noise hashes rather than material colours, so boundary-colour edits do not require changing it.

Tradeoff: **128 MiB of additional VRAM**, plus one startup bake. A newly compiled terrain shader had a 3.31 s terrain-upload measurement; subsequent driver-cached loads measured about 0.23 s for terrain upload. These are startup costs, not included in steady GPU results. The GLSL substitution is confined to terrain FS and relies on the current generated `f_vnoise_` function and uniform naming. The equality checker exercises that integration.

A vertex approximation was avoided because it would change the crack, relief and snow signals. The exact lattice cache addresses ALU cost while preserving those signals.

## Distance-band profile

Diagnostic variants shade only the selected distance band and draw constant colour elsewhere. 360 frames each, same X11 size and scale; first GPU batch discarded. Table subtracts each view’s flat terrain probe (snow/camp 0.05 ms, fire 0.02 ms). These estimates are not additive because branching changes SIMD execution. Diagnostic images are not visual evidence.

| View | 0–30 m before → after | 30–90 m before → after | ≥90 m before → after |
|---|---:|---:|---:|
| Snow | 3.63 → 2.30 ms | 2.84 → 1.46 ms | 0.27 → 0.15 ms |
| Camp | 1.55 → 1.13 ms | 0.48 → 0.38 ms | 0.43 → 0.28 ms |
| Fire | 2.25 → 1.48 ms | 0.09 → 0.08 ms | 0.36 → 0.28 ms |

Actual per-fragment semantic call counts are captured separately at frame 300; counter instrumentation timings are not performance evidence. `vnoise` counts include the octaves inside `fbm3`; the exact cache reduces the cost of each call as well as the number of calls. Component and sample counts follow below.

| View / distance | fbm3 | vnoise | rock colour / rock normal / face normal | snow amount / colour / normal | cold UV | canopy reads / material reads |
|---|---:|---:|---|---|---:|---|
| snow 0–30 m | 18.000 → 15.844 | 87.000 → 71.816 | 1.000 → 0.884 / 0.000 → 0.000 / 0.000 → 0.000 | 1.000 → 1.000 / 2.000 → 1.000 / 1.000 → 1.000 | 1.000 → 1.000 | 2.000 → 2.000 / 3.000 → 3.000 |
| snow 30–90 m | 18.341 → 12.231 | 88.290 → 54.789 | 1.000 → 0.499 / 0.015 → 0.015 / 0.000 → 0.000 | 1.000 → 1.000 / 1.984 → 0.992 / 0.991 → 0.991 | 1.000 → 1.000 | 2.418 → 2.418 / 3.000 → 3.000 |
| snow ≥90 m | 18.000 → 7.000 | 83.000 → 32.000 | 1.000 → 0.000 / 0.000 → 0.000 / 0.000 → 0.000 | 1.000 → 1.000 / 2.000 → 1.000 / 1.000 → 1.000 | 1.000 → 1.000 | 2.000 → 2.000 / 3.000 → 3.000 |
| camp 0–30 m | 6.042 → 5.042 | 25.210 → 20.269 | 0.000 → 0.000 / 0.000 → 0.000 / 0.000 → 0.000 | 1.000 → 1.000 / 0.000 → 0.000 / 0.000 → 0.000 | 0.000 → 0.000 | 2.000 → 2.000 / 2.000 → 2.000 |
| camp 30–90 m | 6.564 → 5.564 | 29.612 → 24.791 | 0.000 → 0.000 / 0.000 → 0.000 / 0.000 → 0.000 | 1.000 → 1.000 / 0.000 → 0.000 / 0.000 → 0.000 | 0.000 → 0.000 | 2.028 → 2.028 / 2.000 → 2.000 |
| camp ≥90 m | 10.399 → 7.669 | 48.291 → 33.612 | 0.658 → 0.658 / 0.000 → 0.000 / 0.471 → 0.471 | 1.000 → 1.000 / 0.000 → 0.000 / 0.000 → 0.000 | 0.000 → 0.000 | 2.000 → 2.000 / 2.000 → 2.000 |
| fire 0–30 m | 21.000 → 20.000 | 86.000 → 81.000 | 1.000 → 1.000 / 1.000 → 1.000 / 0.000 → 0.000 | 1.000 → 1.000 / 0.000 → 0.000 / 0.000 → 0.000 | 0.000 → 0.000 | 2.000 → 2.000 / 2.000 → 2.000 |
| fire ≥90 m | 7.214 → 6.209 | 34.169 → 26.951 | 0.003 → 0.003 / 0.000 → 0.000 / 0.002 → 0.002 | 1.000 → 1.000 / 0.000 → 0.000 / 0.000 → 0.000 | 0.000 → 0.000 | 2.000 → 2.000 / 2.000 → 2.000 |

Averages are per visible terrain fragment in each band (before → after). No middle-distance fire fragments were visible. Function columns count calls, not the amount of work inside their branches. The unchanged cold/material/canopy counts show that the cache and branch work preserve those lookups; snow colour reuse halves its calls.

Static call-site upper bounds, including nested functions (branches make actual counts smaller):

| Function | vnoise before → after | fbm3 before → after |
|---|---:|---:|
| `cold_uv` | 6 → 6 | 2 → 2 |
| `meadow_color` | 11 → 11 | 3 → 3 |
| `rock_color` | 28 → 28 | 6 → 6 |
| `terrain_albedo` | 44 → 36 | 8 → 7 |
| `snow_amount` | 12 → 12 | 4 → 4 |
| `snow_color` | 5 → 5 | 0 → 0 |
| `rock_normal` | 33 → 33 | 9 → 9 |
| `face_normal` | 6 → 4 | 0 → 0 |
| `snow_normal` | 6 → 6 | 0 → 0 |
| `terrain_fs` | 161 → 151 | 32 → 31 |

`face_normal` now takes the shared centre-height value: its four remaining noise reads are the two offset samples, with two centre-height reads computed once by the caller. The upper-bound FS total falls from 161 to 151 noise calls and 32 to 31 fbm calls; visible snow fragments save substantially more through branch gating.

Normals and burn maps retain one sample each. Material processing retains the base material sample, coarse mip-6 cold-presence test, and conditional warped mip-3.5 cold read. `cold_uv` remains two fbm calls / six noise calls when that read contributes. Canopy material modulation retains its mip-2 lookup; near dapple and distant canopy shadow retain their original lookups and distance blend. Only zero canopy coverage skips dapple noise. Rock and snow normal detail are preserved at all distances.

## Image comparison

Full output RGB differences, same frame, position and simulation. Snow, fire, camp and pond were inspected side by side; snow relief, boundaries, lighting, fire, grass, and water have no visible change. Overlook differences are also below visibility. Climb is an intentional camera change and is excluded from terrain equality.

| Image | RGB MAE (0–255) | Maximum channel difference | Changed channels |
|---|---:|---:|---:|
| fire300-gpu | 0.000000000 | 0 | 0.00000000% |
| fire-gpu | 0.000000000 | 0 | 0.00000000% |
| camp-gpu | 0.000000000 | 0 | 0.00000000% |
| pond-gpu | 0.000000000 | 0 | 0.00000000% |
| snow-gpu | 0.000003266 | 1 | 0.00032658% |
| overlook-gpu | 0.000001089 | 2 | 0.00008467% |

99th-percentile channel difference is zero in every terrain comparison. `terrain_noise_check.jo` read back 131,072 full-precision GPU samples, including lattice boundaries and out-of-range fallbacks: maximum cached/reference error **0.000000000**. It clears to a failure sentinel and checks coverage so an empty draw cannot pass.

Canonical before/after image paths (absolute paths are valid in this worktree):

| View | Before | After |
|---|---|---|
| fire300 | [PNG](/var/home/david/dev/botw-clone-sol/build/perf53/verified-before/fire300-gpu.png) | [PNG](/var/home/david/dev/botw-clone-sol/build/perf53/verified-after/fire300-gpu.png) |
| snow | [PNG](/var/home/david/dev/botw-clone-sol/build/perf53/verified-before/snow-gpu.png) | [PNG](/var/home/david/dev/botw-clone-sol/build/perf53/verified-after/snow-gpu.png) |
| camp | [PNG](/var/home/david/dev/botw-clone-sol/build/perf53/verified-before/camp-gpu.png) | [PNG](/var/home/david/dev/botw-clone-sol/build/perf53/verified-after/camp-gpu.png) |
| pond | [PNG](/var/home/david/dev/botw-clone-sol/build/perf53/verified-before/pond-gpu.png) | [PNG](/var/home/david/dev/botw-clone-sol/build/perf53/verified-after/pond-gpu.png) |
| overlook | [PNG](/var/home/david/dev/botw-clone-sol/build/perf53/verified-before/overlook-gpu.png) | [PNG](/var/home/david/dev/botw-clone-sol/build/perf53/verified-after/overlook-gpu.png) |
| climb | [PNG](/var/home/david/dev/botw-clone-sol/build/perf53/verified-before/climb-gpu.png) | [PNG](/var/home/david/dev/botw-clone-sol/build/perf53/verified-after/climb-gpu.png) |

Full logs and numerical comparison: `build/perf53/verified-{before,after}/`, `build/perf53/comparison.json`; band profiles: `build/perf53/profile/profile.json`; count profiles: `build/perf53/components-verified/profile.json`. These generated artifacts are ignored by git.

## Camp and Hopper Pond frame tails

Raw samples use frames 241–720 (480 intervals). `frametime.jo` keeps every old column and appends runtime-gap voluntary/involuntary context switches and user/system CPU time. Intervals label the previous game update/draw plus the runtime gap up to the next begin. `present_ms` is the separately measured runtime present call.

| Capture | p99 interval before → after | Worst interval before → after |
|---|---:|---:|
| Uncapped X11 + CPU probes, camp | 16.966 → 17.002 ms | 33.990 → 23.644 ms |
| Uncapped X11 + CPU probes, pond | 21.392 → 17.725 ms | 62.410 → 22.590 ms |
| Normal paced Wayland + CPU probes, camp | 24.630 → 18.004 ms | 60.962 → 33.329 ms |
| Normal paced Wayland + CPU probes, pond | 18.410 → 18.631 ms | 30.297 → 40.281 ms |

Normal paced runs use the game’s default window: actual 2133×1200, render scale 0.8, `wayland+libdecor dma-buf`, output scale 1.667. They deliberately omit `BOTW_NOVSYNC` and `SLOPPY_PLATFORM`. Do not compare their timings directly with X11 GPU query totals.

Representative worst intervals:

| Capture / interval | Total | Game wall | Present | Other gap |
|---|---:|---:|---:|---:|
| before pond cpu, 376 | 62.410 | 4.436 | 57.859 | 0.115 |
| before camp paced, 266 | 60.962 | 5.967 | 54.883 | 0.113 |
| after camp paced, 399 | 33.329 | 6.781 | 26.380 | 0.168 |
| before pond paced, 621 | 30.297 | 14.506 | 15.440 | 0.351 |
| after pond paced, 588 | 40.281 | 4.176 | 35.962 | 0.143 |

The large 45–62 ms baseline intervals are predominantly blocked in presentation, not one terrain-upload or game-update spike. Final normal-paced camp and pond worst gaps consumed only 0.542/0.590 ms of thread CPU, with six voluntary and zero involuntary switches. That is consistent with waiting in the graphics/presentation stack; game-level logs cannot uniquely separate GPU queue, compositor, or driver blocking. Pond’s paced p99 and worst interval **did not improve**, so presentation tails remain unresolved.

Pond also has real 12–14 ms game CPU excursions: the baseline worst paced interval includes 14.506 ms game wall / 13.898 ms thread CPU. Its preceding long-CPU probe reports vegetation drawing 2.5 ms, vegetation culling 1.2 ms, monsters 1.0 ms, shadow0 0.7 ms, hero drawing 0.7 ms, shadow vegetation culling 0.7 ms. Final long-CPU probes show costs spread similarly across vegetation, characters and shadows, rather than a single new 40–50 ms game section. Instance uploads remain around 13–16 calls / 23 KiB at Pond.

Normal-paced camp mean game wall time varied from 3.278 to 6.068 ms, with broadly higher costs across CPU sections; uncapped after camp mean remains 3.454 ms. These runs were on a shared machine. The logs support CPU throughput/scheduling variability, but do not establish its exact system-level cause. No claim is made that a CPU optimization was delivered.

An early paced experiment explicitly requested a logical 2133×1200 Wayland window, which became **3743×2045** actual pixels. Those oversized stress logs are retained separately in `before/` and `final-gpu/` and excluded from the normal paced table. Baseline Pond’s 50.294 ms interval had 43.125 ms present; baseline camp’s 43.459 ms had 33.727 ms present. The after camp stress capture still hit 93.877 ms, of which 87.591 ms was present (0.908 ms runtime-gap thread CPU, 12 voluntary / zero involuntary switches). The terrain change does not cure that stress tail.

## Climbing camera

A camera-only swept footprint detects grazing pillars. Four splayed tower leg segments mirror render geometry and current tower lift without altering player collision. While climbing, the camera considers nearby yaw offsets, retains its chosen side with hysteresis, immediately shortens a blocked boom, and smoothly restores distance. It waits 0.6 seconds of straight-ahead clearance before releasing the offset and returns smoothly after leaving the wall.

At the reproduced tower climb (`BOTW_TOWER=1 BOTW_AT="-560,1722,0" SLOPPY_INPUT="5:w+"`, frame 720), the baseline hides Link behind the leg. The final camera swings −0.636 rad (36.4°), boom 6.543 m, making Link fully visible at the same player position. The camera regression covers a grazing thin pillar, inactive collider, render-only tower legs, settled stationary climbing, and release. Maximum initial camera step 0.131 m; release step 0.122 m; stationary drift below 0.01 m.

## Validation

All requested checks passed: `feel_test`, `fauna_test`, `element_test`, `element_check`, `save_test`, `architecture_test`, `contact_check`, `integration_test`, `slot_check`, `shrine_route_check.sh`, `shrine_exit_check.sh`, `passage_check.sh`, `opening_check.sh`, `late_story_check.sh`. Additional `camera_check` and full-precision `terrain_noise_check` passed. Final game build, Python compilation, and `git diff --check` passed.

Feel: 99.6% measured/reference agreement, 25/25 behaviour gates. Integration: 125/125. All four shrine routes and exits passed. Passage: 4.8 m from cave mouth at frame 760. Continuous opening passed without gameplay presets. Late story: 16,443 assertions / 8,145 frames / 135.75 simulated seconds, ordered shrines → temple → glider departure, no progress presets. Logs: `build/perf53/checks/`.

Reproduce with the repository’s pinned Sloppy toolchain:

```bash
sloppy/bin/sloppy build game/main.jo -o build/game-after
python3 tools/terrain_bench.py capture build/game-after build/perf/after
python3 tools/terrain_bench.py compare build/perf/before build/perf/after
python3 tools/terrain_profile.py --baseline fac814a --views snow camp fire
python3 tools/terrain_profile.py --baseline fac814a --counts-only --views snow camp fire --output build/terrain-counts
sloppy/bin/sloppy tools/camera_check.jo
flock /tmp/botw-render.lock sloppy/bin/sloppy tools/terrain_noise_check.jo
```
