# Round 79: meadow paint and muted leather

Baseline: `93c4e79`, branch `astra/work`. Matched 1280×720 captures, source/model
snapshots, rejected iterations, logs and before/after pairs are under
`build/round79/`. Captures use one shared render lock per game process.

The shared terrain/blade palette now has dry gold, lush green and cooler clover
washes at roughly 25–80 m scales, using the existing noise calls. Flower blades
occupy smaller, denser damp patches. The worn cave/camp/Temple path has a quieter
earth palette; a new narrow fork follows clear ground from the old man's camp
around the Temple's western lawn to its southern ruins. Ragged bare-earth nests
sit around existing meadow outcrops. No geometry, prop budget or draw pass was
added. Heights, collision and scatter inputs remain unchanged.

The additional wear is baked into the existing GPU material texture, with a
separate CPU payload so scatter eligibility and its random stream stay stable.
The prepared terrain pack stores that payload and invalidates through its
source key. Prepared/generated/mixed-pack checks also assert that dressing
preserves CPU materials and the forest/rock/snow upload channels.

Boots, bracers and belt UV islands are painted together after texture value
grouping. Both orange leather and pale bands now share a muted brown/taupe value
range, retaining the source seams. All three dressed-hero outfits receive the
change. The old-man texture variant, bare hero, skeleton, geometry, draw count,
contacts and grips are byte-identical to baseline.

The initial turquoise clover wash was rejected at native size. The first path
layout was replaced after collision-survey review; the accepted route also
passes a direct production-controller walk. Final acceptance includes the
requested overview, cave-to-camp walk, old-man camp, Temple surrounds, combat
155/300, golden hour and forest views. The gallery is
`build/round79/comparison.html`; full-size pairs are in `build/round79/pairs/`.

Validation:

- `tools/prepare_assets.sh`: PASS.
- `tools/prepared_assets_check.sh`: PASS, full byte equivalence, including the
  additional material upload and its scatter-preservation assertions.
- `tools/journey_check.sh`: PASS, nine legs, 4,865.54 m / 1,123.00 simulated seconds;
  zero stuck points, hard falls or stamina exhaustion.
- Painted-path controller walk: PASS, 260.27 m / 42.70 seconds, maximum slope
  28.7°, zero climbs, falls, hard falls, stuck points or stamina exhaustion.
- `python3 tools/hero_model_check.py --baseline build/round79/before/assets/models`:
  PASS; zero geometry adjustment. `leather-texture-check.json` additionally
  checks exact header/skeleton/geometry bytes and unchanged old-man/bare assets.

Performance uses alternating immutable before/after executables, X11 1280×720,
fixed scale 1, uncapped presentation, 1,200 frames per run and three repeats per
view. The first 240 frames of each run are excluded; each pooled result has
2,880 measured frames. Full interval, callback wall/thread and upload counts
are retained in `build/round79/performance.json`.

| X11 view | Frame p99 before → after (ms) | Callback-wall p99 (ms) | Median GPU total (ms) |
|---|---:|---:|---:|
| overview | 15.99 → 15.98 | 8.27 → 7.25 | 4.39 → 4.39 |
| walk | 15.14 → 15.97 | 10.22 → 11.80 | 4.41 → 4.42 |
| combat155 | 16.54 → 15.01 | 10.37 → 7.56 | 4.49 → 4.48 |

Maximum per-frame uploads remain **6 / 43 / 29** in overview / walking /
combat. The walking X11 p99 rises 0.83 ms despite essentially identical GPU
cost (terrain 1.48→1.49 ms; grass 0.34→0.34 ms). A separate three-pair X11
confirmation, keeping each before/after pair in one short lock, measures
13.84→14.49 ms; median callback wall time is 3.141→3.145 ms. These tails
include blocking/presentation and shared-machine scheduling. They are retained
in `walk-confirmation.json`, not discarded or combined with the first batch.

The recommended Wayland-mailbox mode was checked separately with GPU profiling
disabled, the production window loop, native **2133×1200** output and fixed 0.8
scene scale. Three alternating short paired batches of 960 frames exclude the
first 240 frames each (2,160 samples per phase). All six logs confirm the
`wayland+libdecor dma-buf, mailbox` backend and identical output/scale.
Frame p99 is **11.89→11.51 ms**; median is
**7.47→7.50 ms**. Callback-wall p99 is
**10.63→10.53 ms**. This normal-mode check shows no p99
regression. Exact repeats are in `mailbox-confirmation.json`. An initial
900-frame native-window trial is retained under `unprofiled-default-trial/`;
it was excluded because it did not explicitly log/select the backend and its
frame count left an incomplete logging batch.
