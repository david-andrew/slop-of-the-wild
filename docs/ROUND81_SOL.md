# Round 81 — Sol evidence

Source base: `db844da`, branch `sol/work`. Generated captures, traces, saves,
compiled helpers and dependency environments remain under `build/round81/`.

## Presentation

Options labels the controller setting **Gamepad: swap jump / sprint**. The
keyboard list keeps its thirteen-row viewport and adds a full-height scrollbar,
row range and explicit wheel/arrow hint. All twenty-five actions remain available.
The controller bumpers and Q/C retain their inventory-tab navigation.

Ja Baij's breakable walls have connected, branching fractures with dark chipped
lips and narrow amber cores on both faces. Crystal facets carry different values
and pedestal recesses are darker. Sword bevels are wider and retain brighter
steel against the blade's shaded face; club grain, dark bindings and worn binding
edges separate in sunlight. Shrine floors retain distinct warm plate, scorched
stone, aged green slab and blue frost pigments beneath the same cool lighting.

Oman Au and Keh Namut's arrival lens looks farther into the hall while retaining
the first three mechanisms. The full destination doorway arch shares the reveal.
Keh Namut's closed sluice still physically blocks the monk: its visible gate is
the arrival goal. The 30/60/120 Hz regression includes all four arch corners.

Climbing architecture fully discards supports in its foreground fade region.
The held shaft and shadow casting remain solid. The native GPU regression covers
16,384 pixels for each of these three cases, using the actual building fragment
shader. The production tower course reaches climbing from `-560,1722,0`.

Held lock-on persists when a dodge becomes airborne. Side hops retain the raised
shield pose; a backflip layers the shield arm over its flipping body pose. A shared
production shield transform is used by drawing and measurement. The combat check
covers 420 hop/backflip/air/landing samples at 30/60/120 Hz. The lock lens uses a
larger shoulder angle, and combat without a selected target eases away
from an aligned nearby enemy. Normal aiming and deliberate camera pans retain their
control. Camera checks require separated head centres and complete actor framing. Lock
reacquisition keeps the nearer shoulder, avoiding an orbit through Link during a
windup. Solid clearance reduces that angle when it preserves more of the boom;
manual input releases the unselected shoulder promptly.

## Continuous element interaction

[Frame strip](../build/round81/elements/chain/interaction-strip.jpg) ·
[Continuous rendered clip](../build/round81/elements/chain/play.mp4) ·
[Original frame index](../build/round81/elements/chain/strip.json)

One uninterrupted 1,620-frame session uses inventory, movement, slot and attack
input. The torch catches at the campfire, is carried more than six metres, lights
grass, is extinguished by the normal rain transition, is exchanged for a sword,
then the same doused copy is re-equipped and swung. All propagated grass must be
out before reuse. The complete clip retains one image every four simulation
frames at 15 fps; the strip selects seven original frames. The separate functional
course continues to test saving mid-burn and restoring in a new process.

```sh
python3 tools/element_input_check.py --continuous --record --output build/round81/elements
python3 tools/element_input_check.py --output build/round81/element-functional
```

## Checks and measurement protocol

`tools/combat_framing_check.py` adds walkable terrain, the real Temple entry and a
collidable forest tree to the five-enemy flat course, now 960 frames per scene.
The slope and tree courses use three front-facing attackers; the confined
doorway uses one melee opponent between its walls, a short sidestep and pans
across both jambs. All retain the same geometry and visibility thresholds and use production AI, posed
weapon contacts, lock/unlock, movement and camera orbits. Body and equipment masks
are separate. Visibility includes other bodies and equipment; environment depth,
character dissolve and contact effects are not subtracted from these conservative
CPU masks. Rendered frames supply the environment evidence.

The expanded course exposed a presentation-clearance bug: near-plane body vertices
formed an unbounded projected rectangle, and its distance correction could exile
a foe hundreds of metres. Coverage is now clipped to the viewport, and each
iterative size correction is bounded to 0.35 m. Eight actual posed lens-straddling
cases fail on the old code and pass on the fix. The flat, slope and tree courses require three real contacts; the new
single-opponent doorway requires one. The 6% coverage limit and original
visibility/separation thresholds remain intact.
Complete pose evidence is now saved even when an encounter assertion fails.

The window helper accepts a completed client only when its successful process
produced a fresh, complete PNG of the requested size. It distinguishes this case
from observed live client geometry, propagates unsuccessful child status, and
rejects stale, incomplete or incorrectly sized evidence. A renderer finishing
during the initial geometry-negotiation delay follows the same validation path.

`run_all_checks.sh` includes the completed-client regression and climbing GPU
regression. Its headless `cpu_checks` array remains one entry per line. The latest
full committed sweep remains **127 PASS / 0 FAIL** at the source base; the expanded
runner has 129 groups. This round uses targeted validation and does not claim a
new full-suite sweep.

Every game launch acquires one `/tmp/botw-render.lock`, releases it at process end,
and is bounded independently of queue wait. CPU contention workers start only
inside the benchmark's one render lock and stop with its game process. They have
no GPU context or window. Startup separates compilation, in-game load, callback,
capture and whole-process milestones. Long raw logs include shared system load
and all outliers; queue wait is excluded from startup totals.

## Retained results

| Area | Result and evidence |
|---|---|
| Input and menus | 2,386 input checks; every inventory tab pauses simulation, suppresses world HUD, and resumes pending weather/cooking correctly. `input_check.log`, `menu-final.log`. |
| Shrines | 12,576 arrival checks across 30/60/120 Hz; discovery, sightline, enclosure, lighting, shafts, architecture and all four production-input routes pass. `shrine_*_check.log`, `shrine-route.log`. |
| Combat and camera | 495 swing frames, enemy wrist/weapon tracks, 420 locked dodge/air/landing samples, eight near-plane actor cases and stale-pose protection pass. Lock/release, head separation and manual-pan camera checks pass; peak ground lock transition remains 0.200 m per 60 Hz frame. `combat_check.log`, `camera_check.log`. |
| GPU | Climbing support removal, held-shaft/shadow opacity, grazing post edges, skin palette reuse/COW/rotation and asynchronous shader reflection pass. `climb-occluder.log`, `post_edge_check.log`, `skin_row_check.log`, `shader_load_check.log`. |
| Prepared startup | World/audio/mesh/collision/roof/RNG/texture byte equality and identical generated/prepared opening, overlook, pond and shrine pixels pass. Three fresh-copy startup snapshots pass the 3.5 s median budget. `prepared-assets-final2.log`, `prepared-commitable.log`, `startup-*/summary.json`. |
| Elements and capture tools | Continuous chain and separate save/reload functional course pass. Window completion race, child failure status and stale/incomplete/wrong-size capture rejection pass. `element-continuous.log`, `element-final.log`, `element-functional.log`, `window-check.log`. |

The latest flat, slope and tree pose traces are in `combat-final-source/`; the
final doorway course is in `combat-doorway-final/`. Earlier doorway diagnostics
retain unsuccessful longer strafes, full camera circles and standing multi-hit
expectations. They are not silently counted as passing evidence. The final
single-opponent course uses short pans across the jambs and requires one genuine
posed hit, while the three outdoor crowd courses retain their three-hit minimum.
[Per-scene validated measurements](../build/round81/combat-summary.json) identify
these exact sources and evidence directories.

Visual evidence includes [Options at the bottom of its binding list](../build/round81/options/frame-479.png),
[Ja Baij arrival fractures](../build/round81/shrine-captures/jabaij-arrival.png),
[Oman Au's destination arch](../build/round81/shrine-captures/oman-goal.png),
[Keh Namut's destination arch](../build/round81/shrine-captures/keh-goal.png),
[tower climbing](../build/round81/coordinator/tower-climb/frame-440.png),
[the raised side-hop shield](../build/round81/coordinator/locked-hop/frame-160.png),
and [tent-fire head separation](../build/round81/coordinator-final/tent-fire/frame-230.png).
The tent capture uses `BOTW_TENTFIRE=5` at `-955,1964,0` with ordinary sword input.
The older native tower/hop captures precede the later lock-shoulder changes;
their occluder and shield paths are unchanged by those changes.

[Performance report](PERFORMANCE.md#round-81-contention-audit) retains the complete
CPU diagnosis and warmup audit. Matched-executable contention raises callback
wall p99 from 11.54 to 28.84 ms; recovery thread CPU p99 is 6.51 ms. Most reported
15–26 ms callbacks use less than 8 ms thread CPU. Real CPU bursts accumulate
8–17 simulation ticks after long waits, rather than one loading or periodic
stage. The exact driver/compositor/scheduler cause remains unmeasured.

Fresh-copy prepared load medians are 1.67–1.81 s across this round's two later
snapshots, consistent with the critic's 1.76 s. The warmup probe reproduces a
7.10 s launch, and omitting the newer vegetation/character binding warmups still
produces 7.03 s. Existing outdoor and wet-terrain draws dominate that outlier.
Their opaque driver/wait cost is unresolved; the newer binding warmups remain.
Historical startup figures now live in one report, and the README accurately
labels the latest full committed sweep as 127 groups.
