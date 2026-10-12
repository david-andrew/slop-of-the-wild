# Round 73: vegetation in the main Plateau views

Baseline: `e955219`, isolated `sol3/work` checkout. Evidence is in `build/round73/`; raw build output is intentionally untracked. The round-60 critic images were still present and are copied into `reference/`.

## Appearance

Grass now varies blade proportions and facing per patch, with lance-shaped leaves and fewer scattered seed stalks. Larger density swathes make the forest floor quieter, while meadow gaps retain enough grass to read as a sward. Roots and woodland pigment sit closer to the terrain. Snow-margin grass shortens and thins across mixed coverage instead of disappearing at 25% snow.

Existing broadleaf cards vary in spray size, opening gaps between boughs without changing their UVs or topology. Distant crown atlases retain their original shape and two-triangle budget. The far-tree rim and atlas-lean experiment was rejected at the performance gate.

Green fern texels use muted moss/sage pigment with a narrower value range. They skip crown washes that were immediately overwritten. Snow on firs follows broken bough-scale caps, preserving dark needle texture and exposed boughs. Snow tint samples the surrounding ground over an 80 m span, feathering tree/rock caps beyond the binary climate boundary. The ground mesh/materials and tree placement are unchanged; this improves the vegetation transition, with the underlying terrain boundary still visible.

No texture preparation, texture caching or `vegetation_init` changes. The card shaping is an appearance change in the existing mesh-loading path. No character, shrine, puzzle or structure geometry changes.

## Visual verdict

All requested views were inspected at 1280×720, alongside seventeen paired crops at native pixel size (320×180 per side, before on the left). `before/` uses the immutable baseline executable; `after/` uses `trimmed-game`. Source/binary/image hashes and the exact source diff are in `final-source.json` and `final.diff`.

| View / crop | Judgment at normal size |
|---|---|
| Cave meadow / `meadow-grass` | Clearly better: less repeated blunt grass, more varied curved leaves and coherent swathes. |
| Title / `title-grove`, `title-far-grove` | Modest improvement: more open sprays within the near grove; distant spacing remains recognisable. |
| Forest / `forest-ferns`, `forest-grass` | Clearly better: sage fronds join the floor and isolated dark blade speckling is reduced. Canopy openings improve more modestly. |
| Hopper Pond / `pond-canopy` | Modest improvement to the broken crown edge; the pond composition remains similar. |
| Overview / `overview-snow` | Clearly better snowy firs: green/dark boughs remain visible between caps. Other grove differences are subtle. |
| Golden hour / `golden-grass` | Clearly better: quieter grouped grass with less uniform stalk detail. |
| Temple / `temple-grass` | Modest improvement: quieter fern colour and blade shapes. Frame 480 contains combat, so the vegetation crop avoids the actors. |
| Critic boars companion / `boars-ferns`, `boars-grass` | Clearly better frond colour and fewer isolated seed lines through the close grass. |
| Snow companion / `snow-caps`, `snow-sunlit` | Clearly better: snow no longer erases entire fir crowns; dark boughs and white caps remain distinct. |

The original wide-leaf experiment produced repeated chunky commas and was rejected. A tessellated crown/sine-profile version and subsequent far-rim/atlas-lean variants failed the frame-p99 gate. The final patch omits the far-rim/atlas-lean changes. An overly sparse meadow and overly dark snow experiment was also rejected. The final version restores meadow fullness and snowy caps, uses a polynomial grass profile and retains the original two-triangle atlas budget. No ruled lines, blur, dashed strokes or painterly smear were added.

## Performance

Five alternating before/after pairs per scene under one batch lock, uncapped X11 at verified 1280×720 and scale 1. Every run has 960 frames; the first 240 are excluded, leaving 720 warm frame samples per repeat. `SLOPPY_STATS=log`, raw frame logs and per-pass GPU queries are retained. The baseline/final order alternates each pair. No render/check/asset build overlaps this benchmark within this worktree.

| Scene | Before median frame p99 | After median frame p99 | Before median GPU mean | After median GPU mean |
|---|---:|---:|---:|---:|
| Forest | 20.018 ms | 19.355 ms | 9.936 ms | 9.334 ms |
| Overlook | 16.708 ms | 16.043 ms | 5.943 ms | 5.983 ms |

The final patch passes both frame-p99 gates. Raw logs/screenshots/load snapshots are in `paired-trimmed/`; `performance-trimmed.json` contains every repeat. The rejected far-rim/atlas-lean version had overview p99 15.742 → 16.255 ms across five pairs (`performance-accepted.json`), despite improved forest p99; it is not the committed patch. Historical experiment evidence is retained. Per-repeat wall tails still vary on this shared machine; these medians describe this fixed protocol, not a universal timing guarantee.

## Validation

The listed vegetation-related groups were run through the self-locking suite runner: `tree_test`, `vegetation_reach_check`, `clutter_check`, `landscape_check`, `integration_test`, `element_journey_check`, `fire_scan_check`, `art_shade_test`, `weather_shading_check`, `tree_visual_check`, and `draw_cache_check`: all PASS. Tree visuals cover chopping, falling, floating and burning. Logs: `quiet-cpu-checks.log`, `trimmed-tree-visual.log`, `trimmed-draw-cache.log`. The fern optimisation only omits overwritten shader work. Before dropping the rejected far-view changes, five balanced companion captures (meadow, forest, golden hour, boars and snow) were pixel-identical to the same variant with the fern optimisation.

`tools/prepare_assets.sh` and `tools/prepared_assets_check.sh` PASS; the final prepared check also passed full audio/world/mesh/collision/roof/ownership/RNG byte equivalence (`prepare-assets-trimmed.log`, `prepared-assets-check-trimmed.log`).

Every render owns `/tmp/botw-render.lock` once. Scratch capture and paired performance scripts self-lock their complete batches; self-locking suite/asset tools are called directly. No build evidence is force-added.
