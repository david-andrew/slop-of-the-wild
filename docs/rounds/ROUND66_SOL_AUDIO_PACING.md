# Round 66: score headroom, native pacing, and crowd readability

Base: `c612330`, fast-forwarded on `sol/work`. Raw evidence stays under
`build/round66/`; no runtime sources were changed.

## Score ring

The regression combined a variable mixer multiplier with ring samples divided by
its target gain. A tiny positive fade target could bake enormous ramp samples.
Only the ramp was repainted on a nonzero retarget, leaving the old constant
suffix and one excluded interpolation guard in the ring. A later target change
multiplied those stale samples by a different scale.

The ring now stores the complete envelope directly, with mixer gain fixed at
unity and targets bounded to `[0, 8]`. Every retarget repaints the whole live
window, including its final guard. Unchanged targets refill only consumed frames.
Contiguous constant-tail spans keep the cost bounded without allocating whole
piano tails. The existing 20 ms sample ramp and interrupted-ramp continuity remain.

`music-transition.log` verifies 127/400/800/1600-frame blocks, fractional pitches,
8192-frame native blocks, source equivalence across wraps, actual release silence,
near-zero/negative/excessive targets, and overlapping mood/cue fades. The retained
stress p99 is 0.749 ms; victory/escape p99 are 0.074/0.068 ms. Worst individual
stress frame is 1.424 ms; the requirement is p99 under 1 ms.

`music-render.log` contains every default route, including both 600 s biome
exports. Their peaks are 0.685501 (score) and 0.688370 (full mix), with zero
clipped samples. The suite now has an explicit `music_render` entry that runs all
routes with the headroom assertions enabled. Its runner log is
`suite-music-render.log`, and its detailed log is copied to `checks/music_render.log`.

`live-audio/` captures the real sequencer, production event dispatcher, ambience,
and unnormalized software mixer: scenario, engaged, low-health, ten-minute field,
and two-minute biome walks. `live-biome-final/` additionally verifies four
crossings while a nonzero score envelope is sounding. It walks continuously at
3 m/s across the production forest radius and `area.u8` snow boundary, out and
back on each course; a fixture reset at 60 s joins the distant courses. These are
scripted audio integration inputs, not a terrain-physics or hardware-loopback
capture. Every frame checks stem reconstruction against the actual mixer, and
both pre-limiter overloads and clipped output samples are zero. The full audio
analysis and loudness checks pass (`live-audio-analysis-final.log`,
`mix-loudness-final.log`); the biome full-mix peak is about -3.73 dBFS.

## Presentation attribution and preparation

See `docs/SLOPPY_UPSTREAM.md` section 4 for reproduction commands and limitations.
The 18,000-frame forest control spans 286.99 s; 29 ten-second stalls are native
`vkAcquireNextImageKHR` waits, not `vkQueuePresentKHR`, fences, or game work.
The corrected 95.64 s pond capture and a 65 s clear-only/audio-disabled probe
reproduce the cadence. Pipeline-cache reads occur only during loading in the
forest, and never in the clear-only control. Autosave uses 180 s plus milestones.
The game profiler counter now avoids a collision with the runtime accumulator;
old game wall/gap columns were inflated, while thread/native measurements remain
valid. Raw logs: `forest-before.log`, `pond-after.log`, `presentation-probe.log`.

A separate early hitch is `libdecor_dispatch`: 76.96 ms outside the game callbacks
in `startup-v2.log`. Loading now submits black frames through both native slots,
waits for the swapchain work, and services delayed Wayland decoration events for
a bounded 120 ms. In `startup-v3-1.log`, the 91.36 ms decoration call completes
during loading; first game CPU is 6.985 ms and first-24-frame residual gap peaks
at 0.447 ms. Native acquire/fence waits remain; first-24 producer worst is 49.769 ms.
The second repeat also moves its 95.07 ms decoration dispatch into loading;
first CPU is 8.496 ms and first-24 residual gap is at most 0.490 ms (producer
worst 38.445 ms). `performance-report.json` preserves the native-call lists and
cadence measurements. This does not claim a steady-state WSI or scanout fix.

`warmup-final.log` verifies 47 -> 47 pipelines across weather, night, combat FX,
all shrine paths and scale changes. The check now flushes the production HUD
before its artificial target switches, avoiding an invented 2D pipeline on the
grain attachment with blending disabled; missing pipeline keys are reported.

## Crowd readability

Waiting enemies choose distinct lateral lanes from the camera axis instead of
queuing behind one another. The crowd/world solver also separates nearby combat
head lanes in projected horizontal space, independently of root height. The
locked target, committed attackers, and stationary lookouts retain their poses.
A conservative 2.7 m envelope covers animated ears/head motion and the following
camera tick; normal collision and ground constraints share the solve.

The framing check skins the actual head-weighted vertices, measures projected
head width, and asserts that every visible pair has at least one head-width of
horizontal centre separation regardless of vertical distance. Baseline
`combat-before/` has 740 failing frames; at frame 310 a pair is only 0.118 widths
apart despite 115.88 px of vertical separation. The former 40 px hero/head rule
passes that baseline, demonstrating why the new metric is necessary.

Final all-scene evidence is `combat-final/`: flat five-enemy crowd, walkable slope,
Temple doorway, collidable tree and tent-fire convergence. Existing hero coverage,
40 px hero/head distance, selected windup visibility, posed body/weapon contacts,
capsule gaps, three-frame hit pauses, and camera middle-third checks still apply.
All five courses pass with zero horizontal head-overlap frames. Minimum pair
clearance is 1.219 widths on flat ground, 1.435 on the slope, 1.408 by the tree,
and 1.428 in the tent-fire crowd; the single-enemy doorway has no enemy pair.
The README placed-camp frame 310 is retained in `combat310-final.png`, and the
placed-camp sword check retains 19 impact frames and 13 HP of real damage in
`camp-sword.log`.

Suite-relevant regression logs are copied into `checks/`, with runner summaries
in `suite-relevant.log` and `suite-final.log`. The complete check suite was not
run; the music/combat/camera/input/save/integration/soundscape and relevant warmup,
framing, live-audio and loudness checks were selected for this change.
