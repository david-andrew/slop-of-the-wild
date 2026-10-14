# The Legend of Jo: Slop of the Wild

**[Play in the browser](https://david-andrew.github.io/slop-of-the-wild/)** (desktop browser with WebGL 2; about 95 MB to load).

[Play and evaluate](docs/EVALUATE.md): latest complete Sloppy 0.6.0 sweep **170 PASS / 0 FAIL**
([evidence](docs/EVALUATE.md#whole-regression-suite)).
[Compact performance summary](docs/PERFORMANCE.md), [current listening evidence](docs/MUSIC.md),
and [Round 81 targeted findings and evidence](docs/ROUND81_SOL.md).

*The Legend of Jo: Slop of the Wild* is a parody tribute inspired by *Breath of the Wild*'s
Great Plateau, written in [Sloppy](../slop-lang) (formerly Jot), a small compiled language for games. Everything (rendering,
physics, animation, audio mixing, the tools that build the world) is Sloppy, except the piano
sample importer, two small Python scripts that read the original's map data and one that sets
the title card's lettering in a serif
(`tools/title_art.py` and `tools/names_art.py`, Noto Serif; the game's built-in font is a sans).

Player-facing names use parody aliases. Original actor and item IDs stay internal for
map-data and save compatibility.

[Measured source size, build/load times, headless tests, and Sloppy features and limits](docs/SLOPPY_SHOWCASE.md).

## Run

```
tools/play.sh                           # compile/run with the Sloppy 0.6.0 renderer
tools/warm_assets.sh                    # optional: bake world/mesh/audio/texture packs and GPU pipelines
```

`tools/play.sh` launches without a render lock. Agent captures use
`tools/play_locked.sh`, which owns the shared render lock; never wrap it in
another `flock`. Pass a compiled executable as the play script's argument.
Sloppy 0.6.0 uses Vulkan 1.3 by default on supported Linux drivers. Both Linux
launchers select X11/XWayland when `DISPLAY` advertises an X server; Wayland-only
desktops retain runtime platform selection. `SLOPPY_PLATFORM=wayland tools/play.sh`
overrides this choice. The matched two-minute dynamic forest comparison reduced
frames over 25 ms from **26 on native Wayland to 4 on managed X11**, and worst
interval from **80.0 to 29.8 ms**. X11 p99 was still **18.37 ms**; the strict
16.7 ms target remains unmet in that route. The launcher sets `SLOPPY_VSYNC=0`
for mailbox preference with immediate fallback (the tested X11 driver uses
immediate). `SLOPPY_VSYNC=1 tools/play.sh` restores the release's FIFO default;
`SLOPPY_VULKAN=0` selects OpenGL. Presentation measurements are in
[PERFORMANCE.md](docs/PERFORMANCE.md).

Prepared startup timings, warmup attribution, compilation and process totals
are consolidated in [PERFORMANCE.md](docs/PERFORMANCE.md). In-game load includes
first-callback GPU warmup and excludes compilation. The report distinguishes
fresh-copy prepared launches from verified cold local file pages; neither
measurement flushes shared-library or driver caches.

Run `tools/warm_assets.sh` after source changes. It CPU-bakes world grids,
terrain/upload data, water/farland/architecture buffers, collision/roof maps,
audio and the referenced vegetation/title/name RGBA textures into
`assets/prepared/`, then warms the release's default Vulkan pipelines. GLES
program binaries warm on OpenGL launches with `SLOPPY_VULKAN=0`. All nature inputs
must exist in `assets/src/nature/Textures`; preparation fails if a referenced
image is missing. `tools/prepare_assets.sh` performs only the CPU bake.
Version/size/mtime headers reject stale packs and retain generation on launch.
The texture pack adds 123.45 MiB of ignored prepared data.

Exact fresh-copy reproduction:

```sh
python3 tools/startup_copy_check.py --ref HEAD --repeats 6 --binary-repeats 6 --output build/startup-current
```

The check reports compilation, in-game load, first-frame callback CPU,
first-callback/capture milestones and whole process separately. It owns one
render lock per launch; never wrap it. `tools/prepared_assets_check.sh` compares
complete generated/prepared world, collision, audio and texture bytes;
`python3 tools/prepared_frame_check.py` verifies identical opening, overlook,
pond and shrine pixels. [Protocol and current measurements](docs/PERFORMANCE.md).

`sloppy/` is the **unmodified official Sloppy 0.6.0 release** (binary and
standard library), pinned to `7c8d133` in `sloppy/VERSION`. It has no local
compiler or library patches. Rendering adapters, score gain envelopes and
export peak guards belong to the game. See [SLOPPY_NOTES](docs/SLOPPY_NOTES.md)
for the migration and remaining game-owned adapters.

## Browser build

```sh
tools/build_web.sh                         # Linux x86-64; bundled Sloppy, Node 22+, Python 3
python3 -m http.server 8000 --directory build/site
```

Open `http://localhost:8000/`. Click the game to enable audio and mouse capture;
use the **Fullscreen** button to fill the screen. Progress and options persist in
browser storage. A desktop browser with WebGL 2, float color attachments and gzip
`DecompressionStream` is required.

CI runs **`tools/build_web.sh`** and publishes **`build/site/`** with the existing
Pages workflow. The builder uses CPU-only preparation and wasm tracing; it needs
no GPU, browser, npm packages, external asset downloads or sibling checkouts.
The current site is about **95 MB**: `index.html`, five compressed data archives,
and a matching manifest. Its largest archive is below 35 MB.
It is deployed to https://david-andrew.github.io/slop-of-the-wild/ on every push to `main`.

[Browser measurements, pack choices and optional smoke tests](docs/WEB.md).

## Performance

The current [performance summary](docs/PERFORMANCE.md) covers complete-input startup,
callback CPU execution, present-return intervals and the ten-minute rendered session.
At 2133×1200, Wayland mailbox fire return intervals measure **6.77 ms p50 / 8.53 ms p99**;
these are presentation handoff measurements. Delivered-frame/scanout p99 remains unmeasured.
The table records hardware, output sizes and warmup exclusions; linked JSON preserves
all repeats and tail diagnostics. Superseded frame/startup headlines remain in historical evidence.

`SLOPPY_STATS=log` prints game-side real frame-time
p50/p95/p99/worst every 120 frames; `BOTW_FRAME_LOG=1` adds raw interval, CPU wall/thread time and
instance-upload samples. `BOTW_CPU_TRACE_MS=6 BOTW_CPU=1` retains stage traces near an
8 ms callback budget. [`docs/PERFORMANCE_FINDINGS.md`](docs/PERFORMANCE_FINDINGS.md) separates
load/first-use stalls from steady-state presentation and contention hitches.

Large windows start at 80% scene scale and step down to 72% when late frames repeat;
recovery requires sustained headroom. The watercolor pass follows. Trees past 45 m
(25 m and 0 m in the shadow maps) draw their bark as a plain trunk. Vegetation reuses unchanged
instance buffers per pass; the middle and far shadow cascades take turns. The middle vegetation shadow map uses fewer interior leaf cards beyond 25 m, retaining
the crown envelope and full near-caster geometry. Separate depth shaders
resolve leaf coverage before shading, with the same wind/time uniforms for both view passes.
Linux `BOTW_FPS=60` optionally caps the producer before input polling and rendering;
`0` is uncapped. The five-minute Round 67 comparisons retain uncapped Vulkan mailbox
and dynamic scene scale as the default; neither fixed scale nor 60 Hz pacing removes
the periodic acquire stall (see `docs/PERFORMANCE.md`).

Textures, spatial cells, the shrine chime and representative render paths warm during load.

## What it shows about Sloppy

Everything that runs is Sloppy: a forward renderer with a CDLOD heightfield, three
shadow cascades and a watercolor post pass (shaders written as Sloppy functions and translated to
GLSL), GPU skinning of glTF characters baked by a Sloppy tool, capsule physics, an element system, a
sampled piano score and synthesized sound effects through the standard library's software mixer,
and the tools that turn the original's map data into this world. What it found along the way (no
`discard` or `texelFetch` in the shader translator, flat uniform structs, an optimizer bug with
zero-literal arrays written by foreign calls, timer queries as a GLES extension) and what worked
very well (compile speed, `parallel_map`, shared shader code, the headless test hooks) is in
`docs/SLOPPY_NOTES.md`. Tools for measuring it: `BOTW_GPU=1`, `BOTW_CPU=1`, `BOTW_LOADTIME=1`,
`tools/bench.sh`, `tools/feel_test.jo`, `tools/passage_check.sh` (the scripted walk out of the cave reaches its mouth), `tools/element_test.jo` (the element rules: rain then fire, water, powder, food, ice, lightning, cold), `tools/shrine_exit_check.sh` (each shrine: the orb taken, back up at the entrance with the camera outside the hood).

## Controls

| | keyboard + mouse | keyboard only | gamepad |
|---|---|---|---|
| move | WASD | WASD | left stick |
| camera | mouse | arrow keys | right stick |
| walk slowly | Alt | Alt | tilt the stick a little |
| jump / climb jump / open glider | Space | Space | top face button |
| sprint (climb faster, swim dash) | Shift | Shift | bottom face button |
| attack (hold after a swing: charged spin) | left mouse | J | left face button |
| action: open, examine, pick up | E | E | right face button |
| lock on / shield | right mouse (hold) | K | left trigger |
| side hop / backflip | Space while locked on | Space with K held | top button with the left trigger held |
| perfect guard | E behind the raised shield, just as the blow lands | E | right face button |
| shield surf | in the air (or sliding) with the shield raised: Space again | | lock + top button |
| bow (hold to draw, release to shoot) | R | L | right trigger |
| crouch / sneak | Ctrl or C | C | left stick press |
| throw weapon | G | G | right bumper |
| item buttons | 1 2 3 | 1 2 3 | d-pad left / down / right |
| inventory | Tab or I | Tab | start |
| map | M or Esc | M | back |

In the inventory: E equips or eats, 1/2/3 binds the selected item to a button, X drops it; the
bumpers, Q and C (or clicking) change tabs. Map shows the plateau once the tower is raised (with
the shrines found and where you stand; rest the mouse or the right stick's cursor on a place to see
its name; click or press the action button to drop a pin there, again on a pin to lift it).
**Options** sets camera speeds, inverted axes, volumes and **Gamepad: swap jump / sprint**
(the gamepad's top/bottom buttons, including menu back/drop). Select a keyboard action and
press E/Enter or click, then press its new key; an occupied key swaps the two actions.
Movement, keyboard camera, slow walk, drop and map zoom can also be rebound; arrows or
mouse wheel scroll the binding list; a full-height rail and visible row range mark
the remaining Combat and Menus bindings. Escape cancels capture. In menus, arrows, Enter,
Escape, Q/C and Delete remain fixed for navigation, confirm, back, tabs and drop;
**Defaults** restores all bindings and the gamepad swap. Prompts follow the bindings.
Identical equipment copies show matching `1/3`, `2/3`, etc. marks in their cells and details;
equip and item-button bindings retain the selected copy.
Preferences stay in `~/.botw-clone-options`, separately from progress; scripted
`SLOPPY_INPUT` runs use default controls and keep the saved camera settings.
Sticks use one radial dead zone (movement 16%, camera 14%); camera response is quadratic.
Disconnect cancels held pad actions and restores keyboard glyphs; reconnect restores pad glyphs.
`input_check` injects raw axes/buttons to verify these behaviours. A physical pad is still
needed to check device mapping, drift, unplug detection and reconnect timing on each platform.
`tools/journey_check.sh --keyboard` drives all nine continuous journey legs with keyboard
movement and both camera axes through production input, without mouse or pad input.

Frogs and lizards by the water and fireflies at night dart away from a running Jo: sneak up and
press the action button to catch one. After the first shrine, the action or back button skips the
rest of a Sprite Orb ceremony once the orb is yours.

## Save and resume

Interactive play resumes automatically from `~/.botw-clone-save`. Progress saves when story
beats advance, a terminal or chest is used, or a shrine orb is earned; every three minutes on
solid ground outside combat; and when the window closes or F10 quits. Inventory, equipment,
item-button bindings, arrows, maximum hearts/stamina, tower and shrine progress, story gifts,
opened chests, position/facing, time of day and the complete weather transition are kept.
Ordinary defeated encounters remain cleared on reload. They respawn after ten minutes
of simulation with Jo more than 80 m away; reload preserves the remaining timer.
Collected field placements retain stable identities across reload. Placed weapons,
arrow bundles and prepared food never respawn. Apples, mushrooms, peppers, herbs
and acorns regrow after **7200 s of unpaused simulation**, once Jo is more than
80 m away; saving retains the remaining timer, and offline wall time does not count.
Weapon, shield and bow entries retain heat, wetness and burning through equipment
changes, drops, pickups and save/reload. Night-only skeletons retain their nightly
lifecycle. Storm intensity, gust, wind and lightning restore with their derived
sky and lighting before the first frame. Airborne/cutscene saves use the
last grounded position. Shrine interiors resume at their exterior lift with earned orbs intact;
unfinished puzzle mechanisms reset. Stamina refills on resume.

Start fresh with `BOTW_NEWGAME=1 sloppy/bin/sloppy game/main.jo`, or choose **Start over** in the
inventory's **Options** tab and activate it twice within four seconds (E/Enter or a click).
Starting over replaces the saved journey. Options remain in their separate file.

Test starts never load or write progress: all `BOTW_*` test/debug switches listed below, plus
`SLOPPY_SCREENSHOT`, `SLOPPY_INPUT`, or `SLOPPY_FRAMES`, disable saving, including Start over.
`BOTW_NEWGAME` is the exception: it starts a fresh interactive journey and saves it normally.
The save has a versioned, validated text format and is replaced atomically on Linux.

Interactive callbacks recover real elapsed time with a monotonic clock, bypassing
the window library's 100 ms clamp. The entire production simulation uses steps
of at most **1/120 s**, accounting for up to **0.5 s per callback** (at most 60 steps).
Longer stalls discard time beyond that safety cap without building a backlog.
Inventory, map and options consume wall time while paused; closing them does not
catch up menu time. Fixed-step captures, including screenshots without scripted
input, still advance exactly 1/60 s per frame.
`tools/production_loop_check.sh` tests this actual `main.jo` callback, including the
500 ms elapsed interval, clock/status/save timers, thin cover, single damage,
one interaction pulse and the cap/pause behavior. Smooth/250 ms/500 ms comparisons
also cover all four sword combo contacts, perfect dodge/flurry, perfect and expired
guard windows, arrows and thrown weapons (including thin cover), a Talus fist,
and lightning following a thrown metal target. It owns its render lock.

`sloppy/bin/sloppy tools/save_test.jo` checks file round-tripping, restore, malformed data,
cutscene/shrine resume, autosaves and the window-close hook using fixtures under `build/`.
`tools/encounter_weather_save_check.sh` checks ordinary defeats and respawn timers
across two fresh processes, plus exact restored lighting and the first simulation
frame during storm buildup, settled storm, clearing, lightning and a weather boundary.
`tools/menu_pause_check.sh` checks pause/resume and suppression of world HUD layers
(including pickup banners and prompts) with Inventory, Map and Options open;
it takes the render lock itself.
`tools/save_check.sh` also checks isolation for every current test switch.
`sloppy/bin/sloppy tools/fauna_test.jo` checks footing, wildlife, group-fight separation,
turn-taking, the waiting ring and dropped-weapon pickup.
`sloppy/bin/sloppy tools/camp_alert_check.jo` measures sight, noise and night-noise
reaction time for every placed gathering (all members within one second), plus the
sitter's ground-to-hand pickup and raised alarm poses on the real rig.
`sloppy/bin/sloppy tools/wildlife_path_check.jo` approaches boars and foxes at
30/60/120 Hz, checking obstacle clearance, escape direction and resumed grazing.
`sloppy/bin/sloppy tools/wildlife_observation_check.jo` observes a herd for a minute
and measures planted-hoof drift and slope contact using the drawn leg transforms.
`tools/round85_visual_check.sh` captures uninterrupted one-minute meadow and camp
observations, the live camp alert and storm fauna in `build/round85/`; it owns one
render lock per scene. Night and Talus reference views use
`ROUND57_SCENES='night talus' ROUND57_REGRESSION_VISUALS=0 tools/round57_visual_check.sh build/round85/night-talus`
(which also owns its locks).
`sloppy/bin/sloppy tools/architecture_test.jo` checks the temple portal, tower climb surfaces and the story lookout deck.
`tools/shrine_route_check.sh` solves all four shrines headlessly from fresh interior lift starts:
every puzzle stage, optional chest and its reward, failure/recovery, monk, Sprite Orb and return.
It uses normal movement/combat inputs at 1/60 second with a Sword/Pot Lid entry inventory;
no position, stage or carry presets. It asserts ordered puzzle events and prints PASS/FAIL plus
timing, retaining full trails in `build/shrine-routes/`. Append shrine IDs to select routes.
See [the complete routes](docs/SHRINES.md#complete-scripted-routes) for coverage and timing.
For rendered checks, `tools/shrine_exit_check.sh` locks each shrine render itself; use
`flock /tmp/botw-render.lock tools/passage_check.sh` to serialize its render.
`tools/weather_transition_check.sh` (it takes the lock itself) plays one storm through at the
game's own pace: clear, the storm coming in while Jo stands in the open, Jo running under the
cabin's porch, the sky clearing. It checks that sky, rain and light never jump, that he soaks in
the open and dries under the roof, and that the rendered frames darken and lighten; images in
`build/weather-check/`.

## Test switches (environment variables)

`BOTW_SKIP=1` start outside, `BOTW_TITLE=1` start just before the title-card overlook,
`BOTW_AT="x,z,yaw"` start somewhere (the original's coordinates), `BOTW_HOUR=h`,
`BOTW_WEATHER=clear|cloudy|rain|storm` (with `BOTW_BOLT=frame` a storm strikes lightning on that frame, to see one in a still; `BOTW_BOLT_AT="x,z"` puts that strike there, e.g. into Hopper Pond from `BOTW_AT="-1190,1665,-0.9"` with `BOTW_BOLT_AT="-1201.7,1655.7"`), `BOTW_WEATHER_SEQ="200:storm,1900:clear"` (the weather turns on those frames and arrives at its own pace; `BOTW_WEATHER_LOG=1` prints sky, rain, light and wetness every ten frames), `BOTW_CAPTURE_DIR=dir BOTW_CAPTURE_EVERY=n` (with a screenshot, saves every n-th frame), `BOTW_TOWER=1` (the tower already risen),
`BOTW_CAM="x,y,z,yaw,pitch"` free camera, `BOTW_PAINT=0` watercolor off.
`BOTW_FIRE=1` sets the grass ahead alight with the wind blowing it toward Jo (the front reaches him in a few seconds), `BOTW_TENTFIRE=n` a camp's tent (n = 5: the camp by the
old man's hill, `BOTW_AT="-955,1964,0"`), `BOTW_RISE=1` starts the tower's rise, `BOTW_PASSAGE=1` starts in the passage out of the Shrine of Reheating (hold w), `BOTW_ENTER=n` (with `BOTW_TOWER=1`) rides shrine n's lift down.
Sloppy's own: `SLOPPY_SCREENSHOT=out.png SLOPPY_FRAMES=n` (render frame n and exit),
`SLOPPY_INPUT="10:w+,40:w-"` (scripted keys; with a screenshot the world steps a fixed 1/60 s a frame,
so a scripted run plays out the same however busy the machine), `SLOPPY_FRAME_STATS=1`.
`BOTW_LOADTIME=1` prints how long each part of the load takes; `BOTW_CPU=1` breaks down any frame over 12 ms of CPU. `BOTW_GPU=1` prints the GPU time of each part of the frame (shadows, terrain, trees, grass, water,
post...) every two seconds; under vsync the pass that ends the frame takes in the wait for the screen,
so time the passes with `BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11` too (frames uncapped; the Wayland
compositor paces frames itself). `BOTW_CAMDBG=1` prints the player's state and the camera every ten frames.
`BOTW_CONTACTS=1` prints planted-foot drift, lowest sole clearance, and toe separation every 120 frames.
`sloppy/bin/sloppy tools/contact_check.jo` checks these on a collider course and a slope, including stops, turns, jumps, and disabled contact states.
CPU averages include total frame work and `hero_animate`, even when animation is below the ten largest parts.

## Layout

```
game/        the game (main.jo is the entry)
tools/       world building (heightmap.jo, bake_nature.jo, bake_models.jo), the movement
             similarity test (feel_test.jo), clip ground speeds (stride_check.jo), the score
             rendered to WAV per mood with its statistics (music_render.jo), the model
             viewer, the title lettering (title_art.py), the original's data extractors
assets/      actors.tsv (placements), height.f32 / water.f32 / edge.f32 / area.u8 (generated),
             models/ and nature/ (baked), audio/ (imported piano),
             src/ (downloaded source assets, not in git)
docs/        MOVEMENT_REFERENCE.md, PLATEAU_LAYOUT.md, CHARACTERS.md, ELEMENTS.md, SHRINES.md, MUSIC.md,
             PERFORMANCE.md, SLOPPY_NOTES.md, mapref/ (map data)
```

Rebuild the generated world data: `python3 tools/extract_actors.py && python3 tools/extract_areas.py
&& sloppy/bin/sloppy tools/heightmap.jo && sloppy/bin/sloppy tools/bake_nature.jo && sloppy/bin/sloppy tools/bake_models.jo`.

## Audio credits

The piano recordings are from the [University of Iowa Musical Instrument Samples](https://theremin.music.uiowa.edu/MISpiano.html),
created by Lawrence Fritts: Steinway & Sons model B, performed by Evan Mazunik and recorded by
Michael Cash in 2001. The library permits downloads and use in any project without restrictions.
The game uses attack-aligned, filtered, normalized mono excerpts of the pp, mf and ff recordings;
the melodies and sequencer remain authored in Sloppy. Source URLs, hashes and adaptations are in
`assets/audio/piano-import.json` and `assets/audio/LICENSE.txt`; rebuilding is described in
[docs/MUSIC.md](docs/MUSIC.md).

Footsteps and combat foley use compact adaptations of Kenney's
[Impact Sounds](https://kenney.nl/assets/impact-sounds) and
[RPG Audio](https://kenney.nl/assets/rpg-audio), by Kenney / Kenney Vleugels, under
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). They are layered with original
synthesis; creature voices, water droplets and grass brush remain synthesized. The included
pack licences, archive/source/output hashes and processing settings are in `assets/audio/`
(`kenney-*-LICENSE.txt`, `foley-import.json`). Rebuild with
`python3 assets/audio/import_foley.py --download`; listening exports and measurements are
described in [docs/MUSIC.md](docs/MUSIC.md).

## Combat framing regression

`tools/combat_visual_check.sh` owns one render lock per scene; do not wrap it.
`tools/run_all_checks.sh --only camp_sword_visual_check` covers the placed camp at
`BOTW_SKIP=1 BOTW_AT="-1439,1606,0"`, with a Wanderer's Sword and shield. Its inputs
are `1:k+,1:w+,150:j+,151:j-,165:j+,166:j-,195:j+,196:j-,200:w-,225:j+,226:j-,255:j+,256:j-`:
attack during the approach and keep moving into reach. The check requires actual
enemy HP loss and impact pause. The old 170/185-frame opening stopped movement at
180, fell short of the posed bodies and lost its follow-up to the enemy's attack.
`tools/round57_visual_check.sh` likewise releases the lock between renders.

The offline framing check skins every body triangle over four 960-frame fights, a tent-fire crowd, and the exact README camp sequence (including frame 300):
five enemies on flat ground, three on a walkable terrain slope, one inside the
Temple's ruin doorway, and three beside a collidable forest tree. Each uses attacks,
lateral movement, lock/unlock and camera pans; the doorway uses shorter moves
inside its narrow lane. It measures
screen coverage, perspective-correct foreground overlap with Jo, and a separating
plane between the posed body meshes, followed by exact triangle separation where
the conservative envelopes overlap. Each fight must land real sword damage. Equipment has
separate masks, and selected windup visibility includes other bodies and equipment.
Posed hero/enemy head centres must stay at least 40 px apart at 1280×720.
Every visible enemy pair must also have at least one posed head-width of horizontal
separation, regardless of vertical distance, to exclude two-headed totems. Both the
hero/enemy and enemy/enemy capsules must remain separate. After one second of
lock acquisition, Jo and the selected foe's heads must stay in the middle third.
The additional three-foe course converges beside tent 5 at `-955,1964,0`, with
no player input, including the critic's frame 230.
The contact checks test weapon reach separately. It does not subtract terrain occlusion
or the existing character dissolve, so the screen measurement is conservative.
The offline C helper rasterizes body masks and measures triangle distances;
gameplay and rendering remain Sloppy.

```sh
python3 -m venv build/framing-venv
build/framing-venv/bin/pip install numpy
build/framing-venv/bin/python tools/combat_framing_check.py --output build/combat-framing
```

The check compiles its measurement helper under the output directory and takes one
render lock per scene itself. `--scene flat|slope|doorway|tree|tentfire` selects one case;
the default runs all five; `--frames 720` retains the shorter historical course. `--game PATH --baseline` measures a baseline without enforcing
the new thresholds; `--analyze-only` rechecks a retained pose trace without rendering.
Round 77 before/after captures, per-frame metrics and regression logs are under
`build/round77/`.

`sloppy/bin/sloppy tools/combat_reach_check.jo` checks that short blades, branches,
claymores and spears still connect through their drawn sockets on flat ground and a slope.
