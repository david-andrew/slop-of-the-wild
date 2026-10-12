# Round 66 defect hunt

Base `5b47a6f`, `sol/work`. Run `python3 tools/defect_hunt_check.py` and
`tools/traversal_check --headless`. New probes use production simulation,
keyboard input, complete shrine collision shells, and the cooking/pickup
callbacks extracted verbatim from main. Each scenario gets a fresh process.

## Defects fixed

- **Held wooden shield/bow immune to fire:** guard/draw at a fire for 15 s.
  Both now react at their drawn sockets, burn up, cancel their actions, and douse
  when swimming. An identical spare does not inherit the destroyed shield's fire.
- **Fire arrow heats underwater:** fire an arrow downward through a water plane.
  Accepted flight segments now douse before impact; submerged arrows emit no heat.
- **Immortal wet/burning skulls:** detach a Stalkoblin skull into a pond or fire.
  Its own material exposure now destroys it and its body. Attached bodies drown
  too; skull swaps carry their exposure state.
- **Loose weapons tunnel:** launch a loose sword at 40 m/s through a 4 cm wall
  with a 50 ms step. Swept collision stops it. Pending throw queries still accept
  nearer actors and retire once at cover, retaining the incoming velocity.
- **Early cold and timer drift:** eat a pepper, then expire its warmth 25 ms into
  a 50 ms snowy update. Cold counts only the remaining 25 ms; damage intervals
  retain their fractional remainder.
- **Discarded hitch time:** inject one 500 ms traversal/camera update. Both lost
  250 ms. Their bounded 120 Hz integration now accepts the complete 500 ms.
- **Missed sword hit in a hitch:** attack a forward dummy, stall 250–500 ms.
  Blade sampling now scales with elapsed time; completed/advanced attacks retain
  their historical contact frame instead of being rotated onto the next pose.
- **Pursuit walks into deep water:** put a swimming Link beyond a river bank.
  Ground pursuit now stops at submerged support, preserving bridges above water.
  Knockback still enters water and drowns enemies. The actual plateau night-actor
  regression remains healthy instead of chasing into the critic-location pond.

Each failure has a permanent assertion; minimal before/fixed logs are retained
under ignored `build/round65-defects/round66-*`. The contact-frame fix touches
only `hero_blade_hits` in `game/chars.jo`, outside the hero model seam work.

## Passed clean

Burning submerged logs; dropped metal's pending storm strike into water; barrel
blasts beside a Talus, physical log and wooden crate; windborne fire across a river
without burning water cells; rain-doused cooking preserving held ingredients.
Knocked Bokoblin drowning and lethal cliff landing; climbing/gliding targets;
Talus support at a cliff and lens clearance at a wall; Guardian late cover;
far bow camp alerts; shrine entry/return retaining one live outdoor encounter.

Traversal covers 20/30/60/120/240 Hz, jitter and one 250/500 ms hitch per course:
1,607 assertions pass, including 4 cm wall clearance, stamina, input edges and
exactly 1,440 physics ticks per 12 s. Melee, arrows and throws at 20/240 Hz and
both hitch lengths hit once or stop at cover. Production cave, Temple roof and
all four shrine corner orbits clear the camera lens; foliage/water positions
remain finite. Existing camera checks cover climbing overhangs and Talus mounts.

## Long session and validation

The accelerated headless session runs 108,000 updates (30 simulated minutes),
30 shrine round trips, day/night, four weather types, combat, particles, piano,
ambient loops, spatial effects/echoes and native software mixing. Vitality is
refilled as a fixture; entity, timer, particle and audio pools are not reset.
GPU/driver presentation and a real audio device are outside this session probe.
Peak RSS was 592.0 MiB, with 1.22 MiB retained
after warmup. Early/late four-minute median update cost was
0.957/1.106 ms (within the drift budget). Peak pools: 209 particles,
21 voices, 5 echoes; 2 enemies/292 colliders remained fixed and items settled at 4.
Final memory/pool/update measurements: `build/round65-defects/round66-session-metrics.json`
and `round66-session-rss.json`.

68/68 new assertions, the prior 26 runtime assertions and all 22 fresh-process
save scenarios pass. All usual 20 checks pass; final summary and logs: `build/round66-checks/summary-final.txt`
and `*-final.log` (rendered checks use their original logs). Final hunt log:
`build/round66-defects-final.log`. Render probes acquired `/tmp/botw-render.lock`
once, with self-locking opening retaining its own lock. No push or merge.

## Later production-loop and memory audit

These 250/500 ms tests call subsystems directly. Round 59 found that the native
window callback and `main.jo` still clamped elapsed time before those functions
could receive it. [Round 69](ROUND69_RUNTIME_PERSISTENCE.md) fixes and tests the
actual application callback separately. It also replaces this report's RSS-only
8 MiB growth assertion with simulation-boundary live-allocation/reserved-space
checks plus an allocator-budget RSS guard, retaining raw residency evidence.
