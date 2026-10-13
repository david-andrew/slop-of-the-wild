# Round 91 — Astra: tower clearance, malice, lightning and body fire

Baseline: `d05ace6`, merged from master into `astra/work` before editing.
Evidence stays in ignored `build/round91/`; no source assets or Sloppy release
files changed. `game/fx.jo` changes are confined to lightning. Camera, music,
terrain, water, shrine and canyon code remain outside this patch.

## Changes

- Architecture now discards every active camera-clearance fragment completely,
  including the ordinary approach before climbing begins. All structural
  materials clear the lens within one metre; structural timber also clears the
  player's one-metre body capsule. Held stone and shadow coverage remain solid.
- Malice uses overlapping, feathered density parcels instead of a connected tube.
  Unequal radial eddies and advected density break its silhouette; parcels climb
  continuously and fade before recycling. Daylight retains dark magenta smoke;
  night uses a restrained magenta glow. No bright ribbon centreline remains.
- Lightning uses unequal leaders and descending, tapering forks, with the
  existing soft glow and three pulses. Scripted inspection targeting now checks
  the real ground/water projection to place the impact below mid-frame. This
  changes `BOTW_BOLT`'s default inspection placement; normal storm targeting and
  explicit `BOTW_BOLT_AT` placements retain their existing rules. Nearby pond
  strikes still conduct through water and can shock Jo.
- Authored hair keeps a golden wet pigment, neutralizes the cloth tint's hue
  while preserving its luminance, and slightly reduces wet absorption (42% to
  36%). The wet fibre response removes the amber light cast. Brighter trials
  failed two body-contrast floors and were rejected.
- Burning Bokoblins have six narrow, tapered flames attached to their final
  animated forearms, calves and torso. Transparent submission keeps grass/sky
  from overwriting the tips. Torso-cloud emission is hidden without changing its
  RNG or particle lifetime budget. Attack, windup and sleep pose overrides no
  longer pin a burning runner into the wrong gesture. The existing finite panic
  movement and weapon drop are retained.
- Idle HUD fading was already present. The slot/sensor regression verifies the
  clock, bindings, partial/full stamina and wake events; no HUD changes were needed.

## Verification

`checks/` contains the headless, GPU and rendered logs. The full tower-base route
covers 422.5 degrees in 2,600 controller frames. Its rendered companion covers
2,601 frames / 422.8 degrees and checks **463,085,165 HDR pixels**, with zero
negative-alpha occluder fragments in the projected one-metre full-body envelope.
The small GPU fixture also checks 65,536 completely discarded pixels plus retained
held stone, distant stone and shadow coverage.

The title panorama checks 8,758,920 projections over five aspect ratios, both
input-release routes, and every visible title frame. Its matched background
retains **3.7721:1 minimum contrast** over 4,020 opaque atlas pixels.

The fire checks cover tapered flame shape, anchored roots, a finite 6.75m panic
run over 1.5s from four starting states, original fire RNG sequences, heat queries
and bounded tree discovery. Fauna checks include real rig footing, alerts,
quiet approaches, and normal frog/lizard/firefly catches. Input: 2,386/2,386.

The twelve-view silhouette suite passes its unchanged 0.12 linear-luminance
contrast floor. Minimum silhouette separation: **0.1288** (canopy rain); minimum
paired same-pixel separation: **0.2483** (canopy storm). All six wet captures
were refreshed after the final hair correction; the six unchanged clear/cloudy
paths retain their earlier matched captures, with provenance recorded in
`silhouette-final/provenance.json`. Weather checks also cover continuous smoke
advection, golden hue, material isolation, lightning branching/width/pulses,
waterline behavior and cosmetic RNG isolation.

## Visual evidence and reproduction

The nine scene folders each contain `before.png`, accepted `after.png`, and a
full-resolution `pair.png`; `comparison.html` supplies scene selection, a divider
and native-pixel inspection. Captures are 1280×720 at scene scale 1, at 11:00
except the 22:00 night view. `pairs.json` records the accepted source label and
image hashes. Trial captures remain separately labelled.

```sh
sloppy/bin/sloppy build game/main.jo -o build/round91/game
python3 tools/round91_visual_check.py build/round91/game after
sloppy/bin/sloppy tools/tower_base_climb_check.jo
flock /tmp/botw-render.lock env BOTW_SKIP=1 BOTW_TOWER=1 BOTW_HOUR=11 \
  BOTW_WEATHER=clear BOTW_SCALE=1 SLOPPY_PLATFORM=x11 SLOPPY_VSYNC=0 \
  SLOPPY_WINDOW=1280x720 SLOPPY_FRAMES=2600 \
  SLOPPY_SCREENSHOT=build/round91/climb-verified/final.png \
  sloppy/bin/sloppy tools/tower_base_climb_capture.jo
python3 tools/weather_silhouette_check.py --output build/round91/silhouette-final
```

The visual runner and silhouette tool lock their own renders; do not wrap them.
The full-base capture and small GPU fixture require the caller's single lock.
New CPU and full-base GPU regressions are registered in `run_all_checks.sh`.

Rejected at normal size: the first night-smoke pass was too dark; architecture
fade alone left a wooden root intersecting the waist; fixed lightning distances
left the pond impact too high; the first attached flames were too quiet and were
submitted before grass/sky. The accepted pairs include the corrected versions.
