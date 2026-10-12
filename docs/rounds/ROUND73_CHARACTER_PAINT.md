# Round 73: foreground skin and hair

Baseline: `e955219`. Evidence is under `build/round73/`; it is not tracked.

The accepted change compresses the bare hero's imported muscle highlights toward
the source skin's average pigment. Model-space and hue masks preserve the face,
hands and underwear. The wake-only arm wash is less dark, and the existing hair
locks and crown use closer values. These are offline texture/vertex-colour edits
and two shader constant changes; no new runtime samples, parts or draw paths.

Two fixed-colour skin experiments were rejected at normal viewing size: the first
read as grey stone under the chamber light, and the second was too yellow. Their
source, models and frame-330 captures remain in `rejected-cool/` and
`rejected-warm/`. The retained source-derived palette is in `candidate/`.

The round-60 critic's bright boot/arm-band finding also received an isolated
follow-up trial in `gear-trial/`. It muted the boot and bracer leather without
changing geometry, skin, equipment, the old-man variant or the bare hero.
The native-size combat-155 comparison showed slightly less orange leather, but
the pale bands remained prominent. This was not clearly better and was rejected;
the production leather is unchanged. `gear-trial/combat155-pair.png` and
`gear-trial/verdict.json` retain that decision. Shoulder/cloth transitions and
the bright bands remain follow-up opportunities. Enemy weapon poses and sword
trails were left to Sol2.

## Visual acceptance

The eight character comparison views use 1280×720 output, full scene scale
and the production watercolor pass. Wake frames have no `BOTW_SKIP`; exterior captures use clear weather at 11:00.
Before and after crops use identical rectangles without retouching or enlargement.

* **Wake 420 is the largest improvement.** Painted scapula streaks become a broad
  back plane, and the raised forearm has less of a dark painted band.
* **Wake 330** has quieter skin mottling and clearer, less striped hair masses.
* **Wake 520** has softer muscle outlines and knee colour. This is a smaller gain.
* **Combat 155/300/420:** hair values improve modestly; cloth, leather, scabbard,
  sword, shield and hilt contact retain their existing appearance. All pixels
  changing by more than three RGB levels fall around Link's head.
* **Camp:** the entire rendered scene is pixel-identical. Horns, ears, snouts and
  clubs remain readable, although the skin mottling is still coarse.
* **Old man:** the hood, face, beard, robe and staff retain their existing
  appearance. The paired frame also shows the improvement to Link's hair.

The change is closer to the reference's broad painted colour groups, but the
compressed raised-arm shape and lumbar anatomy remain imperfect. This is a
material improvement, not a claim to have corrected the rig or matched BotW's
character design. The readable equipment and enemy silhouettes do not need new
geometry for this pass.

`comparison.html`, `*-pair.png` and the `before/` and `after/` `*-crop.png` files retain the
visual comparisons. `review-notes.json` records each view's assessment.

## Geometry and validation

The model comparison checks exact positions, normals, UVs, indices, bone data,
skin weights, part names and material-slot grouping against the baseline.
The Bokoblin model remains byte-identical.

| Model | Parts before/after | Vertices before/after | Triangles before/after |
|---|---:|---:|---:|
| Hero | 7 / 7 | 29,306 / 29,306 | 30,630 / 30,630 |
| Bare hero | 4 / 4 | 29,782 / 29,782 | 50,046 / 50,046 |
| Bokoblin | 3 / 3 | 4,913 / 4,913 | 7,764 / 7,764 |

These are asset part counts, not total scene draw counts. Visibility, shadow
grouping, prop draws and contact transforms are unchanged.

Eight CPU groups pass through `tools/run_all_checks.sh --only NAME`:
`hero_model_check`, `enemy_model_check`, `combat_check`, `wake_contact_check`,
`contact_check`, `art_shade_test`, `weather_shading_check` and
`weather_silhouette_test`. Four GPU groups pass: `hero_surface_check`,
`material_paint_check`, `draw_cache_check` and `post_edge_check`.
Logs are `final-cpu-checks.log` and `final-render-checks.log` in the evidence root;
each names its complete suite-run directory.

`weather_transition_check` also passes: **13 regression groups PASS** in total.
The open/shelter, forest, snow and shrine-exit transition scenes all pass.
The production weather-silhouette capture/analyser passes **12/12 cases**, with
minimum contrast/paired separation **17.39026%** against the unchanged 12% floor.
Its frozen candidate sources and assets are verified identical to the final
production game and models. Combat checks 495 swing frames with worst visible-tip
error 0.000011 m; wake grip/sole masks remain exact.

`weather-check.log`, `weather/contrast.json`, `results.json` and `summary.txt`
retain the remaining verdicts and hashes. `combat-material-stability.json`
records the bounds of the hair-only combat changes. No GPU timing claim is made;
geometry, texture sizes, runtime sample counts and draw paths are unchanged.

## Reproduce the character views

```sh
python3 tools/round73_character_check.py prepare before
python3 tools/round73_character_check.py capture before
python3 tools/round73_character_check.py prepare after
python3 tools/round73_character_check.py capture after
```

The capture helper acquires one `flock /tmp/botw-render.lock` for each game
process. Do not wrap it in another lock. Preparation is CPU-only. Optional view
names after the phase select individual captures.

Combat uses `BOTW_SKIP=1`, `BOTW_AT="-1439,1606,0"`,
`BOTW_GIVE=travelers_sword,travelers_shield` and the existing character/combat
reference input:

```text
5:w+,40:w-,45:k+,100:j+,106:j-,125:j+,131:j-,150:d+,152:space+,154:space-,170:d-,300:j+,306:j-,330:j+,336:j-
```

Camp uses `BOTW_SKIP=1 BOTW_CAM="-947,243,1956,-0.85,-0.45"` at frame 120.
The old man uses `BOTW_SKIP=1 BOTW_AT="-951,1876,2.5"`
and `SLOPPY_INPUT="5:w+,40:w-"` at frame 100.

The retained candidate captures use isolated copies of the same final game
sources and assets; source and model hashes are in `candidate/` and `production-manifest.json`.
The final production bake matches both candidate hero models byte-for-byte. The silhouette
adapter, `build/round73/weather.py`, calls the production capture and analyser
with one lock per weather render, releasing it between all twelve cases.
