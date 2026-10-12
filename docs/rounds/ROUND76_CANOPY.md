# Round 76: canopy edges, flower patches, and shaded grass

Baseline: `159dda5`, on the isolated `astra/work` checkout. Matched raw frames,
immutable source snapshots/executables, native-size crops, and all measurement
logs are retained in `build/round76/`. The existing untracked `assets/src` link
is unchanged.

The broadleaf upload now generates a 256×256 painted coverage texture. Nine
unequal overlapping elliptical dabs form three separated sprays, replacing the
source mask's isolated pointed leaves and frayed tips. Small irregular scallops
break the rounded outline. A narrow alpha ramp feeds the existing derivative-sized
dither in the depth prepass; a restrained pigment wash defines the rim. Pigment
continues through transparent texels, avoiding dark color contamination in mips.
The same mask reaches full cards, shadow cards, and the existing crown atlas.

This runs once per cached broadleaf texture at upload. There are no additional
per-frame samples, draws, vertices, or instance buffers. Pine needles, bark,
tree placement, wind, LOD thresholds, and the watercolor post-process are unchanged. No screen blur or hatch/dash patterns were introduced.

Procedural flowers now survive only inside the shared grass tufts, with a
maximum 40% retention in their centers and a smooth falloff to zero outside.
Rejected flowers use ordinary grass ribbons. The existing mesh prefixes and
random stream are unchanged, so all three grass LODs agree. A 100,000-point
sample over the plateau, conditioned on the pre-existing flower patch gate,
estimates 86.3% fewer flowers. This is a distribution estimate, not a count of
visible flowers: terrain, habitat, and screen visibility further filter them.

Shaded blades blend partway toward the existing meadow pigment, use the same
restrained canopy sky hue as the ground, and receive its open-meadow sky bounce.
The blend excludes charred/scorched blades and colored flower heads. It adds no
texture taps, noise evaluations, geometry, or draws.

The capture helper is `tools/round76_canopy_check.py`: run `prepare before` and
`capture before`, then `prepare after`, `capture after`, and `pairs after`.
Preparation reconstructs the baseline game sources from Git. Captures use exact
1280×720 X11 output, scale 1, 11:00 clear weather, and fixed simulation frames.
The helper owns one render lock per launch; do not wrap it in another lock.

Views include the exact crow camera at frame 150, its later frame 720, Hopper
Pond and forest at frame 300, and the requested title input `10:w+,300:w-` at
frames 600, 720, and 900. The earlier combat-155 composition is also reproduced
because it supplied the cited `crow-wing-detail-pair.png`. Crops preserve source
pixels without resizing. Full frames remain available alongside them.

Added checks cover the camp camera `-947,243,1956,-0.85,-0.45` at frame 120,
the old man's spot `BOTW_AT=-951,1876,2.5`, cave-mouth meadow
`BOTW_AT=-1054,1834,0.85`, Temple approach `BOTW_AT=-818,1950,3.14` at frame 300,
and the exact boar camera at frame 150. These use `BOTW_SKIP=1`. The boar camera
also repeats the critic's 10:00 clear lighting without `BOTW_SKIP`; the Temple
has a matching 10:00 check.
The camp crop and full frame show the former colored triangle scatter replaced
by quiet grass with a few flower tufts.

## Acceptance and measurements

The new crown silhouette is clearly better at native size: connected rounded
leaf masses replace the frayed sawtooth edge, while gaps between branches remain.
The meadow captures show much less colored scatter. The shaded-blade treatment
reduces the dark cool contrast against adjacent turf.

- `tree_visual_check.sh`: chopping, falling, floating, and burning pass on the
  combined build (`tree-combined/`).
- `vegetation_reach_check.jo`: all 144 cached/fallback comparisons pass.
- `draw_cache_check.jo`: all 155,648 RGBA bytes match.
- `weather_silhouette_check.py`: all 12 cases pass on the combined build;
  minimum contrast 0.17535 and paired separation 0.27317, above the 0.12 floor.
- Instrumented production vegetation submissions match the baseline frame by
  frame for frames 241–360 in both scenes. Forest color/depth draws are 67/67,
  with 24 or 54 shadow draws; overlook is 25/25, with 10 or 29 shadow draws.
  Grass retains its existing three mesh submissions and unchanged instance lists.

Three alternating pairs pass the frame-time constraint. Results in milliseconds:

| Scene | Before p99, pairs 1/2/3 | After p99, pairs 1/2/3 | Median p99 before → after | Pooled p99 before → after |
|---|---|---|---|---|
| Forest | 17.395 / 23.184 / 17.248 | 20.363 / 15.715 / 16.594 | 17.395 → 16.594 | 20.221 → 17.919 |
| Overlook | 14.766 / 14.802 / 16.209 | 14.803 / 15.509 / 14.782 | 14.802 → 14.803 | 14.831 → 14.837 |

Median GPU time across the three runs is 7.34 → 6.84 ms in the forest and
5.13 → 5.15 ms at the overlook. The first forest after run and the second
forest before run had noticeably higher tails; neither was excluded. The
all-run pooled frame p99 agrees with the median-run conclusion: forest improves,
and overlook is effectively unchanged. Every sampled vegetation triangle
report also matches between builds.

Raw runs use
`performance-combined/pair-{1,2,3}/{forest,overlook}/{before,after}/`.
Each pair owns one render lock and passes `--locked` to `performance_bench.py`,
so child measurements do not nest locks. Order is before/after, after/before,
then before/after. Each run is 1,200 frames at native 1280×720, scale 1, client
window loop, GPU queries enabled, stage trace disabled, with the first 240
frames excluded. Both binaries are warmed with a separate one-frame launch.
All runs, including noisy tails, are retained.

Final evidence validation covers 30 current 1280×720 screenshots across 15
matched views, their exact camera/frame settings, executable and source hashes,
and all required check results (`evidence-manifest.json`). Native crops and
full-frame pairs are in `after/`; `review.html` provides a native-pixel toggle.
