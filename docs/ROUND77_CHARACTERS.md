# Round 77 — faces and Guardian husks

Baseline: `9bea708`, isolated in `build/round77/before/`. Source changes are
limited to the Bokoblin bake, Old Man props/hand pose/body visibility, and static Guardian husks.
The humanoid rig and animation library are unchanged, as are the Bokoblin's
weapon overlay, body, grips, soles, original horn and loincloth. All four source
body textures are byte-for-byte identical. Link's model is unchanged.

## Geometry and submissions

| Geometry | Before vertices / triangles | After vertices / triangles | Submissions |
|---|---:|---:|---|
| Bokoblin, including hidden baked club | 4,913 / 7,764 | 5,642 / 7,828 | Same 3 parts; the live character still hides the baked club |
| Old Man replacement face + beard | 1,065 / 1,632 | 1,947 / 3,048 | Same 2 cached prop draws |
| Old Man concealed ranger body + fingers | 21,613 / 22,666 | 0 / 0 submitted | 2 fewer skinned draws per pass |
| Old Man worn boot toes | 0 / 0 | 132 / 200 | Included in the existing cloak draw |
| All static Guardian husks | 406,470 / 171,684 | 314,610 / 138,804 | Same 5 existing world chunks |

Bokoblin triangles increase 0.82%; husk triangles decrease 19.15%. The extra
palette is still the existing second material slot, now four 16×4 images
instead of four 4×4 white images (+768 uncompressed bytes). There are no new
passes, uniforms, shaders or runtime texture uploads for the heads. The Old
Man's two arm solves run before skinning; face/beard construction stays cached.

The sculpted head replaces only source triangles whose vertices are dominated
by `Head`. A triangle-level check preserves every surviving body/neck vertex
attribute and influence, and the complete club/horn/cloth streams. New head
surfaces use the existing head bone. The budget check caps the model at 8,000
triangles and rejects incomplete, collapsed or reversed authored triangles.

The Old Man's beard now indexes its own vertex grid rather than the preceding
moustache spheres. His concealed hands are checked across 120 samples each of
sit, greeting, idle and glide. All 960 hand samples stay inside the closed cloak;
maximum arm-target error is below 0.1 mm. Seated targets follow the lowered
cloak. His ranger supplies the animated skeleton, while the opaque cloak and
cached boot toes supply the visible body: concealed sleeves, cuffs and trousers
are no longer submitted. The net Old Man change is **21,050 fewer submitted
triangles and two fewer draws per pass**. The staff rests beside him.

Guardian armor follows curved, bevelled sectors. Its raised head has an open
socket rim around a recessed cold lens; generic tube end caps cannot occlude it.
Collapsed knees/ankles follow their own terrain height. Original random draws,
leg fates, placements, chunking and shell collision remain intact.

## Visual evidence

All raw PNGs, 300×300 **unscaled** crops, full-frame pairs, scene environments,
source snapshots and logs are under `build/round77/`. No evidence is forced into
Git. `*-heads-pair.png` places before left and after right;
`*-full-pair.png` places before above after.

- `head-{0,1,2,3}-{0,0.65}`: red, blue, black and green; front and three-quarter
  views at **4 m / 50° FOV**. The default viewer's close-up distance and telephoto
  face FOV are explicitly disabled.
- `combat` and `camp`: the established critic/README scenes; `blue-camp` adds the
  blue encounter. `combat-variant-{0,1,2,3}` and `camp-variant-{0,1,2,3}` use an
  evidence-only palette override on the same animation, gameplay and camera.
- `oldman`: the requested `-951,1876,2.5`, `5:w+,40:w-`, frame 100;
  `oldman-sit`: the longer stationary approach; `oldman-4m`: a face-centred
  four-metre camera using the real production head transform.
- `guardian`: the supplied `-852,222,1918,2.6,-0.4` camera; `guardian-front`
  additionally shows the hollow socket from the front.

The accepted head pairs show an oval muzzle, separate nostrils, sunken beady
eyes, a brow ridge, pointed ears and tusks at normal size. The first overlapping
and mis-indexed head drafts were rejected and replaced. The final Old Man keeps
visible cheek/nose/brow planes and a continuous beard, with no stray hands.

Reproduce captures (each command owns its render lock):

```sh
for phase in before after; do
  python3 tools/round77_character_check.py prepare "$phase"
  python3 tools/round77_character_check.py heads "$phase"
  python3 tools/round77_character_check.py capture "$phase"
  python3 tools/round77_character_check.py oldman-close "$phase"
  for variant in 0 1 2 3; do
    python3 tools/round77_character_check.py variant "$phase" "$variant"
  done
done
python3 tools/round77_character_check.py pairs
```

## Checks

Results and complete logs: `build/round77/checks/`.

```sh
python3 tools/enemy_model_check.py
sloppy/bin/sloppy tools/round77_pose_check.jo
sloppy/bin/sloppy tools/combat_check.jo
sloppy/bin/sloppy tools/fauna_test.jo
python3 tools/weather_silhouette_test.py
sloppy/bin/sloppy tools/weather_fx_test.jo
sloppy/bin/sloppy tools/weather_shading_check.jo
python3 tools/weather_silhouette_check.py --output build/round77/checks/weather-silhouette
BOTW_TRANSITION_OUTPUT=build/round77/checks/weather-transition tools/weather_transition_check.sh
COMBAT_SCENES='windup strike flurry thrown_spin' flock /tmp/botw-render.lock tools/combat_visual_check.sh build/round77/checks/combat after
```

The silhouette suite passes all 12 cases at the 12% floor. Combat contact checks
retain the original weapon poses and report a worst visible-tip error of
0.000011 m across 495 swing frames. The rendered strike error is 0.000123 m;
flurry and thrown-weapon recovery pass. Fauna, Stalkoblin and Talus suites pass,
as do the 5,039 weather FX checks and weather shading checks.

## Frame timing

Raw frame samples from the initial alternating runs and final-source refreshes
are retained in
`build/round77/{before,after}/perf-*.log`; the aggregate is
`build/round77/performance.json`. Protocol: native X11 1280×720, fixed scale 1,
uncapped presentation, fixed simulation step, frames 241–960 retained per run,
three repeats per scene (2,160 samples per phase/scene). Prepared assets are
bypassed equally in both phases. Each lock covers one render or a short matched
pair; other agents share the machine between runs. Interval and callback CPU
wall time are reported separately; these are not scanout measurements.


| Scene | Before interval p99 | After interval p99 | Before / after callback CPU p99 |
|---|---:|---:|---:|
| Combat | 14.768 ms | 17.259 ms | 6.032 / 9.750 ms |
| Old Man | 19.305 ms | 17.742 ms | 5.867 / 5.786 ms |
| Guardian | 15.465 ms | 15.289 ms | 5.816 / 7.975 ms |

All nine after logs identify the final source fingerprint
`c927a3a622a8dce0ca09`. Superseded source timings are archived separately;
no final-source repeats or outliers were dropped. Old Man and Guardian interval
p99 stay flat or improve. The combat tail prompted a separate check because its
three final runs span 15.327–22.242 ms p99, despite only 64 extra model triangles.
The new hand solves add about 0.013 ms to the Old Man update in a 10,000-update
CPU-only comparison (0.00871 → 0.02174 ms).


Two adjacent confirmation pairs used **before → after**, then **after → before**,
with GPU queries enabled equally in both phases. Their 1,440 retained intervals
per phase and every GPU sample remain in `perf-confirm-combat*.log`; the summary
is `build/round77/performance-confirmation.json`. They are kept separate from the
uninstrumented three-repeat table above.

| Combat confirmation | Before p99 | After p99 |
|---|---:|---:|
| Frame interval | 15.605 ms | 15.119 ms |
| GPU total | 4.774 ms | 4.722 ms |
| GPU character color pass | 0.117 ms | 0.078 ms |
| Callback CPU wall time | 7.520 ms | 9.365 ms |

The order-reversed confirmation shows no interval or GPU regression. The initial
combat interval result and higher callback CPU tail are retained rather than
claimed away: this shared-host evidence does not establish identical p99 under
all workloads. No frame-loop, weather, lighting, music or general performance
code was changed.
