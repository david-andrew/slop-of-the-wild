# The four shrines (game/shrines.jo)

Each entrance has a terminal ("Activate": the glow turns from orange to blue) and a lift
("Enter", once activated and once the tower has risen). The lift sinks, the screen fades, and
the player arrives on the lift pad of the shrine's chambers with the shrine's name as a banner. The pad inside ("Leave") goes back up at any time. At the end a seated monk ("Talk")
gives a Sprite Orb (`story.orbs += 1`, the shrine's `done`), fades into light, and the player is
taken back up. Falling into a pit brings the player back to the last safe spot (half a heart).

Coordinates below are local to each shrine's lift (x east, z south, y up; the way on is north).

## Ohman Ow Shrine: Magnet Trial
Chambers 180 m below the entrance.
1. **The bridge.** A pit crosses the first hall. Standing on the orange plate raises a metal
   bridge out of the pit, but it sinks as soon as the plate is let go. Push the metal crate
   (stand against a face and hold the stick toward it; it slides one 2 m cell per push) north
   twice and west five times onto the plate: the bridge stays up.
2. **The Old Sentinel Scout.** A small domed old sentinel (13 HP) guards the Wanderer's Bow on its dais
   (west). It locks a red sight on the player and fires after 1.5 s (move, or perfect-guard it
   back); close up it winds up and spins its blades. Sword hits and arrows damage it; it drops
   amber.
3. **Optional foundry.** The west doorway in the scout hall leads to a Rusty Broadsword treasury.
   A third metal crate starts at (-34,-35). The compact pier blocks a direct westward push;
   two northward pushes clear its corner, then four westward pushes reach the plate at
   (-42,-39). The six cells keep the route choice without the old eighteen-push run. This powers
   a 4 m metal shuttle across a 14 m gap, rising 3.4 m to the treasury. It docks for 4 seconds at each end,
   crosses in 19.5 seconds, and carries riders both ways. A large counterweight hoist, crosshead,
   cable drums, a weight moving opposite the lift, and an under-deck wheel carriage establish
   the heavy lift. Pale floor rails, steel piers, amber plate and blue powered platform supply the clues; no rune or instructional text.
4. **The ledge.** The monk sits on a 3.4 m smooth ledge. Push the second crate north against
   the ledge, jump onto it, and pull up onto the ledge.

## Jaba Badge Shrine: Bomb Trial
Chambers 180 m below (slightly east of) the entrance, outside the Eastern Abbey's area.
1. **Barrels and the brazier.** Two pads keep an explosive barrel each (a new one appears a
   moment after one is used). "Pick up" lifts a barrel over the head, "Throw" throws it; a sword
   hit rolls it. Carried (or rolled) into the brazier's fire, its fuse is lit: 4 seconds. A blast
   breaks the cracked wall ahead (north), and the one in the east wall hides the Wanderer's
   Claymore chest. Blasts hurt the player within 4 m and set off barrels within 8 m.
2. **The chasm.** Across a 10 m chasm stands a cracked pillar. A barrel waits at the near edge,
   another on a pedestal in the chasm, a third by the pillar: set off the first (a lit barrel
   next to it) and the chain carries across; the pillar falls over the chasm as a bridge.
3. **Optional rolling-bomb gallery.** Beyond the Claymore alcove a replenishing barrel
   sits in an engraved chute at (26,-10). A sword strike sends it east, the fire lights its
   four-second fuse, and a shutter at x=32 opens for four seconds in every fourteen. A badly
   timed roll rebounds and explodes without reaching the chain; its pad replenishes. A timed
   roll passes through and sets off four barrels at x=40,47,53,57, breaking the far wall at
   x=61 for a chest of ten Arrows. A two-tier rack of iron-banded wooden bomb drums marks
   the loading end of the gallery. The low channel guides a struck barrel; ordinary carry/throw
   behavior elsewhere is unchanged. The shutter changes amber/blue with its opening.
4. The monk's room is beyond.

## Owa Dime Shrine: Pause Trial
Chambers 180 m below the entrance.
1. **The turning bars.** Two long bars turn over a pit around pillar hubs, in opposite
   directions like meshing gears; every 10 s both lie along the way (the near floor, bar,
   bar, the far floor), and their round end pads meet for a few seconds. The hubs are safe to
   wait on; riders are carried (and the camera turns with them). When the second bar lies
   across the hall, its end touches an island in the east wall with the Wanderer's Shield.
2. **Optional suspended clockwork.** A doorway beyond the shield island leads to two
   more bars with hubs at (24.5,-28.5) and (39.5,-28.5). They turn in opposite directions,
   one third of a revolution out of phase, on a 26-second cycle. A sword or arrow striking
   the crystal on either hub arrests **that bar** for 12 seconds (15-second cooldown).
   Arrest the first along the gap, wait for the other to meet it, transfer, then arrest the
   second to reach the treasury of three Amber. A great toothed wheel with spokes and an
   axle hangs on the south wall, and the working hub crowns turn with their bars. Frozen bars and their crystals turn gold, then resume
   blue motion. Hubs are safe places to wait. Opening the chest deploys a blue return catwalk
   along z=-34; it cannot bypass the outward puzzle.
3. **The boulder stair.** A 36 m stair rises 9 m; every 6.5 s a boulder drops into the top and
   rolls down (4.5 m/s), knocking the player down. Three niches in the east wall are safe: run
   from niche to niche between boulders (about 3.4 s each time). The monk's room opens east of
   the landing at the top.

## Kay Nomut Shrine: Ice Block Trial
A flooded hall (see "Where the chambers are"). The water starts low.
1. **Crystals.** Striking a crystal switch (sword or arrow; south ledge and north ledge) raises
   or lowers the water (blue: high, orange: low). At low water the pool's sides are out of reach
   (a strip of handholds on the south side always leads out); at high water the player can swim
   across and pull up onto the north ledge.
2. **The floating crate and the gate.** A heavy crate floats in the pool. While the water is
   high the inflow's current carries it to the north-east corner, over a sunken platform with a
   plate. Lowering the water then sets it down on the plate, which opens the gate north. (A
   swimmer can push the crate too.)
3. **Optional frost cistern.** The Spear niche opens west into a second, independent
   cistern. Its two crystals, on the dry south rim at x=-20 and -40, toggle the water between
   0.4 m and 4.0 m. Raising the water floats a second crate west over a 2.8 m plate at
   (-35,-14); draining seats it. The weighted plate raises two pale blue ice blocks
   into a stair from the rim to a 6 m Opal treasury. Jump up the ice and return along the dry
   rim. A frozen waterfall hangs from a broken aqueduct on the south wall; pale faceted
   cascades and icicles contrast with the metal clockwork and warm bomb rack. The crate cannot reach the raised support at low water; floating over it at high
   water does not count as weighting the plate. This cistern uses separate water-grid cells,
   and its water, colliders and chest disappear on leaving Kay Nomut.
4. **Climbing.** At high water, handholds on the west wall reach the water: they lead up to a
   niche with the Wanderer's Spear. Beyond the gate the monk sits on a balcony up a climbable
   wall.

## Chamber presentation

The original floors, collision shells and puzzle pieces still own movement. New optional
chambers extend through framed side doorways. Their rewards are a Rusty Broadsword (foundry),
ten Arrows (bomb gallery), three Amber (clockwork), and one Opal (frost cistern); these are all
existing Plateau items. The original chest, main route and monk remain independently reachable. Local lights keep their mechanisms visible. Non-colliding
masonry adds Ohman Ow's vaulted gallery and bridge machinery, Jaba Badge's warm arches and brazier
hood, Owa Dime's suspended gear rings and deep pit supports, and Kay Nomut's pale cistern ribs
and high aqueducts. Relief panels and quieter blue inlays leave the brighter amber fittings
and puzzle objects as focal points. The named decorative meshes are hidden outside their shrine.

Crystal switches have six shaded glass facets, pointed tips, carved octagonal stone plinths,
metal claw sockets and a narrow orange/blue collar. A sword or arrow strike advances the
crystal by one sixth-turn and sends a fading ring of light from its socket. Water valves ring
with the existing chime; clockwork brakes answer with a lower chime and a metal clack. Crystals
remain seated instead of constantly spinning/bobbing, and their glow no longer washes out
material shading. The hit volume and cooldowns are unchanged.

Pressure plates have a fixed stone base, metal bezel and a separate sinking tread. Weighting
or releasing one gives a pitched mechanical click and expanding light ring. Powered pieces
have dark recessed panels, raised metal ribs and visible fasteners, with quieter luminous
inlays. Gate jambs expose their guide rods; the gallery shutter slides between built-up tracks;
the ferry carriage follows its platform. Ice has pale frosted tops and fracture seams, distinct
from the metal framing. All added construction is decorative and follows the existing collision
pieces; the new foundry pier and crate bounds are the only puzzle geometry changes.

Two amber seals turn blue as stages are first completed, with a short chime, motes and a
1.6-second light pulse. These remember completion during the session; the plates, crystals,
bridge and gate still show their current state independently. The seals track the weighted
bridge and defeated scout in Ohman Ow, broken north wall and fallen pillar in Jaba Badge, crossed
pit and upper landing in Owa Dime, and high water and opened gate in Kay Nomut.

The monk uses a single cached procedural model (`game/shrine_monk.jo`): folded cloth, thin
limbs, ribs, closed eyes, prayer beads and a wrapped crown. It uses the existing character
shader's dissolve during the unchanged Sprite Orb ceremony.

## Where the chambers are, and why
Ohman Ow, Jaba Badge and Owa Dime lie 180 m under the plateau (zones push the terrain out of
physics and switch the light to the shrine interior light), placed where the map's water grid
is dry above them. Swimming uses the map's water grid (`water_level`, `water_depth` = level
minus the terrain height), which only gives depth above the terrain, so Kay Nomut's hall
floats 140 m above the lowland east of the plateau. Its mesh (`keh_namut_room`), colliders and
chest are hidden unless the player is inside, and its pool's cells of the water grid hold the
pool's level only while the player is in it.

## Testing
- `BOTW_SKIP=1 BOTW_TOWER=1 BOTW_SHRINE=n` (1 Ohman Ow, 2 Jaba Badge, 3 Owa Dime, 4 Kay Nomut) starts
  inside a shrine.
- `BOTW_SHRINE_AT="x,y,z,face"` places the player (local to the lift).
- `BOTW_SHRINE_STAGE=k` starts with the first stages solved (Ohman Ow 1: crate on the plate,
  2: second crate at the ledge; Jaba Badge 1: the north wall broken, 2: the pillar bridge down,
  3: the alcove open too; Kay Nomut 1: water high and the crate over the plate, 2: water low and
  the crate on the plate).
- `BOTW_SHRINE_GIVE=travelers_sword,...` adds items; `BOTW_SHRINE_CARRY=1` (or `lit`) starts
  holding a barrel in Jaba Badge; `BOTW_SHRINE_ACTIVE=1` activates every terminal.
- `BOTW_SHRINE_LOG=1` prints puzzle events (plates, crates, explosions, water, gate, orb).


## Complete scripted routes

Run `tools/shrine_route_check.sh` for all four shrines, or append IDs (for example,
`tools/shrine_route_check.sh 2 4`). It builds `tools/shrine_route.jo` and runs each shrine in a
fresh process. Each result prints PASS/FAIL, simulated duration, wall time, and the complete
puzzle event trail with frame-stamped route milestones. Full logs are saved in
`build/shrine-routes/1.log` through `4.log`; failure returns a nonzero exit status.

The harness starts on the interior lift using only `BOTW_SHRINE=n`. The wrapper clears
inherited `BOTW_*`/`SLOPPY_*` variables; the harness also rejects position, stage, carry,
loadout and entry presets. Its pre-entry inventory fixture is a Wanderer's Sword and Pot Lid,
with the player's default three hearts and stamina wheel. These let it exercise normal sword
strikes and guarding; it gives no rune, arrows, orb, chest reward, or puzzle solution.

It loads the real terrain/water grids, chamber collision shells, entrance platforms, hero rig
and animations. It drives ordinary `Actions` at 1/60 second in the game's update order:
shrines, interaction, player movement, combat, animation/blade contacts, arrows, chests and
particles. Waypoint steering observes the player's position and the rotating bars' collider
transforms; it never writes player position, health, stamina, colliders or puzzle progress after
the normal lift-start hook. Every wait/movement has a frame budget. Owa Dime's boulder windows
use its fixed release cycle; its route must finish with only the deliberate pit's damage.

The shell wrapper asserts puzzle events in order as well as the harness's direct assertions:
chests open **and award their contents**, recovery restores the correct checkpoint with the
expected damage, each new beat completes in event order, exactly one bonus chest awards its specified contents/quantity and one Sprite Orb is awarded, the shrine is marked done, and the player
finishes grounded within 3 m of the exterior lift.

- **Ohman Ow:** fall into the unbridged pit and recover; push the first crate north twice and
  west five times; cross the held bridge; destroy the scout with sword/guard inputs; open the
  bow chest; test that the pier blocks a direct westward push, route the foundry crate in six
  cells round its corner, ride the rising metal shuttle to the Rusty Broadsword treasury and back; push the second crate north four times; jump/mantle its top and the 3.4 m ledge;
  talk to the monk, receive the orb and return.
- **Jaba Badge:** carry, light and throw replenishing barrels to break the east chest wall and
  then the north wall; collect the Claymore; between those walls, test a closed-shutter
  roll and replenishment, time a successful rolling bomb, collect the ten Arrows and return; fall into the chasm and recover; take a third
  barrel through the doorway before its fuse expires, throw it beside the near chain barrel,
  assert all four blasts and the fallen pillar, cross the bridge, then monk/orb/return.
- **Owa Dime:** fall beside the first turning bar and recover; board the first bar, wait on
  its hub, transfer to the second bar; ride to the east shield island, open its chest; cross the additional clockwork by striking both brakes, verify each
  collider stops, collect the three Amber and use the deployed return catwalk; ride back; cross to the far floor; time runs through all three boulder niches without a hit;
  reach the upper landing, then monk/orb/return.
- **Kay Nomut:** enter the low pool and swim until stamina exhaustion returns the player to
  shore with one heart lost and stamina restored; strike the south crystal to raise the water;
  swim to and climb the west handholds for the Spear chest; raise the second cistern, observe the float over the high plate,
  drain it using the far crystal, jump the raised ice stair for the Opal and return; swim back and mantle the north
  ledge; strike its crystal to drain the pool after the crate has drifted over the plate;
  assert the opened gate; climb the monk's balcony, then monk/orb/return. This shrine has no
  abyss and explicitly disables pit recovery, so its failure/recovery is drowning.

Verified for round 52 on master `21d764d`: simulated durations include
failure recovery, both chests, the new puzzle and return, the orb ceremony and exterior settling.
The wrapper enforces 120–240 seconds per complete route; no duration-padding waits are added.
Waiting for a ferry, fuse, gear alignment, water/current or safe boulder window is part of play.

| Shrine | Fixed steps | Simulated seconds |
|---|---:|---:|
| Ohman Ow | 7,346 | 122.43 |
| Jaba Badge | 8,087 | 134.78 |
| Owa Dime | 10,598 | 176.63 |
| Kay Nomut | 8,818 | 146.97 |

The complete suite takes about 6 seconds of wall time here, including compilation. It is
headless and does not check rendering, audio or the exterior camera; the complementary
`tools/shrine_exit_check.sh` checks the rendered orb/return and camera placement.
Every rendered check must hold the shared lock:

```sh
tools/shrine_exit_check.sh # owns one render lock per shrine
flock /tmp/botw-render.lock tools/passage_check.sh
```


## Regression and visual evidence

Verified 2026-10-09 on `21d764d` with the round 52 shrine revision:
`shrine_route_check.sh` (all four), `shrine_exit_check.sh` (all four), `opening_check.sh`,
`feel_test` (25/25 behavioral checks), `integration_test` (56/56), `save_test`, and
`element_check` (19/19) pass. Logs are under `build/shrine-evidence/round52/`; opening
checkpoints and its full camera trail are under `build/opening-check/`.

### Round 52 shrine revision

The foundry route asserts the blocked direct push and all six successful cells. The reward
assertions check exactly one Rusty Broadsword, ten Arrows, three Amber, or one Opal according
to the shrine, in addition to the original chest, recovery, puzzle, orb and exterior return.
The 120–240-second requirement still applies; the foundry ferry's longer traversal is the
working geared hoist's travel, not a test-only wait.

Current regression logs and matched before/after camera views are in
`build/shrine-evidence/round52/`. Room images in both `before/` and `after/`:

- `oman-foundry.png`
- `ja-rolling-gallery.png`
- `owa-clockwork.png`
- `keh-frost-cistern.png`
- `cistern-switch.png` (close-up)

The views use the unmodified master executable for `before/`, the revised executable for
`after/`, identical player/camera fixtures and 240 rendered frames. Visual fixtures do not enter
the fresh route tests. Every render, including shrine exits and the continuous opening, holds
`/tmp/botw-render.lock`; `opening_check.sh` acquires it itself. A comparison gallery with all
image paths is saved at `build/shrine-evidence/round52/comparisons.html`.
