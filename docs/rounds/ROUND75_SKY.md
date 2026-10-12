# Round 75: title sky and weather layers

Baseline: master `b720d62`, fast-forwarded into `sol2/work`. The work is limited to sky/effects, title opacity, environment grading, and their checks. It does not change vegetation, terrain, structures, farland geometry, or the title camera/composition.

## Changes

The Calamity uses ninety tangent-aligned cards arranged into three uneven coils around the keep. Charcoal undersides, dark crimson-purple shoulders, and faint broken crimson seams remain visible at title distance. The cards now share the full-scene alpha batch instead of the half-resolution smoke target. Their analytic rotation is 0.018–0.026 radians/second, without particle RNG. The title projection test uses the renderer's actual positions, radii, rotations, and complete card envelopes.

Cumulus banks use three overlapping upright lobes, a shallow base, and two joined edge wisps. Rounded lobe surfaces join smoothly in depth, blending their slopes across overlaps, with warm sunlit shoulders and cooler grey-violet undersides. Seeded proportions, mirrored profiles, and elevation offsets vary the banks. The contour contains no high-frequency fragment noise or blur pass. A world-projected Castle clearing separates ordinary cloud pigment from the Calamity in both the panorama and overlook views.

Night clouds have dimmer moonlit pigment and wider painted opacity shoulders. Overcast keeps broad overlapping rolls and internal cloud shading in its continuous deck. Environment saturation, moonlight, golden-hour colour, and particle lighting now refresh before the free-camera return, so inspection uses the same weather-driven grade as gameplay.

The lettering still waits until `TITLE_LETTERING_START = 9.0` after the crest. Its fade to full opacity takes 0.85 seconds instead of two seconds; fade-out, title hold, and camera handoff are retained. The panorama check requires full opacity within one second of appearing.

## Evidence and checks

Matched before/after PNGs and rejected iterations are under `build/round75/`. The title uses `BOTW_TITLE=1 SLOPPY_INPUT="10:w+,300:w-"` at frames 600, 750, and 900, with the production default morning clock. Other requested views include the overview camera `-700,330,2150,-0.8,-0.35`, golden hour `BOTW_SKIP=1 BOTW_AT="-1030,1805,1.57" BOTW_HOUR=6.4`, cloudy and storm skies, and night at hour 23. The supplementary sky fixture pins weather RNG seed 31 and compares the same projection through free-camera and gameplay update paths outside a lightning flash.

Verification results are recorded in `build/round75/final-checks/` and `build/round75/sky-verified/`. All requested checks pass. Lettering contrast minima at frames 600/750/900 are **3.4312:1 / 3.5728:1 / 3.5679:1** over 5,177 opaque atlas pixels. All twelve weather silhouettes pass: minimum ring contrast **0.1833**, minimum paired separation **0.2732** (required 0.12). Matched storm camera grades agree exactly, with **0.0000 RGB-level drift** in the pure-sky sample; storm/clear sky brightness is **78.5 / 140.4**. Canopy, snow, and shrine-exit transition brightness steps are **9.7 / 8.9 / 6.5** levels (limit 12). The uninterrupted wake-to-control opening passes with the faster lettering. Required commands:

- `sloppy/bin/sloppy tools/title_panorama_check.jo`, including actual-pixel `BOTW_TITLE_BACKGROUND` comparisons at 600/750/900.
- `sloppy/bin/sloppy tools/title_handoff_check.jo`.
- `tools/weather_transition_check.sh`.
- `python3 tools/weather_silhouette_check.py`.
- `tools/opening_check.sh`.
- `python3 tools/environment_visuals_check.py` and `python3 tools/sky_camera_check.py`.

Every game process takes `/tmp/botw-render.lock` once. The silhouette checker now releases it between individual weather captures rather than holding it over a four-render view group. Self-locking scripts are called directly. No evidence or binaries under `build/` are staged.
