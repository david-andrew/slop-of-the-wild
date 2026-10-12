# Elements (game/matter.jo, game/elements.jo)

Everything that can react is described by what it is made of (`Matter`) and carries a small
state (`Elem`). Each frame the world measures its exposure (heat from fires near it, water, rain,
cold, electricity) and `react()` applies the same rules to everything:

| exposure | matter | result |
|---|---|---|
| water | anything burning | put out; soaked (wet things catch slowly, dry over a minute) |
| heavy rain | a torch | put out, with ignition heat quenched; stays out while exposed |
| heat (builds up over time) | flammable (wood, grass, trees, monsters) | catches fire; burns for its burn time, then is gone (a torch burns until put out) |
| heat | explosive (barrels) | goes off: a blast that hurts, throws loose items, lights wood, sets off other barrels |
| heat | food | cooks (apple → baked apple, meat → seared steak, shroom → toasted) |
| heat | icy (Ice Gloop) | melts |
| heat | frozen | thaws |
| cold | living | chills, then freezes for a moment |
| electricity | metal, living, or anything wet | shocked: monsters drop their weapons, the player drops a metal weapon |

Sources of heat: lit campfires, burning grass (spreads cell to cell downwind, not in rain, and
leaves scorched ground; its heat browns the grass ahead, and burning brands carried on the wind
start spot fires further on), camp tents of dry hide (they catch, burn and fall in, leaving charred poles in the ash), burning items, burning monsters, burning trees, fire arrows, a lit torch
or burning weapon in hand. Arrows that fly through fire become fire arrows. A storm's lightning
strikes whoever holds metal, and the storm's other bolts strike the ground; each shocks what is near
(further when it is wet), everything in the water it falls into (within 14 m), and metal lying
near it passes the shock on. Fires make updrafts
the paraglider rides; walking into flames, or a grass fire's front passing over him, burns Jo
(a quarter heart) and throws him back (the char it leaves is safe). The snowy heights are cold: they hurt without warm clothes, spicy food or
a fire nearby.

Exposed cold produces pale breath before the first damage tick and a hunched,
trembling idle pose. A storm's metal warning sparks on the equipped gear's draw
socket, including a sword carried on Jo's back.

Examples that come out of the rules rather than being written one by one: a Boko club dropped
by a campfire catches and burns away; apples knocked from a burning tree land baked; a barrel
set off by an arrow shot through a campfire; a monster caught in burning grass
burns and lights the grass around it.

`python3 tools/element_input_check.py` drives the full production callback with
ordinary inventory, movement, slot and attack keys: light a wooden torch at the
old man's campfire, carry it out and ignite grass, save mid-burn, reload in a fresh
process, douse it through a rain transition, equip another weapon, then re-equip
and swing the same doused copy. It asserts sustained extinguishing on every tick
after dousing, exact equipment identity and accepted blade contacts. The bounded
course is included in `run_all_checks.sh`; evidence defaults to
`build/element-input-check/`.

`python3 tools/element_input_check.py --continuous --record --output build/round81/elements`
adds one uninterrupted 27-second simulation course: carried ignition, grass
propagation, a production rain transition, alternate equipment and reuse of the
exact doused torch. It retains the complete 15 fps rendered capture, original
frame numbers, [a short frame strip](../build/round81/elements/chain/interaction-strip.jpg)
and [the continuous clip](../build/round81/elements/chain/play.mp4). These generated
images, video, saves and logs stay under ignored `build/`; only the reproducible
capture tool and documentation are committed. Rain must extinguish the torch
and propagated grass before reuse. The separate functional course still tests
the save/reload boundary.

Add `--tells --record --output build/round79/tells` for normal-camera clips of a
natural meadow storm warning and a walk across the snow boundary without warm
clothing. The storm has no scripted input or forced warning/bolt; the snow run
uses movement and camera keys without setting cold or damage state. Both modes
own one render lock per process; never wrap the tool in another `flock`.
