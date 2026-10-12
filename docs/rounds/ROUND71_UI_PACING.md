# Round 71: combat UI, presentation and cold-file startup

Base `36f77b7`, branch `sol/work`, 2026-10-11. Work is confined to
`botw-clone-sol`; vendored Sloppy sources and character/environment models are
unchanged.

## Combat and inventory

Lock-on uses a fixed-size open orange chevron, a dark outline and a pale inner
stroke. Its vertical position and orange intensity pulse at about 1 Hz. The
Bokoblin attachment is above the head rather than at chest height. Ordinary
enemy health remains hidden until damage; its 80-unit bar has a dark backing
and pale rim, with a 6-unit red fill. It stays readable at the 20 m lock range.

An awake, living Stone Talus within 60 m has a centered bottom health bar and
small name. Dormant/revealing/dead/gone Taluses do not show the bar; leaving the
encounter range hides it. The boss bar replaces the Talus's ordinary overhead
bar. The inventory/menu pause route continues to suppress all combat HUD.

Gear tabs use four columns at 92-unit spacing, square cells and faint empty
placeholders sized to actual inventory capacity (eight weapon slots initially).
The detail panel follows the occupied capacity rows. Empty cells cannot be
selected or activated. Navigation, scrolling and pointer hits use the same grid;
materials/key items retain their six-column circular layout. The input test's
all-item visibility checks now use each tab's column count.

Matched captures call the real update/draw and UI code, with a stationary target
on verified dry grass at `(-1050,1920)` (nearest authored tree >30 m from the target), controlled clear weather and day/night hours. The fixture sets
60% target health for visual inspection; it is not a live damage/AI benchmark.
Before sources are frozen under `build/round71/before/game` and verified byte
for byte against `36f77b7`. All final target captures log **20.003 m**.

| Before/after subject | Files in each `build/round71/{before,after}/` directory |
|---|---|
| Lock marker and damaged ordinary bar, bright grass | `lock-day.png` |
| Lock marker and damaged ordinary bar, night | `lock-night.png` |
| Stone Talus bottom bar, 60% health | `talus.png` |
| Empty eight-slot Weapons tab | `weapons-empty.png` |
| Two weapons plus six empty slots | `weapons-partial.png` |

All ten final captures were visually inspected at exact 1280×720. Capture
image/binary hashes and final game-source hashes are retained in
`build/round71/ui-evidence.json`.

## Presentation option and protocol

`tools/play.sh` defaults the already-supported **`SLOPPY_PRESENT=mailbox`** before
runtime initialization, preserving explicit overrides. Use
`SLOPPY_PRESENT=paced tools/play.sh`, or pass a compiled executable to the
launcher. It owns the render lock: do not wrap it again. Direct compiler launches
retain Sloppy's default. X11 retains EGL pacing, because this runtime's mailbox
option is Wayland-only. `BOTW_NOVSYNC=1` remains an explicit X11 override, with
the production queue bound retained. No vendored code changes are required.

The probe renders the forest at fixed scene scale 1.0. Each configuration has
two 1440-frame captures, retaining frames 241–1440 (1200 samples per repeat).
Percentiles use nearest rank; worst values retain all steady outliers. Native
Wayland runs use the production runtime loop and confirm dma-buf presentation.
GNOME's 1.667 output scale needs logical 768×432 and 1280×720 for physical
1280×720 and 2133×1200 respectively. X11 uses the established exact-client-size
adapter; both loops retain actual platform presentation. Every output PNG and
sample count is checked. Other agents' CPU/build activity is uncontrolled.

These are **producer/update-to-update intervals**, not delivered-frame or
scanout timestamps. The API exposes no Wayland presentation-feedback or X11
compositor timestamp API. Mailbox can replace an image before display. Report
presentation-call waits separately from complete frame intervals; the earlier
**50.885 → 10.314 ms** result was a presentation wait, not an entire frame.

| Platform / mode | Physical output | Producer p50 / p99 / worst, ms | Present-wait p99 / worst, ms |
|---|---|---:|---:|
| wayland / paced | 1280x720 | 16.671 / 21.117 / 42.080 | 15.658 / 36.759 |
| wayland / mailbox | 1280x720 | 7.367 / 11.230 / 32.229 | 6.962 / 27.549 |
| x11 / paced | 1280x720 | 17.370 / 18.226 / 25.116 | 14.306 / 15.703 |
| x11 / uncapped | 1280x720 | 10.790 / 18.539 / 23.927 | 14.307 / 17.271 |
| wayland / paced | 2133x1200 | 16.664 / 22.916 / 59.270 | 15.719 / 36.369 |
| wayland / mailbox | 2133x1200 | 12.971 / 17.042 / 21.708 | 0.285 / 11.883 |
| x11 / paced | 2133x1200 | 17.372 / 18.946 / 27.751 | 14.080 / 15.348 |
| x11 / uncapped | 2133x1200 | 14.800 / 18.752 / 21.246 | 3.045 / 3.883 |

Each row pools both complete repeats (2400 steady intervals). Mailbox improves
Wayland producer p99/worst at both outputs, but it does not eliminate all long
frames. X11 uncapping lowers producer p50 while leaving p99 near paced results;
it remains an override. [All individual repeats, flags and measured binary/runtime hashes](../ROUND71_PACING_EVIDENCE.json).

## Cold prepared-file startup

The rootless probe syncs and uses `POSIX_FADV_DONTNEED` on this worktree's eight
prepared CPU packs, local shader binaries and test executable, then verifies
**zero resident pages with `mincore`** before each cold launch. The tested set
was 155 files / 552.18 MiB (eight packs, 146 local shader-cache entries and one
executable; unused cache entries are included). Three cold/warm
pairs run under one render lock. Game initialization includes representative
GPU warmup/completion; process time includes runtime initialization, capture and
shutdown and excludes compilation/lock wait. All four prepared mesh-pack hits
are required. Output is exact 1280×720 X11 at scene scale 1, with swap interval 0.

This measures a cold **local asset/executable file page cache**, not a fully
cold machine. Model/texture/source-input pages, shared libraries/compiler source caches,
kernel metadata and GPU or driver caches remain warm; global `/proc/sys/vm/drop_caches` is root-owned
and is not written. A fresh pathname/copy is not itself evidence of cold pages.
The initial attempt rejected stale local packs; its 5.49 s generated load is
retained in `build/round71/startup-stale-packs` and supplies no prepared-load claim.

Cold/warm results (three launches each; all retained):

| Local file cache | In-game load median (range), s | Whole process median (range), s |
|---|---:|---:|
| Verified cold | **2.48 (2.48–2.53)** | **2.67 (2.66–2.73)** |
| Warm immediately after cold | **1.60 (1.57–1.61)** | **1.77 (1.76–1.78)** |

[Every startup run and pack/executable hashes](../ROUND71_STARTUP_EVIDENCE.json).
The warm comparison uses the same compiled executable and prepared packs.
These results do not include source compilation or establish a full system cold
launch budget.

## Climbing and checks

The body-normalized climb measurement is **0.489 body heights/s**. The proposed
BotW reference **0.909 body heights/s** (one height per 1.1 s) lacks a footage
URL/frame window for the described stamina-free cycle. It remains **G / guess**,
excluded from measured agreement. Existing footage establishes 0.921 torso
lengths/s; converting that to standing body heights requires pose assumptions.
No movement constant changed. See [the evidence audit](../MOVEMENT_REFERENCE.md).

Passed: production build; input **2088/2088**; slots including paused transactions
and both carried-metal warning positions; combat **495 swing frames**, visible
tip error ≤0.000011 m; feel **99.6/100 measured agreement**, **29/29 behavior**;
integration **1316/1316**; fauna zero failures including **158/158 Talus**;
camera, contact, save, element, presentation and rendered menu-pause checks. `slot_check` had a stale
2.65-radian back attachment expectation from before the merged scabbard change;
it now independently expects the rendered 2.45-radian sword attachment.

Reproduction (all render helpers below own their locks; never wrap them):

```sh
python3 tools/round71_ui_check.py before  # freezes 36f77b7 if needed
python3 tools/round71_ui_check.py after
python3 tools/round71_pacing.py
tools/prepare_assets.sh
python3 tools/round71_startup.py
sloppy/bin/sloppy tools/input_check.jo
flock /tmp/botw-render.lock env BOTW_SKIP=1 sloppy/bin/sloppy tools/slot_check.jo
sloppy/bin/sloppy tools/combat_check.jo
sloppy/bin/sloppy tools/feel_test.jo
```

The first Wayland sizing diagnostic intentionally rejected 2133×1200 output
requested as 1280×720. Its raw data remain under
`build/round71/pacing-sizing-diagnostic`; it is excluded from the matched results.
Initial downhill/occluded and shallow-water target captures were rejected; the final fixture uses verified dry grass.
Raw logs, binaries, images and page-residency lists stay under ignored
`build/round71/`. No `build/` files are force-added.
