# Rain silhouette regression after round 68

Base: `4b1f7bb`; branch: `astra/work`. This is a game regression. The
silhouette analyser and its 0.12 linear-luminance contrast floor are unchanged.

## Cause and controlled comparisons

The suite's seed-31, frame-300 captures reproduce exactly: meadow rain has
0.05524 silhouette contrast and Hopper Pond storm has 0.07202. The analyser
compares the eroded body interior with a 3–8 pixel exterior ring, and also
checks the same-pixel hidden-body background. Its body mask, shadows, time,
camera and weather stay matched between the three production draw passes.

Frozen single-change variants and their captures are under
`build/silhouette-fix/`. `ablate.py`, `capture.py`, the variant source trees,
logs, `ablation-metrics.json` and `capture-diffs.json` retain the experiment.

- Restoring the previous grass-fire point-light selection produces identical
  visible, hidden and mask pixels in both failing views. Sol2's fire lighting
  does not cause these failures.
- Restoring full near-plant geometry changes only a lower-left meadow fern
  (pixels x=0–121, y=410–539), outside the body and its contrast ring. Pond
  storm is pixel-identical. Both contrast measurements remain exactly the
  baseline values. Whole-plant clearance and its shadows are not the cause.
- Restoring the old rain implementation leaves meadow rain at 0.05744 and
  pond storm at 0.04066. Thin, denser streaks are not the cause.
- Removing only the new 12% sky / 26% ground fill leaves meadow rain at
  0.07554 and pond storm at 0.00219. Removing the useful ambient fill does
  not repair the regression.
- Restoring only wet-cloth absorption from 0.25 to 0.42 leaves meadow rain
  at 0.11109 and pond storm at 0.03526.
- Restoring only the previous character exposure bounds leaves meadow rain
  at 0.08192 and pond storm at 0.06830.
- Restoring both character changes reaches 0.13719 in meadow rain, but only
  0.09573 at the pond. The stronger ambient light still needs a small canopy
  value reserve against dark water.

The main regression is the combined brightening of wet clothing and the
rain-only character exposure bounds (up to 1.30 of the environment reference,
including lifting canopy shade from 0.85 toward that range). Jo's mean body
value approaches the surrounding grass and water even though local details
become brighter.

## Repair

Restore the wet-cloth value group and the original open-ground exposure
bounds. Under wet daytime canopy shade, smoothly reserve a little more
contrast by moving the reference multiplier from 0.85 toward 0.78. This
uses the existing habitat, wetness, daylight and interior envelopes. Dry and
night exposure bounds retain their previous values; NPCs and creatures do
not opt into this hero exposure correction.

The round-68 sky/ground bounce, 8,200 rain parcels, dense thin near streaks,
reduced streak opacity, water ripples, pigment corrections and smooth
underwater shading remain. The cloth absorption still fades out continuously
underwater rather than stacking on submerged pigment.

The final targeted captures reach 0.13719 / 0.13501 silhouette contrast and
0.25581 / 0.24567 paired separation for meadow rain / pond storm. They retain
the baseline body-mask sizes. `matched-fix.jpg` is the viewed, downscaled
before/after comparison.

## Performance

Two alternating AB/BA pairs per scene use the frozen master and final
executables at 1920×1080, with 1,440 frames per run and the first 360 frames
excluded. Pooled CPU p99 improves from 7.161 to 6.759 ms in canopy rain and
from 6.062 to 5.975 ms in pond rain. Both pass the strict non-increase gate,
without a noise allowance. Settings, source hashes, executable hashes and raw
frame samples are in `build/silhouette-fix/evidence/`; the acceptance report
is `performance-steady-default/summary.json` and names candidate `final`.

## Validation

- `weather_silhouette_check`: PASS, all 12 view/weather pairs, unchanged
  0.12 silhouette and paired-separation floors. Final minimum silhouette
  contrast is 0.13501. Runner evidence is `build/all-checks/run-pYZxVgdE/`;
  retained captures, masks and measurements are
  `build/silhouette-fix/final-silhouettes/`.
- `task68_readability_check`: PASS, `build/all-checks/run-2tLGa8Hv/`.
- `round96_weather_check`: PASS, `build/all-checks/run-LULdoqtK/`.
- `weather_shading_check`: PASS, `build/all-checks/run-YIXyFFJt/`.
- `tools/weather_transition_check.sh` through the runner: PASS,
  `build/all-checks/run-EJlscm0U/`. The cabin route covers 3,010 frames and
  shelter/clearing; forest, snow and shrine-exit routes each cover 2,700
  frames, with largest static brightness steps of 7.7, 7.6 and 6.5 levels.
  Retained images and weather logs are in
  `build/silhouette-fix/final-transitions/`.
- `round93_lighting_check.jo` via the headless builder: PASS, 4,860 existing
  exposure/pigment/normal cases; `build/silhouette-fix/round93-lighting.log`.
- `tools/prepare_assets.sh` and `tools/prepared_assets_check.sh`: PASS,
  complete CPU/generated asset byte equivalence. The initial diagnostic pack
  rejected stale prepared caches; regenerating them repaired the cache, with
  no tracked asset or prepared-input changes.
- `python3 tools/critic_pack.py --only captures build/silhouette-fix/verified-pack`:
  PASS, all 45 shots. The matched frozen master pack is `baseline-pack/`.
  All 45 downscaled side-by-side pairs were viewed: 42 are pixel-identical;
  only `rain-300`, `storm-299` and `storm-300` change, restricted to Jo's
  image region. No new grid, dither, card edge, black mass, hue cast or shape
  repetition appears. Full comparison data and viewed sheets are in
  `review/` and `visual-review.json`.
- `gate-rain-comparison.jpg` additionally compares the round-68 gate pack,
  current master and this repair. The dense rain, brighter environment fill,
  ripples, dry/chamber/swimming/wildlife fixes and other approved scene
  changes remain. The three weather shots regain a dark wet-cloth value
  group while hair, limbs, equipment and garment planes stay distinguishable.
