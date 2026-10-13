# Round 82: foliage, boar, body fire and Options

Based on `c612330`, addressing the five round-64 critic findings. Raw matched
captures, frozen executables, source hashes, settings, logs and comparison pairs
are in `build/round82/`. Nothing under `build/` is committed.

The fir crown keeps three closed 40-vertex fans per authored branch, with the
same draw/material buckets and shadow triangle budget. Narrow, tapered fans start at
unequal positions and diverge asymmetrically. A position hash varies the branch
openings without advancing placement or gameplay RNG. Snow sits on the finer
upper shelves. The five source variants retain their bounds, positive volume,
outward winding, unit normals and bounded triangle counts (3,168–7,920 view;
2,112–5,280 shadow). Removing the redundant terminal ring reduces view triangles
by 25% while preserving eight-sided snow normals and the narrow silhouette.

The boar's mane uses 14 overlapping dark swept clumps with unequal widths,
heights and offsets. Extra body/head rings ease the rump, withers and neck joins;
a tapered thigh embeds in the body at the existing hip/knee pivots. The complete
near boar drops from 2,952 to 2,856 triangles while retaining 14 near / 6 distant
draws. Animal
placements, AI, gait, leg transforms and hooves are unchanged.

Burning actors retain the same eight flame cards. Their unequal lengths and
widths follow the final animated limb endpoints; the upper tongues curve with
limb direction and opposite locomotion velocity. Seeded edges and upper breakup
keep the tips from reading as identical attached torches. Roots remain fixed to
the existing final skin pose, and fire simulation, damage, duration and RNG are
unchanged.

Low plants sample the existing burn map at their roots and frond vertices in a
plant-specific vertex shader, so view, depth and shadow passes collapse the same
fronds. Burned plants turn to char and stop moving in the wind. Trees retain their
original uniform/sampler payload, and a constant zero removes char shading from
their fragment programs. A conservative 64×64 tile map limits the plant shader
to batches whose full transformed frond bounds overlap char or heat. Trampling
and suppression do not flag tiles; prepared-map restoration rebuilds them. Both
shader paths are warmed before gameplay. Merely trampled ground does not burn
plants. Spent grass cores discard their ribbons; fading edges retain only low
stubble. Ground-level lightning paints the existing terrain scorch channel
without requiring ignition. Water, elevated impacts and roof-covered ground
receive no ground scar.

Options places headings, rows, secondary labels, navigation hints and status
messages on one opaque local surface. Secondary text is opaque sage, with a
consistent background across snow, meadow and shrine views.

## Reproduce

```sh
mkdir -p build/round82/master-baseline
git archive 2e8499d game | tar -x -C build/round82/master-baseline
python3 tools/round82_critic_capture.py prepare master --game-dir build/round82/master-baseline/game
python3 tools/round82_critic_capture.py prepare lean
python3 tools/round82_critic_capture.py capture master
python3 tools/round82_critic_capture.py capture lean --baseline master
cc -shared -fPIC -O2 tools/round82_draw_audit.c -o build/round82/draw-audit.so
python3 tools/round82_critic_capture.py performance lean --baseline master --frames 2880 --warmup 720
python3 tools/round82_options_contrast_check.py --label lean
```

Capture/performance commands own one `flock /tmp/botw-render.lock` per game
process; do not wrap them in another lock. The master snapshot stays under
`build/`; no checkout or source replacement is required. The Vulkan audit counts
actual indexed and nonindexed draws at each present. Master primes two loading
presents before the first timed callback; the parser excludes those while
retaining the raw audit log. Timings alternate AB/BA/AB, with 2,880 frames per run
and the first 720 excluded. Compare median run frame/main-thread p99 using the
established 3% + 0.10 ms tolerance. Every steady-state draw count must match.
The Vulkan runtime has no GLES pass timer queries; frame intervals measure the
actual backend rather than substituting unavailable pass timings.

## Checks

Passed on the final source: `tree_test` (75/75, 30/60/120 Hz), `vegetation_reach_check`,
`vegetation_tail_check`, `fir_bough_check`, `fir_surface_check`, `fauna_test`,
`wildlife_path_check`, `wildlife_observation_check`, `fire_query_check`,
`fire_scan_check`, `fire_test`, `element_check` (19), `element_test`,
`input_check` (2,386/2,386), `round80_fire_check`, `round91_fire_check`,
`round82_scorch_check`, `round82_plant_surface_check` (6,144 GPU pixels),
`render_warmup_check` (50 pipelines before/after), `wildlife_mesh_check`,
and the production build. The new scorch check covers
local dry/rain impacts, elevated impacts, cover and water plus 18 articulated
flame trail cases. New scorch and GPU plant checks are registered in the check
runner.

An early boar candidate was rejected after visual inspection because
its mane still read as a regular comb. Its capture is retained separately; the
final boar pair uses the darker, broader 14-clump candidate.

A root-only plant candidate was rejected: the fire260 fern rooted outside the
burn still extended green fronds over char. The final shader combines root and
undeformed vertex samples and fully wilts plants at the existing ignition heat.
The GPU probe covers that crossing-frond case as well as whole-plant masks.

The 14-clump intermediate candidate was also rejected because raised ends
read as fins. Final locks arch over the sampled local back surface and end
inside the coat, including the tapering rump.

The inherited whole-vegetation burn shader failed camp/overlook timing. Its
successor isolated vertex sampling to low plants but failed the forest p99
budget. Those reports are retained under `performance-accepted/` and
`performance-optimized/`; they are not passing final evidence. The final
candidate also removes char shading from tree/fir fragment programs and uses the
scorch-region broad phase to retain the healthy plant path in unaffected batches.
The fragment-only attempt is retained under `performance-specialized/`.

Timing batches alternate fresh baseline/candidate runs. A resumed batch reuses
only complete 1,440-frame logs/PNGs with matching executable hashes; new batches
never import baseline timing from an earlier session. Baseline-source snapshots
for the corrected strike/interior cameras are exactly `c612330`. The Options
interior waits for 90 frames before pausing so it measures a settled room.
Secondary-label pixels measure at least 10.64:1 against the same (19, 23, 22)
local background in snow, grass and the dark shrine interior.

## Integration

Merged master `2e8499d`, including the cliffs, shrine ceiling, malice, lightning,
character lighting and hero hands. `chars.jo`, `terrain.jo` and the check runner
merged automatically; the master changes are retained. Post-merge production
compilation, all 19 CPU checks, plant/fir GPU probes, electric-depth pixels and
50-to-50 pipeline warmup passed. `prepare_assets.sh` and
`prepared_assets_check.sh` passed complete audio/world/mesh/collision/roof/RNG/
texture byte equivalence and named draw order.

The first post-merge electric probe reached its pixel assertions but failed
saving into a missing evidence directory. It was mistakenly in the CPU batch;
its corrected run uses the render lock. That initial result and the potentially
overlapping timing capture remain under `integration/initial-results.json` and
`integration/rejected-probe-overlap/`. The corrected GPU results are in
`integration/gpu-results.json`.

The six-ring fir candidate failed the snow p99 budget in both short and longer
batches (`performance-integrated/` and `performance-release/`). Profiling retained
under `integration/profile/` distinguishes foliage draw time from the longer
simulation stages. The final five-ring candidate cuts view triangles by 25%,
retains the inspected silhouette, and keeps the shadow/draw budgets. Immutable
body-fire socket arrays avoid idle-frame allocations; matched body-fire pixels
are unchanged by that cleanup.

Final source hashes are in `lean-source.json`; master hashes in `master-source.json`.
Final matched visuals are `<scene>/master.png`, `<scene>/lean.png` and
`<scene>/pair-lean.png`. The earlier `before.png`/`after.png`/`pair.png` files retain
the original `c612330` comparison, rather than silently mixing source bases.

Final evidence is `performance-lean/*-report.json`: all four views pass the
3% + 0.10 ms frame/main-thread p99 tolerance, with identical per-frame draw
sequences across all three repeats. These are 1280×720 Vulkan/X11 measurements,
not a claim about scanout timing or other hardware. The run ranges remain in
each report; the host exhibits noticeable tail variance.

| View | Frame p99, master → final (ms) | Main-thread p99 (ms) | Draws |
| --- | --- | --- | --- |
| snow | 8.214 → 7.955 | 7.520 → 7.305 | 342–381, identical |
| camp | 7.798 → 8.121 | 6.329 → 6.524 | 433–475, identical |
| forest | 12.990 → 12.285 | 8.538 → 8.376 | 541–560, identical |
| overlook | 8.608 → 8.903 | 6.099 → 6.018 | 311–344, identical |

`integration/final-results.json` records 28/28 final-source checks: 19 CPU checks,
four GPU probes, preparation, prepared equivalence, production compilation,
production wildlife geometry, and Options pixel contrast. The exact checked
source hashes match `lean-source.json`. The compact interactive comparison in
`build/round82/review.html` uses derivatives; raw PNGs remain untouched.
