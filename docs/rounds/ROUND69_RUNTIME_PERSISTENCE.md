# Round 69: production elapsed time and persistent item transactions

Base merged revision: `fe93d1c396d777619b39ea923c00da4563cef274`.
Changes are confined to the project; neither the vendored Sloppy toolchain nor the
separate slop-lang repository is changed.

## Actual application callback

The Round 59 critic supplied 500 ms to `main.jo` and observed only 50 ms of world
clock/status progress. The native window loop independently supplied at most
100 ms. Direct subsystem hitch tests therefore did not prove live-loop behavior.

`main.jo` now measures `time()`, Sloppy's monotonic clock, between callbacks.
The first callback uses its supplied interval so asset load/warmup is excluded.
Each interactive callback accepts 0–500 ms and runs all simulation functions in
steps no larger than 1/120 s, at most sixty steps. Longer stalls discard excess
elapsed time without carrying catch-up debt. Menus poll input once, consume wall
time and return before simulation; all fixed-step captures retain 1/60 s
per displayed frame. Autosave bookkeeping runs once per callback, and native close/F10 saves once
before catch-up and returns. One-frame actions are consumed on the first substep, held
controls remain held, and mouse/controller look is divided across the substeps.

`tools/production_loop_check.sh` compiles the entire real `main.jo` with a fixture
callback and owns one render lock. It verifies:

- a supplied 500 ms callback advances simulation, hour, warmth and autosave time
  by 500 ms;
- a 500 ms monotonic interval hidden behind a native 100 ms callback also advances
  all 500 ms;
- a moving item stops at a 4 cm wall and two overlapping hostile arrows damage
  Link only once;
- a two-second stall accepts 500 ms/60 steps, and the next small callback has no
  catch-up backlog;
- one E pulse picks up one of two co-located items across sixty substeps;
- a paused menu consumes elapsed wall time without advancing the world or
  catching up when closed;
- fixed-step captures advance 1/60 s even without scripted input and despite a
  500 ms wall interval;
- native close/F10 writes the save before simulation and does not advance a
  500 ms catch-up interval on its final callback.

`tools/menu_pause_check.sh` also passes its full four-tab/dawn/weather/warning/
cooking/HUD regression. These tests establish production-loop guarantees; the
older traversal/camera/combat 20–240 Hz and 250/500 ms probes remain subsystem
guarantees. They do not promise bounded whole-frame CPU cost or hitch-free GPU
presentation under every load.

## Placement and gear persistence

Field placements use an identity made from original item ID and source position,
independent of runtime array ordering or the position after falling. This includes
actor-derived field items, the five opening branches and placed camp rocks. A successful
pickup records the identity; full inventory leaves the world item and ledger
unchanged. Burning/consuming a placed item also records its removal.

Placed gear, arrow bundles and prepared foods never respawn. Apples, mushrooms,
peppers, herbs and acorns regrow at their original placement after 7200 seconds
of unpaused simulation and only when Link is at least 80 m away. The remaining
timer survives restart; offline wall time does not advance it.

Each weapon/shield/bow inventory entry owns an elemental record, including
unequipped entries and duplicate item types. Drop/throw/shock transactions transfer
heat, wetness and burning to the actual world item; pickup transfers them back.
Save records retain all entries and the equipped weapon, shield and bow state.
Legacy saves without the new records still decode with their original defaults.
Earlier saves cannot retroactively identify pickups they never recorded.

The new `tools/placement_gear_save.jo.in` runs through `defect_hunt_check.py` in
three fresh processes. It collects the placed Rusty Broadsword, camp rock, apple and mushroom;
saves equipped burning weapon/shield/bow state; uses the inventory UI's real drop
transactions; reloads, picks up the ground items using main's real callback and
saves/reloads again. It also reloads an almost-expired material timer and verifies
that only materials regrow, after expiry and distance eligibility.

## RSS investigation

The critic's full hunt grew 9156 KiB after its wall-time-based warmup sample and
failed the old 8192 KiB assertion. Its isolated repeat grew 812 KiB. Re-examining
its retained samples shows stepwise residency changes rather than a reproducible
slope. RSS includes resident allocator free lists, lazily touched pages and
transparent huge-page residency; it is not a count of live game allocations.

Two instrumented fresh 30-minute hunts now record memory at the same simulation
minute boundaries. After minute eight, live allocations stay within one allocation
(6204–6205), and reserved address space grows **1024 KiB** in each run. RSS grows
**564 KiB** in the earlier run and **19,856 KiB** in the final full hunt; the final
run's huge-page residency changes by **96,256 KiB**. The old RSS assertion would
fail that final run despite stable live allocations and reserved space.

The separate 60-minute / 216,000-frame investigation stays at 6205–6206 live
allocations, grows **3324 KiB RSS / 2048 KiB reserved space** after minute eight,
and grows only **932 KiB RSS** during its second half. Huge-page residency changes
by **83,968 KiB** while total RSS grows just 3324 KiB. No sustained live-object
leak is observed; the RSS-only 8 MiB assertion was unstable.

The permanent check keeps raw external RSS samples and per-minute RSS, virtual
memory, huge-page and allocation counts. After two passes through all four weather/
shrine cycles, it requires a live-allocation range no larger than 32 and reserved
address-space growth below 8 MiB. Its RSS guard is 64 MiB, matching the vendored
native allocator's documented per-thread large-block reuse budget (`__BIG_KEEP`), rather than
an 8 MiB page-residency assumption. No allocator or machine settings are changed.
Timing and particle/voice/projectile/entity bounds remain independently checked.
This is headless simulation/native-mixer evidence, not a GPU/driver leak test.

Raw logs and JSON are under `build/round65-defects/` and
`build/sol-memory-60.{log,json}`; compact tracked evidence is linked below.

## Startup terminology and merged-revision measurements

The historical 1.60 s median measured `loaded in`: initialization from `t0` inside
`game/main.jo` through the first callback's GPU warmup. It did **not** measure the
whole source command. At historical `6f76ed5`, 18 warm, prepared source launches
reported 1.60 s in-game (1.52–1.67 s), 2.925 s whole process, and six compiled
launches reported 1.575 s in-game. The critic's six later prepared source launches
reported 3.26 s in-game (3.07–3.46 s); that does not reproduce the historical number.

Current measurements below use an archived `fe93d1c` tree beneath this worktree's
ignored `build/`, with the four ignored terrain inputs, revision-matched CPU packs
baked by `tools/prepare_assets.sh`, and warm, driver-validated shader cache entries.
Six source-command and six executable launches use 1280×720 X11 output, default
opening scene, scale 1, uncapped one-frame capture. Each is a fresh process; no
page/shader caches are flushed. A single `flock /tmp/botw-render.lock` serializes
the batch, and measured process time excludes lock wait. Other CPU jobs and the
one-minute load average are recorded, not controlled. The executable is built
before timing; `sloppy/bin/sloppy game/main.jo` compiles for every source launch.
Whole process includes compilation where applicable, initialization, first capture
and shutdown. The prepared pack hits are required, not presumed from file existence.

| Launch mode, six fresh processes each | In-game `loaded in`, median (range) | Whole process, median (range) |
|---|---:|---:|
| `sloppy/bin/sloppy game/main.jo` (compiles) | **1.655 s** (1.630–2.370) | **3.030 s** (2.970–3.770) |
| Prepared release executable | **1.585 s** (1.550–1.640) | **1.770 s** (1.730–1.820) |

All twelve launches are retained, including the first source launch at 2.370 s
in-game / 3.770 s process. One-minute system load ranged **3.50–4.38**.
The 3.5 s **in-game median** target passes in both modes; it is not a whole-process
budget. These measurements concern the merged base, not a future combination of
concurrently edited branches.


Reproduce with `python3 tools/startup_copy_check.py --ref fe93d1c --repeats 6
--binary-repeats 6` (the script owns its render lock). The retained prepared tree
can be reused with `--prepared-copy build/startup-fe93d1c`; logs and full JSON are
under `build/sol-startup-fe93d1c/`. The final callback capture and log are under
`build/production-loop-check/`.

## Validation

Passed: production-loop fixture, menu pause, full defect hunt (both passes plus
three fresh-process placement/gear transactions), save/status/encounter-weather/
Talus save wrappers, and input/element/camera/combat/traversal/cooking checks.
The input suite reports 2088 checks; cooking reports 67; Talus save/element reports 60.

[Compact measurements and regression evidence](../ROUND69_RUNTIME_EVIDENCE.json).
