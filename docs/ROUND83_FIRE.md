# Round 83: fuel fronts, charcoal and attached fire

Base: `500126f`, fast-forwarded onto `sol2/work`. Raw renders, source hashes,
executables, logs and before/after strips live under ignored `build/round83/`.

Grass ignition no longer writes a 4.4 m preheat mark. A cell receives full
charcoal only on burnout or extinguishing, confined to that cell's footprint.
Adjacent spent texels join into one wash; bilinear filtering and low-frequency
noise soften the outside edge. Terrain and grass stubble use varied warm
charcoal-brown instead of pale ash islands or uniform blue-black paving. The existing noise
controls the value range; a wider shader blend softens the bilinear cell margins
without writing scorch into neighbouring live fuel. The existing fern
root/tip scorch shader follows the same map and is exercised on the GPU.

Every visible live grass cell within 60 m has a persistent rooted flame on every
draw, independent of random particle births. Its narrow tongues curl and break
up as noise travels upward. Existing random particles, their simulation
lifetimes and the fire emitter's RNG calls remain intact. Nearby grass particle births are
tagged and hidden at draw time so they cannot reintroduce cones or linger over
spent char; distant grass and other fire sources retain their ordinary cards. Cards fade as whole
instances from 3 to 4.5 m from the camera. A conservative perspective bound limits
each card to 30% of each screen axis, at most 9% screen area. Near crossed ember
cards are omitted: their flat orange footprints resembled downward reflections.
Normal terrain occlusion and frustum culling still apply.

Wood barrels char, lose their shape and burn out in 4.5 seconds after ignition.
Camp crates and the cabin's decorative barrel now register with the material
system; all parts of a crate share a named char/collapse/hide state. Burnout
retires its collider. Prepared architecture stores the same prop ownership.

Jo and burning monsters use the pose-bound body shader. Connected roots feed
rising tongues with advected gaps and a delayed flow shoulder; locomotion bends
the tips into a short wake. Torso tongues overlap more closely. Small birds use
a feather-sized, brief fire plume, and dead birds emit no visible new plume.
Bird feedback retains the original emitter's RNG sequence.

## Validation

- `fire_test`: exact 30/60/120 Hz and saturated-pool RNG sequences, emitter
  budgets and equipment dousing.
- `fire_query_check`: 3,380 bounded/unbounded heat-query pairs.
- `fire_scan_check`: bounded discovery of 36 exposed trees, with cover rejection.
- `element_test`, `element_check` (19 checks), `integration_test`
  (1,316/1,316, including 75 tree/log checks).
- `round80_fire_check`, `round91_fire_check`, `round82_scorch_check`:
  near-flame geometry, body shape/panic, lightning scars and plant broad phase.
- `round83_fire_check`: 320 continuous flame phases and draw RNG, ignition versus
  burnout, exact production-resolution scorch footprint, projected card limits
  including body trails, real barrel/crate burnout, and live/dead bird emission.
- `round82_plant_surface_check`: production GPU root/tip scorch sampling,
  collapse/pigment, crossing fronds and conservative cached batch bounds.
- `fauna_test`, `wildlife_observation_check`.
- `prepared_assets_check.sh`: complete generated/prepared byte equivalence,
  including ownership, collision, named draw order and RNG.

All render launches take exactly one `/tmp/botw-render.lock`; the capture tool
owns one lock per render and must not be wrapped in another `flock`. Its default
lock wait is 60 seconds (`--lock-wait`); exit 75 means a busy lock. Performance
defaults to three repeats per scene (`--repeats`), matching the protocol below.
The former private long-batch review/profile modes have been removed. The current
`profile LABEL` mode records every frame's `cpu_mark` zones with the same scene
settings, taking a separate lock for each render. Profiling is diagnostic only;
the `performance` gate still runs without CPU-zone tracing.

## Reproduction

Preserve a baseline source tree inside this workspace, then compile both versions:

```sh
mkdir -p build/round83/baseline
git archive 500126f game | tar -x -C build/round83/baseline
python3 tools/round83_fire_capture.py prepare before --game-dir build/round83/baseline/game
python3 tools/round83_fire_capture.py capture before
python3 tools/round83_fire_capture.py prepare charcoal-final
python3 tools/round83_fire_capture.py capture charcoal-final
python3 tools/round83_fire_capture.py performance charcoal-final
```

Captures use 1280×720, scale 1, Vulkan on X11, clear weather, hour 11 and fixed
1/60 s simulation. Fire frames: 150, 230, 260, 290, 320 and 600; tent-fire
frames: 150, 230, 260, 320, 600 and 900. Full strips retain the baseline above
the candidate; full-size source frames are beside their logs.

CPU measurement disables intermediate screenshots, alternates AB/BA/AB over
three repeats of each scene, excludes frames 1–240 and removes no outliers.
Fire runs for 720 frames; tent fire for 960. Callback wall time includes GPU
waits; thread time measures main-thread execution. The gate uses the median of
the three run p99 values, with a 3% + 0.10 ms tolerance for both CPU measures.

The first candidate (`after`) is retained as rejected evidence: its three
persistent particle-style clumps per cell looked like repeated orange cones.
The final rendering (`final-fire`) uses one flowing multi-tongue card per cell,
omits near flat ember cards and hides tagged nearby grass particle cards.
The intermediate `accepted` fire strip is also rejected: untagged grass births
still made cones and orange remnants, and Jo needed a longer joined torso flow.
Superseded `final`, `flow` and `accepted` executables and partial jobs are
retained; their queued capture/measurement jobs were stopped before completion.

## Completion after master merge

The interrupted changes were preserved in `42868d7`, then master `de17257`
was merged without conflicts in `78dda2f`. The untracked `assets/src` symlink
was removed before merging; the nature textures and license now live in this
checkout as tracked files. No piano source link was needed.

The reviewed final pigment spans `(0.040, 0.030, 0.024)` to
`(0.090, 0.068, 0.048)`, with stronger variation from the existing terrain
noise and grass shade. The terrain blend spans mask values 0.12–0.82 rather
than 0.08–0.42; the burn map still marks only consumed cells. The brighter
`warm-char` probe is superseded by `charcoal-final`.

The capture helper replaces master's explicit `main` before appending its
benchmark entry point. Each render locks separately, busy locks exit 75, and
no private long-batch lock or diagnostic trace mode remains.

All twelve targeted CPU entry points listed above passed after the merge;
`integration_test` reports 1,316/1,316. The plant GPU check passed its production
root/tip sampling and cached bounds checks. `prepare_assets.sh` and
`prepared_assets_check.sh` passed, including complete prepared/generated byte
identity and named draw order. The scorch/fuel checks and both asset commands
were repeated after settling the final pigment. Logs are under
`build/round83/checks-final/`.


Final visual evidence is `build/round83/fire-charcoal-final-strip.jpg` and
`build/round83/tentfire-charcoal-final-strip.jpg`, with the `500126f` baseline
above the final candidate. Full-size frames 600–900 show warm dark charcoal,
value variation and a softer transition into living grass. Source hashes,
executable hashes, settings and all twelve requested final frames were verified.

The complete three-repeat-per-phase CPU run **failed the p99 gate** in both
scenes; no outliers were removed and no extra measurement repeats were taken.
`build/round83/performance-charcoal-final.json` records:

- Fire: callback wall p99 15.509 → 16.831 ms (limit 16.074 ms, FAIL);
  main-thread p99 6.271 → 6.159 ms (limit 6.559 ms, PASS).
- Tent fire: callback wall p99 32.342 → 37.272 ms (limit 33.412 ms, FAIL);
  main-thread p99 13.447 → 17.846 ms (limit 13.950 ms, FAIL).

The benchmark comparison against `500126f` includes the master merge as well
as Round 83; it does not isolate the charcoal shader adjustment. The earlier
`performance-idle-fire.json` also failed its fire gate. At `f151be8`, performance
was unresolved; functional and visual success did not establish a passing CPU
budget. The full run log is
`build/round83/checks-final/performance-final.log`.

## CPU performance follow-up

CPU zones identified repeated combat skinning as the tent-fire hotspot; the
fire effects-list build averaged only 0.120 ms. Decode palette rows once, skin
identical vertex inputs once, and retain immutable local poses across recursive
clearance repairs. The diagnostic skinning p99 fell 6.897 → 2.902 ms. Full body
vertices, indices, contacts and draw geometry are preserved.

Round 83 moved crates out of culled chunks into named meshes. The scene's 292
named architecture meshes previously bypassed frustum culling. Cache their
bounds at load, apply the exact shader lift/collapse, and reject offscreen meshes
before material lookups. Crates share a fresh heat-source list after barrel
explosions. Persistent flames construct their final vertices directly, skipping
the discarded ordinary-particle geometry and terrain samples.

`performance-cached-fire-cost.json` **passes both gates**, using the unchanged
three-repeat AB/BA/AB protocol, frames 241 onward and no removed outliers:

- Fire: wall p99 7.009 → 6.943 ms (limit 7.319); thread p99
  5.499 → 4.862 ms (limit 5.764).
- Tent fire: wall p99 9.946 → 9.722 ms (limit 10.344); thread p99
  9.838 → 9.568 ms (limit 10.233).

These are fresh matched `500126f`/candidate medians; wall times differ from the
earlier report. Failed `pose-cache`, `direct-flames` and `bounded-props` reports
remain in `build/round83/`. Profiles and summaries are alongside them.

All twelve CPU checks, the plant GPU check, and both asset commands passed.
`combat_geometry_check` also verifies cache reuse, translated roots and palette
COW invalidation, plus 616,710 reference contact comparisons. `named_bounds_check`
checks 80 exact shader corners and lift/collapse frustum re-entry. A retained
GPU fixture compares the old and direct flame vertices over 36 cases / 36,864
pixels. Logs are in `build/round83/checks-performance/`.

Final full-size frames and baseline/candidate strips are
`build/round83/{fire,tentfire}/cached-fire-cost/` and
`build/round83/{fire,tentfire}-cached-fire-cost-strip.jpg`.
All twelve final RGB frames are pixel-identical to `charcoal-final`; the
comparison is `build/round83/visual-cached-fire-cost-comparison.json`. Candidate
source/executable hashes and 1280×720 output settings were verified.
