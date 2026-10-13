# Round 93 — castle smoke, lightning, Jo lighting and wake anatomy

Based on `c612330`, on `astra/work`. Evidence is in ignored `build/round93/`.
No changes to the runtime, gameplay strike damage, other worktrees or other artists' assets.

## Changes

- Castle malice has 288 independently fading parcels distributed through three
  overlapping, noise-warped circulation banks. Height is independent of azimuth;
  the former rising helical centreline is gone. The banks move at different
  angular speeds and retain opaque-scene depth rejection around the spires.
- Storm lightning has a broader white core and a stronger feathered blue halo.
  Core and halo share the existing pulse envelope. Conservative scene-depth
  sampling prevents output-resolution glow crossing a foreground leaf boundary.
  Ordinary body-shock arcs retain their original profile and halo strength.
- Outdoor Jo applies cloud attenuation to direct as well as ambient light, with
  neutralized illumination under cloud and a reduced low-sun contribution.
  Diffuse brightness follows the environment's original light uniforms and
  `paint_light` response for equivalent material, normal and shadow, with a
  ±15% exposure envelope. Dry/open illumination keeps an 8% lower bound reserve;
  the darker end is available in dense overcast forest habitat. Soaked cloth
  absorbs more diffuse light, while skin/leather/hair retain their wet pigments.
  Additional rain absorption eases out when the existing wading absorption applies.
  The old hero-only 65% storm skylight boost is removed.
  Local firelight, emission, hit flashes, and the indoor
  wake remain outside this diffuse exposure constraint.
- The bare hero has an elliptical elbow-to-wrist taper and curved subdivisions
  through the forearm, wrist and dorsal fingers. The existing shoulder surface
  blends into those loops. Original vertex indices, rig, hand weights and supporting
  palm vertices are retained; new vertices interpolate existing influences.
  The dressed hero's model is byte-identical to the baseline.

## What the luminance comparison means

The ±15% requirement is measured in linear Rec.709 against *equivalent environment
shading*, not the average luminance of differently colored ground. The existing
silhouette test needs at least 12% Michelson separation from the exterior ring,
which mathematically requires about 27% luminance difference. It cannot coexist
with a ±15% raw body/ring limit on the same samples. Paired body/background captures
also test separation at the exact pixels behind Jo, without exposure normalization.

## Validation

- `round93_lighting_check.jo`: 4,860 material/normal/shadow/exposure/canopy cases across
  cloudy, rain and storm at 11:00, 18.6 and 22:00. Diffuse/environment ratio is
  0.85000–1.15000. Indoor bypass is exact.
- `weather_silhouette_check.py --verify`: all 12 meadow/canopy/pond ×
  clear/cloudy/rain/storm views pass the unchanged 12% ring and paired thresholds.
  Minimum ring contrast is 13.0%; minimum paired separation is 20.3%.
  Cloudy dusk/night checks also pass (14.6%/20.8% ring contrast).
  `silhouettes/provenance.json` records each capture binary and unchanged-path
  reuse during the weather iterations.
- `round93_electric_check.jo`: production GPU shader at 1080p, with an 80%-scale
  cut-out foreground depth target. Three consecutive frames have a 12-pixel
  half-bright core and a 52/52/50-pixel halo. Both are rejected behind the canopy;
  the opening still transmits lightning.
- `round92_lightning_check.jo` and `round92_lightning_target_check.py`: water and
  direct-metal damage, single-hit behavior, RNG/inspection targeting and three
  simulation rates pass. The real forest captures retain 12/12 health quarters.
- `round78_weather_check.jo` and `round91_weather_check.jo`: all three banks cover
  both sides of the castle across 72 time/band/view cases; bounded geometry,
  continuous advection, eroded opacity and dim magenta night color pass.
- `title_panorama_check.jo`: smoke remains inside the title composition at the
  existing camera times and aspect ratios.
- `hero_model_check.py --baseline build/round93/baseline-models`: finite geometry,
  unit normals, skin weights, closed leg surface, unchanged skeleton/socket bytes,
  soles, original non-shoulder influences and supporting palms pass. The bare mesh
  has 52,848 vertices; the largest original-vertex adjustment is 24.484 mm in the
  forearm. Original finger radii and supporting palm vertices are unchanged.
- Wake/contact/stride checks retain wrist drift of 0.014 mm, planted palm
  orientation, lift-off clearance, free-hand clearance and ordinary foot contacts.

## Visual evidence and rejected candidates

The capture tool stores frame-exact PNGs, settings and executable hashes for the
820-frame title, castle-facing combat, tower rise, night, 1080p strike sequences,
cloudy daytime/dusk/night and wake frames 330/420/520. Separate day/night sweeps
sample 30 seeded times across 15 minutes with the title camera and lighting fixed.
Only draw time is varied; no simulation is advanced between sweep samples.
All 60 phase images were visually reviewed: no letter-like shape was observed.
The extra combat panorama uses a draw-only castle-facing orbit while preserving
production combat/input/AI and restoring the normal camera before every update;
normal gameplay-camera combat captures are retained alongside it.

The subdivision-only wake candidate did not sufficiently improve the oversized
forearm and was rejected in favor of the tapered version. The first dusk
attenuation lacked the bounded environment response. The strongest neutral-color
candidate without the readability reserve had only 6.9% exterior-ring contrast at
dusk; it was rejected despite improving the orange color cast. These intermediate
images remain under their candidate/lighting labels for audit.

All render launches take one `flock /tmp/botw-render.lock`, never nested. CPU-only
baking and numeric checks run without the render lock. No build artifacts are
force-added to Git.

The final dusk view has 14.6% exterior-ring contrast and 27.2% paired separation
(minimum 12% for each). Body linear luminance falls from 0.05765 to 0.05390 in
that matched view, while the orange cast is visibly reduced. The 1.05-reference
trial was also rejected because it made the character brighter than the baseline;
the accepted dry/open minimum is 0.92 of the environment reference.
The weather experiments are also retained. Removing the extra skylight alone
lost canopy contrast; shadow-only response and stacked rain/wading absorption
also failed parts of the weather matrix. The final response uses smooth forest
habitat and overcast ramps, with separate rain-soaked cloth and wading absorption.

## Reproduction

From this worktree, compile `tools/round93_capture.jo`, then run
`python3 tools/round93_capture.py <binary> <label> <scene...>` (the script owns
its render lock). Scene names and exact input are in that tool. Compile
`tools/weather_silhouette_capture.jo` and pass it to
`tools/weather_silhouette_check.py --binary <binary> --output <directory>`
for the full matrix. The electric GPU fixture must be launched under one
`flock /tmp/botw-render.lock`; other numeric/model checks do not render.

`tools/round93_report.py` builds `build/round93/index.html`, the paired PNGs,
and both 30-time contact sheets from the retained captures. Gallery labels
select accepted versions; candidate folders retain rejected trials. The final
source also builds normally with `sloppy/bin/sloppy build game/main.jo`.
