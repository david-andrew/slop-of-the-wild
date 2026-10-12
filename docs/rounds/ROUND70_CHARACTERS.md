# Round 70: character value structure at gameplay distance

Baseline: `4da5600`, fast-forwarded onto `astra/work` before editing. Full-frame
1280×720 pairs, native crops, masks, measurements and raw validation logs are in
`build/round70/`. Open `comparison.html` for before/after toggles at native 1×
or fit-to-window scale. `results.json` records source, bake and asset hashes.

## Implementation

- Bake muted red pigment with broader value separation into the Bokoblin. The
  existing mesh carries darker back/shoulder mottling, shaded inner ears and a
  lighter belly. Rest-space texture painting adds a lighter snout, two nostrils,
  a dark mouth and ivory teeth. The existing single horn is retained. Pupil
  placement uses the immutable source eye mask, independently of new paint.
- Reduce nine crown locks to seven wider, asymmetrically swept clumps. Increase
  the separation between golden top locks and the dark underlayer. Vary lock
  values, widths, overlap and tip heights; use warmer scalp pigment.
- Round the compressed wake humerus cross-section by at most 8 mm and use a
  radial shading frame through the upper arm and elbow. Add a wake-only
  vertex pigment wash around the right upper arm, elbow and
  forearm, with a darker underside/core and a contact crescent on the back.
  It follows the existing skinning and wake gate. No vertices, light sample,
  fragment texture read, draw, skeleton or contact transform is added.

Only `tools/bake_models.jo`, its three generated model assets and
`game/charshade.jo` change production behavior. No `chars.jo` edits.

## Screen measurements

Screen-space HSV is computed from display sRGB. The same baseline-selected,
eroded skin mask is used before and after, excluding bone/eyes/wood/cloth.
The exposed-back rectangle is also reported separately to distinguish pigment
variation from deep occlusion shadows. Raw masks and sampling coordinates are
saved with `measurements.json`. Value span means P95 minus P05.

| Screen region | Mean saturation before → after | Mean value before → after | Value span before → after |
| --- | ---: | ---: | ---: |
| combat | 66.38% → 54.10% | 0.5034 → 0.4571 | 0.5569 → 0.6235 |
| camp | 64.31% → 52.20% | 0.6289 → 0.5404 | 0.4431 → 0.4667 |
| camp_back | 62.89% → 52.06% | 0.6884 → 0.5830 | 0.0784 → 0.2471 |

Hair stripe-band spectral power fraction: **28.75% → 19.29%**.
This is the fraction at three or more cycles across a fixed 31-pixel interior
head scanline, averaged over six rows after linear detrending and Hann windowing.
The full spectra and luminance profiles are retained; the statistic measures
spatial frequency distribution, not absolute edge amplitude.

## Geometry, contacts and rendering budget

All three models retain byte-identical non-hair positions, normals, UVs and
skin influences, including the Bokoblin pupils (`final-contract.json`).
All skeleton/socket transforms, grips, soles, combat geometry
and model draw counts are unchanged. Each hero mesh loses 384 hair vertices /
128 triangles. Bokoblin stays at 4,913 vertices / 7,764 triangles / three parts.
Hero has seven parts and bare hero four. Texture counts/resolutions are unchanged.

`hero_model_check`, `enemy_model_check`, `wake_contact_check`, `combat_check`,
and `contact_check`: **PASS**. Combat verifies 495 swing frames; worst visible
weapon-tip error is 0.000011 m. The wake soft-tissue correction remains
bounded at 0.03465 m and is exactly absent at grip/sole samples.

Weather silhouettes: **12/12; minimum 14.31034%**, exceeding the
unchanged 12% floor for both silhouette contrast and paired separation.

GPU protocol: three alternating frozen production before/after pairs per scene
and resolution, scale 1; 357 measured frames per run after warmup. Acceptance:
after median ≤ baseline × 1.03 + 0.1 ms. Baseline uses baseline model assets.

| Scene / output | Before ms | After ms | Limit ms | Result |
| --- | ---: | ---: | ---: | --- |
| 1280x720-wake | 2.944 | 2.824 | 3.132 | PASS |
| 1280x720-combat | 6.112 | 6.330 | 6.395 | PASS |
| 2133x1200-wake | 6.872 | 6.903 | 7.178 | PASS |
| 2133x1200-combat | 12.765 | 12.707 | 13.248 | PASS |

Rebake with `sloppy/bin/sloppy tools/bake_models.jo hero bokoblin`. Evidence
fixtures in `build/round70/capture.py` and `gpu.py` adapt the round-69 drivers
with baseline `4da5600`. They own their flock; never wrap them in another.
`measure.py`, `report.py` and `document.py` regenerate analysis and reports
from the saved captures and logs. All scratch and render artifacts stay in
ignored `build/`; none are force-added.
