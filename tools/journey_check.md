# Continuous Plateau journey

Run `tools/journey_check.sh` from any directory. This CPU-only check does not render or
need the render lock. It builds a snapshot of the current production modules, surveys
the finished terrain, plans routes, and drives one player continuously from the Shrine
of Resurrection mouth through the tower, Ohman Ow, Jaba Badge, Owa Dime, Kay Nomut, and the
Temple of Thyme roof meeting.

The default driver uses `Actions` stick, sprint, jump/held jump, and interact inputs with the
production player controller at 60 Hz. `tools/journey_check.sh --keyboard` runs the same nine
legs using discrete held/pressed/released keys through `input_update`, with no mouse or pad.
Arrow keys drive the production camera orientation solve shared with movement; both yaw and
pitch are exercised. Ground travel turns the camera before holding forward; airborne wall
catches use the nearest keyboard direction immediately. Climbing uses surface-local WASD.
The CPU fixture omits the lens/collision positioning solve. Its output lives separately in
`build/journey-keyboard-check/`, and metrics identify the input mode. Climbing and recovery consume/refill the stock
stamina wheel. There is one initial player placement at the requested start; subsequent
legs never set player position, velocity, health, stamina, or last-safe position. The
survey and A* planner only write waypoint files. Clearance includes production props,
rocks, structures, vegetation colliders, and water. The planner conservatively budgets
climbs between places where the player can stand and rest. Authored Owa Dime rest/ridge
waypoints guide the difficult field approach. The Hylia pass needs no route exclusion.

The nine ordered legs must each finish within 1,200 simulated seconds; individual
waypoints normally have a 90-second budget. Death, leaving the Plateau, missing tower
activation, missing Temple reward, or an unexpected displacement over three metres in
one frame fails the check. Brief blocked progress is logged and the driver may recover
using production jump/climb inputs. Maximum slope means the steepest surface climbed
or ascended on foot. Falls count landings more than one metre below the airborne peak,
including intentional jumps; hard falls use the controller's `land_hard` flag. Stuck
points count episodes with less than 0.3 metres of progress over two seconds, including
episodes subsequently recovered.

The fixture replaces only GPU mesh/texture uploads, retaining terrain generation and
collider creation. Navigation ticks run production story, player, interaction, and FX
updates; enemy AI, cold damage, and weather progression are outside this navigation
fixture and have separate checks. Two story accommodations keep travel continuous:

- Tower geometry is emerged before the physical ascent. After climbing and descending,
  the driver examines the actual foot guidance stone. It then settles tower reveal
  flags with the existing `raise_tower_now` helper and releases the cutscene state,
  excluding the rise cinematic's scripted actor relocation. `late_story_check.sh`
  separately validates that cinematic and its camera handoff.
- This entrance-only route supplies the four-orb meeting prerequisite after all four
  entrances are reached. `shrine_route_check.sh` and `late_story_check.sh` separately
  validate interior solutions and earned awards. The roof ascent and meeting callback
  are executed here through production movement and interaction.

Artifacts are under `build/journey-check/`: `run.log`, `trace.csv` (30-frame samples),
`survey.csv`, `goals.csv`, `leg-*.csv`, `metrics.json`, `sources.json` (SHA-256 source
manifest), the generated snapshot, and executable. Failures retain their exact world
point and trace. `tools/journey_controller_check.jo` provides focused regressions for
slope reprojection, slide-band climbing, falling wall catches, and lethal landings.

Trace columns are `frame,x,y,z,stamina,hp,state` (no header).

## Measured result

Final Round 64 navigation run: **67,374 frames, 1,122.90 simulated seconds, 4,851.34 metres**.
All nine legs passed with **zero stuck detections and zero stamina exhaustions**.
The runner now rejects either condition, and the old snow-bank avoidance region was
removed from A*: it surveys and traverses the corrected production bank directly.

| Leg | Seconds | Metres | Maximum slope | Climb seconds | Stamina outs | Falls | Hard falls | Stuck detections |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cave-to-tower | 99.68 | 594.12 | 23.6° | 0.00 | 0 | 0 | 0 | 0 |
| tower-climb | 123.20 | 101.14 | 90.0° | 82.23 | 0 | 0 | 0 | 0 |
| tower-descent | 105.45 | 113.53 | 90.0° | 70.13 | 0 | 0 | 0 | 0 |
| Oman-Au | 51.57 | 304.25 | 28.3° | 0.00 | 0 | 0 | 0 | 0 |
| Ja-Baij | 102.12 | 595.49 | 21.2° | 0.00 | 0 | 0 | 0 | 0 |
| Owa-Daim | 158.43 | 938.31 | 55.3° | 0.02 | 0 | 1 | 1 | 0 |
| Keh-Namut | 213.05 | 955.76 | 72.4° | 48.58 | 0 | 0 | 0 | 0 |
| Temple-approach | 195.87 | 1185.26 | 39.5° | 0.00 | 0 | 1 | 0 | 0 |
| Temple-roof-meeting | 73.10 | 62.57 | 90.0° | 53.10 | 0 | 0 | 0 | 0 |

Small production blockers corrected:

- Hylia's southern bank alternated steep climb and slide surfaces around
  `(-1322.8,346.9,2133.4)`, `(-1318.3,333.7,2120.0)` and
  `(-1324.8,356.4,2144.0)`. A short graded, feathered pass removes the repeated
  slips and stock-wheel exhaustion without changing global traversal tuning.
- Ohman Ow's low entrance lip blocked the oblique approach at
  `(-677.7,171.9,1517.9)`. A drawn outer tread with matching collision bridges
  that lip, and the base collider now matches the drawn 1.2 m base height.

- Tower collision now follows the existing seven rest ledges and flared crown; the
  previous uninterrupted shaft and absent crown support prevented stock-wheel rests
  and safe descent. Its existing top deck is climbable.
- Falling wall grabs follow held stick input while facing turns, with sufficient reach
  to catch the tower rim. The feet still require a supporting wall probe.
- Terrain-wall reprojection preserves feet height, removing upward drift that defeated
  held-down input during descent.
- The terrain climb threshold matches the slide threshold, allowing uphill climbing
  on the formerly trapped 45–50° band.
- Owa Dime's entrance pad has a broader terrain blend, removing its artificial steep
  spike; one four-metre rest shelf at the surrounding mean height breaks its western
  stock-wheel ascent into two courses.
- The Temple's existing roof deck and parapet are climbable, allowing the final mantle
  from the solid belfry corner pier.
- Lethal landing damage retains the dead state instead of immediately overwriting it
  with ground state.

Map pins are placed/removed with click or confirm at the mouse/right-stick map cursor,
are limited to 64, and are drawn only on the map. Optional `pin=u,v` save records keep
older saves compatible; changes participate in autosave milestones. `input_check`
covers mouse clicks, glyph removal, held-button repeat prevention, right-stick/pad
placement, unknown/off-map clicks, and the limit. `save_test` covers round trip,
capture/apply, malformed coordinates, non-finite values, overflow, older saves, and
autosave detection.

Map preview: `build/journey-check/map-pins.png`, generated by
`flock /tmp/botw-render.lock env SLOPPY_PLATFORM=x11 SLOPPY_SCREENSHOT=build/journey-check/map-pins.png SLOPPY_FRAMES=4 sloppy/bin/sloppy tools/slate_map_view.jo`.

## Validation

All requested checks pass: `feel_test`, `fauna_test`, `element_test`, `element_check`,
`save_test`, `architecture_test`, `contact_check`, `integration_test`, `slot_check`,
`input_check` (39/39), `camera_check`, `combat_check`, `title_handoff_check`,
`shrine_route_check.sh`, `shrine_exit_check.sh`, `passage_check.sh`,
`opening_check.sh`, `late_story_check.sh`, and `journey_check.sh`.
The additional `journey_controller_check` also passes. Regression logs are in
`build/journey-regression/`. Passage finished 4.8 m from the cave mouth after 760
frames; late story passed 17,823 assertions through four earned orbs and leaving.
Opening screenshots include `build/opening-check/mouth-reached.png` and
`build/opening-check/control-returned.png`.
