# Round 71: character and enemy materials

Baseline: `91809e7`, on `astra/work`. Reproduction tools and final evidence are
in `tools/round71_character_{check,report}.py` and `build/round71/`.

## Material changes

- Blue Bokoblin: baked muted slate blue, darker back mottling, a pale belly and
  snout, and dark nostrils/mouth. Remove the runtime recolor that flattened the
  texture's material groups. The original emissive mask, red/black/green texture
  variants, model geometry and all animation/contact data remain identical.
- Stalkoblin: warmer ivory crowns, grey aged shafts, darker joint ends and
  underside washes. Reduce the overpowering fill/rim; keep amber eye emission
  isolated in its existing texel. The generated body/skull topology is unchanged.
- Monk: aged bronze trim, quieter warm-grey skin and linen, more distinct pleats,
  sunken temples and neck shadows. Paint only the existing generated vertices.
- Guardian husks: broaden plate values, add mineral/oxide variation, desaturate
  moss and reduce ivy intensity. Process only vertices appended by the husk
  builder; retain the shell/leg geometry, collisions and chunk draw structure.
- Dressed hero: broad torso and sleeve folds, shadowed side planes, worn hems,
  knee highlights and creases, plus restrained face/neck shading. Normalize
  each cloth region's approximate linear-light energy to its original palette,
  including the shirt's back, preserving the established Old Shirt value.
  The bare hero and old-man texture variant remain byte-identical.

There are no new shaders, texture slots, texture sizes, geometry or draws.
The report verifies exact baked positions, normals, UVs, indices, influences,
rigs, part counts and unrelated texture variants against the frozen baseline.
Hero: 29,306 vertices / 30,630 triangles / seven parts. Bare hero: 29,782 /
50,046 / four. Bokoblin: 4,913 / 7,764 / three. The Stalkoblin retains two
parts and the monk one; their generation loops and indices are unchanged.

## Reproduction

The baker is CPU-only. Every render command below owns its render lock; do not
wrap these Python entry points in another `flock`.

```sh
sloppy/bin/sloppy tools/bake_models.jo hero bokoblin
python3 tools/round71_character_check.py prepare before
python3 tools/round71_character_check.py prepare after
python3 tools/round71_character_check.py capture before
python3 tools/round71_character_check.py capture after
python3 tools/weather_silhouette_check.py --output build/round71/weather
python3 tools/round71_character_check.py gpu-prepare
python3 tools/round71_character_check.py gpu-run
python3 tools/enemy_model_check.py
python3 tools/hero_model_check.py --baseline build/round71/before/assets/models
sloppy/bin/sloppy build tools/combat_check.jo -o build/round71/combat-check
flock /tmp/botw-render.lock build/round71/combat-check
python3 tools/round71_character_report.py
```

The report consumes the check logs stored under `build/round71/`; redirect the
three check commands to their corresponding `*_check.log` files when reproducing.
Only Pillow is needed for the Python image report. Full source manifests,
camera/environment settings, baseline assets, GPU binaries and logs remain in
`build/round71/`. GPU tests freeze production updates in combat (characters) and the husk
view (static building meshes), and use three alternating before/after pairs,
357 steady-state samples per run, at
1280x720 and 2133x1200. Acceptance is baseline median × 1.03 + 0.1 ms.

The five production views are combat frame 155; night frame 180 at hour 23,
`BOTW_AT=-672,1535,0.8`; blue camp frame 120 near the Hopper Pond actor at
`(-982.10,188.24,1643.50)`; the requested shrine-2 monk close-up at frame 120;
and the requested Guardian-husk camera at frame 120. Night measurements use
the unobscured distant Stalkoblin to avoid confusing the foreground skull with
the changed hero shirt. The crop still shows both enemies.

Saturation and value use display-space HSV. Full-frame, fixed-crop and matched
changed-material statistics are separate. The latter use identical pixel
coordinates in both images, selected by an RGB difference greater than three
levels within the documented measurement region. These are change masks, not
complete semantic masks. Linear Rec.709 luminance is also recorded. Weather
acceptance uses the existing independent visible/hidden/body-mask protocol.

## Final results

`enemy_model_check`, `hero_model_check` and `combat_check` pass. Combat covers
495 swing frames, with worst visible-tip error 0.000011 m; Stalkoblin drawn
skull/physics centre error is 0.000000 m. Weather silhouettes pass 12/12,
with a minimum of 13.38% (canopy storm).

| GPU view | Before median | After median | Delta | Allowed maximum |
| --- | ---: | ---: | ---: | ---: |
| 1280x720-combat | 6.302 ms | 6.291 ms | -0.011 ms | 6.591 ms |
| 1280x720-husks | 7.044 ms | 7.117 ms | +0.073 ms | 7.355 ms |
| 2133x1200-combat | 13.225 ms | 13.459 ms | +0.234 ms | 13.722 ms |
| 2133x1200-husks | 12.862 ms | 13.138 ms | +0.276 ms | 13.348 ms |

All four comparisons pass. Exact framebuffer dimensions, final asset hashes
and fixture binary hashes are verified by the report.

| Matched changed material pixels | Saturation before → after | Value before → after | Value P10–P90 before → after |
| --- | ---: | ---: | ---: |
| combat | 33.5% → 34.1% | 60.1% → 59.5% | 29.0%–80.0% → 28.2%–80.4% |
| night | 48.8% → 51.3% | 50.6% → 39.8% | 19.6%–84.7% → 20.8%–70.6% |
| blue-camp | 50.0% → 48.6% | 54.5% → 41.5% | 36.9%–76.1% → 23.5%–65.1% |
| monk | 46.6% → 37.7% | 44.7% → 38.0% | 26.7%–69.0% → 18.8%–60.4% |
| husks | 22.6% → 20.5% | 45.5% → 41.9% | 28.2%–63.5% → 25.1%–60.0% |

Full-frame and complete crop measurements, sample counts and linear luminance
are in [measurements.json](../build/round71/measurements.json). The interactive
[comparison](../build/round71/comparison.html) embeds its images and works offline.
`results.json` includes validation summaries, model contracts and source/asset
identities. Every pair below is before on the left and after on the right.

| View | Full-frame pair | Native crop pair |
| --- | --- | --- |
| combat | [Full frame](../build/round71/combat-pair.png) | [Crop](../build/round71/combat-crop-pair.png) |
| night | [Full frame](../build/round71/night-pair.png) | [Crop](../build/round71/night-crop-pair.png) |
| blue-camp | [Full frame](../build/round71/blue-camp-pair.png) | [Crop](../build/round71/blue-camp-crop-pair.png) |
| monk | [Full frame](../build/round71/monk-pair.png) | [Crop](../build/round71/monk-crop-pair.png) |
| husks | [Full frame](../build/round71/husks-pair.png) | [Crop](../build/round71/husks-crop-pair.png) |
