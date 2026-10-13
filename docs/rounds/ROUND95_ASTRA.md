# Round 95 — Astra: husks, reveal, firs and close-up details

Baseline `500126f`; `astra/work` was fast-forwarded from master before editing.
All renders use `/tmp/botw-render.lock`. Evidence and isolated source/model
snapshots stay in ignored `build/round95/`.

## Accepted changes

- Guardian crowns use plain weathered pigment instead of face-like procedural
  strokes. One smaller recessed lens sits on the front of the tilted crown;
  the former detached back-facing annulus is gone.
- The roof meeting has three shots across twelve seconds. The man turns into
  a translucent blue spirit during seconds 2–4, holds through the close shot,
  awards the paraglider at second 8, and fades during seconds 9–11.5. Control
  returns at second 12. Every prop and its shadow share the fade. Camera rays
  clear the actual spire and parapet. No dialogue or new on-screen text.
- Three narrow, unequal fir sprays replace two broad spearheads. Four rings
  keep the original view-triangle budget; shadow triangles fall by 25%.
  Dark green lower surfaces and upper snow caps remain intact.
- Bare forearms use a narrower anatomical envelope and blended elbow skin
  weights; the wake corrective spreads across the joint with less inflation.
  The installed mesh has 48,959 vertices versus 52,848 before. Skeleton,
  hand/sole surfaces and influences outside the bare arms are exact.
- Wading footfall rings carry a water-only marker. Their centre and eight
  circumference samples must stay above exposed water at the original level.
  Dry grass, a different surface level, and expansion across the bank reject
  the ring. Rain/puddle rings keep their original behavior.
- The castle sky clearing fades whole cloud banks, avoiding curved pieces
  left by cutting an ellipse out of a cloud.

## Review and verification

The noontime storm comparison showed zero changed ground pixels after removing
flat puddle cards. That speculative change was rejected and the cards restored.
A second diagnostic omitted airborne bird shadow casters at the supplied storm
position, default dawn time, across ten frames from 1–10 seconds: every pixel
matched. No isolated floor blotch was reproducible; this finding remains open.
The diagnostic was not applied to production. The visibly speckled spirit trial
was also rejected in favor of actual alpha blending after the sky pass.
The initial denser fir trial was replaced with geometry at the baseline view
budget before acceptance.

CPU checks cover the complete earned-orb story and delayed reward, roof camera
clearance and translucency timing, all five fir meshes, real water/shore rejection,
and 75 tree/log assertions. The continuous opening passed all thirteen captures
from wake through returned control, plus the six title camera handoff routes.
After the final arm refinement, dense wake captures and the wake-contact/opening
CPU checks passed again. The weather silhouette matrix passed all twelve views;
its lowest contrast was 0.130 against the required 0.120. The reveal check also
proves enemy damage cannot interrupt Jo while control is held.

Matched views are generated with `tools/round95_visual_check.py`; `--prepare`
freezes the source and model paths. `before --prepare` reads production sources
and hero meshes from `500126f`. Default captures acquire a flock per scene;
`--locked` is only for a batch already wrapped in one outer flock. The same
explicit option is available on `tools/weather_silhouette_check.py`.
