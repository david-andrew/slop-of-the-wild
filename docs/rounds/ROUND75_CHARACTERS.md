# Round 75: character values and small bird silhouettes

Baseline: `3a99aaa` on `astra/work`, including the merged `82bf1da` wake pose.
Matched 1280×720 captures, native-pixel pairs, rejected trials and check logs
are in `build/round75/`. No capture changes the production actor placement,
AI, camera distance or scene scale.

Bokoblin backs now use a continuous dark wash instead of the procedural
vertex-color speckles. Red skin and the blue texture also compress the imported
mottling, retaining the lighter front/muzzle, dark ears, eyes, teeth and mouth.
The camp views at frames 120 and 300 show the clearest improvement: broad back
planes replace isolated blotches. Combat keeps the expressive face marks.

The hero's boot, bracer and belt hardware receives a value-only adjustment,
masked by source mesh UVs and low texture saturation. Leather retains its hue
and saturation. The mask includes mid-gray source texels that become pale in
sunlight, as well as the brightest texels. The first two masks were rejected:
`rejected-trim-soft/` was too subtle, and `rejected-trim-threshold/` still left
bright bands between the darkened highlights. The final combat-300 pair shows
quiet gray hardware against the existing warm leather.

The Old Shirt and Warm Doublet waist paint blends across a wider vertical
region. The Old Shirt hem sits slightly closer to the upper shirt's value, and
coincident cloth/belt/trouser normals are softened. This reduces the abrupt
shading transitions without changing the waist silhouette or adding geometry.
The old man's texture is unchanged; the shared ranger mesh receives the same
normal smoothing. The bare hero is byte-identical to the baseline.

Crow, pigeon and sparrow flight wings have a broader, bowed outline with a
continuous hand-feather edge. Shallower up/down poses retain more visible wing
area at gameplay distance. The combat sky pair makes this particularly clear.
A darker hawk tint was rejected because the overlook pair did not show a clear
improvement at native size; that trial is in `rejected-hawk-tint/`. The imported
hawks remain a follow-up opportunity. Wing animation timing, fauna behavior, actor scale, draw
batches and triangle counts are unchanged.

The camp's sitter already turns independently between frames 120 and 300.
Existing per-actor animation phase offsets and speeds separate resting guards
and waiting combatants. No extra pose change was warranted at normal size.
`enemy_weapon_pose.jo`, weapon-carry logic and attack contact timing are unchanged.

Reproduce the matched captures with `python3 tools/round75_character_check.py
prepare before`, then `capture before`; repeat for `after`. Optional view names
select a smaller set. The helper takes one render lock per game process; do not
wrap it in another `flock`. The evidence run also used short before/after pairs
under one lock, returning the lock between cameras. `boars` is the requested
camera at frame 150; `birds720` checks the later fauna at the same camera.
`crow-spot` also repeats the exact camera without `BOTW_SKIP`. These boar-view
samples have no clearly visible flying crows in either revision, so they are
regression evidence, not the basis for accepting the wing change. The naturally
flying combat crows provide that comparison. `title` is the actual overlook at
frame 600. Full-frame pairs and identical
cropped rectangles retain native pixels without enlarging the actors.

Checks: hero and Bokoblin model contracts against the baseline; procedural
wildlife mesh normals, indices, bounds and budgets; the complete CPU fauna
suite; camp roles; weather shading; wildlife voices; hero footing and mantle
contacts. Model positions, UVs, indices, rig data, influences, texture dimensions
and alpha remain exact. Hero: 29,306 vertices / 30,630 triangles. Bokoblin:
4,913 vertices / 7,764 triangles. Every procedural bird pose retains its prior
triangle count, including 330 triangles for a flying crow. No new runtime
parts, texture samples or draw calls are introduced.

All twelve final clear/cloudy/rain/storm silhouette cases pass across the meadow,
canopy and Hopper Pond. Minimum linear-luminance silhouette contrast is
**0.177**, and minimum paired separation is **0.273**, both above the **0.12**
floor. Results and visible/hidden/mask captures are in
`build/round75/weather-silhouette/`; the final check log is `weather-final.log`.
