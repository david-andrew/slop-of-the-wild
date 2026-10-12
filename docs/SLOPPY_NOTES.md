# Notes on the language

Written while building the game in Jot; the language has since been renamed Sloppy, and the game
moved to Sloppy 0.2 (see the end). Several of the gaps below have been closed upstream since.


Historical notes from the Jot toolchain (`jot/`, slop-lang `00abb0e`). The current
checkout uses the unmodified toolchain in `sloppy/`; its revision is in `sloppy/VERSION`.

## Library addition: pointer lock (the only change to the pinned standard library)

Mouse look needs the pointer locked to the window with relative motion. The library had no
pointer lock, so `jot/lib/game/` gained `mouse_lock(on: bool = true) -> bool` (window.jo):
- On Wayland it binds `zwp_pointer_constraints_v1` and `zwp_relative_pointer_manager_v1`
  (wayland.jo + the protocol tables in wlclient.jo). It locks the pointer (persistent), hides
  the cursor, and feeds unaccelerated relative motion into `mouse_delta()`.
- Elsewhere (X11, web) it returns false, and the game falls back to turning the camera while the
  middle mouse button is held.

About 70 lines; the data-driven protocol tables in wlclient.jo made it easy.

## Worked around in the game (no library or compiler changes)

* **The shader translator has no `discard`, `texelFetch`, `textureLod`, `gl_InstanceID` or
  `gl_VertexID`.**
  - `shader(vs, fs)` returns the GLSL as plain strings, so `game/gfx.jo` defines marker
    functions in Jot (`glsl_discard`, `glsl_fetch`, `glsl_lod`, `glsl_instance`, ...).
  - It rewrites their bodies in the GLSL text before `make_shader` (`make_sh`).
  - These markers power alpha-tested leaves, the heightfield read in the terrain and grass vertex
    shaders, and GPU skinning from a bone-matrix texture.
* **Uniforms must be a flat struct of scalars, vectors, mat4 and textures (no arrays).**
  - Bone palettes go in an RGBA32F texture.
  - Shadow cascades are three separate matrices and samplers.
* **`draw_instanced` uploads the instance buffer on every call.**
  - `draw_static` in gfx.jo keeps instance buffers on the GPU and re-uploads only when they
    change: terrain patches, grass patches, trees, particles.
* **Map values can't be mutated in place** (`m[k].push(x)`): read, modify and store back.
* **Smaller language points:**
  - `use` is not transitive.
  - An `if` expression used as a call argument needs parentheses.
  - `none` can't be an enum variant.
  - There is no scalar `mix` (use `lerp`).
* **A top-level assignment to another file's global declares a new global instead.**
  `title_pad = pad_chord(...)` in main.jo left music.jo's `title_pad` empty, so music.jo
  quietly built its own on first use (a 236 ms hitch on entering a shrine). Globals of a module
  are set from a function in that module (`music_pads()`), as the shrines' build hook already was.
* **`parallel_map` is for the load, not the frame.** Culling the trees' 64 m cells in parallel
  each frame (a few hundred cells, the plants of each tested on its own core, the results
  gathered after) raised the forest's CPU time from 7.5 to 10.6 ms: the per-call cost of the
  threads outweighs a few milliseconds of tests. The frame loop stays single-threaded.
* **A `discard` early in a fragment shader spoils the derivatives after it.** The cave mouth is
  cut out of the terrain with `glsl_discard`; placed at the top of `terrain_fs`, the pixels next
  to the cut whose neighbors had gone took NaN slopes (the facet normal, texture LOD), and the
  watercolor pass's blur spread each into a soft black disc. The discard comes last now.
* **Stdlib names leak into user programs.** `sky_vs`, `post_vs`, `blur_fs` and `hash21` are taken
  by draw3d.jot, so shaders need prefixed names.
* **An all-zero literal array written through `data()` by a foreign call reads back as 0** in the
  release build (`v: u64[] = [0]`, then `glGetQueryObjectui64vEXT(id, pname, data(v))`: `v[0]`
  stays 0; the same array literal with a nonzero element sees the write). `game/gputime.jo` uses
  `fill(u64(1), 1)`. Looks like the optimizer treating the literal's elements as known constants.
* **GPU timer queries are an extension in the GLES context** (`EXT_disjoint_timer_query`, entry
  points from `eglGetProcAddress`), and the 32-bit result read returns 0 on the NVIDIA driver;
  `BOTW_GPU=1` uses the 64-bit one.
* **`encode_png` writes uncompressed PNGs**, so the baked character textures are stored raw
  (36 MB of models).

## What worked very well

* **Compile speed.** The whole game (~17k lines plus the library) compiles in about a second.
  World generation, baking and the heightmap tool run in a few seconds as plain Jot programs.
* **`parallel_range` / `parallel_map`** make heightfield generation, normal maps, the piano
  sample bank and kernel-regression interpolation fast on 8 cores without ceremony.
* **Writing shaders in Jot** with the same types as the game code: shared noise and lighting
  functions (`shade.jo`) are called from terrain, grass, trees, water, sky and characters.
* **Value semantics and structs** keep game state simple: no aliasing bugs, and copy-on-write
  arrays.
* **The software mixer** was enough to synthesize a piano (inharmonic partials, two-stage decay,
  baked reverb), every sound effect, and the ambient beds at start-up.
* **The headless testing hooks** (`SLOPPY_SCREENSHOT`, `SLOPPY_FRAMES`, `SLOPPY_INPUT`): every feature
  here was checked by scripted runs and screenshots, and `tools/feel_test.jo` runs the real
  player code without a window.

## Moving to Sloppy 0.2

- Files are `.jo`; the test hooks are `SLOPPY_SCREENSHOT`, `SLOPPY_FRAMES`, `SLOPPY_INPUT`,
  `SLOPPY_STATS`.
- Names starting with `_` are now private to their file. Ten that were shared between files
  (`__mb_sphere`, `__draw_char`, `__cell_pos`, ...) lost their underscores; nothing else changed.
- `mouse_lock()` is in the library now, so the pinned toolchain is unmodified.
- Upstream since: shader `discard()`, `texel()`, `sample_lod()` (the game's `glsl_*` markers still
  work), maps changed in place (`m[k].push(x)`), compressed PNGs from `encode_png`.

## Frame hitches and profiling (2026-10-09)

The pinned runtime remains unmodified. Measurements and repeat ranges are in
[PERFORMANCE.md](PERFORMANCE.md) and [PERFORMANCE_FINDINGS.md](PERFORMANCE_FINDINGS.md).

* The runtime uses **reference counting with per-thread allocation/free lists**, not a tracing
  garbage collector (`sloppy/lib/core/rt.jo`). A wall-clock frame spike is not evidence of GC.
  `game/frametime.jo` adds real update-to-update p50/p95/p99/worst logging and, on Linux, main-thread
  CPU time from `CLOCK_THREAD_CPUTIME_ID`. Several 12–19 ms wall-CPU frames used only 5–6 ms of
  thread CPU: time waiting/preempted, not 12–19 ms of computation. This does not distinguish a
  blocking driver call from scheduler delay by itself.
* **Wayland pacing is independent of EGL's swap interval.** The library waits for compositor
  frame callbacks/free dma-buf buffers in `__wl_wait_buffer`; changing `eglSwapInterval` cannot
  uncap that path. Use `BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11` for GPU headroom and record the actual
  pixel size: GNOME/Xwayland can resize the requested window. The benchmark reports both backend
  sizes instead of assuming they match. Presentation includes pacing/driver/compositor waits;
  a 28 ms present wait does not identify which one missed a deadline.
* **GPU query age is not proof of readiness.** `game/gputime.jo` now checks
  `GL_QUERY_RESULT_AVAILABLE` for all passes before reading a frame's timer results. If any query
  is unfinished, discard that timing sample, count it, and reuse the slot without a blocking
  result read. Otherwise a profiling run itself can stall when the GPU falls behind.
* **`draw_static` does not re-upload**, but vegetation culling used to upload identical instance
  buckets on every frame. `VBucket.uploaded` retains the last data with Sloppy's value semantics;
  an exact byte comparison skips the GL call when matrices and tints match. A burned tree's tint
  invalidates the cache. Dynamic selection still uploads as needed; the three passes retain
  independent buffers. `inst_uploads`/`inst_bytes` expose the actual calls, not guesses.
* The vegetation depth/shadow passes now have **separate fragment shaders**. Coverage (alpha,
  near-camera/player dissolve, dither) is resolved in the view depth pass, then the shading pass
  uses `GL_EQUAL` with depth writes off. Its uniforms are shared with the depth pass, so wind/time
  match even outside fixed-step screenshots. Shadows retain the exact old leaf coverage. Neither
  meshes, LOD distances nor shadow resolution were reduced.
* **Lazy loading was visible in gameplay.** The name atlas took about 197 ms in a shrine-entry
  run; because HUD drawing followed the last timing marker, it was incorrectly labelled `post`.
  There are now separate HUD timing markers. Names/title textures and vegetation's cell index
  initialize during load. Representative outdoor/shrine/cave draws warm render paths before the
  first presented frame. Warmup runs in the first callback, after the runtime has initialized its
  2D batch and received the compositor's final window size; warming before that point can crash
  sprite batching or allocate targets twice. The loader reports warmup separately, includes it
  in total load time, and does not advance the world/story. `BOTW_NO_WARMUP=1` is an A/B hook.
* The standard-library **`sfx_chime()` synthesizes a fresh 1.2-second sample on every call**.
  Shrine lift/activation calls cost about 17–18 ms of CPU even after shaders were warm. Game code
  caches the exact sound in `game/audio_cache.jo`, generated at load; shrine/story calls reuse it.
  No runtime sound synthesis implementation was changed.

`BOTW_FRAME_LOG=1` emits buffered raw sample rows every 120 frames:
`frame sample: number interval_ms game_cpu_wall_ms gap_ms thread_cpu_ms uploads bytes`.
`gap_ms` includes runtime final submission/audio, statistics output, polling and presentation;
Linux raw rows also append voluntary/involuntary main-thread context-switch counts from
`getrusage(RUSAGE_THREAD)`. Involuntary switches provide direct evidence of preemption; voluntary
ones identify blocking/yielding (including driver waits), without assigning every delay to one
caller. Early baseline logs predate those two columns. CPU is the preceding update/draw frame,
matching that interval. It is not a pure swap timer.
Latest raw rows append `user_cpu_ms system_cpu_ms` from the same thread's `getrusage` call;
the report records how many samples have these optional columns. Some quiet-machine spikes
used 12–15 ms of thread CPU, mostly in userspace, with no context switches. Preemption therefore
explains some outliers, but not all; the logs do not isolate a single cause for the remaining
inflation across sections.
`BOTW_SCALE=0.8` fixes scene resolution for comparisons instead of letting adaptive scaling
reallocate targets and change the workload. These are diagnostics; none adds text to the game.

The burning-camp profiling rows also append `runtime_present_ms gap_minus_present_ms
runtime_gap_thread_cpu_ms`. Presentation comes directly from the runtime's preceding
`__platform_present` call (`__last_present`); the remaining gap includes final submission,
audio/polling, buffered logging and scheduling outside the measured game callbacks. The last
column measures thread CPU between the end of game drawing and the next update, so wall waits
can be distinguished from runtime work. None of these identifies the compositor's internal
reason for a wait. `tools/bench.sh` now includes the tent fire through interval 900 and supports
`BENCH_VIEW="burning tent" BENCH_MODES="paced gpu cpu"` for separate paced, GPU and CPU runs.
It renders 960 frames to flush the final 120-row log batch, and reports intervals 241–900.

Terrain now resolves the cave cut in a dedicated view depth shader, draws buildings/trees,
and shades surviving ground with `GL_EQUAL`; the lit shader has no discard. This allows early
depth rejection before the material/noise work. The shadow shader keeps the original closed
hill. Burn marks only dirty bytes whose quantized values changed, then pack one dirty rectangle
for upload across all terrain passes. Smooth smoke accumulates premultiplied color/opacity
in a half-resolution HDR buffer using full-resolution opaque depth for soft intersections.
Its composite uses `GL_ONE, GL_ONE_MINUS_SRC_ALPHA`; small sharp effects keep their original
resolution. `BOTW_FX_FULLRES=1` bypasses the smoke buffer for quality/cost comparisons.

**A file-private name assigned from another file makes a new variable, silently.** `__storm_k`
lived in env.jo; `__storm_k = 1.0` in main.jo compiled without a word and declared main.jo's own
`__storm_k`, so the storm preset never reached the weather (a critic found storm stills looking
clear). State another file sets belongs in a public name or a struct field (`env.storm_k`).
A compiler warning for an assignment that shadows another file's private name would have caught it.
