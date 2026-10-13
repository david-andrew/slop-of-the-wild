# Round 94: green fir tiers beneath snow caps

Based on `c683702`, on `astra/work`. Snowy firs regain dark green bough masses
without restoring the old padded lobes. Two full, tapered sprays form each
authored branch, with one lateral fork whose side, start, reach and width vary
deterministically. Openings between the pointed terminals retain an irregular
silhouette. Placement and gameplay RNG are unchanged.

Central spray width increases from 22–29% to 43–50% of the authored branch width;
the single lateral spray uses 46–53%. Depth is 7.5–9.5% of branch reach, below
the old padded branches' 11.5–13%. Snow follows the upper ridges: the normal
threshold changes from 0.10–0.58 to 0.38–0.76. The unequal solid ridges define
the cap outline directly, avoiding an extra fir snow-noise lookup. Other
vegetation retains its existing drift wash. Shoulders, hanging tips and
undersides remain green.

Replacing three overlapping sprays with two reduces both view and shadow
triangles by **one third relative to current**. View triangles are half the old
six-ring rounded model's count. Closed, outward-wound fir sprays also cull back
faces inside the existing vegetation draw function. Both Vulkan and OpenGL
restore two-sided rendering immediately afterward; bark, leaf cards and crown
atlases retain their existing behavior. No extra noise samples, textures, draws
or material buckets are introduced. A dedicated fir color program specializes
away unused card, plant and impostor paths while sharing the same uniforms and
vertex program. It is covered by production pipeline warmup.

## Matched visual evidence

Full-resolution triptychs are `build/round94/<view>/triptych.png`, ordered
**before / current / after**. PNGs, logs, environment settings, source hashes and
frozen executables are retained. `review.html` is a self-contained comparison
with full-frame/detail toggles; the raw PNGs are unmodified.

- **Before:** `c683702` with only `fir_boughs.jo` restored from `9d9f7b9`, the
  pre-thinning rounded geometry. This isolates the fir change from unrelated
  old game changes. The supplied historical round-82 pair is preserved as
  `round82-snow-reference.png`.
- **Current:** untouched `c683702`.
- **After:** candidate 7, frozen under `after/game`. `after-game` is a
  byte-identical copy of the measured `candidate7-game`; provenance records the
  alias, source hashes and executable hash. Final after captures use that binary.

All views use Vulkan/X11, 1280×720, full scene scale, 11:00 clear weather,
fixed-step simulation and the production watercolor pass. Each game render
owns one non-nested `flock /tmp/botw-render.lock`.

| View | Frame / camera | Visual decision |
| --- | --- | --- |
| Snow | 150; `BOTW_AT=-1060,2230,2.0` | Green tiers and dark undersides return; distinct smaller white caps and pointed forks avoid both rounded pads and white skeletons. |
| Camp | 120; `BOTW_CAM=-947,243,1956,-0.85,-0.45` | Fuller green overhead branches retain unequal tapered openings and a readable camp. |
| Forest | 150; `BOTW_AT=-1000,1620,3.14` | Standard forest composition retained; this view mainly shows broadleaves. |
| Forest firs | 150; `BOTW_CAM=-880,206,2273,2.60,-0.16` | Supplemental non-snow grove: fuller than current, finer and less rounded than before. |
| Overlook | 720; `BOTW_TITLE=1`, input `10:w+,300:w-` | Distant tree belts retain their layered silhouette; title and landscape remain readable. |

## Checks

Existing checks pass without changing their intent or thresholds:

- `fir_bough_check`: five variants retain deterministic vertices, placement RNG,
  authored bounds, finite unit normals, outward winding and closed positive
  volume. View/shadow triangles are **3,360/2,240; 3,360/2,240; 2,112/1,408;
  5,280/3,520; 5,088/3,392** respectively.
- `tree_test`: **75/75** at 30/60/120 Hz.
- `vegetation_reach_check` and `vegetation_tail_check`.
- GPU `fir_surface_check` and `round82_plant_surface_check`.
- `render_warmup_check`: **51 → 51** pipelines.
- Production compilation, asset preparation/warmup and `git diff --check`.
- Production tree captures: chopping/falling, floating and burning log assertions.

Raw final results and source hashes are in `build/round94/checks/`.

## Performance

Final evidence is `performance-candidate7/*-report.json`. Fresh current/final
runs alternate **AB/BA/AB**, with 2,880 frames per run and the first 720 excluded.
Report keys `before` and `after` mean **current `c683702`** and **candidate 7**.
Each reported figure is the median of all three run p99s, without outlier
removal. Every measured per-frame Vulkan draw count must match. Frame and
main-thread p99 use the existing **3% + 0.10 ms** tolerance against current.

The table's historical **B** timings come from the initial three-way batch;
**C/A** are the fresh final pairs. B is a separate historical reference, not a
fresh paired speed comparison with the final build. The older rounded geometry
was faster in some views. Raw reports retain every repeat and show substantial
host timing variation. Intervals measure presentation handoff, not scanout.
Hardware: NVIDIA GeForce GTX 1070; Vulkan/X11, 1280×720, full scene scale.

| View | Frame p99 B / C / A (ms) | Main-thread p99 B / C / A (ms) | Draws | Current budget |
| --- | --- | --- | --- | --- |
| Snow | 7.785 / 8.851 / 8.268 | 7.107 / 8.145 / 7.528 | 342–381 | PASS |
| Camp | 7.406 / 8.188 / 8.228 | 5.007 / 6.318 / 5.785 | 433–475 | PASS |
| Forest | 13.411 / 12.958 / 12.301 | 9.732 / 8.690 / 8.168 | 541–560 | PASS |
| Forest firs | 9.569 / 8.469 / 7.645 | 5.900 / 5.716 / 5.233 | 345–349 | PASS |
| Overlook | 10.255 / 8.342 / 8.528 | 7.097 / 5.486 / 5.020 | 311–344 | PASS |

## Rejected iterations

Candidate 1's 0.66–0.93 snow threshold left too little snow on outer branches.
Candidate 2 restored the visual balance but failed the close-fir timing budget.
Its frozen source, binary, original captures and three-way timing batch remain
in `rejected-candidate2/`; that batch also recorded a stricter comparison with
the historical rounded geometry, separate from the current baseline budget.

Candidate 3 added culling through a wrapper. It failed forest, including a
fixed six-pair confirmation retaining all first three pairs, and overlook.
One overlook run also failed the identical-draw comparison. Candidate 4 inlined
culling but still missed the forest budget. `performance-candidate3/`,
`performance-candidate4/`, `profile/` and their raw logs retain these failures;
none is final passing evidence. Candidate 5 removes the redundant third spray
and passes the other four views, but misses snow, including a six-pair
confirmation. `performance-candidate5/` preserves all those runs. Candidate 6
keeps that geometry and eliminates the redundant fir snow-noise lookup, but
misses the overlook frame budget. `performance-candidate6/` retains that result.
Candidate 7 isolates the optimization in a dedicated solid-fir color program;
all five captures are pixel-identical to candidate 6, and all five final paired
performance checks pass.

The first two supplemental grove cameras faced a hillside; their images remain
in `rejected-forest-camera*`, separate from the final evidence.

## Reproduce

Snapshots are ordinary directories under `build/`, not worktrees. No checkout,
forced add, or writes to another repository are needed.

```sh
mkdir -p build/round94/{before,current,after}
git archive c683702 game | tar -x -C build/round94/before
git show 9d9f7b9:game/fir_boughs.jo > build/round94/before/game/fir_boughs.jo
git archive c683702 game | tar -x -C build/round94/current
cp -r game build/round94/after/
for label in before current after; do
  python3 tools/round94_fir_capture.py prepare "$label"
  python3 tools/round94_fir_capture.py capture "$label"
done
python3 tools/round94_fir_capture.py triptychs
cc -shared -fPIC -O2 tools/round82_draw_audit.c -o build/round94/draw-audit.so
python3 tools/round94_fir_capture.py performance after --baseline current
```

The tools own their render locks; do not wrap them in another flock. Use a new
candidate label for a new timing batch. The retained gallery can be regenerated
with `python3 tools/round94_fir_report.py candidate7`. The experimental three-way diagnostic and six-pair confirmation scripts remain
under `build/round94/diagnostics/`. Everything
under `build/round94/` remains untracked.
