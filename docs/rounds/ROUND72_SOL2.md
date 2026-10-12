# Round 72 — Sol2: Elements and Shrines

Fast-forwarded sol2/work to master 445d6b8 before editing.

## First-time-player findings and fixes

- **Oman Au:** a crate hides the plate's shallow movement and quiet click. Increased depression and positional click, added an activation chime, and pulse the connected circuit on press/release. A brief “Bridge held · 1/2” acknowledgement makes progress explicit.
- **Ja Baij:** the gallery shutter snapped between positions. Its mesh and collider now travel together over 0.25 seconds, with distinct opening/closing sounds. Main passage/pillar milestones also acknowledge progress.
- **Owa Daim:** matching bar ends and an expiring brake gave weak timing cues. Alignment now brightens matching tips and chimes; arrested bars flicker/click in their last two seconds and click when restarting.
- **Keh Namut:** distant water motion made valve responses ambiguous. Both valve groups add directional water sound; the cistern also rumbles. Ice formation starts with a crack and blue motes, then retains its completion chime. Named water/gate milestones show progress.
- **Brambles/barrel rubble:** a nearby lit torch now teases smoke/embers from dry brambles, respecting rain and cover. Both cleared obstacles produce a resolve chime and rising gold ring at the surviving chest.
- **Cold/storm:** exposed Link exhales frost before damage, hunches and shivers while idle. Warmth protections stop the cues. Metal attraction starts with a metallic crackle before the existing sparks/strike countdown. Overlapping Ice Chuchus could re-freeze Link through immunity; contact effects now respect immunity, and thaw grants a brief escape window while preserving damage.
- **Cooking:** ingredients tumble over the actual pot, which bounces/rocks during the existing jingle. A chase lens trapped far behind the cabin is recovered before cooking. Steam uses that pot's position. Resting ingredients now sit on collision floors rather than becoming buried beneath cabin/camp surfaces; placement identity remains unchanged.
- **Systemic play:** aligned the idle torch mesh/flame with an upright hand socket. Actual exterior falls/drowning also exposed zero-heart movement; cleanup now preserves death and normal respawn, with nonlethal shore recovery retained. New jumps/landings reset the fall peak, preventing lethal damage from an earlier descent.

New cosmetic motes preserve chemistry/weather RNG.

## Verification

Production-loop input fixture and capture sources are retained in ignored `build/round72/`. Only initial BOTW_SKIP/BOTW_AT; movement, climbing, combat, pickup, inventory, terminals and rewards use ordinary Actions. A frame is saved every second. Captures/logs stay in ignored `build/round72/`; captures used the shared flock, while self-locking check scripts owned theirs. The manual session was closed at the coordinator’s request; future capture locking must cover only each scripted render, never an idle session.

Rendered completed routes: Oman Au (19,377 frames), Ja Baij (21,416), Owa Daim (40,027), natural metal/storm warning and strike, unprotected snow, torch/grass/wind, bramble burn and reward, barrel blast/rubble removal and chest (4,951 frames), and cabin Hold → Cook (1,073 frames, with camera recovery). Keh Namut’s exterior production-input approach remained incomplete when the coordinator requested wrap-up. Its full puzzle route passes headless; this is not a completed first-time-player render check.

Green regressions: all four fresh-lift shrine routes (main/optional puzzles, chests, recoveries, orb and exterior); shrine discovery 32/32, lighting, arrival and ceremony; integration 1,316/1,316; element rules 19 and Round 71 checks 16; normal-input element journey 7/7; cooking 67; feedback 16; save round-trip/status/encounter/weather resumes. Weather silhouette captures from the final visual changes pass 12/12 (minimum separation 0.158 against 0.12).
