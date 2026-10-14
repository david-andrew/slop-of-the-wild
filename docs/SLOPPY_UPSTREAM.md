# Sloppy 0.6.0 upstream report

Verified against the unmodified release `7c8d133`, after the port commits from
`165ffae` through `91a91b0`. GPU observations below are on **GTX 1070, NVIDIA
580.178.04**, Linux: X11 for offscreen pixel probes, Wayland for pacing and
pipeline probes. API compile failures and CPU mixer/filesystem probes are driver
independent. Ordered by likely impact on a game; missing optional features are
identified as API requests, rather than incorrect language semantics.

Every reproducer is standalone, with no game imports or adapters. From the repo
root, run `sloppy/bin/sloppy tools/upstream/<name>.jo`; for window/GPU programs:

```sh
flock /tmp/botw-render.lock env SLOPPY_PLATFORM=x11 SLOPPY_NO_AUDIO=1 SLOPPY_VULKAN=1 sloppy/bin/sloppy tools/upstream/readback.jo
# Repeat pixel probes with SLOPPY_VULKAN=0 for the OpenGL control.
python3 tools/upstream/verify.py  # owns one batch render lock; do not wrap it
```

The verifier passed all 22 expected-failure/control runs on the machine above.
Assertions deliberately fail when they reproduce a defect. The three missing-API
probes deliberately fail compilation. Pacing and prewarm probes print evidence,
without imposing a hardware-independent timing threshold.

## 1. Vulkan readback ignores crop bounds and element type

- **Repro:** [readback.jo](../tools/upstream/readback.jo). A 1×1 crop of a 2×2
  RGBA8 target changes guard byte 4 from 17 to 64: it copies the entire image,
  potentially overflowing a correctly sized caller buffer. RGBA32F 1×1 readback
  returns red 0.25 but leaves alpha at -1; expected alpha 1. OpenGL preserves the
  guard and returns all four floats. Buffers in the repro are oversized for safety.
- **Workaround:** `game/pixel_readback.jo:game_pixel_readback`, called by
  `game/gfx.jo:game_read_pixels` / `game_read_pixels_f32`, copies the requested
  region and converts the actual image format.
- **Upstream:** honor x/y/w/h and requested type in `vkgl.jo:vgl_read_pixels`;
  `vk.jo:__vk_read_pixels` currently copies width×height×4 bytes unconditionally.
  Handle float/integer formats and reject unsupported conversions explicitly.

## 2. Unfenced SPIR-V float arithmetic produces noise lattice seams

- **Repro:** [hash_seam_repro.jo](../tools/upstream/hash_seam_repro.jo). Maximum
  adjacent red jump is **249/255 on Vulkan, 8/255 on OpenGL**, versus a continuous
  interpolation bound of 11/255. The unstable expression is `fract(p * 0.1031)`;
  the inferred cause is driver contraction/reassociation after inlining, not an
  incorrect opcode. [The earlier one-operation bisect](rounds/ROUND64_RENDERER_PARITY.md)
  removes the seam by decorating only that initial multiply with `NoContraction`.
- **Workaround:** `game/spirv_helpers.jo:game_spirv_noise_precision`, applied by
  `game/shader_load.jo:shader_load_submit` to both vertex and fragment modules,
  decorates the hash scale multiplication. Vertex noise changes terrain/foliage
  geometry and shadow silhouettes too; fencing only fragments leaves those unstable.
- **Upstream:** emit `NoContraction` on float operations to uphold CPU-equivalent
  evaluation, or provide an explicit strict precision mode with a documented
  contract. Verify shared expressions across call sites on both shader backends.

## 3. Vulkan mipmap generation silently does nothing

- **Repro:** [mipmap.jo](../tools/upstream/mipmap.jo). After `glGenerateMipmap`,
  LOD 2 of a 4×4 red checker is **255 on Vulkan, 127 on OpenGL**; expected 128±1.
  `gl.jo:glGenerateMipmap` returns immediately on Vulkan, whose image allocator
  creates only one mip. Explicit LOD and minification therefore use the base image.
- **Workaround:** `game/vulkan_textures.jo:game_mip_texture`, called by
  `game/gfx.jo:bytes_texture`, allocates and blits a full static RGBA pyramid.
- **Upstream:** allocate mip levels/views, generate their contents and transitions,
  and honor minification/mip sampler options. Report unsupported formats explicitly.

## 4. Presentation and frame-fence stalls remain under mailbox

- **Repro:** [presentation.jo](../tools/upstream/presentation.jo), with
  `SLOPPY_PLATFORM=wayland SLOPPY_VSYNC=0`; set `PROBE_FRAMES` for longer runs.
  A 240-interval clear-only run had **21.58 ms worst present-return wait** on
  Vulkan mailbox. FIFO paced at **16.66 ms median**, versus mailbox's 0.22 ms;
  release OpenGL still paced at 16.66 ms with vsync disabled. These are producer
  measurements, not scanout or an isolated desktop guarantee. Expected: the public
  presentation setting honors requested pacing, with waits attributable by stage.
- **Game evidence:** [Sol's complete attribution](PERFORMANCE.md#every-mailbox-tail-attribution-and-game-fixes)
  records **155.66 ms acquire, 42.17 ms fence, 25.58 ms submit** tails. The short
  standalone probe does not reproduce those exact maxima. The ten-minute route
  had 191/297 FIFO windows over 20 ms, versus 4/297 with the older patched GL
  mailbox path; release GL and the current game are separately identified there.
- **Workaround:** the Linux launchers select managed X11/XWayland when DISPLAY is advertised, with fastest Vulkan presentation and an explicit platform override; `game/main.jo:render_warmup`
  and persistent render resources remove game first-use/allocation causes. No
  game workaround eliminates the remaining runtime waits.
- **Upstream:** `__vk_present` acquires with infinite timeout before submitting
  recorded rendering; `__vk_begin_frame` waits on a fixed two-frame ring. Overlap
  rendering/acquire, expose paced queue depth and acquire/fence/submit telemetry;
  make the OpenGL Wayland path honor the public presentation setting too.

### Round 66 critic follow-up: managed X11 versus native Wayland

The unmodified release still reproduces the native Wayland ten-second hitch.
The updated standalone [presentation probe](../tools/upstream/presentation.jo)
prints elapsed time, interval and prior present duration for every post-warmup
return over 25 ms, along with output/platform and final sample count. Run:

```sh
sloppy/bin/sloppy build tools/upstream/presentation.jo -o build/upstream-presentation
flock /tmp/botw-render.lock env SLOPPY_PLATFORM=wayland SLOPPY_VULKAN=1 SLOPPY_VSYNC=0 SLOPPY_NO_AUDIO=1 PROBE_SECONDS=120 timeout 150 build/upstream-presentation
flock /tmp/botw-render.lock env SLOPPY_PLATFORM=x11 SLOPPY_VULKAN=1 SLOPPY_VSYNC=0 SLOPPY_NO_AUDIO=1 PROBE_SECONDS=120 timeout 150 build/upstream-presentation
```

A 65-second Wayland clear-only repeat records **six 46.6–49.4 ms presentation
waits**, ten seconds apart; its X11 repeat records **zero >25 ms returns**, worst
13.04 ms. The outputs differ (2133×1200 versus 1280×720), so retain that caveat.
The size-controlled two-minute production forest matrix at **2133×1200**, with
dynamic scaling and a managed X11 client, records **26 >25 ms returns / 80.0 ms
worst on Wayland mailbox**, versus **4 / 29.8 ms on X11 immediate fallback**.
FIFO records **459 / 264.2 ms** and **81 / 221.0 ms**, respectively. The full
matrix and callback/presentation attribution are in [PERFORMANCE.md](PERFORMANCE.md#round-66-critic-follow-up-managed-x11-launcher-and-swimming).

X11 exposes immediate rather than mailbox on this driver: this is a comparison
of the release's requested fast modes, not a claim that both WSI surfaces support
mailbox. A remapped override-redirect full-scale X11 stress run still has periodic
waits; window management and load matter. The launcher workaround applies to
ordinary managed X11 with production dynamic scaling. It does not establish that
the runtime has fixed native Wayland, or guarantee zero tails on X11. Earlier
native-call traces below identify the cadence with acquisition; upstream should
investigate the Wayland WSI/acquire path and expose comparable telemetry for both
surfaces. A ten-minute normal managed X11 run at 1280×720 has p99 13.826 ms,
32 >25 ms returns, and only two >25 ms presentation calls without the repeating
cadence. Callback waits/scheduling dominate its remaining tails. A separate traced
repeat confirms substantial involuntary preemption and catch-up simulation; this
is not evidence that all remaining pauses originate in Wayland WSI. The strict
zero-tail target remains unmet. Raw repeat evidence is `build/round66-sol/`, including the standalone
logs and `pacing-summary.json`. The vendored Sloppy tree is unchanged.

### Round 66: the ten-second presentation stall

`build/round66/forest-before.log` retains 18,000 present-return intervals over
286.99 s. `tools/vulkan_call_trace.c` attributes 29 periodic waits to
`vkAcquireNextImageKHR`: 26.73–79.70 ms, at 10 s intervals (successive calls
within about 20 ms of that cadence). Main-thread game execution remains small;
the original game wall-time column was inflated by a collision between
`game/frametime.jo:__frame_cpu` and the runtime's identically named accumulator.
The game counter now has a separate name. Thread CPU and native call timestamps
were unaffected; do not use the old wall/gap columns for attribution.

The corrected 7,200-frame pond capture spans 95.64 s and has nine acquire waits
of 34.79–39.81 ms, again ten seconds apart. A **65 s clear-only standalone**
`tools/upstream/presentation.jo` run, with audio disabled and no game imports,
also has six post-startup acquire waits of 41.55–51.54 ms at the same cadence.
That rules out game autosave, weather/environment work, actors, and game audio.
Autosave polls once per simulated second and saves after 180 s or a milestone,
not every 15 s. The forest trace has only two `vkGetPipelineCacheData` calls,
both in loading; the clear-only trace has none. No periodic pipeline creation or
cache save accompanies these waits. Native present/fence/submit are separately
traced; the recurring ten-second spike is acquire, rather than queue-present or
a frame fence. Other unrelated fence stalls remain visible in the raw logs.

Reproduce the standalone observation on the NVIDIA/Wayland setup above:

```sh
cc -shared -fPIC -O2 tools/vulkan_call_trace.c -o build/round66/vulkan_call_trace.so
flock /tmp/botw-render.lock env LD_AUDIT="$PWD/build/round66/vulkan_call_trace.so" SLOPPY_PLATFORM=wayland SLOPPY_VSYNC=0 SLOPPY_NO_AUDIO=1 PROBE_SECONDS=65 sloppy/bin/sloppy tools/upstream/presentation.jo
```

The observed block is inside the driver's WSI acquire call. These measurements
cannot distinguish the driver from compositor scheduling or explain its internal
ten-second timer. Sloppy's `__vk_present` waits with infinite timeout for an image
**before submitting the recorded scene**, so it exposes that wait directly on the
frame path. An upstream fix needs WSI/driver investigation and an acquire/submit
policy that can overlap useful work. Moving game saves would not remove this
measured stall. Game loading now primes both Vulkan presentation slots and the
swapchain; steady-state acquire waits persist independently of that warmup.

The separate early 90–96 ms hitch is **not a late graphics pipeline**. In the
instrumented startup control, the third measured interval was 91.91 ms:
`libdecor_dispatch` alone took 76.96 ms, outside update/draw and presentation.
No long ALSA call accompanied it. It occurs after the first buffers map, when
libdecor processes delayed decoration/activation work (the trace does not isolate
its GTK/font internals). Priming only the swapchain and doing one roundtrip did
not absorb that deferred work. `game/main.jo:render_warmup` now also services a
bounded 120 ms Wayland decoration window during loading. In the first verified
capture, the expensive dispatch takes 91.36 ms **before** the game timer starts;
the first callback is 6.99 ms, and first-24-frame residual gap peaks at 0.45 ms.
The second repeat moves a 95.07 ms dispatch into loading, with first CPU
8.50 ms and first-24 residual gap at most 0.49 ms. Early native acquire/fence
waits still occur; first-24 producer worst is 49.77 / 38.45 ms,
so this is removal of the attributed decoration hitch, not a scanout guarantee.
Raw controls and repeats are `build/round66/startup-v2.log` and
`build/round66/startup-v3-{1,2}.log`. Upstream should complete client-decoration
mapping/activation work in initialization, or expose an explicit preparation API.

## 5. Signed fragment derivatives are absent from the public shader API

- **Repro:** [signed_derivatives.jo](../tools/upstream/signed_derivatives.jo)
  fails with `unknown function 'dFdx'` (and `dFdy` is absent too), before either
  backend runs. `fwidth` is available but loses sign and axis, so it cannot recover
  a facet normal. Expected: signed scalar/vector derivatives on GLSL and SPIR-V.
- **Workaround:** `game/gfx.jo:game_dfdx` / `game_dfdy` use tagged `fwidth`
  helpers; `__patch_glsl` and `game/spirv_helpers.jo:game_spirv_derivatives` replace
  them with `dFdx`/`dFdy` and `OpDPdx`/`OpDPdy`.
- **Upstream:** expose signed derivatives as shader builtins, with defined fragment
  stage restrictions and software-backend behavior.

## 6. Vulkan R32F uploads fall back to RGBA8

- **Repro:** [r32f_upload.jo](../tools/upstream/r32f_upload.jo) uploads float
  0.125 to `GL_R32F/GL_RED/GL_FLOAT`. Sampled red is **0 on Vulkan, 32/255 on
  OpenGL**; expected 32±1 after RGBA8 output quantization. `__vg_format` lacks
  R32F and falls back to RGBA8, interpreting float bytes as channels.
- **Workaround:** `game/gfx.jo:float_texture` explicitly allocates Vulkan format
  100 (`R32_SFLOAT`) and uploads four bytes per texel.
- **Upstream:** map R32F correctly, preserve source format/type and byte stride
  for uploads/subuploads; reject unknown formats rather than silently changing them.

## 7. Framebuffer color/depth snapshots do not route through Vulkan

- **Repro:** [snapshots.jo](../tools/upstream/snapshots.jo) blits color+depth
  between two targets. Destination red stays **0 on Vulkan**, versus **64 on
  OpenGL**, expected 64±1. The release exposes `glBlitFramebuffer` as a raw GLES
  extern in `dmabuf.jo`; it does not operate on Vulkan images. This is missing
  backend routing, not a missing symbol. The pixel probe checks the color result.
- **Workaround:** `game/gfx.jo:game_copy_target`, called by
  `game/post.jo:post_copy_depth`, transfers both opaque color and depth images.
- **Upstream:** expose portable color/depth copy or blit with independent source
  and destination targets, supported format/size rules and resource transitions.

## 8. Shadow rasterization bias has no portable setter

- **Repro:** [shadow_bias.jo](../tools/upstream/shadow_bias.jo) fails with
  `unknown function 'glPolygonOffset'` before backend selection. Vulkan's default
  `__vg_make_pipeline` also leaves `bias_on` zero. Expected: configurable constant
  and slope bias for shadow draws; a GLES extern cannot configure a Vulkan pipeline.
- **Workaround:** `game/vulkan_shadow.jo:game_shadow_pipeline` creates separate
  biased pipelines; `game_draw_program` selects them during shadow passes.
- **Upstream:** add portable raster bias state and include it in pipeline keys,
  or enable dynamic depth bias. This is an API request, not a claim that every
  Sloppy shadow implementation needs raster bias (receiver bias is another option).

## 9. Per-voice gain changes step at mixer block boundaries

- **Repro:** [gain_ramp.jo](../tools/upstream/gain_ramp.jo) exercises the actual
  CPU mixer without a device: constant 0.5 becomes **0.0 in one sample** after
  `set_volume(id, 0)`. Expected for a requested 20 ms ramp: 960 smoothly changing
  output frames, including retargeting an unfinished ramp.
- **Workaround:** `game/music.jo:__score_play` gives each score voice private
  samples; `score_set_volume` bakes interrupted envelopes into its unplayed suffix.
- **Upstream:** add an optional ramp time to `set_volume`, advancing gain per output
  sample for pitched and streaming voices. Immediate volume remains valid when
  requested; this is an API request. The live mixer already soft-clips peaks.

## 10. Shader creation and a warm disk cache do not pre-create state pipelines

- **Repro:** [pipeline_prewarm.jo](../tools/upstream/pipeline_prewarm.jo), Vulkan:
  `make_shader` leaves **0 pipelines**; first draw and a new color-mask state
  create 1 then 2. Creation takes **7.93 / 2.18 ms cold**, **0.20 / 0.06 ms warm**:
  the valid disk cache speeds creation but does not pre-create objects. Expected
  API: prepare complete draw states during loading. Lazy creation is not a cache bug.
- **Workaround:** `game/main.jo:render_warmup` / `character_warmup` draw actual
  attachment/material/state variants. [Game attribution](PERFORMANCE.md#every-mailbox-tail-attribution-and-game-fixes)
  found two omitted shadow variants costing 14.13 / 288.24 ms in native creation.
- **Upstream:** expose prewarm keyed by attachments, topology, color mask, blending
  and bias; persist dirty cache data away from the critical draw/present path.

## 11. A nonexistent XDG cache parent silently disables pipeline persistence

- **Repro:** [pipeline_cache_path.jo](../tools/upstream/pipeline_cache_path.jo):
  `XDG_CACHE_HOME="$PWD/build/upstream/missing/cache" sloppy/bin/sloppy tools/upstream/pipeline_cache_path.jo`
  prints an empty path if that parent is absent. After `mkdir -p` of the parent,
  it returns a `.vkpipelines` path. Expected: create parents or report the failure.
  `mkdir` is intentionally nonrecursive; `vk.jo:__vk_pcache_path` does not create
  the XDG base before trying its `sloppy` child.
- **Workaround:** no game fix. `tools/package_cache_check.py:main` uses an existing
  empty HOME with XDG unset, exercising the working HOME fallback; this does not
  cover a nonexistent explicit XDG path.
- **Upstream:** recursively create the selected cache directory (without changing
  ordinary `mkdir` semantics), and surface persistence errors.

## 12. Vulkan per-pass GPU timestamps are unavailable

- **Repro:** [gpu_timestamps.jo](../tools/upstream/gpu_timestamps.jo) fails with
  `unknown function 'vkCmdWriteTimestamp'`. Neither timestamp queries nor a
  portable per-pass timing helper are exposed. Expected: GPU pass durations and
  nonblocking availability checks, separate from CPU producer intervals.
- **Workaround:** `game/gputime.jo:gpu_mark` disables GLES profiling on Vulkan,
  printing `gpu timing: use Vulkan frame intervals; GLES pass queries unavailable`.
  `game/frametime.jo:frame_stats_end` provides CPU/interval evidence instead.
- **Upstream:** bind `vkCmdWriteTimestamp` (or timestamp2), query pools/reset/results,
  timestamp period/valid bits, and expose asynchronous timing on capable queues.
  The compile probe establishes missing bindings, not a driver timestamp failure.

## 13. Vulkan anisotropic filtering is disabled (optional quality feature)

- **Repro:** [anisotropy.jo](../tools/upstream/anisotropy.jo), Vulkan: native
  `samplerAnisotropy` support is **1**, but the runtime's device-feature factory
  requests **0**. `glTexParameteri(..., GL_TEXTURE_MAX_ANISOTROPY, 8)` is ignored
  by `vgl_tex_parameter`; the four default samplers leave `aniso_on` zero.
  Expected when requested and supported: enable the feature and honor its setting.
- **Workaround:** `game/gfx.jo:bytes_texture` requests 8× through its GLES extern
  on OpenGL; Vulkan retains ordinary mip filtering. There is no Vulkan workaround.
- **Upstream:** expose optional per-texture sampler anisotropy, enable the supported
  device feature, clamp to device limits and retain a non-anisotropic fallback.
  This is a quality/API request, not a correctness requirement for all games.

## Candidates not retained

The historical all-zero literal-array FFI write problem passes on this release
(ordinary and `--release` runs observe `memset` writes through `data([0])`). The mixer already
has a `tanh` soft clip, so “no live limiter” was too broad; the game export guard
is not evidence of a missing live clipper. Corrected CPU swizzles, stricter actor
borrows/declaration order, and the now-public discard/texel/LOD/instance/vertex
operations are migration changes or fixes, not outstanding bugs. Cached chimes,
asset packaging, render-target reuse and broader warmup are game responsibilities;
startup upload batching alone does not establish a driver-independent runtime bug.
