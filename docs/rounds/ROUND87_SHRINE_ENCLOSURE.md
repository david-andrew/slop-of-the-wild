# Round 87 — readable shrine ceilings and lift wells

Baseline: master `ead9c13`, fast-forwarded on `astra/work`. Production changes
are confined to `game/shrines.jo`.

The large black bands in round86 were actual lift-well surfaces painted almost
black, rather than absent room roofs. The wells now have visible stone courses,
rails on all four sides, an exterior face, and a dim blue cap with a recessed
luminous rim. Bounded cool bounce describes their depth without competing with
the orange puzzle controls. The 16 m cap and the open roof aperture remain.
Vaults receive quiet reflected light and shallow transverse stone bands.

The wider enclosure audit also found structural gaps beyond the lift well:

- Oman’s vertical ceiling steps faced away from the room and were culled.
  Their winding and normals now face into the room.
- Whole skipped connecting walls left gaps above and beside passages when the
  neighboring room was lower or narrower. Oman’s second hall, Ja Baij’s second
  and monk halls, and Keh’s monk hall now have complete walls around the same
  4 m openings. Doorway reveals have solid undersides.
- Ja Baij’s original flat roof collision let a maximum-downward-pitch chase
  camera rise above the sloping visible ceiling near the sidewalls. Narrow
  collision strips now follow every profiled soffit, including annex roofs.
  Camera pitch limits and the round86 field of view are unchanged.
- Raised-camera review exposed open shoulders at Oman's wider pit ends. The
  expanded downward audit also found Owa's unlined lower side chamber and an
  opening beneath Keh's raised treasury. Stone retaining faces, a complete
  abyss floor in Owa's annex, and a full-height treasury fascia close them.

## Validation

`tools/shrine_enclosure_check.jo` checks production geometry with back-face
culling: 18,480 rays over the whole sphere at 48 bearings and eleven elevations from
35 lift, raised-camera, control, hall, stair, annex and monk positions. All hit a real shell.
It also checks visible cap pigment, restrained emission and local bounce, then
settles the production chase camera in 1,440 combinations of position, yaw and
pitch. All remain below the visible ceiling. The baseline fails both the
geometry audit and the cap-material assertion; the separate baseline camera
sweep found 65 above-ceiling views.

The existing checks pass: arrival (12,576 containment assertions at
30/60/120 Hz), sightline (19), shaft (36 culled rays), lighting (25 plus hook
cache reuse), round86 idle framing and next-stage hierarchy, discovery (32/32),
and ceremony (4,063). All four end-to-end routes pass, including failure
recovery, main and bonus chests, puzzles, monk/orb and exterior return:

| Shrine | Frames | Simulated seconds |
| --- | ---: | ---: |
| Oman Au | 8,041 | 134.02 |
| Ja Baij | 8,239 | 137.32 |
| Owa Daim | 10,746 | 179.10 |
| Keh Namut | 8,992 | 149.87 |

## Visual acceptance

The final review contains **208 matched before/after views**, with no missing
captures and no rejected views. All twenty recorded before/after pans complete
at least 360°. Manual review covers each shrine's arrival, first puzzle,
upward shaft view, normal and raised full turns, lift handoff, plus Ja Baij's
low eaves at both pitch extremes. The original round86 framing is included.

Largest near-black connected region in the upper third (pixels):

| Original defect | Before | After |
| --- | ---: | ---: |
| Oman Au first puzzle | 39,575 | 527 |
| Ja Baij first puzzle | 24,321 | 127 |
| Keh Namut first puzzle | 6,396 | 8 |

All four upward shaft views have zero near-black pixels in the upper third.
Owa's original first-puzzle view was already enclosed and remains clear.
The conduits and doors retain their visual priority. The initial raised Oman
capture was rejected for a remaining pit-shoulder gap and corrected with real
stone end faces; the acceptance threshold was not relaxed. One interrupted
Ja Baij capture opened the map and failed the full-turn check; it was rejected
and recaptured. Rejected evidence remains under `build/round87/rejected/`.

Full-resolution images, contact sheets, hashes, test logs and an interactive
comparison are in `build/round87/{before,after,sheets,image-report.json,checks,compare.html}`.

## Reproduce the visual review

Evidence and scratch files live under ignored `build/round87/`; no generated
files are force-added. The two capture scripts acquire and release
`/tmp/botw-render.lock` separately for each render. Do **not** wrap them in flock.

```sh
sloppy/bin/sloppy build game/main.jo -o build/round87/after-game
python3 tools/round87_shrine_inspector.py game build/round87/after-game-inspect
tools/round86_shrine_visual_check.sh build/round87/after build/round87/after-game
tools/round87_shrine_visual_check.sh build/round87/after build/round87/after-game
ROUND87_VIEWS=descent tools/round87_shrine_visual_check.sh build/round87/after build/round87/after-game
ROUND87_SHRINES=2 ROUND87_VIEWS='down-pan eave-high' tools/round87_shrine_visual_check.sh build/round87/after build/round87/after-game
build/round87/venv/bin/python tools/round87_shrine_report.py build/round87
```

The round87 script captures a production chase-camera 364° horizontal sweep,
a raised-boom sweep looking down, an almost exactly vertical free-camera view,
and optional real lift descent and low-eave sweeps at both pitch extremes.
The capture machine has inverted vertical camera controls. The script reads
that preference to choose the appropriate keys without changing it, and the
evidence logs record the resulting pitch. Pan samples every ten frames
are spaced approximately 23° apart with overlapping fields of view; the headless audit supplies a finer 7.5° grid.
Before and after use the same inputs, frame numbers, resolution, time and weather.
The upward inspector retains the production renderer and runs real shrine
updates: ordinary free-camera mode returns before shrine visibility/lighting.
Its 89.43° elevation avoids a float32 `look_at` singularity at world-coordinate
magnitudes; the separate shaft check casts exactly vertical rays. The baseline
inspector is built from `ead9c13` archived under `build/round87/baseline/game`.

The report requires Pillow, numpy and scipy. It records hashes and near-black
connected regions in the upper third, creates contact sheets for manual review,
verifies a full 360° turn from the recorded camera positions, and rejects a
region of 2,500 pixels or more, or a previously large void that
has not shrunk by at least 80%. Intentional transfer fade frames are excluded;
real descent samples start at frame 180. This image check complements geometry
and manual inspection; it does not treat all dark engravings as missing space.
