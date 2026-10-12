# Round 64: Talus motion, field journey and terrain pigments

Base `0d1b209`, branch `sol3/work`. Render artifacts and raw checks remain in
ignored `build/round64/`; this report and reproduction tools are committed.

## Talus

The attached-player branch no longer holds one pose for twelve seconds. The
shared boulder pose breathes, settles the arm masses and makes a restrained search
turn about the last approach bearing. A shake warns after 4.2 seconds of attachment
and lasts 1.6 seconds. The heave spends 120 stamina while gripping/mantling or 200
while standing; it ejects Link only if his wheel is exhausted. The next attempt
starts after another 4.2 seconds. Idle and shaking transforms feed rendering,
climbing sections, ore position, rider carry and planted-foot carry together.
The documentary ride check compares feet from their cached IK support pose
through both production motion and the forced turn, retaining the 0.1 mm root
and 1 cm foot limits. Shoulder swings use a close stance on the safe rear apron
and aim toward the current ore bearing; the low crown is below the cutting arc
when Link stands in the middle of the deck. Controller movement, hit callbacks and the fixed weak-point/defeat requirements remain production ones.

The upper front planes now have a broken highlighted brow over two dark fracture
hollows. This is pigment on the existing skin in `talus.jo`, preserving the ore
crown, Astra's faceted geometry, solid envelope and instanced draw count. No post,
shade, charshade, storm or fire-pool changes are part of this work.

At 30/60/120 Hz, a real production catch followed by fourteen seconds of idle
climbing survives two shakes, stays attached, and spends exactly 240 stamina.
The ordinary approach/climb/mantle, riding and exhausted-ejection cases also pass.

## Field journey

Before: four recovered stuck detections and one stamina exhaustion. The points:

| Route | Position | Cause / correction |
| --- | --- | --- |
| Oman Au | `(-677.709,171.856,1517.944)` | Oblique approach meets the low round base lip before the pad lifts the feet. A drawn outer tread and matching cylinder bridge it; base collider height matches the drawn 1.2 m base. |
| Keh Namut | `(-1322.814,346.936,2133.429)` | Sliding/climbing on a steep narrow Hylia bank. |
| Keh Namut | `(-1318.327,333.688,2120.022)` | Same bank's changing gradient causes repeated regrabs. |
| Temple approach | `(-1324.825,356.375,2143.950)` | Same bank, climbed in the opposite direction; eventually exhausts stamina. |

A short graded pass, feathered into the southern Hylia bank, corrects all three
mountain points without changing player traversal tuning or the summit. The
planner's previous circular snow-bank avoidance rule was removed. The runner now
asserts zero stuck episodes and zero stamina exhaustions after retaining its
metrics, source hashes and trace for diagnosis.

After: all nine legs pass, **67,374 frames / 1,122.90 simulated seconds /
4,851.34 metres**, zero stuck episodes, zero stamina exhaustions. The Temple
field approach climbs for zero seconds instead of 27.08 seconds. The separate
roof ascent still uses its real climbable rest ledges and production meeting.

## Terrain colour inputs

The forest floor now keeps distinct copper leaf drifts, moss cushions and bare
soil at all view distances. A root-soil apron around actual trunk centres is
baked into the unused green channel of the existing canopy texture. Canopy gaps
keep lighter moss/litter, and the old duplicated litter stack and distant fade
to one dark green were removed. Leaves remain a close-view pigment detail. Wet organic litter/root soil absorbs
more light than open turf, preserving Link’s silhouette under the storm deck.

The ground and grass share a smooth low-sun pigment response: warmer sun-facing
paint and cooler violet shadow paint. It follows solar elevation, direct-light
strength and warm sunlight, fading out under moonlight or deep storm darkness.
Temple-side slopes reuse the baked moisture field for dry soil islands and darker
vegetated gullies. Snow's material warp is smaller and elongated with the wind;
the boundary retains a mixed scree/tundra margin instead of broad round lobes.

## Startup integration

The existing prepared-world asset key includes `terrain.jo`, `worldgen.jo` and
`structures.jo`, so a cache baked before these changes is rejected automatically.
Regenerate the prepared world from the merged sources when integrating Sol's
startup-baking work. This branch uses the production regeneration fallback during
captures; steady-state GPU samples exclude startup and the first 240 frames.
Preserve RGBA when baking/uploading canopy data: R remains canopy coverage,
and G now carries the trunk-centred root-soil apron.

## Reproduction and evidence

Build each frozen phase before modifying its source:

```sh
mkdir -p build/round64/{before,after}
sloppy/bin/sloppy build game/main.jo -o build/round64/before/game
# apply this commit's game changes, then build the second phase
sloppy/bin/sloppy build game/main.jo -o build/round64/after/game
tools/round64_capture.sh before
tools/round64_capture.sh after
python3 tools/round64_report.py
python3 tools/round64_gpu_check.py
# The retained final batch uses a separate immutable executable and output folder:
mkdir -p build/round64/after-final
sloppy/bin/sloppy build game/main.jo -o build/round64/after-final/game
python3 tools/round64_gpu_check.py --after-binary build/round64/after-final/game --output build/round64/gpu-final
python3 tools/round64_visual_check.py
```

`round64_capture.sh` locks every render separately. `round64_gpu_check.py` owns
one lock around its alternating matched batch; do not wrap either tool in an
outer lock. The matched before/after tools force `BOTW_NO_PREPARED_ASSETS=1` so an old frozen
executable cannot accept a later bake using runtime source keys. Retained captures
already used regeneration fallback because this branch invalidated the old cache.
The GPU check measures 2133×1200 X11 output at the default 0.8 scene
scale with raw timer queries and frame intervals. The existing
`cliff_capture_window.py` helper withdraws and sizes only the child client, and
the check verifies the PNG dimensions. It retains warm frames 241–700
and rejects GPU p99 at or above 20 ms in any changed view. The report states
sample counts and frozen executable SHA-256 values. Each phase/view is one run,
so it does not claim the three-repeat ranges of the broader benchmark suite.

Paired PNGs: `forest-comparison.png`, `boars-comparison.png`,
`golden-comparison.png`, `overview-comparison.png`, `snow-comparison.png`,
`hylia-pass-comparison.png` and `talus-comparison.png`. Continuous Talus sheets:
`talus-before-sequence.png` and `talus-after-sequence.png` (frames 100–600).
`talus-motion-comparison.gif` loops post-rise frames 200–600 at 3.33× speed.
The interactive comparison is `build/round64/index.html`; its small preview
copies are derived from the full-resolution matched GPU captures at frame 720.

## Validation

```sh
tools/journey_check.sh
tools/traversal_check --headless --out build/round64/traversal
sloppy/bin/sloppy tools/talus_test.jo
sloppy/bin/sloppy tools/talus_skin_check.jo
sloppy/bin/sloppy tools/talus_mesh_check.jo
sloppy/bin/sloppy tools/camera_check.jo
sloppy/bin/sloppy tools/fauna_test.jo
tools/talus_save_element_check.sh
TALUS_CAPTURE_LOCK=1 tools/talus_visual_check.sh build/round64/talus-visual
tools/daylight_check.sh
python3 tools/weather_silhouette_check.py --output build/round64/weather-silhouette
```

The visual Talus runner uses its per-capture lock mode above; daylight and weather
silhouette runners own their locks. Do not put another `flock` around these calls.
The final retained `round64_visual_check.py` batch also owns one lock, and calls
its compiled documentary actor and weather capture helpers without nested locks.
Its default run regenerates all seven after views, all eight Talus cases and all
twelve weather silhouettes from the final game sources; `visual-sources.json`
records their hashes. `--skip-after`, `--skip-weather` and `--talus-scenes` support
focused fixture reruns while retaining completed captures. Weather image analysis
still runs after the render lock is released.


- `journey_check.sh`: all nine legs; zero stuck and zero stamina exhaustion.
- `traversal_check --headless`: 997/997 assertions.
- `talus_test`: 158/158 checks, including two held idle shakes at all three rates.
- `talus_skin_check`, `talus_mesh_check`, `camera_check`, `fauna_test` and
  `talus_save_element_check.sh`: pass.
- `journey_controller_check` and `architecture_test`: pass.
- `daylight_check.sh`: all seven dawn/dusk views pass, 97 logged samples each,
  exactly one shadow-light handover each; largest brightness step 8.0 (limit 10).
  Captures and logs are copied to `build/round64/daylight/`.
- `round64_gpu_check.py`: all six changed views pass the 20 ms GPU p99 budget
  at verified 2133×1200 output, scale 0.8, including wet storm forest. Each
  phase/view has 460 warm queries. Final logs/data: `build/round64/gpu-final/`.
- `weather_silhouette_check`: all twelve clear/cloudy/rain/storm cases pass.
  Minimum silhouette contrast is 0.108 (canopy rain; limit 0.10). Canopy storm
  contrast is 0.229, with paired separation 0.287. Final captures and measured
  pixels: `build/round64/weather-silhouette-final/`.
- Rendered Talus: all eight cases pass (dormant, reveal, awake, front, climb,
  ride, weak point and defeat). Ride root error is 0.000000 m and worst planted
  foot drift is 0.000440 m over 495 samples. The weak-point case reaches 230 HP
  by frame 900; the stronger sword defeats the Talus and produces all six ore
  drops by frame 1800. Final images/logs: `build/round64/talus-visual-final/`.

## Matched GPU results

| View | GPU p50 before → after (ms) | GPU p99 before → after (ms) | Frame interval p99 before → after (ms) |
| --- | ---: | ---: | ---: |
| forest | 12.20 → 11.95 | 15.13 → 14.54 | 19.00 → 18.50 |
| golden | 8.34 → 8.62 | 11.36 → 11.23 | 15.94 → 16.41 |
| overview | 7.43 → 7.40 | 9.81 → 9.64 | 16.76 → 17.02 |
| snow | 8.47 → 8.91 | 10.95 → 11.20 | 16.39 → 16.83 |
| talus | 11.62 → 12.34 | 14.63 → 15.26 | 18.52 → 18.52 |
| wet-forest | 12.11 → 11.49 | 15.34 → 14.85 | 20.03 → 18.96 |

Final-source GPU p99 is below 20 ms in every view. Full means, worst samples,
frame intervals and frozen executable hashes are in `build/round64/gpu-final/report.json`.
Each phase/view is one matched run, not a three-repeat range. The earlier pigment
run (`gpu/`) had a 21.33 ms forest frame-interval p99; the intermediate wet-pigment
run (`gpu-pre-face/`) had a 20.62 ms wet-forest frame-interval p99. They are retained
for transparency, rather than treated as repeat ranges for the final executable.
The rejected size-mismatch probe is only in `diagnostic/gpu-wrong-size/`.
