# Round 70: startup review after the weather merge

The extra outdoor warmup draws do not explain the reported default-opening
`startup_copy_check` failure. The merge at `4174934` keeps the outdoor body inside Sol's
`if not opening:` guard, which is correct for deferring outdoor texture work. Startup classifies the actual player
position before the first camera update. The check clears `BOTW_*` overrides,
so it starts in the cave and skips this entire body, including the clear-cloud,
rain/night, and extra wet-terrain draws. The two initial outdoor world passes
already existed in `76a4595`; the merge changes their cloud values and restores
one additional wet-world pass. It does not add three world passes to that base.

The saved environment is restored after the rain/night pass; the extra wet pass
restores wetness and the alternating shadow-frame counter. The outdoor guard
also avoids forcing the deferred terrain maps during the cave opening. However,
it leaves the newly changed weather programs without a draw specialization;
that separate coverage gap is fixed below. The shader sources, prepared
assets, timing budget, and startup measurement protocol remain unchanged.

## Measurement protocol

Evidence is under `build/astra-startup-review/` in `botw-clone-astra`. The
unmodified `tools/startup_copy_check.py` was run with `--repeats 6
--binary-repeats 6`, twice for each revision, in merged/baseline/baseline/merged
order. Every batch creates its own clean archived copy, prepares the assets,
and launches six fresh source processes and six fresh binary processes.
Both revisions use Vulkan/X11, 1280×720, full scale, and the default cave
opening. Each launch takes the shared render lock; launch timing excludes the
lock wait. No driver setting, shader cache, or system cache was cleared.

`merged-{1,2}/summary.json` and `baseline-{1,2}/summary.json` retain the inputs,
source/binary hashes, commands, per-stage timing, first-frame timing, screenshots,
and load averages. `comparison.json` aggregates them; `repeat.py` and
`summarize.py` retain the run order and aggregation. These are shared-machine
measurements, not isolated-machine benchmarks or proof of a speedup.

## Reported failure

The original `4174934` failure is retained as `reported-failure.json` (copied
read-only from the coordinator's startup summary). Its source median is 4.470 s,
with a 2.35–9.63 s range, and its binary median is 2.465 s. The 9.63 s source
launch spends 1.71 s in world loading and 3.02 s in enemy placement, before
render warmup; warmup itself is 1.647 s. The 8.01 s launch spends 2.35 s in world
loading and 3.596 s in warmup. Other launches of that same binary/revision have
roughly 0.7–0.8 s warmup. The first pre-merge comparison batch also exhibits
4.07–4.09 s source outliers with 2.404–2.475 s warmup, despite lacking the extra
wet-world pass.

This rules out attributing the failure to those skipped outdoor submissions.
The spikes span unrelated loading stages and also occur before the merge.
Shared-machine/driver scheduling is consistent with the observations; its exact
contribution has not been isolated. The 3.50 s budget remains unchanged.

## Weather coverage correction

A direct production-loop probe reproduced a separate coverage gap in the merged tree: start in
the cave, render a clear outdoor view, then change to rain/night with closed
clouds and wet terrain. Pipeline count increased **49 → 51**. The new entries
were wet terrain (program 3, key 1002) and closed sky (program 27, key 1002).
See `cave-weather-coverage.log` and its retained fixture. The cached driver
binaries do not substitute for creating the per-process pipeline handles.

`weather_pipeline_warmup` now submits one terrain patch through both dry and wet
programs and draws both sky programs into the production HDR target under a
16×16 scissor. It runs after the hidden cave view has initialized the scene and
shadow uniforms, for both cave and outdoor starts. It does not select terrain,
require streamed maps, advance shadow scheduling, or change the environment
seen by the first frame. The extra full-world wet pass is removed; the existing
representative daytime and rain/night outdoor passes remain guarded.

The corrected probe retains **51 → 51** pipelines through the weather change.
The new `weather_warmup_check` preserves this regression in the render checks
of `run_all_checks.sh`, including an assertion that the cave's maps are still
deferred after warmup. Its negative control is the failed unmodified-merge run,
not a source-text assertion. Existing outdoor-start warmup coverage and the
production streaming check are also exercised.

## Startup results

All four unmodified-revision batches passed the unchanged 3.50 s median budget.
Each pair below is the source / binary median, in seconds:

- `merged-1` (`4174934`): **2.365 / 2.285**.
- `baseline-1` (`76a4595`): **2.425 / 2.345**.
- `baseline-2` (`76a4595`): **2.415 / 2.410**.
- `merged-2` (`4174934`): **2.390 / 2.505**.

Pooling the two batches per revision gives **2.425 / 2.395 s before** and
**2.380 / 2.360 s after** the merge (12 samples per mode per revision). Source
ranges are 2.26–4.09 s before and 2.29–6.15 s after; binary ranges are
2.25–3.47 s before and 2.16–3.59 s after. Pooled warmup medians are
0.7615 / 0.7295 s before and 0.7710 / 0.7315 s after. Post-launch one-minute
load averages span 1.26–5.46 across the four batches. No sample was discarded.

The final small-draw correction also passes `startup_copy_check --worktree
--ref 4174934 --repeats 6 --binary-repeats 6`: **2.490 / 2.465 s** medians,
2.40–4.81 / 2.35–3.36 s ranges. Its render-warmup medians are 0.790 / 0.795 s;
post-launch load averages are 3.94–4.74. Evidence:
`fixed-startup/{summary.json,source-*.log,binary-*.log}`. This is a small loading
coverage correction, not a demonstrated cure for unrelated startup outliers.

## Targeted validation

- `tools/run_all_checks.sh --only weather_warmup_check`: **PASS**, 1/1.
  Runner evidence: `build/all-checks/run-XQXVRixs/`; wrapper log:
  `build/astra-startup-review/weather-check-runner.log`.
- Existing `render_warmup_check` fixture extended locally to exercise cloud
  values 0.42 and 0.85, with both clear and rainy outdoor starts: **PASS**,
  **53 → 53** pipelines in each (`coverage-{clear,rain}.log`). This also covers
  combat effects, shrine transitions, and cached render-scale switches.
- `task70_startup_stream_check` on Vulkan: **PASS**, no map uploads in frames
  0–3, one bounded tile in frame 4, complete by frame 300 (`stream-check.log`).
- `bash -n tools/run_all_checks.sh` and `git diff --check`: **PASS**.
- The same production streaming check on OpenGL: **PASS** (`stream-opengl.log`).
  Pipeline inventory assertions are Vulkan-specific; no OpenGL startup-budget
  claim is made from this compatibility run.

## Visual evidence

The explicit capture-only critic pack completed on the final game sources:
`python3 tools/critic_pack.py --only captures build/astra-startup-review/final-pack`.
All **45** final captures were viewed against `/tmp/crit70pack/captures`, at
480×270 per image in side-by-side sheets `pack-comparison/sheet-01.jpg` through
`sheet-12.jpg`. Thirty-two are pixel-identical to that older `b73727d` reference.
The 13 changed shots include the already merged camera, cooking-pot, scorch,
rain-lighting, and HUD changes. No new grid, dither, hard card edge, aliasing,
black blob, colour cast, or shape repetition attributable to this warmup change
was apparent. Per-shot differences and the review record are in
`pack-comparison/{summary.json,reviewed.txt}`.

For a direct check of this correction alone, the unchanged
`task70_weather_capture.py` froze `4174934` and the patched worktree with the
same seeds, camera, hour, weather, and frame count. Clear and rainy forest shots
at frames 240 and 300 are all **pixel-identical**. All four downscaled pairs were
viewed (`forest-{clear,rain}-{240,300}.jpg`, `matched-images.json`), with original
PNGs/settings/source hashes in `matched-{before,after}/`.

The full-pack resume also **passed**:
`python3 tools/critic_pack.py build/astra-startup-review/final-pack --resume`.
It retained the 45 captures, completed the 120-second pacing route, rendered
13 audio clips/scores, and passed all eight selected checks: `feel_test`,
`integration_test`, `input_check`, `opening_test`, `combat_check`,
`weather_fx_test`, `music_harmony_check`, and `late_story_check`. Manifest/report:
`final-pack/{pack.json,index.html}`; command output: `pack-full.log`.
Its p99 present-return interval is 16.250 ms, with three intervals above 25 ms
(worst 35.365 ms); CPU-thread p99 is 10.380 ms. This shared-load route is not a
matched before/after control, and its scheduling spikes are retained rather than
reported as an isolated-machine speedup. Only the targeted checks and the full
pack's selected checks were run, not the complete repository suite.

## CPU controls and remaining limits

The first three unpinned matched captures per version were mixed: median run
CPU-thread p99 was **6.387 → 8.062 ms** in clear forest and **6.382 → 6.756 ms**
in rain. These results are retained in `cpu-comparison.json` and the six
`matched-{before,after}{,2,3}/` directories; they were not dropped from the report.

To distinguish a change from machine/placement variation, the exact same frozen
binaries were then run on CPU 2, with an identical-baseline A/A/A/A control and
an A/B/B/A comparison. The scene settings, 901-frame process length, and 718
steady samples were unchanged. Each process takes its own render lock. The
standard critic-pack nearest-rank percentile (`ceil(n*p)-1`) is recomputed from
raw logs by `pinned_report.py`; `pinned-cpu/summary.json` and `runs.json` are the
canonical results rather than the progress log's initial floor-rank estimates.

- Clear forest: identical-baseline p99 spans **6.577–8.921 ms** (2.344 ms spread).
  Paired mean run p99 is **7.3595 → 6.5235 ms**; the two comparison runs are
  8.271/6.448 ms before and 6.469/6.578 ms after.
- Rain forest: identical-baseline p99 spans **6.741–6.933 ms** (0.192 ms spread).
  Paired mean run p99 is **7.3695 → 7.0735 ms**; the two comparison runs are
  7.669/7.070 ms before and 7.048/7.099 ms after.

The CPU-tail increase does not reproduce in these ordered, affinity-pinned
controls. They do not establish an isolated-machine speedup: the unpinned tail
variation and the full-pack route's spikes remain visible in the evidence.
`pinned-cpu/*/*/{run.log,settings.json}` retain executable hashes, flags, commands,
and load averages. The final `game/main.jo` hash matches the final startup copy,
critic pack, and frozen binary used for the CPU controls.

The exact cause of the coordinator's intermittent startup spikes remains
unisolated. All five startup-copy batches passed the existing median budget;
no budget was relaxed. The cave-start weather coverage gap is fixed and guarded
by a reproducible failing-before/passing-after check. Prepared inputs and the
vendored Sloppy release were not changed.
