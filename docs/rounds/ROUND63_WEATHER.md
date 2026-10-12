# Round 63 weather and electrical feedback

Base: `a0a8d7d`, worktree `botw-clone-sol2`, branch `sol2/work`.

Electrical bolts now use 28 connected narrow trunk segments and 16 tapered fork
segments instead of up to 4,148 overlapping glow sprites. Lower bends are spaced
closely enough to remain jagged in the near Hopper Pond view. Core width uses the
actual camera-to-strike distance, including `BOTW_BOLT_AT` overrides.

Water flashes use eight short radial leaders with small twigs inside the accepted
connected wet region. Obstructed leaders retain the flood graph's route around
cover. Each filament checks wet connectivity before bending sideways and retains
its accepted route in `strike_paths`. The existing 1,680-segment conduction cap
and 6,000-particle pool remain in place. Water conduction reaches 16 m; the metal
relay reach remains 14 m. The supplied pond wader is approximately 14.95 m from
the forced strike, so the previous 14 m water radius could not hurt him.

An accepted electrical wound starts a 0.32 s body-arc flicker alongside the existing
hurt/flinch pose. A forced atmospheric strike samples the flinch immediately,
because it occurs after the normal animation update. Invulnerability and blocked
hits do not start the flicker. Held-weapon shocks preserve their existing damage
and equipment-removal behavior.

Electrical particles carry the `.arc` emissive kind and use one sparse draw after
watercolor, before the HUD. This draw samples the existing opaque depth copy,
so foliage, buildings and figures still occlude lightning. Both core and soft halo
skip paint, pigment pooling, ink and image wobble. No mask target or full-screen
pass is added. The additive instance buffer is reused. **`post.jo`, `shade.jo`
and `charshade.jo` are unchanged**, keeping Astra's material brushwork separate.

Rain retains the 8,200-streak budget and existing two depth populations. Wider,
brighter streaks with varied width/length and stronger near opacity make that
population visible. Splash-ring width and visible opacity increase without changing
emitter random calls, particle count, shelter rejection or diversity distributions.
Storm grading preserves green/brown saturation; wet grass retains more of its
albedo hue. Lightning increases the sky deck visible through canopy gaps and
uses stronger multiplicative ambient light with less additive white on the ground.
Night campfire light uses a broader 20 m falloff and lower peak intensity, extending
the warm-to-moonlit transition over more grass.

## Evidence and reproduction

All evidence is local under `build/round63/` and intentionally excluded from git.

- `before/`: frozen base executable and first diagnostic captures.
- `before-exact/`: exact draw-end captures from isolated `a0a8d7d` sources.
- `before-exact-seed31/`, `after-exact-seed31/`: diagnostic captures with ambient
  strikes before the forced checkpoint; excluded from the final comparison.
- `after/`: first implementation diagnostic captures.
- `after-exact/`: final production captures for pond strike, forest storm,
  pond rain and night camp.
- Each view contains `frame-299.png` (pre-strike), `frame-300.png` (strike),
  `frame-302.png` (+2), `frame-305.png` (+5), `final.png` and `run.log`.
- `weather-silhouette/`, `weather_silhouette_check.log`,
  `weather_transition_check.log`, `daylight_check.log`: required visual checks.
- `weather_fx_test.log`, `element_check.log`, `weather_shading_check.log`,
  `integration_test.log`: headless verification.
- `gpu/summary.json`, `gpu_check.log`: two paired large-output repeats per scene,
  verified 2133×1200 X11 client output, fixed 0.8 scene scale, 600 producer frames per run,
  steady GPU samples from frame 240 onward; includes the atmospheric strike at 300.

`tools/round63_weather_capture.py before|after --output <directory>` captures the
currently checked-out source, using the full production entry point with a fixed
game RNG seed 63, weather RNG seed 2, fixed 1/60 s simulation, and four screenshot
checkpoints. Seed 2 has no ambient strike during the first 306 updates, isolating
the forced strike and its damage reaction. The source hashes and both seeds are
recorded in each capture manifest.
Use `before --source-revision a0a8d7d --output build/round63/before-exact` to
reproduce the isolated baseline. The original `before` executable is retained.
Screenshots are taken at draw end, after the world and HUD but before presenting,
so each filename names that exact frame. The production update-start screenshot
hook can read an older back buffer; its first diagnostic captures are retained
but are not used for the final strike-frame comparison. The fixture uses the requested views and pond impact
`BOTW_BOLT_AT="-1201.7,1655.7"`. Forest and pond strikes occur on frame 300.

`tools/round63_weather_gpu.py` compares the retained base executable to the current
source. Both scripts own their render locks; **do not wrap them in another flock**.
The silhouette, transition and daylight checks also own their locks.

Final results and image comparisons are recorded in `build/round63/report.md`.

## Verification

- `weather_silhouette_check`: 12/12 passed; minimum silhouette contrast 14.27%,
  minimum paired separation 29.51%, both above the 10% requirement.
- `weather_transition_check`: all four views passed, including shelter, forest,
  snow and shrine exit.
- `daylight_check`: all seven dawn/dusk views passed; largest brightness step 8.1.
- `weather_fx_test`: 5,034 passed; `element_check`: 19 passed;
  `weather_shading_check`: passed; `integration_test`: 1,316/1,316 passed.
- Large-output GPU probe: all six final runs passed the 20 ms p99 budget.
  Maximum final p99 was 15.544 ms. Maximum electrical draw was 0.442 ms,
  including the forced pond strike. Twelve raw before/after runs are retained.

The exact quiet-seed pond captures retain 12 HP at frame 299. The baseline remains
at 12 HP through 300/+2/+5; the revised source drops to 8 HP with `hurt` state on
frame 300 and retains the flinch/body flicker at +2/+5. All 32 checkpoint images
are 1280×720. Final capture and GPU manifests match the checked-out game sources.
