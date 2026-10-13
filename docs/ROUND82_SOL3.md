# Round 82 — Sol3

Base: `d05ace6`, after merging `master` into `sol3/work`.
Evidence lives in `build/round82/`; generated packs and captures remain ignored.

Jaba Badge's room-A north and east collision gaps now contain named fracture
meshes. North spans `(-2..2, 0..4, -21..-20)` and east spans
`(10..11, 0..3.5, -12..-8)`, matching the base-centred physics boxes.
The existing blast hooks hide exactly those names when they disable collision.
The continuous rendered throw/blast/walk checks reach local north z=-25.707 and
east x=12.770, with Jo still grounded.

`shrine_obstruction_check` is a separate entry in `cpu_checks`. Its wrapper
refreshes the packs and starts two independent processes: generated assets and
a required prepared-cache hit. Both inspect 617 fixed shrine colliders plus
all three Crack meshes, crates, gates, bridges, shutters, rotating bars/tips,
barrels, both pillar orientations, and the rolling boulder's hit radius.
Moving bodies expose their actual submitted vertex/index buffers only while
the test capture flag is enabled. Fixed puzzle solids require matching bounds;
profiled roof backing requires a matching visible soffit and horizontal reach.
The check also verifies blue slate floor vertices and blast hide/disable hooks.
A deliberately emptied north-wall mesh is rejected by the negative fixture.

The canyon retains its collision surface and LODs, with selected ribs changed
to angular projection/recess planes, sharper shelf returns, more faceted light,
and a few larger seated fragments. The final near mesh has 21,980 triangles,
below the existing 22,000 limit. The water crest bows across its width, edges
wander with descending strands, small pale drops replace smoky side puffs,
and upstream ripples/highlights move toward the fall. Gameplay water grids
retain their existing levels. Passage debris forms unequal one-sided clusters
with long gaps and occasional small chips across the route. All four shrine
floors share blue slate; fixture light, brass details and soot retain accents.

Targeted validation passed:

- `tools/prepare_assets.sh` and `tools/prepared_assets_check.sh`: full generated/
  prepared mesh, collision, roof, ownership, draw-order, texture and audio parity.
- `tools/run_all_checks.sh --only shrine_obstruction_check`: 1 PASS, 0 FAIL.
- All four `tools/shrine_route_check.sh` routes, including both Jaba Badge gaps.
- `tools/shrine_wall_visual_check.sh`: both real barrel throws, blasts and walks.
- `tools/journey_check.sh`: 67,380 controller frames, 4,865.54 m, all nine legs.
- Landscape, passage mesh (476 probes), cliff mesh (541 front rays), and five
  production cliff climbing routes.
- `tools/passage_check.sh`: 4.9 m from the cave mouth after 760 frames.
- `tools/opening_check.sh`: every wake/door/passage/title/control checkpoint and
  the six title continuity cases.
- Shrine paint, lighting, circuits, arrival framing, and water/FX contact checks.

Review artifacts:

- `before/`: matching baseline camera views at 1280×720.
- `refined/`: accepted canyon, pool and crest/upper-river captures.
- `after/`: shrine palette/doorway and passage comparisons; initial water study.
- `doorways/{north,east}/`: approach, blast and walk frames plus full camera logs.
- `motion-refined/`: continuous fixed-camera water motion frames;
  `water-motion-analysis.txt` measures water-only pixel changes between frames
  300 and 320 (12.95/255 at the waterfall, 0.98/255 upstream).
- `opening-evidence/`, `shrine-route-evidence/`, controller trace and check logs.

The initial four-fragment shelf study exceeded the geometry budget and was
reduced; earlier water candidates in `after/` and `final/` were superseded.
All game renders acquire `/tmp/botw-render.lock` once. The wall visual script
owns its locks and must not be wrapped in another `flock`.

The baseline east approach already contains a dark panel masking the lower
part of that doorway; it remains in the captures. The new fractures are visible
above it, and the blast and grounded alcove walk verify the complete gap.
`refined/east-detail.png` retains this separate visual issue for follow-up.
