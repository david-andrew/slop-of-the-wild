# Round 69 sol2: gate follow-ups after 901b3d5

## Changes

- The fuel-edge sheet has unequal animated peaks inside a taller transparent
  envelope, with a broader fade into ground glow. It now includes boundaries
  beside spent fuel and isolated live cells. Its lower connecting mass blends
  in from 4.5–7 m; the cited grass-fire 150/260 views contain visible flames
  roughly 6–17 m from the camera. The existing upper tongues keep their shape. At 30–80 m
  the full sheet remains active, with the existing 80–90 m distance fade.
  A lower mass also joins the existing tongues where terrain hides that outside
  contour. It uses the soft live-fuel perimeter while upper crowns retain their
  original footprint. Very compressed cards retain the earlier no-bar guard;
  grazing contour segments fade before becoming thin vertical needles.
- Cooking-fire logs use three gently curved round sections with shaded bark,
  circular cut ends and short, irregular glowing fissures following the surface.
  The dark spherical log ends that formed the small bottom-centre blob are gone.
- The burning-character light is centred on the torso above the belt. Its
  existing distance attenuation now shades the hanging cloth toward the hem.
  The actual production source is shared with the headless falloff check.

## Validation

Evidence is under `build/task69-sol2-followup/`. The baseline fixture and all
45 master captures are frozen from `901b3d5`; source identity was checked
against that commit. Final fixture sources and hashes are recorded in
`source-verification.json`.

All 14 final-source targeted checks passed (`checks-v6/`):
`task69_fire_check`, `task68_fire_check`, `round91_fire_check`,
`round83_fire_check`, `round67_fire_check`, `round80_fire_check`,
`round66_fire_material_check`, `fire_test`, `element_test`, `cooking_check`,
`combat_check`, `round88_material_check`, `weather_shading_check`, and
`art_shade_test`.

`tools/prepared_assets_check.sh` (including `tools/prepare_assets.sh`) passed
on these sources. `prepared-assets-v6.log` records complete prepared/generated
mesh, collision, ownership, RNG, texture and combat-socket equivalence.

The extended registered `task69_fire_check` covers the broad transparent
contour foot/top, the actual production source's cloth falloff, and connected
near roots above terrain-occluded contours. The existing compressed-card
no-bar guard in `task68_fire_check` remains intact.

Six matched 30/60/80 m views at frames 200 and 260 were personally viewed in
`distance-comparison/`, using `distance-master/` and `distance-v6/`.

## CPU p99

The initial three alternating AB/BA pairs use fixed 1280×720 Vulkan, scale 1,
seed/hour/weather/input/dt, CPU 2, 240 warmup frames, nearest-rank per-run p99
and median of three runs. No measured-frame screenshots or removed outliers.
The existing gate is `after <= before × 1.03 + 0.10 ms`.


| Scene | Thread p99 before → after (ms) | Thread gate | Wall p99 before → after (ms) | Wall gate |
| --- | ---: | --- | ---: | --- |
| night | 9.194 → 9.169 | PASS | 9.902 → 13.664 | FAIL |
| camp | 10.668 → 10.841 | PASS | 15.379 → 18.281 | FAIL |
| grass-fire | 6.074 → 6.128 | PASS | 11.937 → 10.877 | PASS |
| tent-fire | 11.510 → 11.478 | PASS | 15.276 → 17.378 | FAIL |
| body-fire | 5.912 → 6.183 | PASS | 10.272 → 11.100 | FAIL |

All five thread-CPU gates pass. The initial overall wall/thread script exits
FAIL because four wall-time gates fail; its unfiltered samples and summary
are retained in `bench-v6/` and `bench-v6.log`.

The diagnostic night pair in `trace-night/` enables CPU-stage and GPU-pass
logging. Wall p99 is 11.193 → 34.318 ms while thread p99 is 9.906 → 10.073 ms.
GPU FX is about 0.044 ms in both binaries, and total GPU work stays about
7.4–7.6 ms. The wall-minus-thread spikes occur in unchanged CPU skinning,
collision and vegetation stages, with no queue-fence waits in the traced tail.
Heavy unrelated CPU workloads were active on the shared machine. This is
consistent with scheduling contention rather than added fire rendering cost.
The trace is diagnostic and is not substituted for the ordinary CPU gate.

The longer confirmation keeps three AB/BA pairs, CPU 2 and the same frozen
binaries, with 1800 frames per run and 240 warmup frames. Each pair owns a
bounded render-lock batch. It also exits FAIL (`bench-confirm/`):

| Scene | Thread p99 before → after (ms) | Thread gate | Wall p99 before → after (ms) | Wall gate |
| --- | ---: | --- | ---: | --- |
| night | 9.075 → 9.158 | PASS | 15.606 → 25.570 | FAIL |
| camp | 9.820 → 10.332 | FAIL | 10.977 → 11.733 | FAIL |

The longer camp thread result exceeds its 10.215 ms budget by 0.117 ms. This
contradicts a clean performance clearance; the ordinary five-scene thread
suite alone must not be presented as the complete performance result.

A final bounded scheduler-observed night pair (`scheduler-night/`) uses
1200 frames and the ordinary renderer flags, without CPU/GPU tracing. It
passes the numerical wall/thread comparison: wall p99 10.565 → 10.869 ms;
thread p99 9.092 → 8.971 ms. Over the monitored 840 frames, process CPU runtime
is 7.908 → 7.839 s and elapsed time is 8.445 → 8.482 s. Raw scheduler samples,
context-switch counters, environments and binary hashes are retained. This
single diagnostic pair supports contention as an explanation but does not
replace the failed three-pair gates.

Unresolved: performance clearance on a quieter machine. The short suite's
four wall gates and the longer camp thread/wall gate remain failed results.
No samples were removed and no further repetitions are used to select a pass.

## Final visual review

`final-pack-v6/` contains all 45 final-source captures. Every shot was personally
viewed, downscaled and side by side with both the fresh `901b3d5` master pack
and `/tmp/crit69pack/captures` in `visual-review/page-01.jpg` through
`page-15.jpg`. `visual-review/reviewed.json` records the viewed pages and exact
final PNG hashes.

- `master-comparison/`: 45 paired views against `901b3d5`, at 640×360 per image.
  39 shots are RGB-identical. Only night 300, grass-fire 150/260/600, tent-fire
  900 and body-fire 300 change. All four approved camp frames remain identical.
- `shared-master-comparison/`: all 45 comparisons against the shared older
  pack. Five are identical (wake and the four shrines). Other differences
  outside the six intended shots are already present in the `901b3d5` baseline.
- `distance-comparison/`: all six personally viewed 30/60/80 m pairs.
- `audit-views/`: matched downscaled crops of the final background sheet,
  round cooking logs and shaded cloth against `901b3d5`.

No new grid, dither, hard card edge, unrelated colour cast, aliasing or black
blob was identified in the final self-review. The advancing edge is connected,
its peaks vary, cooking logs retain round lit volume and short irregular cracks,
and the cloth shades toward the hem. The approved ordinary camp fire is intact.

The explicit final-tree capture audit passed:

```sh
python3 tools/critic_pack.py --only captures build/task69-sol2-followup/capture-audit --resume
```

The audit copies the completed final pack, then revalidates its sources,
fixture, scene settings, all 45 shot names and PNG hashes. It retains those
fresh captures rather than rerendering them. Relevant audit fire 150/260/600,
tent background/logs, body cloth, night and camp 640 images were viewed again.
`capture-audit.log` records `PASS retained 45 matched captures`.

## Full pack

```sh
python3 tools/critic_pack.py build/task69-sol2-followup/final-pack-v6
python3 tools/critic_pack.py build/task69-sol2-followup/final-pack-v6 --resume --capture-batch-scenes 8
```

Status **PASS**: 45 captures, startup probes, the native 2133×1200 real-time
120-second route, 13 audio clips/scores and all eight fast checks.
Cold/warm-median/new-build startup is 10.64/2.12/2.22 s. Native frame-interval
p99 is 17.405 ms over 10,223 steady samples; five intervals exceed 25 ms.
Presentation uses immediate mode (driver mailbox fallback).

The first process exited 143 after 17 completed captures. No game sources
changed. The supported resume retained their exact hashes and completed all
remaining sections, with bounded eight-scene/approximately 60-second capture
batches. The prior interrupted wall duration is estimated from the first
fixture build log's timestamp and marked as estimated in the manifest.
The reported total is approximately 2,045.8 s, including 1,443.4 s waiting
for the render lock. Its under-25-minute wall-time flag is false; time excluding
recorded lock waits is about 602.5 s. Full log: `final-pack-v6.log`.

All game/window runs used the shared render lock in bounded batches; no nested
locks or vendored Sloppy edits were introduced. Simulation and gameplay RNG
are unchanged. Superseded probes and interrupted earlier packs are diagnostic
history, not the final evidence.

## Handoff

The four visual follow-ups are implemented and committed for independent gate
review. Performance clearance remains unresolved: the failed ordinary wall
gates and longer camp CPU gate require verification on a quieter machine.
This change is not represented as having a clean CPU performance gate.

