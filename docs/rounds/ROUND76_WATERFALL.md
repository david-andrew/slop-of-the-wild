# Round 76: continuous west waterfall

Baseline: master `52b9982`; work and commit on `sol3/work`.

The west curtain now uses one world-space flow coordinate across its three
steep runs and two rock benches. It no longer restarts its edge mask, lip or
whitening at each grid segment. Three anisotropic paint layers form long,
unequal, tapered rivulets moving downward at 22 m/s, with finer aerated breakup.
The shallow upper lip retains its reflective water treatment before the face
turns white. Broken foam marks the 194 m and 144 m ledge contacts.

Averaging shallow shelf water with adjacent drops buried part of the sheet
inside an exposed rock lip. The existing shared vertices now bow outward near
those contacts (at most 6.5 m), tapering back into the lip, banks and receiving
pool. No vertices, indices, passes or particle instances were added. The
heightfield, water-height grid, collision and swimming data are unchanged.
Existing west ledge spray sits in front of the bowed sheet; the existing mist
billows and low veil concentrate nearer the plunge pool, with the existing
outward ripple rings retained. Only rock immediately beside this course gains
an uneven dark, cool spray wash. Other waterfalls retain their prior shading.

## Visual evidence

`build/round76/waterfall-{before,after}/` contains native 1280×720 stills,
three consecutive snapshots ten updates apart (300, 310, 320), source manifests,
compiler logs, executable hashes, environments and timing logs. Snapshot names
identify the update that reads the preceding completed framebuffer. The final
321 still is separate. Native stacked pairs and motion GIFs are at the root of
`build/round76/`; `waterfall-report.html` provides a view/frame selector and
comparison slider, including a native-pixel option.

Cameras:

- West cliffs: `-1600,235,1815,1.2,-0.15` (requested critic camera).
- Below, receiving pool: `-1565,119,1858,1.22,0.22`.
- Cliff top: `-1380,288,1837,-1.78,-0.65`.

The first overly uniform strand pass and an upper-lip pass that painted a broad
pale strip over shallow water were rejected. Their scratch captures remain in
`waterfall-candidate/` and `waterfall-final/`; those are not the accepted result.
The accepted `waterfall-after/` comparisons were inspected at native size in
all three views. No blur, ruled-line pattern or dashed-stroke texture was added.

Reproduce with `python3 tools/round76_waterfall_check.py prepare before|after`,
then `motion before|after`, `pairs`, or `perf before|after REPEAT`.
Each game run owns one `flock /tmp/botw-render.lock`; invoke the tool directly.
Motion capture saves PNGs and is intentionally excluded from timing evidence.

## Verification and west-cliff performance

`tools/prepare_assets.sh` ran explicitly; `tools/prepared_assets_check.sh`
rebakes and checks the accepted generated/prepared buffers byte for byte.
`water_coverage_check`, `map_water_check`, `landscape_check`, `weather_fx_test`
and `tools/journey_check.sh` pass. Journey: 67,380 controller frames, 4,865.54 m,
zero stuck points and zero hard falls. Journey and map coverage are unaffected
by the subsequent render-only refinements. Logs are under `build/round76/` and
the standalone checks' recorded `build/all-checks/` directories.

Three 960-frame runs per phase at the requested west-cliff camera, physical
1280×720 X11, scene scale 1, no vsync, fixed 1/60 simulation step. Exclude the
first 240 frames; use nearest-rank percentiles, then median across repetitions.
2,160 steady frame samples per phase. `waterfall-performance.json` retains every
run's result; raw samples remain in the logs and metadata beside the captures.

| Metric (ms) | Before | After |
| --- | ---: | ---: |
| Frame interval p99 | 15.176 | 15.200 |
| Frame interval p50 | 9.265 | 9.560 |
| GPU total p99 | 3.622 | 3.639 |
| GPU total p50 | 3.541 | 3.555 |
| Water GPU p50 | 0.124 | 0.122 |
| Callback wall p99 | 7.623 | 8.275 |

Frame p99 changes by +0.024 ms (+0.16%), within the repeated-run spread.
Intervals measure update-to-update execution including presentation and polling,
not compositor scanout. Raw callback timing is retained rather than hidden.
No claim of an independent critic score or broader frame-rate improvement.
