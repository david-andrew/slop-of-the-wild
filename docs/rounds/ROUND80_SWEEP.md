# Round 80: pre-critic art sweep

Baseline `ae2daae`, `astra/work`. Inspected all 28 requested standard captures
at 1280×720, scale 1. Exact settings, the ranked ten-defect list, native
before/after pairs and rejected trials are in `build/round80/`; start with
`sweep.md` or `comparison.html`.

Four accepted corrections:

- Paraglider suspension now terminates at animated palm sockets, with actual
  grips. The banked/lofted canopy retains its own motion. Four rigid baked lines
  become one six-instance cord/grip batch per render pass while gliding.
- Butterflies use thin lobed wings and dark margins instead of inflated
  ellipsoids. Their reduced span and quieter pigment read as insects. Each
  species falls from 596 to 130 triangles; the three existing batches remain.
- Wake lamps have tapered ceramic housings and smaller amber apertures that
  fit the restoration basin's curves.
- Lookouts have open rails, diagonal timber braces, deck planks and lashings.
  Existing deck and shaft colliders are unchanged.

Rejected a moss shader trial: it removed too much forest growth and did not
improve the old-man rock. Vegetation is restored exactly. Remaining assignments
are polygonal moss caps/rock shapes, snow-pine halos, cool noisy shaded grass,
castle malice (Sol2), the west waterfall (Sol3), and the old man's cloak drape.
No changes to terrain, accepted meadow/leather work, combat, weapons, UI,
weather/fire effects or the west waterfall.

Validation also exposed an existing storm-meadow silhouette failure: baseline
contrast was 0.088775 against the 0.12 floor. Adjusted the existing hero-only
storm fill to retain dark wet-cloth separation over open turf and gentle fill
under canopy, with continuous habitat/weather/interior transitions. Clear
weather and interior lighting remain unchanged. Native storm comparisons and
the generated-asset baseline reproduction are retained with the sweep.

Validation passes: all twelve weather silhouettes (minimum 0.176870; storm
meadow 0.088775 → 0.189), the 4,865.54 m production journey, prepared asset
byte equality and four exact prepared/generated frames, continuous opening,
fauna visuals, architecture, wake contacts, wildlife mesh and shrine checks.
Full results are in `build/round80/sweep.md` and its check logs.
The new CPU geometry check covers animated suspension contacts, degenerate
cord axes, thin double-sided butterfly topology and terminal bounds/collision;
it is included in `tools/run_all_checks.sh`.
