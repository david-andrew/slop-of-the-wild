# Traversal checks

Run `tools/traversal_check` from any directory. It runs headless production-input
trajectories at 30, 60 and 120 Hz plus irregular frame schedules, then captures
continuous rendered sequences at 60 Hz and with jitter/hitches.
Each game capture takes `/tmp/botw-render.lock` and releases it on completion;
compilation, verification and image encoding run outside the lock. Waiting for
another agent's render does not count against the 180-second game-process timeout. Outputs live in
`build/traversal-check/` and do not touch saves or game options.

Useful commands:

```sh
tools/traversal_check --headless
tools/traversal_check --headless --baseline 73006e5
tools/traversal_check --render-only
tools/traversal_check --render-only --render-cases corner_press
tools/traversal_check --verify-rendered
```

`--baseline REV` extracts that revision's complete `game/` tree into `build/`,
compiles the same current course and measurement code against it, and records
before measurements without modifying the checkout. Baseline defects do not have
to pass the post-fix assertions. `--out PATH` keeps an independent run.

The course supplies initial fixtures only. Thereafter it fills keyboard held and
pressed buffers, calls **production `input_update`**, and runs the real player,
camera, animation selection, foot and mantle solves. It never assigns Actions,
warps the player, or forces a traversal state after initialization. The chain and
rain cases start already gripping a valid wall; the separate mantle cases cover
approaching, grabbing, climbing and pulling over its top through normal input.
The lift is an isolated moving metal platform driven through the shrine's actual
`__ride` carry callback before the player update. Full-shrine route checks remain
responsible for puzzle mechanism timing and rotating-bar routes.

Cases cover uneven slope walking/running/sprinting and stopping; completed,
let-go and stamina-interrupted mantles; a narrow doorway followed by a right turn;
turning/reversing while pressing against the wall; jump/fall landing into held
sprint; climb → fall → glide → regrab; three repeatable wet-climbing slips; and
riding, walking off and landing from the moving platform.

Each headless CSV contains every frame over 12 seconds: player position/velocity,
state, stamina, grounded flag, landing lag, sprint state, camera position/target,
yaw/pitch, boom length, per-frame steps, independent sphere/solid overlap,
final-skin planted-foot drift/sole clearance/toe gap, active contacts, landing pose,
held mantle-grip error and events. `report.json` contains assertions, event times,
maximum errors over **complete trajectories**, state/slip-aligned path comparisons,
camera overshoot and settling to within 20 mm. The stationary tail must have less
than 1 mm per-frame movement. Settling must agree across rates within 150 ms;
signed overshoot stays under 150 mm.

Every complete player/camera trajectory has a 150 mm cross-rate bound, including
the doorway and discrete state transitions. Diagnostics also compare complete
intervals aligned by observed transitions. Rain deliberately
slips by 900 mm at once; a one-frame slip timing difference must not be classified
as foot slide. Lens overlap is independently measured from sphere-to-box/cylinder
distance and must stay below 1 mm; planted-foot drift below 1 mm, soles above
-5 mm, and toe separation above 40 mm. Camera frame steps must shrink with the
update interval, bounded by `40 / Hz + 0.025` m; this rejects the original
3.1–3.3 m jumps at every rate while allowing smooth obstacle retraction.

Rendered runs use the same course/input/player/camera and production hero draw,
character shaders, shadows and watercolor post on a continuous heightfield mesh.
They retain 40 PNGs at 250 ms intervals, a selected six-frame `strip.png`, an
animated `sequence.webp`, and a rendered `trajectory.csv` for each case. The
rendered player/camera trajectory must agree with headless 60 Hz within 2 mm.
`--verify-rendered` repeats these checks and rebuilds strips without GPU work.
These are isolated regression fixtures, not screenshots of the complete Plateau.

## Findings against 73006e5

- Mantle let-go and exhaustion were ignored: both completed instead of falling.
  Both now transition directly from mantle to air; exhaustion uses the existing
  climb drain. Non-ground states also clear the stale grounded flag.
- The mantle arm solve still used 0.55 s after the player's mantle became 0.8 s.
  Grips could miss the rim by 1.180–1.216 m during the first half of the pull.
  Using `MANTLE_TIME` holds them within 0.016 mm. The final solve also samples
  the body clip on that clock, so its standing pose no longer arrives at 69%
  of the physical pull.
- Camera center rays missed door jambs, and the player capsule's step permission
  admitted the lens through platform tops before ejecting it sideways. Independent
  lens overlap reached 650 mm under wall pressure, 163 mm at the doorway and
  282 mm at the lift; now below
  0.003 mm. At 60 Hz the completed-mantle/drop camera step falls from 3.204 to
  0.624 m, and lift departure from 3.133 to 0.496 m. At 120 Hz those steps fall to
  0.326 and 0.264 m, respectively. The lens now slides along solids while the
  collision boom settles. Stationary camera overshoot peaks at 92 mm; settling
  ranges from 0.17 s on slopes to 3.99 s after regrabbing a wall.
- Moving lift contacts remained fixed in the world: 36–66 mm foot drift. Anchors,
  contact normals and brake contacts now follow their supporting collider's rigid
  transform; lift drift is at most 0.068 mm over all three rates.
- Wall pressure during a tight turn brought the toes within 12.7 mm at 120 Hz.
  Enforcing each foot's existing side constraint on the final IK target keeps
  separation at least 114.6 mm in that case.

No player/camera tuning constants were changed. Existing slope drift remains
below 0.02 mm, landing lag is 80 ms after a jump and 650 ms after a hard fall, and
held sprint is recognized on the first ground update after landing. The measured
reference feel score remains 99.6/100 with 29/29 behavioral checks passing.

## Irregular frame and boundary regressions

Five additional production-input courses cover sprint/stop/direction changes,
three short jump taps, three separate attack taps, camera look press/releases,
and sprinting into a 4 cm wall. Each runs for exactly 12 seconds / 1440 physics
ticks under alternating 8/25 ms, seeded random 5–50 ms, the random sequence with
100 ms hitches every seventh displayed frame, and an 8.2/0.2/8.1/0.3 ms sequence
that repeatedly produces zero-tick frames. The reference uses 120 Hz frames.
Only timestamped input events split a displayed interval; hitches otherwise reach
`player_update` and `camera_update` as a single 100 ms call.

Press/releases occur 0.1 ms before/after 120 Hz boundaries. Every schedule sees
exactly the same keyboard timeline through production `input_update`, including
a 0.2 ms jump tap spanning a boundary and a tap entirely in a zero-tick interval.
CSV columns record dt, input counts, physics tick counts, accepted swing IDs and
the minimum z across every internal physics sample. Checks require exactly three
jumps/attacks, every physics tick retained, and the capsule to remain on the
approach side of the thin wall at every substep. These are behavior assertions,
not just checks of the input buffers.

Compare every displayed state to the reference's matching completed physics
tick, including zero-tick frames. This avoids inventing an interpolated pose
between ticks or across jumps/landings. All player/camera errors remain below
150 mm; yaw below 25 mrad. The attack fixture calls the production combat update
once per displayed frame, as main does; combat's variable-frame lunge therefore
has a nonzero cross-rate displacement within that same bound.

Each additional rendered course uses the jitter/100 ms hitch schedule. Its entire
12-second trajectory must match headless within 2 mm. The 600-frame capture keeps
40 images and a six-frame strip, holding the settled final view after the course
ends. CSV timestamps and strip labels report simulated time.

Defects found by these cases:

- Movement used the previous displayed frame's camera yaw for every physics
  tick in a hitch. Reusing the camera orientation solve between player ticks
  removes direction-change drift without moving camera collision or combat
  correction ahead of the world update.
- Camera look consumed the remainder's delta early. It now retains the delta
  belonging to unintegrated time, including frames that contain no physics tick.
  Microscopic cancellation residue is cleared so a released look returns to idle
  instead of continually resetting the auto-follow timer.
- Float roundoff in an unobstructed boom could activate collision damping.
  A 0.1 mm comparison tolerance prevents that false collision; real collision
  clearance and the existing lens-overlap assertions remain enforced.

Against `de0c3db`, the hitch direction-change course's peak player/camera error
falls from 359.8/288.5 mm to zero at recorded precision. The tiny-frame camera
course falls from 181.9 mm to 0.010 mm; all camera look profiles peak at 0.303 mm.
Attacks remain within 138.4 mm, with exactly three accepted presses in every
schedule. The wall fixture includes 43 real 100 ms updates; a hitch reaches
contact and subsequent hitches attempt 810 mm of travel while the capsule stays
at z = 0.370 m. The complete headless suite passes 997 assertions.

## Round 66 extremes

The headless suite now also runs 20 and 240 Hz plus one complete 250/500 ms
update in each timestamped course. Player/camera accept up to 500 ms per call,
retaining the bounded 120 Hz physics integration. Main's ordinary interactive
callback still caps its simulation dt at 50 ms; these direct production-path
probes deliberately test larger intervals than the normal callback supplies.
At 240 Hz, compare completed physics ticks and measure camera displacement at
its 120 Hz integration rate. Zero-tick frames repeat the prior pose; they cannot
be compared to a future reference tick or required to advance sprint recovery.
The 20 Hz feedback-controlled mantle/regrab course allows 0.30 m for the later
input observation; timestamped irregular-input courses retain the 0.15 m bound.
