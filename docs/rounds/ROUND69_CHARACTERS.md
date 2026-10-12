# Round 69: foreground characters

Baseline: `645907d`. Started from `fe93d1c`, then fast-forwarded the updated
master before final validation; retained its storm fill/rim changes.
Evidence: `build/round69/comparison.html`, with full-resolution pairs and logs
under `build/round69/`. No changes to the main loop, inventory, saves, shrines,
storm/rain FX, map, vegetation or farland. The contact-shadow receiver in
`fx.jo` is the one effect change.

## Changes

- Replace twenty equally spaced hair locks with nine asymmetric, wider,
  overlapping masses. Curved cross-sections have smooth normals, restrained
  value differences and staggered, swept ends. Scalp paint uses broad washes
  instead of high-frequency streaks. Ponytail and crown share the existing draw.
- Weld and diffuse bare-body normals through the torso, shoulder girdle and
  limbs. Locally relax the elbow/knee surface by at most 1.895 mm in the final
  model, preserving vertex order, skin weights and topology. This baked surface
  and its normals deform in ordinary run, attack and climb as well as the wake.
  The broad back shaping also removes the imported superhero scapular ridge,
  with at most 33.04 mm of local depth change. Existing deltoid volume limits
  and the wake contact corrective remain intact. Finished-surface area normals
  are rebuilt after shaping and welded across UV borders, then diffused through
  the surrounding skin. This removes the imported normal ridges carried through
  the previous analytic deformation. The cap retains slightly more thickness
  while remaining within the existing radius/upper-arc bounds.
- Broaden the hero skin's sunlight and point-light terminators and add a small
  skin-only shadow floor. Calibrate the skin mask to the actual baked albedo
  range. Cloth, bone and enemies retain their painted diffuse bands.
- Restrict the existing contact-shadow cards to ground receivers using the
  copied opaque scene's material marker. The indoor card was cutting a dark cuff
  through the ankle and seated arm; it must not blend over skin or cloth. This
  reuses the bound scene texture and existing instanced draw, with one colour
  read only for contact cards.
- Compress red Bokoblin pigment into a deeper, less saturated red. Vertex
  pigment adds a darker back, lighter belly, low-contrast mottling and darker
  snout/ear recesses. Shape the existing brow and cheek vertices; preserve the
  blunt snout, raised ears and narrow jaw. Bone horn/teeth and brown loincloth
  retain their separate material values. Stable per-enemy value variation and
  a stronger close-range sky rim help separate overlapping combatants.

## Geometry contract

Both hero meshes lose 2,112 vertices / 704 triangles from hair only. The hero
has 29,690 vertices / 30,758 triangles in seven parts; the bare hero has 30,166
vertices / 50,174 triangles in four parts. Bokoblin remains 4,913 vertices /
7,764 triangles in three parts. No texture slots, texture resolution, draw
passes, bones or contact geometry are added. Rig transforms, hands, soles and
Bokoblin influences remain unchanged. Hero influences remain unchanged, too.

The bake is reproducible with:

```
sloppy/bin/sloppy tools/bake_models.jo hero bokoblin
```

## Validation and reproduction

`hero_model_check` compares against the frozen baseline assets and checks
closed bare-leg topology, welded normals/weights, deltoid limits and contacts.
`enemy_model_check` also checks the historical pre-round-62 rig/topology/contact
contract. `wake_contact_check`, `combat_check`, `contact_check` and the complete
`opening_check.sh` are logged alongside the captures. Opening passes all twelve
checkpoints, followed by five complete/interrupted title-camera approaches.

`round69_character_check.py prepare before|after` builds the evidence fixtures;
`capture before|after wake chase combat camp wake330 run` renders the requested
production cameras. `poses-batch before|after` renders frozen production idle, run,
attack and climb clips for both outfits. Those close-ups use the production
bare-body scale and Old Shirt variant. Ordinary run/combat evidence additionally
uses the real gameplay update and contact solve. All captures are 1280×720 at
scene scale 1, with matching time/camera inputs saved next to each image.

`round69_gpu_check.py prepare` builds frozen production wake/combat scenes.
`run` measures three alternating before/after pairs at both 1280×720 and
2133×1200, scene scale 1, discarding samples before frame 480. Acceptance is
median total GPU time no greater than baseline × 1.03 + 0.1 ms. Baseline renders
load the baseline model files, not the modified assets. Frozen updates replay
the production hero contact-card list each frame, so the new contact receiver
is included in the measured scene rather than disappearing after the freeze.

`weather_silhouette_check.py --binary build/round69/weather-final-game --output
build/round69/weather-final` measures twelve matched visible/hidden/mask triples.
`round69_character_report.py` also enforces the **12%** floor on both the
silhouette contrast and paired separation, and requires every check and GPU
pair to pass before emitting the final report. The updated master already
sets the stock weather test's threshold to 12%; it remains unchanged.

GPU drivers release the lock between view suites and record model/binary hashes.
`run-batch` holds one lock for all four view/size suites; it is used for the
final measurements. `run-highres` can resume both high-resolution views after the
720p pairs finish. All render drivers own `/tmp/botw-render.lock`; do not wrap them
in another flock. Standalone model-viewer renders inside the driver acquire
one lock. `opening_check.sh` and the stock weather suite already self-lock.

## Recorded results

- Hero model, enemy model, wake contact, complete opening, combat and contact
  checks: **PASS** on the final assets.
- Weather silhouettes: **12/12**, minimum **17.06244%** (canopy/rain), including
  the stricter 12% acceptance floor. All paired-separation measurements pass.
- Before/after evidence includes all four requested cameras, the earlier wake
  angle, a production run and eight close-up outfit/pose combinations per side.

## Wake diagnostics

`after/diagnostic-no-pool.png` disables the entire `pool_draw` pass at frame 420.
The ankle band remains. It also survives constant albedo, disabled cascade
shadow reception and disabled watercolor postprocessing. The frame-420
normal-debug image initially appeared to show a normal seam because the contact
card still composited dark colour over that debug output.

The cause is the separate `PInst` kind-9 contact-shadow card in `fx.jo`: its
indoor elevation crosses the ankle during the wake. The new receiver mask
excludes figure markers from that card while retaining the ground shadow.
Closed-leg topology, matching seam normals/weights and a CPU triangle
intersection check of the posed ankles rule out an open or intersecting mesh.
Diagnostic images/sources and the CPU inspection are under `diagnosis/` and
`after/diagnostic-*`.

The updated-master static pose baseline reuses captures only after verifying
byte-identical model, skeleton, shader, clip and viewer dependencies. Final bare
pose captures are rerendered with the finished normals and shoulder shaping.
The `chars.jo` edit is confined to `monsters_draw`, outside the hero equipment
block reserved for Sol's sheath work.

Final frozen-scene GPU medians (three alternating pairs, 357 measured frames
per run, with the hero contact cards retained):

| View / output | Before (ms) | After (ms) | Result |
| --- | ---: | ---: | --- |
| 1280x720-wake | 2.979 | 2.943 | PASS |
| 1280x720-combat | 6.392 | 6.322 | PASS |
| 2133x1200-wake | 6.985 | 6.963 | PASS |
| 2133x1200-combat | 12.897 | 12.484 | PASS |
