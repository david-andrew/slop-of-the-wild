# Round 64: Vulkan noise lattice seams

The exact unstable expression is `q = fract(p * 0.1031)` in `game/shade.jo`'s
`hash12`. After driver inlining, the lattice offsets passed by `vnoise` can
contract/reassociate with that initial scale multiplication. Its rounding
changes are amplified by the final `fract` in the hash. A shared corner then
approaches almost zero from one cell and almost one from another. Cubic
interpolation cannot hide that discontinuity: it becomes world-aligned
rectangles in water normals, rain, terrain pigment and scorch detail.

The expression bisect on the NVIDIA GeForce GTX 1070 is decisive:

- The raw Vulkan probe has a maximum adjacent red jump of 246 counts at image
  row 154, near noise coordinate `(-418, 587)`. OpenGL's maximum there is 1.
- Adding `NoContraction` only to the initial `OpVectorTimesScalar` by
  `f32(0.1031)` removes the seam: maximum jump 1, and red-channel mean absolute
  difference from OpenGL is 0.01547 counts over all 512×512 pixels.
- Fencing the dot product, the feedback addition, the last addition, or the
  entire final hash arithmetic does not remove the 246-count jump.
- Fencing all hash ALU or all float ALU also works, but is unnecessary.

This is a floating-point precision/optimization portability problem. The
emitted GLSL and SPIR-V express the same hash and interpolation, and the
SPIR-V disassembly is structurally correct. There is no evidence here of an
integer hash, signed remainder, saturating conversion, uniform ABI, texture
LOD or derivative code-generation error. The initial multiply has no
`NoContraction` decoration in the unmodified compiler output. The inferred
mechanism is driver contraction/reassociation after inlining; these results
do not establish an incorrect Sloppy opcode or an integer-rule regression.

## Game workaround

`game_spirv_noise_precision` in `game/spirv_helpers.jo` identifies the hash's
initial multiplication by its f32 scale constant (`0x3DD32618`) and decorates
that result with `NoContraction`. `shader_load_submit` applies it to vertex
and fragment modules; the signed-derivative adapter remains fragment-only.
GLSL, the source hash, all uniforms and descriptors, and every other shader
optimization stay as before. No compiler/runtime files are changed. The adapter deliberately
uses no generated function or result ID; the GPU continuity check catches a
future compiler shape change that stops matching it.

## Reproducer and evidence

All scratch sources, executables, images and detailed logs are ignored files
under `build/round64/`:

- `hash_seam_repro.jo` is a standalone Sloppy source with no game imports,
  textures, branches, derivatives, integer cell conversions or material code.
  It renders only the original float hash and interpolated noise. Build with
  `sloppy/bin/sloppy build build/round64/hash_seam_repro.jo -o build/round64/renderer/hash-seam-repro`.
  Run under `flock /tmp/botw-render.lock` with `SLOPPY_PLATFORM=x11`,
  `SLOPPY_FRAMES=1` and `SLOPPY_SCREENSHOT=...`; compare default Vulkan with
  `SLOPPY_VULKAN=0`. The output is 512×512. The executable writes the emitted
  GLSL and SPIR-V to `renderer/repro.glsl` and `renderer/repro.spv`.
- `renderer/noise-probe.jo`, `probe-variants.py`, `probe-more.py`, their emitted
  modules, and `expression-bisect.json` retain the one-operation experiments.
- `renderer/before/` holds the four exact X11 1280×720 Vulkan/OpenGL pairs
  at master `d05ace6`, with 4× absolute pixel differences.
- `renderer/ablations/` retains copied game sources, replacement manifests,
  Vulkan captures and logs for water normals, reflections, rain rings,
  terrain detail, shared noise and scorch-mask removal. These experiments
  change one term at a time and are diagnostic, not replacement artwork.
- `renderer/fixed/` holds the final executable's matched four-view pairs,
  capture manifest, raw differences, quiet-surface differences and
  `structure-summary.json`.
- `renderer/checks/` holds water, weather, fire, shade and floating-point GPU
  continuity logs. `renderer/negative-control.log` records all four original
  renderer pairs failing the new structure check.

## Regression protocol

`python3 tools/renderer_structure_check.py` builds the game and captures
Hopper Pond clear/rain (`BOTW_AT=-1190,1665,-0.9`), the Temple path
(`BOTW_AT=-818,1950,3.14`), and fire scorch (`BOTW_FIRE=1`, frame 260).
It owns one render lock per process and uses the exact client-size helper.
Default Vulkan and `SLOPPY_VULKAN=0` use the same deterministic simulation
frames, hour 11, scale 1 and 1280×720 X11 output.

The check compares quiet surface crops, filtering each with a nine-pixel box
to suppress grain and single-pixel raster differences. A persistent residual
above 6 RGB counts in more than 2% of the surface fails. Whole-frame average
error is also recorded but is not the acceptance criterion. This prevents
small actors, smoke, UI and the rest of the landscape from diluting a blocky
water/path/scorch failure. The original four views fail at 5.817%, 12.738%,
15.626% and 5.393%, respectively.

`tools/noise_seam_check.jo` reads 262,144 RGB32F samples of the original probe
through the production shader adapter. Cubic value-noise interpolation
bounds adjacent differences to 1.5 × 10/512 = 0.0293; the check allows 0.04
for float/raster rounding and rejects a discontinuous corner. Both checks
are registered in `tools/run_all_checks.sh` using its existing lock ownership
conventions.

### Vertex-stage regression at `56f1216`

The fire view at frame 260 failed with a 3.066% broad residual while pond,
rain pond and Temple remained at 0.000%. The bright patch behind the flames
already differed in the opaque HDR buffer, before smoke or heat refraction.
Fragment-only hash precision changes did not remove it. The loader had left
vertex hashes unfenced, although terrain displacement, grass and foliage
silhouettes use the same noise helpers. Applying the existing initial-multiply
fence to the vertex module reduces the fire crop's residual to 0.000%, with
the fire materials and simulation unchanged. The 2% comparison limit is retained.

`noise_seam_check.jo` now also samples noise in a 129×129 vertex grid and reads
the interpolated RGB32F image. This exercises shared lattice corners in both
shader stages through the production loader instead of testing only fragments.
Raw diagnostic source copies, captures and the old-loader negative control
are retained under `build/fire-parity/`; matched CPU captures use
`build/round83/performance-parity/`.

The full renderer check passes all four views at 0.000% broad residual. The
OpenGL fire capture remains pixel-for-pixel identical to the baseline. Both
native backends pass the fragment/vertex continuity probe with maxima
0.028334677 / 0.028277934; the old loader passes the fragment probe and fails
the vertex probe. The seven fire behavior/material checks and shader loader,
shader adapter and terrain-noise checks also pass.

Three alternating AB/BA pairs per scene pass both CPU p99 gates (3% + 0.10 ms,
frames after the first 240, no outliers removed). Callback wall/main-thread
medians in ms are fire 9.225/7.416 → 7.809/5.811, tent-fire 11.699/10.972 →
10.225/9.921, and lightning 13.761/7.986 → 13.470/7.893. The complete timings,
settings, source hashes and binary hashes are in `build/round83/`.

## Final validation

All four native-renderer comparisons pass. The fixed broad-residual fractions
are 0.000% (pond), 0.000% (rain pond), 0.000% (Temple), and 0.366% (scorch),
against the unchanged 2% limit. The unfixed executable fails all four views.
The standalone raw Vulkan reproducer has the same 246-count boundary jump;
OpenGL has 1. The production module passes `spirv-val --target-env vulkan1.2`.

The RGB32F continuity test passes on both Vulkan and OpenGL with the same
maximum adjacent error, 0.028334677. Bypassing the production adapter rejects
the raw Vulkan shader. Headless checks pass for water coverage, map water,
wading, wake contact, weather effects, weather shading, fire behavior, fire
queries, fire scanning, round-80 fire, and painted shading (11 groups).

Every final ablation source tree is compared byte-for-byte with the frozen
`d05ace6` archive; each differs in exactly its named shader file. Early
ablations copied the live tree and are kept separately as discarded evidence
in `renderer/ablations-live-source-discarded/`. Final images and manifests are
in `renderer/ablations/`. The remaining captures were completed in one
self-locking batch, with no nested locks. `renderer/report.html` presents the
matched crops, including the OpenGL reference.
