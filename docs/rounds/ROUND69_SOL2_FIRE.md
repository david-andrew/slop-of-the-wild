# Round 69 sol2: visual-gate follow-up

This report supersedes the earlier report for rejected commit `195491b`.
Final evidence is under `build/task69-sol2-revision/`.

## Changes

- Grass fire has an additional low emissive sheet along the outside fuel
  contour. Adjacent segments overlap with soft ends and shared world-space
  crests; the existing tongues supply taller silhouettes. The sheet blends
  in from 12–22 m, remains active through 80 m, and fades out by 90 m.
  It skips enclosed cells and boundaries beside spent ash. Roots are bounded
  and feathered where a neighbouring cliff cannot support them. The existing
  ground halo supplies a stronger warm glow at distance.
- Ordinary fire smoke receives no added warm particle tint, and grass smoke
  uses neutral grey pigment. The pink/salmon column and muddy brown tree haze
  are removed. Shrine 2's final image is RGB-identical to master, including
  the brazier smoke where the orange blob appeared.
- Cooking fires use round charcoal logs with dark end caps and narrow
  emissive cracks. Whole-log emission is removed from these logs. The approved
  night pot lighting remains in place.
- Burning enemies retain the approved articulated flame coverage. Their
  scoped point light has a smaller radius and restrained colour/intensity;
  the whole-body burn veil is reduced. Painted material and shaded limbs
  remain visible, with stronger light near the torso flames.
- The approved bare camp bonfire, its glowing logs, and the night iron light
  are preserved. Chemistry, fuel lifetime, gameplay RNG, terrain, colliders,
  and the vendored Sloppy release are unchanged.

## Visual evidence

All captures use the existing matched fixtures: weather seed 31, fixed
hour/weather, camera/input settings and 1/60-second simulation, 1280×720 Vulkan
at scale 1. Images were downscaled before inspection.

- `final-pack-v9/`: fresh full pack, including all 45 final shots.
- `master-comparison/`: all 45 shots paired with `/tmp/crit69pack/captures`,
  at 640×360 per image; 15 comparison pages, all personally viewed.
- `visual-review.json`: viewed shot names and exact final PNG hashes.
- `gate-comparison/`: matched crops against rejected `195491b`, including
  grass 150/260/600, tent pot 900, body 300, night 300, and shrine 2 180.
- `distance-v9/` and `views/distance-v9-{30,60,80}.jpg`: final 30/60/80 m
  horizontal-offset views at frames 200 and 260, paired with the frozen
  master views in `build/task69-sol2/distance-before-v3/`. All six viewed.
  Logged slant distances are 31.78, 63.57 and 84.76 m.

Of the 45 master comparisons, 33 are RGB-identical. The 12 changed shots are
four camp frames, three grass-fire frames, night, tent fire, body fire, snow,
and swimming. Snow and swimming differences are confined to distant fires.
All four shrine images are RGB-identical. No new checker/dither, hard sheet
end, hanging cliff triangle, unrelated colour cast or black blob was found.

The explicit final-tree captures command also passed:

```sh
python3 tools/critic_pack.py --only captures build/task69-sol2-revision/capture-audit --resume
```

The audit copied the completed fresh capture section and revalidated its exact
sources, fixture, scene settings, required shot names and PNG hashes. All 45
shots were retained; the helper's legacy console message says 43. Relevant
fire/night/shrine crops were viewed again from this audit. The original full
pack's PASS remains intact. Audit log: `capture-audit.log`.

Earlier probe and distance directories are superseded diagnostic experiments.
Stopped full packs are explicitly marked superseded; they are not final evidence.

## Checks

All 14 targeted checks passed on the final sources, using
`tools/run_all_checks.sh --only NAME`; logs are in `checks-v9/`:

`task69_fire_check`, `task68_fire_check`, `round91_fire_check`,
`round83_fire_check`, `round67_fire_check`, `round80_fire_check`,
`round66_fire_material_check`, `fire_test`, `element_test`, `cooking_check`,
`combat_check`, `round88_material_check`, `weather_shading_check`, and
`art_shade_test`.

The existing registered `task69_fire_check` now covers neutral smoke,
continuous contour joins, transparent exposed ends, spatial body-light falloff,
and bounded/transparent unsupported cliff endpoints, alongside the previous
fire/rig/material checks.

`tools/prepare_assets.sh` and `tools/prepared_assets_check.sh` passed on the
final tree. `prepared-assets-v9.log` records complete audio/world/mesh/collision,
ownership/RNG, texture and combat-socket byte equivalence.

## CPU p99

Baseline: frozen master `cb21e87` at `build/task69-sol2/before/fixture/capture`.
Candidate: final-source `probe9/fixture/capture`. Three alternating AB/BA pairs
per affected scene, CPU 2 for both binaries, identical settings, 240 warmup
frames, nearest-rank per-run p99 and median of three runs. No measured-frame
screenshots or removed outliers. Both wall and thread CPU gates use the existing
`after <= before × 1.03 + 0.10 ms` budget.

| Scene | Wall p99 before → after (ms) | Thread p99 before → after (ms) | Gate |
| --- | ---: | ---: | --- |
| night | 13.404 → 11.904 | 9.194 → 9.077 | PASS |
| camp | 14.239 → 11.343 | 10.884 → 10.848 | PASS |
| grass-fire | 7.990 → 8.124 | 5.870 → 5.898 | PASS |
| tent-fire | 11.803 → 12.019 | 11.184 → 11.121 | PASS |
| body-fire | 8.320 → 8.387 | 5.830 → 5.926 | PASS |

All 30 raw runs, executable hashes, environments and the aggregate are in
`bench-v9/`; script `bench-v9.py`, log `bench-v9.log`, result `summary.json`.

## Full pack

```sh
python3 tools/critic_pack.py build/task69-sol2-revision/final-pack-v9 --capture-batch-scenes 8
```

Status **PASS**: 45 captures, cold/warm/new-build startup probes, the native
2133×1200 real-time 120-second route, 13 audio clips/scores, and all eight fast
checks. Startup cold/warm median/new-build times were 17.83/2.04/2.34 seconds.
Native frame-interval p99 was 15.645 ms across 9,824 steady samples; six exceeded
25 ms. Actual presentation was immediate (driver mailbox fallback).
The full pack took 1,315.0 seconds wall time and met its under-25-minute flag.
Full log: `final-pack-v9.log`.

All render/window runs used bounded `/tmp/botw-render.lock` batches through
self-locking helpers or caller-owned flocks, without nested locks. Evidence
remains ignored under `build/`. `source-verification.json` maps the pack's
pre-commit source hashes to the delivered commit.

Unresolved implementation issues: none identified in final self-review.
Independent visual-gate approval is pending.
