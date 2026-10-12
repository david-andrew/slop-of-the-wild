# Round 70 — sheath, fire tail, journey and crowds

Base `645907d`; `botw-clone-sol`, branch `sol/work`.

- Cached leather scabbard with metal locket/chape and exposed hilt, ending at the
  opposite hip. Shared attachment transforms separate sword, shield and bow.
  Drawn blades keep their combat length. `chars.jo` edits only the gear block/import.
- Fire discovery rejects trees outside conservative ignition bounds, preserving
  six-callback coverage. Loose-item updates collect active heat sources once,
  add new ignitions immediately and check live state. Other queries use full
  scans. Timing buffers are reused; CPU trace fragments join once.
- Owa Daim’s cliff lip near `(-960,2322)` escaped the 2 m endpoint survey. Eight
  samples per directed edge now exclude steep descents. The 4.858 km journey has
  zero hard falls, stamina exhaustion and stuck points. Owa retains one ordinary
  landing; zero hard falls is now asserted.
- Combat states receive clearance before alert rises. Living Bokoblin pairs use
  2.5 m; four initially overlapping, zero-alert fighters retain ≥2.499 m at
  30/60/120 Hz with waiting-ring participation. Physics capsules/skeleton spacing
  remain intact. Matched `combat420` live-pair clearance rises 2.204→2.607 m;
  that recording has three survivors.

## Measurements

Warm scale 1, steady frames ≥241, all outliers retained. Fire: two 2400-frame
captures per phase at exact 1280×720. Forest: two baseline/one final 3600-frame
captures at exact 2133×1200. Full flags, load readings, hashes and worst frames:
[`ROUND70_RUNTIME_EVIDENCE.json`](../ROUND70_RUNTIME_EVIDENCE.json).

| Metric, ms | Baseline | Final |
|---|---:|---:|
| Fire CPU wall p99, individual runs | 7.926 / 9.512 | 8.392 / 8.491 |
| Fire CPU wall p50 / p95, pooled | 4.696 / 7.136 | 4.409 / 6.690 |
| Fire CPU wall / thread p99, pooled | 8.293 / 7.802 | 8.477 / 7.949 |
| Forest CPU thread p99, pooled | 7.690 | 7.010 |
| Forest interval p99 / worst, pooled | 18.621 / 46.407 | 18.300 / 30.206 |

Both final fire runs meet the 8–9 ms target and match baseline pixels exactly.
The critic’s 10.21 ms was not consistently reproduced; timing varies between
runs, so these measurements do not establish a causal p99 reduction.

**Remaining presentation stall:** baseline native Wayland pacing reproduced
50.885 ms present with only 0.592 ms runtime-gap thread CPU; game work was
5.897/5.819 ms wall/thread. Queue polls in that batch stayed ≤2.827 ms. Mailbox
reduced present p99/worst 13.628/50.885→0.303/10.314 ms. Runtime callback/buffer
waiting (`sloppy/lib/game/wayland.jo:1036`) is implicated; callback timing versus
buffer release/driver behavior remains unproven. Targets resized only at frame
0; no steady shader requests or >1 ms uploads occurred on the stalled frame.
Other paced uploads reached 6.192 ms. Live allocations ranged over 25;
reference counting excludes tracing GC but does not exclude transient allocation.
Disabling the X11 queue bound worsened present p99 2.791→19.389 ms; it remains
on. Presentation defaults and vendored runtime are unchanged.

## Verification and artifacts

Passed journey, defect hunt (30 simulated minutes), combat, contact, fauna
(37,872 spacing checks; Talus 158/158), integration 1316/1316, trees 75/75,
fire query 3380 exact pairs, heat-source differential 43,882 exact queries,
fire scan, elements, input 2088/2088, camera and feel 29/29. Long-session RSS
growth: 944 KiB; virtual growth: 0; live-allocation range: 1.

Sword before/after: `build/round70/{before,after}/idle.png`; both directories
contain idle/run/climb/glide/swim with/without shield/bow and an idle side view.
Production sword/combat images: `build/round70/scene-{before,after}/`.
Logs: `build/round70/`; journey trace/metrics: `build/journey-check/`.

Reproduction helpers: `round70_sword_check.py`, `round70_scene_check.py`,
`round70_present_probe.py`, `round70_heat_check.py`, `round70_report.py` under
`tools/`. Sword/scene/benchmark helpers own their locks. Baseline sources are
frozen under `build/round70/before/game`; report validation checks source hashes,
complete captures and paired fire pixels. Scratch stays in ignored `build/`.
