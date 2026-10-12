# Evaluate the Grate Plateau

Run commands from the repository root. Requirements: the pinned `sloppy/bin/sloppy`, Bash, Python 3 with Pillow, FFmpeg, ripgrep, `flock`, and a working X11/Wayland display for render checks. Generated evidence stays under `build/`.

## Play

`tools/play.sh` compiles and launches; `tools/play.sh build/game` launches an existing executable. Sloppy 0.6.0 defaults to Vulkan FIFO; the launchers set `SLOPPY_VSYNC=0` for measured lower-p99 mailbox/immediate, with `SLOPPY_VSYNC=1` restoring FIFO; `SLOPPY_VULKAN=0` selects OpenGL. Agent captures use `tools/play_locked.sh`, which owns `/tmp/botw-render.lock`.

Controls: WASD move, mouse/arrows camera, Alt walk, Shift sprint, Space jump/climb jump/glider, Ctrl/C crouch, left mouse/J attack (hold for spin), right mouse/K lock/shield, E action/perfect guard, R/L bow, G throw, 1–3 items, Tab/I inventory, M/Esc map. Space while locked hops/backflips; airborne shield + Space surfs. Inventory: E equip/eat, 1–3 bind, X drop, Q/C tabs. Gamepad: sticks move/camera, top face jump, bottom sprint, left attack, right action, left trigger shield, right trigger bow, right bumper throw, d-pad items, Start inventory, Back map. Options supports rebinding, camera settings and jump/sprint swap. [Full controls and save behavior](../README.md#controls).

| Test switches | Purpose |
|---|---|
| `BOTW_SKIP=1`, `BOTW_TITLE=1`, `BOTW_PASSAGE=1` | Outside, title overlook, cave passage starts. |
| `BOTW_AT="x,z,yaw"`, `BOTW_CAM="x,y,z,yaw,pitch"` | Player start in original coordinates; free camera. |
| `BOTW_HOUR=h`, `BOTW_TIMESCALE=k` | Clock start and clock speed. |
| `BOTW_WEATHER=clear\|cloudy\|rain\|storm`, `BOTW_WEATHER_SEQ="200:storm,1900:clear"` | Fixed weather or continuous transitions at specified frames. |
| `BOTW_BOLT=frame`, `BOTW_BOLT_AT="x,z"` | Force a storm lightning strike. |
| `BOTW_FIRE=1`, `BOTW_TENTFIRE=n` | Grass ignition or camp tent ignition. |
| `BOTW_TOWER=1`, `BOTW_RISE=1`, `BOTW_ENTER=n`, `BOTW_SHRINE=n`, `BOTW_SHRINE_AT="x,y,z,yaw"` | Raised tower, rise sequence, shrine entry, interior and interior position. |
| `BOTW_GIVE="item_id,..."`, `BOTW_ORBS=n`, `BOTW_DOORS=1` | Inventory, orb count and opened resurrection doors. |
| `BOTW_PAINT=0`, `BOTW_SCALE=1` | Disable watercolor; fixed full scene scale. |
| `SLOPPY_SCREENSHOT=build/frame.png`, `SLOPPY_FRAMES=n`, `SLOPPY_INPUT="10:w+,40:w-"` | Capture/exit frame and scripted inputs; captures advance fixed 1/60 s. |
| `BOTW_CAPTURE_DIR=build/frames`, `BOTW_CAPTURE_EVERY=n` | Additional periodic captures with a screenshot run. |
| `BOTW_WEATHER_LOG=1`, `BOTW_CAMDBG=1`, `BOTW_CONTACTS=1`, `BOTW_SCENE_LOG=1` | Weather, camera, planted-foot and scene diagnostics. |
| `BOTW_NEWGAME=1` | Fresh interactive journey; replaces progress as it saves. |

Gameplay/test/debug starts and Sloppy capture/input/frame switches disable progress I/O; `BOTW_NEWGAME` saves normally. Performance switches are below. [Complete switch descriptions](../README.md#test-switches-environment-variables).

## Prepare and measure startup

`tools/warm_assets.sh` CPU-bakes world/mesh/collision/audio/RGBA texture packs into `assets/prepared/`, then warms driver-specific shader binaries in `build/shader-cache/`; it takes the render lock once. `tools/prepare_assets.sh` performs only the CPU bake. All referenced nature PNGs must be present in `assets/src/nature/Textures`; incomplete preparation fails. Rewarm after source changes; stale headers fall back to generation.

| Mode / command | Numbers measured |
|---|---|
| `BOTW_LOADTIME=1 tools/play_locked.sh` | Per-stage seconds and in-game `loaded in`: initialization through first-callback GPU warmup; excludes compilation and earlier process startup. |
| `python3 tools/startup_copy_check.py --ref HEAD --repeats 6 --binary-repeats 6` | Fresh copy with all 20 ignored nature PNGs; separate release compile, source/executable in-game load, first-frame callback CPU and callback/capture milestones, whole-process medians/ranges. Both in-game medians must be ≤3.5 s. Owns one lock per render. |
| Add `--resident-repeats 6` to the copy check | Same copied executable with the original working directory; diagnostic for pathname/working-directory effects, requiring matching prepared payloads; warms each working directory before measuring. |
| `python3 tools/round71_startup.py` after warming | Three verified cold-local-file/warm executable pairs: load seconds, process seconds, major faults and `mincore` residency. Evicts only local prepared packs, shader binaries and executable; other caches remain warm. Owns one lock per launch; includes all nine packs and verifies cold residency inside the lock. |
| `BOTW_NO_PREPARED_ASSETS=1 BOTW_LOADTIME=1 tools/play_locked.sh`; bench `--shader-cache disabled` | Generation fallback / shader-miss costs. These are separate from prepared warm startup. |

Current release startup measurements are in [PERFORMANCE.md](PERFORMANCE.md). The [historical Round 81 audit](rounds/PERFORMANCE_PRE_060.md#round-81-startup-and-warmup-audit) retains earlier fresh-copy repeats, warmup outliers, timer boundaries and source hashes.

```sh
python3 tools/startup_copy_check.py --ref HEAD --repeats 6 --binary-repeats 6 --output build/startup-current
```

The helper copies a clean revision, including tracked terrain, plus local nature inputs into a fresh `build/` directory, runs `warm_assets.sh` there, then times standalone builds and individually locked source/executable launches. Preparation and lock wait are excluded from launch times. `loaded in` includes GPU warmup, first-frame callback CPU excludes it, and whole process includes capture/write/shutdown. Milestones from streamed logs mark callback completion before runtime submit and capture completion at frame index 1; neither measures display presentation. `python3 tools/prepared_frame_check.py --resume` retains completed captures only with a byte-identical rebuilt executable.

## Whole regression suite

`tools/run_all_checks.sh` runs the current standalone CPU, persistence, mesh, GPU-equivalence, gameplay/render, audio and prepared-startup checks. It prints one `PASS`/`FAIL` per group, continues after failures, prints totals and exits nonzero for any failure. Use `--list` for the complete manifest or `--only NAME` to rerun a group. After an interruption, `--resume build/all-checks/run-DIRECTORY` retains passing groups at the original HEAD with unchanged tracked files in `game/`, `assets/`, `sloppy/`, `tools/` and `docs/ref/` (runner recovery edits allowed); failed and unfinished groups run again. Logs, result TSV, starting commit/worktree state and summary are in a unique `build/all-checks/run-*/` directory; test fixtures/captures remain in their existing `build/` directories.

**Never wrap the runner in `flock`.** It calls self-locking tools directly and takes exactly one lock for each caller-lock tool; waits for shared render access have no timeout. Headless checks need no render lock. Helper-only `*_checks.jo` and fixture tools run through their entry points. Historical round capture/report workflows and before/after GPU comparisons require specific baselines and are indexed in [rounds/](rounds/); they are not standalone regression verdicts. Benchmarks measure performance separately.

The final Sloppy 0.6.0 sweep records **136 PASS, 0 FAIL, 136 groups**, **2,892 s**.
Evidence: [`summary.txt`](../build/all-checks/run-I1kSostA/summary.txt),
[`results.tsv`](../build/all-checks/run-I1kSostA/results.tsv) and per-group logs.
It starts at `d283589`; the analyzer-only correction `04bdf22` is committed before
its group executes. Game, assets and compiler sources are unchanged throughout.
All 129 standalone `.jo` tool entries compile without warnings; fixture/helper
modules compile through their wrappers. Native and browser game builds compile.

The earlier audit recorded **134 PASS, 2 FAIL**: a snow lighting probe was killed
and moved its camera; a cue masking assertion included its legacy 20 ms ramp.
Damage-guarded completed-frame capture passes the unchanged brightness limit on
both renderers. The old patched mixer reproduces the cue onset result within
0.00005 dB; raw onset data remains, and the unchanged 6 dB margin applies to the
settled body. No game gains or lighting thresholds change. Menu captures also
set the release's `SLOPPY_VSYNC=0` where they request uncapped rendering; the
EGL-only `BOTW_NOVSYNC` flag cannot uncap Vulkan. These corrections and root-cause
evidence are in [SLOPPY_NOTES](SLOPPY_NOTES.md) and [MUSIC](MUSIC.md).
Earlier 127-group and other sweeps remain historical records in git and
`build/all-checks/`; current timing and render limits are separate below.

The [compact performance summary](PERFORMANCE.md) is the current timing entry point;
its linked JSON retains repeats, flags, hashes and measurement limitations.

## Movement comparison (2026-10-11)

Run `sloppy/bin/sloppy tools/feel_test.jo --csv build/movement-quantification/after`,
then `python3 tools/feel_trace_check.py build/movement-quantification/after` (CPU-only).
The harness prints **25 PASS, 0 FAIL, 36 response GAP rows** and exports
`measurements.tsv` plus complete frame traces. Parameter/clip/legacy-footage agreement
is **99.8/100**, behavioral correctness **29/29**. The 8-frame reversal animation is
now an unscored physical-heading proxy, so this replaces the 26-row/99.6 aggregate.
**Zero of the six controlled response families has an accepted BotW baseline.**

Allowances for controlled references are ±5% displacement/speed and ±2 BotW frames
(0.066667 s) timing. GAP rows declare that future allowance without computing a pass.
First heading crossing uses 5°; stopping uses <0.05 m/s. Existing climb-footage
uncertainty ±0.134 s is not evidence for controlled two-frame agreement.

| Measure | BotW reference and source | Ours | Tolerance | Verdict |
|---|---|---|---|---|
| Steady run / sprint | [5.556 / 8.10 m/s, clip roots × AS rates](https://github.com/ntngel1/botw-renderer/blob/656ceeb6ab2dd0eb0d6fa352cd1a3adddf0ec10b/docs/research/wiiu-as-frame-ctrl.md) | 5.556 / 8.100 m/s | ±5% | PASS |
| Rest → 90% run / sprint | [No physical rise-time curve](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.233333 / 0.333333 s | ±0.066667 s if sourced | GAP |
| Run displacement at 0.1/0.2/0.5/1 s | [No controlled startup displacement](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AS/Player_Move.as.yml) | 0.119167 / 0.458333 / 2.099418 / 4.877414 m | ±5% if sourced | GAP |
| Sprint displacement at 0.1/0.2/0.5/1 s | [No controlled startup displacement](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AS/Player_Move.as.yml) | 0.119167 / 0.458333 / 2.592501 / 6.642508 m | ±5% if sourced | GAP |
| Release stop time, run / sprint | [No controlled release trace](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.200000 / 0.300000 s | ±0.066667 s if sourced | GAP |
| Release stop distance, run / sprint | [No controlled release trace](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.547208 / 1.206112 m | ±5% if sourced | GAP |
| 90° / 180° run body and velocity response | [Threshold 120°; no timing curve](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.183333 / 0.250000 s | ±0.066667 s if sourced | GAP |
| Jump 90° steering, lateral / forward / airtime | [MaxSpeedInAir=0.3; steering equation unidentified](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.895928 / 1.723463 m; 0.533333 s | ±5%; ±0.066667 s if sourced | GAP |
| Forward glide displacement over 2 s / speed / sink | [Native 0.02/0.35 fields have unresolved semantics](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml) | 15.547119 m / 7.773560 m/s / 2.600098 m/s | ±5% if sourced | GAP |
| 90° glide body / velocity response | [GlideRotSpeed=20; physical conversion unidentified](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml) | 0.783333 / 2.100000 s | ±0.066667 s if sourced | GAP |
| 90° glide peak heading rate | [GlideRotRate=0.2; physical conversion unidentified](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml) | 108.861981°/s | ±5% if sourced | GAP |
| Camera target lag at a run | [Chase coefficients; no validated follow equation](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/GameRomCamera.aiprog.yml) | 0.088288 m | ±5% if sourced | GAP |
| Camera reaches 45° / settles within 5° after world 90° input | [No isolated auto-follow trace](https://github.com/zeldaret/botw/blob/49c6b5c18344de6555163b3af7044970ad9d7c5e/src/Game/Actor/Camera/Action/actionCameraChase.cpp) | 1.350000 / 5.333333 s | ±0.066667 s if sourced | GAP |
| Neutral-stick sink vs vertical-only drop | [~3.2 m/s estimate, ~70 m/~22 s; no horizontal motion](https://journals.le.ac.uk/index.php/pst/article/download/3330/3017/8787) | 3.201302 m/s sink; 5.844830 m/s horizontal | ±0.16 m/s display allowance; protocol differs | UNSCORED |
| 180° physical heading vs reversal animation | [8/30 = 0.266667 s clip duration](https://github.com/ntngel1/botw-renderer/blob/656ceeb6ab2dd0eb0d6fa352cd1a3adddf0ec10b/docs/research/wiiu-as-frame-ctrl.md) | 0.250000 s | ±0.066667 s display allowance; different measure | UNSCORED |

Free traversal response constants were left unchanged without a defensible baseline. The
current public decompilation still has calculation stubs; the published TAS script
has inputs without synchronized outputs. All numerical estimates and incompatible
proxies remain excluded. [Full 36-row response table, source details, protocols and
limits](MOVEMENT_REFERENCE.md#movement-response-comparison--2026-10-11-critics-9192);
[machine-readable audit](ref/movement-quantification.json).

Validation: **203 trace/evidence checks, 1,607/1,607 traversal checks**, journey
**zero stuck points / zero hard falls / zero stamina outs**, stride slip ≤0.047%,
contact PASS. Render runs: zero. These checks establish reproducibility and internal
correctness; controlled original-game response agreement remains a gap.

## Listening clips

`python3 tools/listen.py` renders eight 45 s stereo clips and four shrine stems, verifies stem reconstruction and balance, and writes `build/listen/index.html`, `LEVELS.md`, `levels.json` and WAVs. Open the HTML to listen. The helper owns its render locks; do not wrap it. `python3 tools/live_audio_check.py` exercises the production event dispatcher; `python3 tools/analyze_live_audio.py build/live-audio --check` checks masking, repetition and headroom; `python3 tools/mix_loudness_check.py --check` measures full-mix loudness. [Listening protocol](LISTEN.md), [music and source credits](MUSIC.md).

## Performance

`SLOPPY_STATS=log` reports frame p50/p95/p99/worst every 120 frames; `SLOPPY_FRAME_STATS=1` adds runtime stats. `BOTW_FRAME_LOG=1` retains raw intervals, callback wall/thread CPU time and upload samples. `BOTW_CPU=1 BOTW_CPU_TRACE_MS=6` attributes expensive CPU stages; `BOTW_GPU=1` reports pass timer queries on OpenGL; Vulkan uses return/CPU counters; `BOTW_GPU_FRAME_LOG=1` retains per-frame GPU samples. For OpenGL GPU execution costs use `SLOPPY_VULKAN=0 BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11`; paced frame intervals and GPU/CPU execution are different measurements. Verify actual output pixels, scale, warmup exclusion, shared load and every repeat; mailbox producer intervals are not scanout timestamps.

```sh
mkdir -p build/evaluate-performance
sloppy/bin/sloppy build tools/performance_game.jo -o build/evaluate-performance/game
python3 tools/performance_bench.py capture build/evaluate-performance/game build/evaluate-performance/gpu --revision "$(git rev-parse HEAD)" --exact-output --window-loop client --window 1280x720 --scale 1 --repeats 3 --cpu-trace
python3 tools/performance_bench.py report build/evaluate-performance/gpu
BENCH_LOG_DIR=build/evaluate-performance/bench BENCH_JSON=build/evaluate-performance/bench.json tools/bench.sh > build/evaluate-performance/bench.md
```

Those tools self-lock; never wrap them. `performance_bench.py --mode paced|mailbox` captures producer intervals; `tools/round71_pacing.py` compares native Wayland paced/mailbox with X11 paced/uncapped. `tools/terrain_bench.py capture EXE build/perf/after` and `compare build/perf/before build/perf/after` measure terrain/camera costs. [Metrics, limitations and historical results](PERFORMANCE.md).

## Evidence index

Paths below are in `tools/` unless stated otherwise. Run standalone `.jo` checks with `sloppy/bin/sloppy tools/NAME.jo`; GPU checks require the lock policy in the suite manifest.

| Area | Key tools and purpose |
|---|---|
| Movement | [feel_test.jo](../tools/feel_test.jo) `--csv build/feel`: measured-reference agreement and separate behavioral score; [stride_check.jo](../tools/stride_check.jo): clip stride speeds; [contact_check.jo](../tools/contact_check.jo): feet/hands against surfaces; [traversal_check](../tools/traversal_check): continuous trajectories, hitch/rate comparisons and frame strips. Read [MOVEMENT_REFERENCE.md](MOVEMENT_REFERENCE.md), source annotations in `docs/ref/footage/`, and run `python3 docs/ref/verify_movement_response_sources.py` to verify pinned source hashes (cache in `build/movement-reference-sources/`). |
| Combat | [combat_check.jo](../tools/combat_check.jo): posed weapon/socket contacts; [fauna_test.jo](../tools/fauna_test.jo): perception, spacing, turn-taking, Stalkbonk and Talus suites; [combat_visual_check.sh](../tools/combat_visual_check.sh): production swing/flurry/throw captures. |
| Elements | [element_test.jo](../tools/element_test.jo), [element_check.jo](../tools/element_check.jo): material/reaction rules; [element_journey_check.sh](../tools/element_journey_check.sh): input-driven tree/log/fire course; [element_input_check.py](../tools/element_input_check.py): full-loop carried ignition, fresh-process save/reload, rain dousing and exact-copy reuse; [tree_test.jo](../tools/tree_test.jo): tree/log interactions and persistence; [cooking_check.jo](../tools/cooking_check.jo): recipes and warmth; [fire_query_check.jo](../tools/fire_query_check.jo): exact heat-query equivalence. [ELEMENTS.md](ELEMENTS.md). |
| Weather | [weather_fx_test.jo](../tools/weather_fx_test.jo), [weather_shading_check.jo](../tools/weather_shading_check.jo): emitters and lighting/coverage; [weather_transition_check.sh](../tools/weather_transition_check.sh), [daylight_check.sh](../tools/daylight_check.sh): continuous weather and clock transitions; [weather_silhouette_check.py](../tools/weather_silhouette_check.py): matched hero/background contrast. |
| Shrines | [shrine_route_check.sh](../tools/shrine_route_check.sh): solve all four through normal inputs; [shrine_arrival_check.jo](../tools/shrine_arrival_check.jo), [shrine_sightline_check.jo](../tools/shrine_sightline_check.jo), [shrine_shaft_check.jo](../tools/shrine_shaft_check.jo): camera/geometry; [shrine_exit_check.sh](../tools/shrine_exit_check.sh): orb-to-exterior handoff. [SHRINES.md](SHRINES.md). |
| Story | [opening_check.sh](../tools/opening_check.sh): uninterrupted wake-to-title; [opening_test.jo](../tools/opening_test.jo), [wake_contact_check.jo](../tools/wake_contact_check.jo): wake support/camera; [title_handoff_check.jo](../tools/title_handoff_check.jo), [title_panorama_check.jo](../tools/title_panorama_check.jo): input return and title framing; [story_approach_check.jo](../tools/story_approach_check.jo): greeting ownership; [late_story_check.sh](../tools/late_story_check.sh): final story route. |
| Audio | [listen.py](../tools/listen.py): clips/stems and balance; [live_audio_check.py](../tools/live_audio_check.py), [mix_loudness_check.py](../tools/mix_loudness_check.py): event mixes and loudness; [combat_music_check.jo](../tools/combat_music_check.jo): threat tiers/clock; [soundscape_check.jo](../tools/soundscape_check.jo): spatial species/ambience. [LISTEN.md](LISTEN.md). |
| Performance | [prepared_assets_check.sh](../tools/prepared_assets_check.sh), [prepared_frame_check.py](../tools/prepared_frame_check.py): byte/frame equality; [production_loop_check.sh](../tools/production_loop_check.sh): elapsed-time combat/simulation; [startup_copy_check.py](../tools/startup_copy_check.py), [round71_startup.py](../tools/round71_startup.py): launch modes; [performance_bench.py](../tools/performance_bench.py), [bench.sh](../tools/bench.sh), [terrain_bench.py](../tools/terrain_bench.py): repeat timings. [PERFORMANCE.md](PERFORMANCE.md). |
