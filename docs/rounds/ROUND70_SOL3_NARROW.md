# Round 70 sol3: narrow revision

Base: clean master `76a45952c7d9a96d4f38662f16e0671a6ba40eea`.
The rejected `7d65743` is not an ancestor of this branch.

Only two game modules change:

- Snow-free ground bush leaf cutouts become denser from above, with no dither or alpha blending.
  The ground-view colour and cutout calculation stay unchanged. The overhead
  pigment preserves the existing luminance, with authored leaf folds bounded
  to 82–118% of that value and approximately unchanged mean brightness.
  Separate bush colour/depth programs keep the other foliage colour programs,
  textures, geometry, placement RNG and shadows unchanged. Existing owned Bush
  meshes used as tree-crown lobes retain master shading, using a lossless
  GPU-only snow-channel tag; snowy shrubs also retain master shading.
- The two west receiving-pool mist emitters select the existing continuous soft
  density fringe. Their positions, sizes, instance counts and billboard
  geometry stay unchanged. Their zero stretch avoids the rain-streak path.
  Every other waterfall retains master's exact particle payload.

No optional Temple floor change is included. Paving, grass coverage, marsh,
fir boughs, snow coverage, cliffs and terrain retain the base revision's source.

Evidence lives in this checkout's ignored `build/` directory:

- `build/task70-sol3-narrow-master/`: all fixed critic captures from an immutable
  clean-master fixture.
- `build/task70-sol3-exact-final/`: final critic pack.
- `build/task70-sol3-narrow/`: matched camp, pool, Temple interior and ground
  approach captures, source manifests, check logs and alternating paired timings.
- `build/task70-sol3-narrow-mask/`: diagnostic-only captures recolouring bush
  materials and the two mist emitters to locate their visible regions.

The baseline fixture was copied and built before any game edits. Its capture
runner omits redundant startup measurements; it uses the critic pack's original
scene fixtures, seeds, weather, time, viewport, fixed step and render-lock rules.
Final captures use the unmodified `tools/critic_pack.py` CLI.

Validation:

- Full final critic pack: **PASS**, including 45 captures, the 120-second native
  real-dt route, 13 audio exports and all eight bundled checks. All production
  source hashes match the final working tree.
- Viewed all 45 matched master/final shots, downscaled side by side in 23 pages
  (`build/task70-sol3-narrow/comparison/`). Current viewed-page hashes are recorded
  in `reviewed-pages.sha256`. Also viewed the final matched camp and ground
  approach timing captures (`final-camp-pair.jpg`, `final-approach-pair.jpg`).
- Exact per-channel RGB comparison: **35 entire shots identical**; the remaining
  ten differ only inside the approved materials and their existing filter
  footprint. **Zero changed pixels outside those regions**. Alpha is fully
  opaque in every compared output. See `pixel-comparison.json` and
  `region-verification.json` under `build/task70-sol3-narrow/`.
- Region checks use a diagnostic bush-material colour mask and actual west-mist
  UV-disk projections from the production particle vertex shader, captured under
  `build/task70-sol3-mist-geometry/`. The unchanged postprocessor's two Gaussian
  passes extend 25.848 full-resolution pixels, with a conservative 36-pixel
  finite footprint including sampling/rasterization; bush diagnostic paint uses
  an eight-pixel fringe. No broad manually selected scene rectangle is used.
- All 14 existing canonical foliage shader stages are byte-identical to master
  (`exact-shader-equivalence.json`). The two new bush programs are separate.
- `round69_foliage_check`: **PASS**; `vapor_shape_check`: **PASS**.
- `tools/prepare_assets.sh`, then `tools/prepared_assets_check.sh`: **PASS**,
  including byte equivalence for prepared world, meshes, collisions, ownership,
  RNG, textures, audio and combat records. Logs are `final-*.log` under
  `build/task70-sol3-narrow/`.
- `git diff --check`: **PASS**. No vendored Sloppy changes.

Paired CPU measurements use the same master/final executables throughout,
1280x720 X11 Vulkan, fixed simulation/weather/hour, actual GPU draws, and three
alternating AB/BA/AB pairs. Values below are medians of the three run p99 values
in milliseconds. Both callback thread CPU and callback wall time pass the
predeclared 3% + 0.10 ms tolerance; draw-count sequences are identical.

| Scene | Thread CPU before → after | Callback wall before → after | Frames / warmup | Core | Report under `build/task70-sol3-narrow/` |
| --- | --- | --- | --- | --- | --- |
| Camp | 5.402 → 5.422 | 7.593 → 7.191 | 960 / 240 | 2 | `performance-exact/camp-report.json` |
| Ground approach | 7.307 → 7.064 | 8.184 → 7.686 | 960 / 240 | 2 | `performance-exact/approach-report.json` |
| Pool | 6.178 → 5.492 | 7.469 → 7.215 | 3600 / 600 | 2 | `performance-exact-steady/pool-report.json` |
| Temple interior | 3.956 → 4.117 | 6.368 → 6.143 | 3600 / 600 | 1 | `performance-exact-quiet/temple-report.json` |

Timing limitation: this is a shared, contended machine. Earlier short pool and
Temple runs, and the longer Temple run on core 2, failed the tail threshold.
A byte-identical master/master control also failed it (thread p99 +17.5%).
Those raw runs remain in the evidence rather than being discarded. Longer
sampling settled the pool comparison. For Temple, a background-load sample
selected the quieter physical core 1 before repeating both binaries; that
paired protocol passed. Temple total frame p99 still rose 6.857 → 7.663 ms,
despite lower callback wall p99; this is not a GPU/frame-time regression claim.
No game source changed between these protocols. Core-load and profiling
evidence is retained alongside the reports.

No unresolved implementation changes remain. The optional Temple floor issue
is deliberately left at master's behavior, as requested for this narrow branch.
