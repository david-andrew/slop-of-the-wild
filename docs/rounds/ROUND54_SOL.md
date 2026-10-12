# Round 54: camera, occluders, enemy contacts, noise cache

Baseline `046aeb3`; branch `sol/work`. Work is confined to the Sol worktree. Generated evidence is under `build/round54/` and is ignored by git.

## Occluders and climbing camera

Occluder coverage now uses actual fragment pixels instead of a fixed 853×480 screen grid. Both vegetation depth and architecture use the same full-resolution pattern. Retained faded fragments carry a negative HDR alpha marker; four existing watercolor taps detect it, resolve their already-computed quadrant means, and suppress ink/pigment around the coverage holes. There is no new render target, pass, sample fetch, or transparency sorting. Ordinary leaf cutouts and shadows keep their existing behavior. This is full-resolution coverage plus blur, rather than alpha blending.

The climbing camera evaluates nine foreground frustum rays in addition to the original three strips, and expands the mirrored tower-leg footprint near the lens. Side selection/hysteresis remains. Mid-boom visibility obstructions use the wider climbing fade instead of collapsing the camera at an adjacent wall edge; physical lens clearance remains. Outer tower supports fade across the frame while the central shaft is retained. No on-screen text or subtitles were added.

`camera_check` now covers adjacent climb faces, an upper beam missed by the center ray, overhangs, and a narrow architectural corner. Maximum per-frame camera movement: initial tower 0.131 m, release 0.183 m, continuous surface transitions 0.460 m. Stable settled views pass.

| Evidence | Before | After |
|---|---|---|
| Fixed trunk occluder, frame 360 | `build/round54/tree-before/tree.png` | `build/round54/tree-final/tree.png` |
| Tower climbing, frame 300 | `build/round54/before/climb300.png` | `build/round54/after/climb300-final3.png` |
| Tower climbing, frame 720 | `build/round54/before/climb-gpu.png` | `build/round54/paired/after/climb-gpu.png` |

The trunk fixture uses production vegetation and post passes, with a fixed camera and player pose. It is an occluder fixture, not a recreation of the critic's original swim screenshot. Its selected tree is at (-1266.82, 280.5514, 1381.88). Tower captures use `BOTW_SKIP=1 BOTW_TOWER=1 BOTW_AT=-560,1722,0 SLOPPY_INPUT=5:w+`.

## Animated enemy contacts

`enemy_contacts.jo` reads the actual monster skeleton, embedded club vertices, and the same slash/air-attack/punch clips used by the renderer. CPU socket/weapon tracks are baked once at 240 Hz and animation speed 1.3, without GPU resource allocation. The fitted club axis, attached weapon length, enemy build scale, facing, and frame movement produce the contact segment. Active intervals sample the swept arc and call production `blade_contact`, including cover. Shoves use the animated fist. The shared Bokoblin/blue Bokoblin/Stalkoblin path is covered; baseline `EKind` has no Moblin. The weapon radius/facing-only damage gates are removed; one-hit gating and guard, perfect guard, stun, and flurry rules remain.

The additional integration cases call production monster updates at 30/60/120 Hz for club, spiked club, spear, and branch. Twelve front cases each land exactly once; 48 beside/behind/above/cover cases miss; 12 defense cases preserve guard/parry/hop/backflip behavior. Running the same expanded suite against baseline source passes 256/280: all 24 beside/cover cases hit incorrectly. Final source passes **280/280**, removing **24/24** reproduced false contacts. The fauna perfect-guard fixture now places a carried club in actual contact, replacing its old radial-only setup.

## Noise memory and precision

The four-corner terrain hash cache is RGBA16F instead of RGBA32F: **128 MiB → 64 MiB**, still one fetch and the same coordinate rectangle/octaves. Explicit rounding to multiples of 1/2048 avoids driver-dependent half-store truncation. The maximum hash rounding error is 1/4096 = 0.000244140625; convex cubic interpolation cannot amplify it. The checker allows that bound plus 0.000001 for arithmetic differences and independently retains the original <0.000001 tolerance on the ALU fallback.

GPU readback: **131,072 samples**, including **26,545 cached samples**, maximum error **0.000244200**, fallback error **0.000000000**. Coverage/sentinel checks remain. Noise log: `build/round54/noise-final.log`.

## Performance and remaining presentation tail

GTX 1070; `BOTW_GPU=1 BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 BOTW_SKIP=1 BOTW_SCALE=0.8`, fixed 1/60 simulation. Requested X11 window 2133×1200, actual pixels 2246×1227, scene 1796×981. Each view runs baseline then final for 720 frames under one shared lock. GPU values are medians of subsequent completed 120-query batches, discarding the first; intervals use frames 241–720 (480 samples). GPU total sums instrumented passes, not elapsed presentation time.

| View | GPU total before → after | Terrain before → after | Post before → after | Interval p50 before → after | Interval p95 before → after | Worst before → after |
|---|---:|---:|---:|---:|---:|---:|
| Camp | 9.230 → 9.240 ms | 1.320 → 1.310 ms | 1.450 → 1.500 ms | 10.984 → 10.836 ms | 17.242 → 17.835 ms | 38.703 → 40.172 ms |
| Pond | 9.200 → 9.165 ms | 1.430 → 1.425 ms | 1.425 → 1.485 ms | 10.300 → 10.476 ms | 17.909 → 17.436 ms | 44.153 → 39.825 ms |
| Climb | 6.470 → 6.590 ms | 0.235 → 0.405 ms | 1.440 → 1.430 ms | 7.919 → 8.170 ms | 14.621 → 14.393 ms | 38.320 → 16.932 ms |

Ground-view GPU totals are effectively flat (+0.1% camp, −0.4% pond). **Climbing is +0.120 ms / +1.9%, so strict flat-or-better is not achieved for every view.** The changed climb view reveals more terrain; its terrain pass adds 0.170 ms while post drops 0.010 ms. Ground post adds 0.05–0.06 ms. These small costs are reported rather than hidden by a total-only comparison. Shared-machine scheduling and concurrent non-BOTW GPU work are uncontrolled.

An earlier separately queued run measured initial baseline/final GPU totals 8.625/9.125 ms camp and 8.810/9.185 ms pond, with increases across unchanged passes too. The immediate paired baseline above rises to 9.230/9.200 ms, supporting substantial run-to-run conditions as part of that apparent regression. Paired logs, images, environments, and full numerical report: `build/round54/paired/{before,after}/`, `build/round54/paired/comparison.json`. Compact numerical evidence is committed as `docs/round54-sol-numbers.json`.

The ~13–14 ms bimodal tail is **not fixed**. Frame logs localize it to the runtime's EGL presentation call. In baseline climb, 221 of the 480 steady intervals fell between 12 and 15 ms; their median game work was 2.753 ms and median presentation wait 10.601 ms. Camp's corresponding 171 intervals had 2.942 ms game work and 10.084 ms presentation. The fixed-size diagnostic reproduces the tail with only 3.33 ms instrumented GPU work.

| 1280×720 diagnostic | GPU median | Interval p50 / p95 / worst | Presentation p95 |
|---|---:|---:|---:|
| Mapped X11 | 3.330 ms | 7.983 / 14.009 / 16.495 ms | 11.594 ms |
| Same window unmapped | 3.325 ms | 8.305 / 13.910 / 16.523 ms | 11.755 ms |

Unmapping this process's newly-created window does not eliminate the wait. A driver sync override also left p95 at 13.706 ms mapped / 14.699 ms unmapped. EGL configuration reports minimum swap interval 0, maximum 1, and accepts setting 0. These experiments exclude a rejected interval-zero request and simple visibility-dependent composition as sufficient explanations; they do not uniquely distinguish driver queue, GPU, Xwayland, or compositor blocking. No ineffective driver override is shipped. Probe logs: `build/round54/present-probe/`, `build/round54/driver-unsynced/`, `build/round54/swap-probe.log`. Reusable diagnostic: `tools/frame_tail_probe.py`.

## Validation

All requested checks passed: `feel_test` (99.6/100 measured agreement, 29/29 behavior), `fauna_test` (0 failures; 18 windups, 0 overlapping blow frames), `element_test`, `element_check` (19), `save_test`, `architecture_test`, `contact_check`, `integration_test` (280/280), `slot_check`, `input_check` (26/26), `terrain_noise_check`, all four `shrine_route_check.sh` routes, all four `shrine_exit_check.sh` exits, `passage_check.sh`, `opening_check.sh`, and `late_story_check.sh`. Additional `camera_check` passes.

Passage reaches 4.8 m from the cave mouth at frame 760. Continuous opening passes without gameplay presets and returns control at frame 3700. Late story passes 16,443 assertions over 8,145 frames / 135.75 simulated seconds, earning four orbs and the paraglider before departure. Latest shader build and slot render pass. Ground/opening checks preceded the final support-mask and paint bookkeeping tweaks; those final shaders are exercised by the final slot and image/benchmark renders.

Logs: `build/round54/checks/`, `shrine-route-final.log`, `shrine-exit.log`, `passage.log`, `opening.log`, `late-story-final.log`, `slot-final.log`. Python syntax, shell syntax, and `git diff --check` also pass.

## Reproduction

```bash
sloppy/bin/sloppy build game/main.jo -o build/game-round54
sloppy/bin/sloppy tools/camera_check.jo
sloppy/bin/sloppy tools/integration_test.jo
flock /tmp/botw-render.lock sloppy/bin/sloppy tools/terrain_noise_check.jo
flock /tmp/botw-render.lock tools/occluder_check.sh build/occluder-check
python3 tools/terrain_bench.py capture build/game-round54 build/perf-round54 --views camp pond climb --modes gpu --frames 720
python3 tools/frame_tail_probe.py build/game-round54 build/presentation-round54
```

The benchmark and presentation probe lock their actual render processes internally. Opening locks itself; late story is headless. Do not wrap either story script in another lock.
