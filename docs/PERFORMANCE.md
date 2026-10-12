# Performance — Sloppy 0.6.0, 2026-10-12

The pinned toolchain is the unmodified official **0.6.0** release (`7c8d133`).
Measurements use an i7-6700 / GTX 1070 on the shared Linux host, after the full
suite completed, with no controlled CPU workers. These are observed distributions,
not isolated hardware guarantees. Vulkan pipeline caches are warm unless stated otherwise.

## Vulkan presentation at 2133×1200

Two 720-frame captures per scene/mode, with the first 240 frames discarded:
**960 pooled intervals per row**, nearest rank, production dynamic scene scale.
Each helper owns one render lock per process. Intervals are present-return
handoffs, not scanout timestamps. `SLOPPY_VSYNC=0` was confirmed as **mailbox**
on this driver; the release defaults to FIFO when the variable is absent.

| Scene | FIFO p50 / p99 / worst ms | Mailbox p50 / p99 / worst ms |
|---|---|---|
| Forest | 16.67 / 25.26 / 34.09 | 11.13 / 15.54 / 50.14 |
| Fire | 16.68 / 33.62 / 53.15 | 8.91 / 12.95 / 17.00 |
| Overlook | 16.68 / 30.35 / 57.53 | 7.43 / 10.81 / 44.37 |

Mailbox lowers p99 in all three matched views, so `tools/play.sh` and
the packaged launcher select `SLOPPY_VSYNC=0`. Set `SLOPPY_VSYNC=1` to restore
FIFO; set `SLOPPY_VULKAN=0` for OpenGL. The old locally patched
`SLOPPY_PRESENT=mailbox` option is gone. The forest mailbox worst is **50.14 ms** versus FIFO's **34.09 ms**: lower p99
does not remove every hitch. GLES per-pass timer queries do not
measure the Vulkan renderer; its diagnostics report return intervals and CPU.

## Ten-minute forest session windows

Each mode walks the same forest/meadow waypoint route for 600 real seconds,
with production dt and dynamic scale at 2133×1200. Movement continues through
all ten minute samples: FIFO covers **2.53 km**, mailbox **2.55 km**. Complete
monotonic two-second windows begin after four seconds plus an even-second boundary;
counts below use each window's nearest-rank p99. All outliers remain.

| Mode | Interval p50 / p99 / worst ms | Windows p99 >20 ms | Windows p99 >17.5 ms |
|---|---|---|---|
| Fifo | 16.67 / 31.36 / 331.99 | 191/297 | 268/297 |
| Mailbox | 11.32 / 17.56 / 223.17 | 45/297 | 104/297 |

Mailbox improves both window counts, but the strict all-window 17.5 ms target
is **not met**. Worst window p99 is **178.64 ms FIFO / 63.85 ms mailbox**.
These producer-return measurements include callback and presentation stalls;
they are not delivered-frame timings. After minute one, live allocation ranges
are **50,533–50,550 FIFO / 50,544–50,575 mailbox**. RSS ends at **799.67 / 771.91 MiB**,
with brief higher samples retained in the JSON; heap counters do not measure
all live bytes.

## Matched render validation

Ten fixed-frame 1280×720 views compare Vulkan, release OpenGL and master
`6d09c8c` (the renamed game with the previous toolchain). The opening uses frame
600, after its initial blackout. On release OpenGL, opening/overlook/forest/fire/
pond/camp/snow/shrine/title match master **pixel for pixel**; storm differs by
one count in one channel of one pixel. The CPU pine width hash explicitly retains
the old swizzle evaluation input; otherwise the compiler fix reshaped firs.

Vulkan preserves scene geometry, objects and UI, but does **not** reproduce every
OpenGL pixel. Across these views, mean absolute RGB difference is **0.05–2.66
counts out of 255**; p99 is **1–27 counts**. Mip pyramids now work, while the
release device does not enable OpenGL's 8× anisotropy. Shader floating-point
and sampling differences remain visible in textured foliage/shading. Cropped
RGBA/float readback, facet orientation, terrain noise, skin palettes and material/
post surfaces are verified by real GPU checks. Exact Vulkan/OpenGL parity is
not claimed. Images and 4× difference maps remain in `build/sloppy060/visual-gated/`.

## Prepared startup from a fresh export

Clean `git archive` plus all nature texture inputs, freshly prepared packs,
`warm_assets.sh`, then six new source processes and six executable processes.
X11 1280×720, scene scale 1, one captured frame. Lock wait is excluded; shared
page/driver caches are not flushed. Every pack hits, with zero startup PNG decodes.

| Launch | In-game load median (range), s | Whole process median (range), s |
|---|---|---|
| Compile and run source | 1.475 (1.43–1.52) | 3.180 (3.15–3.23) |
| Prepared executable | 1.355 (1.33–1.45) | 1.615 (1.58–1.71) |

In-game load includes first-callback render warmup. Source process time also
includes compilation. First-callback thread CPU medians are **4.117 / 4.410 ms**
for source/executable. Warm-cache startup meets the existing **3.5 s load median**
budget. A new GPU/program pipeline cache can add substantial first-launch
shader work; warm-cache figures must not be presented as cold-cache times.

The self-contained Linux package is built from HEAD, with linked nature texture
inputs materialized at their target timestamps. The packaging preflight at `9138e8f`, extracted at
`BOTW_SKIP=1 BOTW_AT="-1000,1620,3.14"` hits every prepared pack, reports
**zero PNG decodes** and **18,587 vegetation placements**. Two one-frame forest
launches use an isolated `XDG_CACHE_HOME`: empty Sloppy pipeline cache **8.91 s
load / 9.76 s whole process**, then warm **1.31 / 2.18 s**. Shared driver/page
caches are unchanged; this is not a fully cold machine. Forest screenshot cost
also differs from the opening used by the repeated startup audit.

Reproduce (Python helpers take their own locks; the direct session takes one explicitly):

```sh
python3 tools/render_evidence.py pacing --output build/sloppy060/pacing --repeats 2 --frames 720
sloppy/bin/sloppy build tools/render_session.jo -o build/sloppy060/session
# Repeat once with SLOPPY_VSYNC=1 (FIFO), once with 0 (mailbox):
BOTW_SKIP=1 BOTW_AT="-1140,1500,3.14" BOTW_HOUR=11 BOTW_WEATHER=clear \
BOTW_FRAME_LOG=1 SLOPPY_PLATFORM=wayland SLOPPY_WINDOW=1280x720 \
SLOPPY_VSYNC=1 PROBE_SECONDS=600 PROBE_ROUTE=forest \
flock /tmp/botw-render.lock timeout -k 5 660 build/sloppy060/session > build/sloppy060/forest-fifo.log
python3 tools/renderer_compare.py --baseline build/sloppy060/master-renamed --output build/sloppy060/visual
python3 tools/startup_copy_check.py --ref HEAD --repeats 6 --binary-repeats 6 --output build/sloppy060/startup
```

[Machine-readable release evidence](performance-sloppy060.json) records the full-suite
verdicts, flags, source hashes, repeats, session windows and audio/render results.
Raw evidence is retained in `build/sloppy060/pacing-final/`,
`build/sloppy060/forest-final/`, `build/sloppy060/visual-gated/` and
`build/sloppy060/startup-final/`. Summaries include flags, source/executable
hashes, every repeat and raw interval/window distributions.

[Historical pre-0.6 OpenGL timing, contention and startup studies](rounds/PERFORMANCE_PRE_060.md)
retain their original data and protocols. They are separate from these release
Vulkan measurements.
