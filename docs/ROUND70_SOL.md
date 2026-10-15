# Round 70: glide framing and startup

The glide view retains its 7.2 m trailing boom even inside the cave-proximity
radius above the overlook; the 2.8 m passage cap no longer applies in flight.
The automatic glide view now ignores the ground camera's crest lift and settles
at 0.16 radians instead of 0.30. The crest search could add another 0.65 radians
and retain it after leaving a ledge. These camera rules predate the recent tower and masonry changes. The captured
overlook trace showed the passage cap active in open air; the terrain correction
also needed to be excluded from flight away from the cave.
Normal boom retraction and final lens collision still apply. The displayed glide
aim uses the requested pitch independently of collision-recovery descent lag;
manual pitch input remains available.

`task70_glide_check` fails on the original camera and passes on the new one. It
projects the horizon through the displayed field of view at 30, 60 and 120 Hz,
including inherited lifts of 0, 0.30 and 0.65 radians. A second route uses the real
Plateau terrain, solid architecture and production player controller at the
critic pack's overlook air launch. The delayed neutral-stick and held-stick routes keep the projected horizon at
26.0–31.7% of image height throughout gliding. The check uses the production cave-proximity flag and asserts the full nominal
glide boom as well as the projected horizon. The existing camera regressions
also pass.

Outdoor terrain maps now stream after the first four frames of the cave opening:
one 64-row noise tile or at most 512 KiB of texture data per callback. A production-loop check verifies no payload uploads in frames 0–3, one bounded
noise tile in frame 4, and completion in frame 131. Warmup classifies the actual
starting player and uses the cave view; its initially unpositioned lens at the
world origin must not force an outdoor drain. The height
and burn maps needed by particles remain available at startup. A complete mip
pyramid is generated after each base image finishes. An outdoor draw requires
complete maps and drains remaining work immediately; an outdoor checkpoint start
uses bulk transfers rather than dozens of small render-pass transitions.
No partial map is displayed outdoors.

Hidden warmup views use a 16×16 scissor, retain shader/material coverage, and omit
a redundant wet-world submission. During the cave opening, outdoor terrain
pipeline recipes can compile without forcing its texture payload. Full coverage
is restored before both starting-camera cascade refreshes. Grain caches are
initialized without the scissor at both production resolutions.

`task70_stream_check` compares every terrain-noise lattice texel and every texel
of both synthetic texture mip pyramids against the existing eager GPU path.
All floating-point errors are exactly zero. Indoor views also skip terrain/grass
culling and GPU patch uploads that cannot contribute visible pixels. Prepared-asset checks pass complete
byte equivalence for world, terrain, audio, textures, geometry and physics.

Startup measurements and their cache, resolution and desktop-load conditions are
in [PERFORMANCE.md](PERFORMANCE.md). Raw results and matched images are retained
under `build/task70-sol/` in this worktree. Sloppy remains the unmodified release.

Matched open-Plateau flight pairs at frames 90, 240 and 320 were viewed after
480×270 downscaling per image. Their rendered camera traces improve from
18.0–25.7% to **26.2–31.9%** projected horizon height. Evidence:
`build/task70-sol/open-flight/` (settings, raw captures, pairs and `horizon.json`).
The official pack fixture is unchanged: it flies toward a nearby cliff, which
can occlude the skyline even with a correct camera angle. The additional open
flight distinguishes camera orientation from that terrain occlusion.

The explicit capture-only pack completed on the final game sources, followed by
its full-pack resume in `build/task70-sol/final-v4-pack/`. Every one of its 45
shots was viewed against `/tmp/crit70pack/captures` in side-by-side sheets,
downscaled to 480×270 per image (`build/task70-sol/pack-comparison/`). Forty-two
are byte-identical. Passage-90 changes 123 pixels; passage-850 changes 6,672
pixels, confined to the outdoor aperture. Their mean RGB absolute differences
are 0.00014 and 0.0629 on a 0–255 scale. Neither has an apparent new artifact at
the reviewed scale; the remaining changed shot is the intended glide view.
No new grid, dither, card edge, aliasing, black blob, colour cast or repeated
shape was apparent across the complete comparison. Per-shot results and review
record are in `summary.json` and `reviewed.txt` beside those sheets.

Targeted validation passed:

- `task70_glide_check` and existing `camera_check` (final-v4 logs).
- `task70_stream_check`: all GPU noise/mip errors exactly zero; a deliberately
  different positive-control pair verifies that the comparator detects errors.
- `task70_startup_stream_check`: production opening defers frames 0–3, uploads
  one tile at frame 4, and finishes at frame 131.
- `tooling_check`, `tools/prepare_assets.sh`, and
  `tools/prepared_assets_check.sh` (complete prepared byte equivalence).

Logs remain in `build/task70-sol/{glide-check-final-v4,camera-check-final-v4,
stream-check-final,startup-stream-check-final,tooling-check,prepare-final,
prepared-final}.log`. Only these targeted checks and the full pack's selected
fast checks are claimed; the complete repository check suite was not run.

The **full final-tree critic pack passed**, retaining the 45 rendered captures,
then running a 120-second real-dt route, 13 audio clips/scores, and eight selected
fast checks (`feel_test`, `integration_test`, `input_check`, `opening_test`,
`combat_check`, `weather_fx_test`, `music_harmony_check`, `late_story_check`).
Manifest and readable report: `build/task70-sol/final-v4-pack/{pack.json,index.html}`;
command output: `build/task70-sol/final-v4-full.log`. Its 2133×1200 forest route
has CPU-thread p99 6.719 ms versus master 8.116 ms, and present-return p99
15.034 ms versus 16.320 ms (no final intervals over 25 ms).

The completed matched CPU controls retain 18 launches, three per version/scene,
with identical seeds, input, weather, time and 1280×720 full scale. Steady CPU
p99 improves: forest **7.295 → 6.838 ms**, glide **5.152 → 5.003 ms**, opening
**4.572 → 4.191 ms**. Complete-scene p99 also falls in every scene. The actual
gliding window improves **4.913 → 4.599 ms**; opening's first-120-frame p99
improves **5.122 → 4.523 ms**, with deferred transfer costs included. Evidence:
`build/task70-sol/paired-cpu-production/{summary.json,protocol.json,protocol.py}`
and per-run logs. These are shared-load CPU measurements. The earlier partial
trace-enabled control's higher forest tail is preserved and reported in
[PERFORMANCE.md](PERFORMANCE.md), together with the slightly higher early-glide
p99 and opening median/worst costs. No isolated-machine speedup is claimed.

The strict low-activity startup control on the exact final executable measures
**10.71 s cold / 1.61 s warm median (1.61–1.64 s)** at 2133×1200. The **1.5 s
warm target remains unresolved**. The official glide fixture's cliff can still
occlude the skyline; automatic camera orientation is checked independently.
