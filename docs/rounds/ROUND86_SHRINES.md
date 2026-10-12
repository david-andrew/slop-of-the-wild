# Round 86 — shrine mechanisms without added text

Visual baseline: `90944b9`, work on `astra/work`. Merged coordinator master
`68ba705` before committing and reran shrine validation. The new destination
key joins Sol's immutable render-hook cache, including visibility and reuse checks. Production changes are confined to
`game/shrines.jo`. Puzzle collision, timings, controls, rewards and routes are
unchanged. No explanatory text or hints were added.

## Walk from the lift

- **Oman Au / foundry.** The old idle lens clipped the weight on the right, while
  the left pressure plate and distant monk were visible. The entry lens now
  includes the whole weight, plate, bridge mouth and destination. Orange side
  inlays mark the pushing faces. A raised conduit joins the plate to the winding
  drum, supplementing the floor connection to the rising bridge. Standing on the
  plate still demonstrates the bridge; leaving releases it, making the nearby
  matching weight useful. The next crate remains orange after the scout dies and
  dims only once delivered to the monk's ledge. Riveted iron and forge lighting
  remain the hall's material identity.
- **Ja Baij / blast chamber.** Previously the fire drew the eye but the barrel
  rack sat at the edge of the lens. Both barrels, the brazier and cracked doorway
  now share the lift view and the approach to the rack. Thin orange inlays sit
  on the existing barrel hoops. The floor circuit joins rack, ignition bowl and
  blast wall; it changes to quieter blue when the wall breaks. Lit fuses retain
  their existing pulse. The chain barrels use the same material cue in the next
  hall. Soot, fired masonry and red lighting retain the blast-chamber theme.
- **Owa Daim / clockwork.** The wheel and hubs were visible, but the traversable
  bars were pale stone/metal shapes with weak edge cues and the destination was
  lost behind the wheel silhouette. Orange rails now join each boarding tip to
  its hub. They turn blue during the existing alignment window; a passed hub
  dims. Annex brakes follow the same orange-input/blue-activated convention.
  Low ivory lamps and a landing ring mark the real stair doorway below the
  wheel. The monk remains around the existing bend. Brass gears, worn treads,
  shafts and the timing of both bars are preserved.
- **Keh Namut / cistern.** The old view showed the far crystal across the water
  while hiding the reachable near crystal off the right edge. The wider entry
  view reveals the near switch, floating weight, inflow, receiving plate and
  gate. Raised conduits stay above the water and join the near valve to the
  inflow, and the weight socket/far drain to the gate. The float has the same
  orange inlays as the foundry weight. After raising the water, the near valve
  dims while the far drain stays bright. Aqua stone, frost and reflected water
  detail remain intact.

The entry lens eases back to the ordinary 50-degree view as Link leaves the
landing. It never forces yaw. Ivory doorway inlays echo the monk's chamber;
orange marks unsolved inputs and blue marks active/completed work. Existing
solve pulses remain the brightest brief event. Completed signals and runes
settle below the next step's intensity.

## Evidence

Sixteen 1280×720 frames are retained locally under `build/round86/`:
`before/{1..4}-{arrival,puzzle}.png` and `after/{1..4}-{arrival,puzzle}.png`.
Numbers follow `BOTW_SHRINE`: Oman Au, Ja Baij, Owa Daim, Keh Namut.

Both revisions use `BOTW_SHRINE=n BOTW_TOWER=1 BOTW_SKIP=1`, fresh puzzles,
frame 180, and the production chase camera. Arrival has no input. The first
puzzle approach walks right toward the initial control for Oman, Ja Baij and
Keh, or forward toward Owa's first bar, for frames 20–55. The same inputs are
used before and after. These are gameplay frames, not free-camera compositions.
The baseline binary was compiled before edits from `90944b9`.

Reproduce the final frames:

```sh
sloppy/bin/sloppy build game/main.jo -o build/round86/after-game
tools/round86_shrine_visual_check.sh build/round86/after build/round86/after-game
```

The capture script owns one render lock per view; do not wrap it in `flock`.
`ROUND86_SHRINES` and `ROUND86_VIEWS` select a subset. Generated frames, binaries
and logs stay in ignored `build/`; none are force-added.

## Validation

- All four complete `tools/shrine_route_check.sh` routes pass, including each
  annex, chest, failure recovery, monk, orb and exterior return: 134.02, 137.32,
  179.10 and 149.87 simulated seconds respectively.
- Arrival: 12,576 camera containment assertions at 30/60/120 Hz pass.
- Sightlines: all 19 control/mechanism rays and tower-survey checks pass.
- Lighting: all 25 pigment, bounded-light and ambient checks pass; cached hook
  keys, including the new goal key, retain steady reuse and invalidation.
- Ceremony: 4,063 assertions, idle repeat and all four camera exits pass.
- Discovery: all 32 objects remain discoverable within the existing three-second
  camera scan; runes and roof winding pass.
- All 36 descent-shaft rays pass. Round 78 wall relief and monotonic solve-pulse
  checks pass.
- All four rendered `tools/shrine_exit_check.sh` cases return to the exterior
  entrance with the camera outside the hood.
- New `tools/round86_shrine_check.jo` verifies every first control/mechanism and
  destination is inside the settled, hands-off lens; the next signal is brighter
  than a completed signal; the scout does not retire the still-needed ledge
  crate; and the ordinary lens returns beyond the landing.

Logs are in `build/round86/checks/`. Scripted routes and visual inspection are
not a substitute for a new naive-player study; no human solve-rate claim is made.
