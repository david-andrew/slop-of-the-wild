# Round 85 — painted cliffs and plateau dressing

Resumed the unfinished work on `sol3/work` at `500126f`, preserving the inherited
landscape edits. Merged master `43d5088` (including `431a3f5`), then integrated
master `284b4e1` when Astra's `d87c883` weather work landed during validation.
Final validation and captures use the latter integration. Before images use
`500126f`; roof, husk, fir, sky and weather differences inherited from master are
not claimed as landscape changes here.

## Changes and visual review

- Cliff skins and gorge returns retain shared smooth normals instead of mixing
  in each triangle's face normal. Desaturated skylight, neutral granite pigment,
  softly feathered moss, and baked dipping-bed pigment replace the navy wedges
  and hard green patches. Existing intersecting shelves, collision and LOD
  geometry remain. Pigment uses the existing material channel.
- Waterfall channels have unequal opacity and foam density, with moving breaks
  down the sheet. The roll stays connected and the ledge splashes remain.
- Jaba Badge's thin transverse ceiling overlays and obsolete emissive rib
  inlays are removed. They caught pink lamp light or intersected the new roof
  profile as pale diagonal streaks; the chamber's
  broad structural ribs, profiled roof, lift well and collision remain.
- Temple entrance piers have recessed and chipped courses, missing facing
  stones, clustered fallen blocks and rooted ivy sprays. Original structural
  collision preserves the entrance and roof route.
- Existing meadow pigment strokes carry more contrast at overview height.
  Unequal groups of young trees, offset lower crowns and shrubs feather six
  woodland margins. Placement uses hashes and existing batches, checks routes,
  water and slope, and adds no colliders.

The inherited capture driver held the shared render lock over whole performance
batches. It now acquires and releases `flock /tmp/botw-render.lock` around each
individual game process. A leftover process from the stopped worker was
terminated before fresh final evidence was collected. Its partial timings and
intermediate images remain in the ignored evidence directory; they are excluded
from the final report. Two transient Vulkan allocation failures affected both
baseline and candidate; their logs are retained in `rejected-allocation/` and
excluded from measurements. The first ceiling revision still showed pale
inlays and was rejected; `accepted/` retains that intermediate evidence.

## Evidence and reproduction

Matched native 1280×720 before/after pairs, immutable source snapshots, binary
hashes, launch environments, frame logs, and the local comparison gallery live
under `build/round85/landscape/`. The final report checks snapshot hashes and
camera/environment equality and fails if a performance budget is missing or
exceeded. Generated evidence is not committed.

Views include the requested waterfall camera, pool, rock at 2 m, waterfall crown,
plateau overlook, dawn/day overview, forest, temple front/flank, and five Jaba
roof/lift views. The close camera is at x=-1549.128; the existing cliff's ray hit
is x=-1547.128 at y=180, z=1785.

```sh
python3 tools/round85_landscape_capture.py prepare before
python3 tools/round85_landscape_capture.py prepare after
python3 tools/round85_landscape_capture.py capture both
python3 tools/round85_landscape_capture.py perf
python3 tools/round85_landscape_capture.py motion before cliffs pool
python3 tools/round85_landscape_capture.py motion after cliffs pool
python3 tools/round85_landscape_report.py
```

Do not wrap these helpers in another render lock. CPU-only preparation and
checks do not acquire the render lock.

## Validation

`tools/prepared_assets_check.sh` invokes `tools/prepare_assets.sh`; both completed
on the merged final source. Generated and prepared audio, world, architecture,
collision, roof, ownership, RNG, textures and mesh bytes agree.

Both uninterrupted journeys pass with no stamina outs, falls, hard falls or
stuck points: controller 67,890 frames / 4,865.45 m; keyboard 69,918 frames /
4,874.58 m. The journey harness now verifies the timed spirit reveal before
waiting for the paraglider award introduced by master; the former assertion
expected an immediate reward.

Landscape, waterfall shape/coverage, map water, cliff mesh, temple roof, shrine
arrival/sightline/shaft/lighting/paint, round86 framing and all four complete
shrine routes pass. Final enclosure checks cover 18,480 culled mesh rays and
1,440 settled camera views. Logs are in `build/round85/checks/integrated-*.log`; GPU material checks are
`resume-{fir_surface,terrain_noise,material_paint}_check.log`. The integrated
round96 weather regression also passes.

## Final performance and acceptance

GTX 1070, Vulkan/X11, native 1280×720, scene scale 1, fixed 1/60 simulation.
Three alternating before/after pairs per view (repetitions 40–42), frozen at
frame 360; first 480 intervals excluded, 960 steady samples per run. Values
below are medians of run p99, in milliseconds. The acceptance budget is
baseline × 1.03 + 0.10 ms for both callback interval and callback wall time.

| View | Frame before | Frame after | Callback wall before | Callback wall after |
| --- | ---: | ---: | ---: | ---: |
| cliffs | 5.630 | 5.788 | 5.268 | 5.323 |
| overview | 6.861 | 7.007 | 6.500 | 6.627 |
| overlook | 6.184 | 6.190 | 5.789 | 5.809 |
| forest | 10.439 | 10.518 | 9.989 | 10.067 |
| temple | 8.761 | 7.317 | 7.699 | 6.716 |
| s2ceil | 9.013 | 7.994 | 6.880 | 5.321 |

All six budgets pass. These are callback intervals, not measured scanout.
The shared host produced substantial late-run scatter, especially at the temple
and shrine; these figures are an acceptance check, not evidence of a causal
speedup. Individual runs and exact launch environments remain in `report.json`
and the raw logs. The earlier validated build is retained in `pre-weather-merge/`.

Final review accepts the softer cliff faces at the waterfall, pool, 2 m camera
and crown; unequal flowing waterfall channels; the clear Jaba roof in the
raised-camera, wide and eave views; damaged temple masonry and ivy; and the
stronger overview ground strokes and woodland margins. Unchanged views remain
as controls. The 16 full-resolution pairs and six paired motion frames are
under `build/round85/landscape/`; `review.html` provides the comparison slider.
The motion check samples the waterfall sheet itself, excluding moving mist.
No generated evidence, raw reference footage or Python caches are committed.
