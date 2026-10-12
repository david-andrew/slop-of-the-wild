# What this tree shows about Sloppy

One language drives world generation, rendering and GLSL translation, physics,
element reactions, animation and software audio. Production functions also power
headless tests and deterministic captures. Prepared packs and fast native builds
keep iteration short.

- **Prepared startup:** compiled load/process medians **1.635 / 1.830 s**, six
  complete-input 720p launches; pre-texture-fix `6f4aad8` was **3.660 / 3.870 s**.
  Source medians are **1.660 / 3.120 s**; independent compilation is **1.400 s**.
  All 20 nature PNGs are present; prepared launches decode zero PNGs.
- **2133×1200 Wayland present-return p99, default / mailbox:** forest
  **21.13 / 13.63 ms**, fire **23.50 / 8.53 ms**, overlook **19.33 / 9.98 ms**.
  These are handoff proxies, **not delivered frames or scanout**.
- **Ten rendered minutes:** forest, combat, fire, storm and snow; second-cycle
  RSS stays within **1.70 MiB**, live heap allocations within **25**, large-block
  cache at **50.5 MiB**; GPU memory **954–972 MiB**. Total RSS growth is **7.03 MiB**.
  Per-minute return p99 is **11.99–20.21 ms**, retaining the fire miss and rare hitches.

Build, loading, callback wall/thread execution and present calls are separate
measurements. Heap counters do not expose total live bytes. [Current table,
protocols, exact commands and all-repeat evidence](PERFORMANCE.md).

## Where Sloppy fell short

GPU warmup/caches, texture-backed bone uniforms and shader-marker rewriting were
needed; per-frame parallel tree culling cost more than it saved. The pinned
Wayland runtime offers mailbox and call duration, but discards frame-callback
timestamps and does not bind `wp_presentation`. The inspected upstream Vulkan
backend calls `vkQueuePresentKHR` without display-timing/present-wait feedback.

Delivery evidence needs a runtime change: bind `wp_presentation`, request
feedback before each surface commit, associate frame IDs, and expose clock ID,
presented time/refresh/sequence/flags and discarded events. Keep bounded buffers
and release ownership; report hardware-timing flags and discard counts rather
than assuming every commit reaches scanout. `tools/play.sh` selects the pinned
mailbox option; direct launches retain runtime-default pacing.

[Runtime findings/workarounds](SLOPPY_NOTES.md),
[movement reference gaps](MOVEMENT_REFERENCE.md). Historical profiling stays in
focused reports and git history, rather than overlapping showcase tables.
