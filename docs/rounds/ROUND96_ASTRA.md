# Round 96 — Astra: forest wetness and weather

Baseline: `431a3f5`, branch `astra/work`. Work and evidence are confined to
`botw-clone-astra`. Every game process ran inside one `/tmp/botw-render.lock`;
there are no nested render locks. Images, binaries, frozen sources, settings,
logs, and the one-minute movie remain in ignored `build/round96/`.

## Forest-floor diagnosis

The fixed camera is `BOTW_SKIP=1 BOTW_AT=-1000,1620,3.14`, frame 300,
weather RNG seed 31. Both 11:00 and the original default-hour route are
captured, with matching clear weather. The latter starts at 6.6 and advances
normally to 6:41; the 11:00 comparison freezes the day clock.

`layers/before/` and `layers-default/before/` add terrain, vegetation,
projected shadows, canopy shade, cloud shadow, wet darkening, puddles,
storm illumination, storm post grade, water, actors/props, and effects in
that order. Every layer redraws the same simulation instant. Full-storm
single-layer ablations and root/canopy/puddle/burn masks cross-check the result.

The broad dark floor is terrain wet absorption, not a cloud tile or decal.
`terrain_fs_surface` multiplied already-dark moss/litter by as little as 0.45
(`0.43 + forest * 0.12` absorption). Storm illumination then compressed those
patches into a nearly black mass. Removing projected shadows, cloud shadow,
water, burn, contact pools, or puddle cards changes **zero pixels** in the
sampled left/right floor regions. Puddles have no effect in the right region
and a small reflective contribution on the left; canopy shade contributes
only a few RGB levels. See `ablation-diffs.json`, the contact sheets, and
per-layer difference images for the numerical and visual evidence.

`forest_wet_absorption` now accounts for pigment value: dark moss/root soil
absorbs 24% and brighter litter up to 43%, with a smooth transition. It
preserves value order and wet/dry continuity. Open turf, stone, and dry
terrain retain their prior response. This retains the forest's moss and
leaf-litter pattern while removing the over-darkened patch.

Rejected diagnostics: removing wetness entirely turns the floor into dry
bright ochre; removing forest pigment erases the litter. Neither was applied.

## Weather changes

- Rain keeps the existing 6,200 far and 2,000 near seeds. The falling volume
  now wraps below the ground/lens and respawns overhead; wind follows drop
  height. Near-volume edges fade before horizontal wrapping. Storms retain
  more near drops and lengthen their varied streaks by 35%. Near/far width,
  opacity, and length variation remain. The initial wrapped-rain draft was
  rejected because its drift phase could jump sideways; the accepted path
  passes 4,734 continuous-motion samples.
- A local dawn correction puts the 6:24 sun at **2.572 degrees** above the
  horizon. It fades out by 7:30, leaving daytime and dusk trajectories intact.
  The low eastern disk uses warm, bounded radiance instead of bleaching its
  pink lighting color to white. The captured disk meets the distant ridge.
- Two slow cloud-bank oscillations modulate sky, haze, and diffuse/direct
  illumination continuously, independently of the day clock. Quiet lighting
  remains bounded; flash behavior retains its existing multi-stroke pulse.
  The oscillations fade in only as the dense deck develops (storm strength
  0.8–1.0). The initial ungated version reduced the cabin clearing contrast
  to 6%, failing the existing 10% check, and was rejected. Full-storm
  captures retain the accepted lighting cycle.
- A saved countdown draws one interval per natural strike, **10–20 seconds**,
  replacing the per-tick random trigger. Six bounded visibility queries select
  nearby ground/water contacts in the actual view. Natural bolts now render in
  free-camera inspection too. Scripted strikes and their damage rules remain.
- Save files retain the cloud phase, countdown, and weather RNG. Older saves
  receive defaults; malformed/duplicate clock records are rejected. An
  imminent strike and the rounded phase-wrap boundary both resume correctly.

## Validation and reproduction

`round96_weather_check.jo` is registered in `run_all_checks.sh`. It covers
30/60/120 Hz cadence, fixed-hour continuous lighting, dawn elevation, 80
camera/phase target combinations, 50 occluded-target cases, rain motion, and
bounded/ordered wet pigments. Existing weather FX, weather shading,
environment update, silhouette-analyzer, and save/resume checks pass.

The cabin transition passes its unchanged 10% clearing threshold: 74 → 82
display luma (baseline 73 → 82). Forest, snow, and shrine-exit transitions
also pass, with largest static brightness steps of 9.7, 7.7, and 7.7.
The `final/` frozen snapshot includes the
transition gate; its full-storm render is pixel-identical to `after/`.

All seven daylight routes pass (meadow/forest/snow dawn and dusk, plus
pond dawn), with a maximum brightness step of 8.1 and exactly one dimmed
moon/sun handover per route. `daylight-verify.log` records the clean final
verification; the rendering run completed all seven views but its trailing
shell read was disrupted by editing the locking wrapper while it was running.

The sky camera check passes all five views: gameplay/free-camera grades
match exactly, their sky RGB drift is 0.0000, and storm/clear sky brightness
is 43.7/136.0. Night and cloudy reference views are retained.

The full silhouette matrix passes all 12 meadow/canopy/pond weather views.
The lowest contrast is 0.143 against the 0.120 floor; storm-canopy contrast
is 0.444 with 0.495 paired separation. All captures are verified 960×540.

The matched image checks show 1,098 → 2,609 bright effects pixels, with the
same seed budget. Clear noon is pixel-identical. At 6:24 the disk centroid
moves down 21.2 pixels and its mean blue channel drops from 220 to 179.

The one-minute fixed-hour capture has four visible contacts at 16.30, 31.25,
42.13, and 52.80 seconds, 19.9–41.8 m from Jo, with health unchanged.
Quiet sky luminance ranges from 0.482 to 0.644; the sampled rendered scene
ranges from 39.4 to 50.9 display luma. The baseline sky is constant at 0.562,
and its eight strikes are 198–480 m away, including gaps under two seconds.
See `minute/after/storm-minute.mp4`, the contact sheet, and `report.json`.
PNG capture time is not a performance benchmark.

Reproduce historical/current snapshots with:

```sh
python3 tools/round96_capture.py prepare before --ref 431a3f5
python3 tools/round96_capture.py prepare after
python3 tools/round96_capture.py capture before storm clear dawn layers storm-default clear-default layers-default minute
python3 tools/round96_capture.py capture after storm clear dawn layers storm-default clear-default layers-default minute
python3 tools/round96_capture.py pairs
python3 tools/round96_report.py
```

Run the rendered regression checks directly:

```sh
python3 tools/weather_silhouette_check.py --output build/round96/silhouette
BOTW_TRANSITION_OUTPUT=build/round96/weather-final SLOPPY_PLATFORM=x11 SLOPPY_VSYNC=0 BOTW_NOVSYNC=1 tools/weather_transition_check.sh
python3 tools/sky_camera_check.py --output build/round96/sky
BOTW_DAYLIGHT_OUTPUT=build/round96/daylight tools/daylight_check.sh
```

Captures and daylight checks acquire and release the render lock per game process.
Run self-locking checks directly, without an outer lock. An initial baseline
batch held the lock too long; that batch mode was removed after coordinator feedback.
