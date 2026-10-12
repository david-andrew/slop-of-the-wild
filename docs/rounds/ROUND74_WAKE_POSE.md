# Round 74: supported wake pose

Baseline: `e4d8e3e`, on `astra/work`. Native 1280×720 before/after frames,
full-size side-by-side pairs, detail crops, source snapshots and check logs are
in `build/round74/`. `comparison.html` switches between all six requested frames.
Each capture sequence owns one render lock; the weather runner releases it
after each individual game process. `opening_check.sh` owns its own lock.

## Retained change

Replace the explicit right-hand temple gesture with a palm resting over the
raised thigh. The elbow bends outward, leaving room between upper arm and ribs.
The hand stays over the thigh while the legs gather, then releases from 3.45 to
4.25 seconds as the pelvis rises over the feet. The shared arm solver accepts
an optional bend direction; other callers retain their existing animated pole.

Blend the three local spine rotations partly toward a relaxed pose during the
push, reducing the abrupt chest/lumbar bend. Preserve the source root/leg clock,
left-palm anchor and lift-off, camera path, idle blend and 5.8-second wake exit.
No meshes, textures, equipment, vegetation or startup code changed.

Visual decision: **keep**. At 330 and 360, the hand rests on the knee instead of
crossing the mouth/face; the near arm has a clear silhouette. At 420, the hand
helps the rise instead of hanging from a sharply raised elbow. The back is
slightly more upright. Frame 300 remains a smooth reach; 480 and 520 retain the
standing recovery. Angular waist geometry is still visible: this improves the
pose, not the underlying mesh topology. The optional gear-trim trial is deferred.

## Validation

- `tools/opening_check.sh`: all 12 continuous-opening checkpoints passed;
  control returns at frame 3932. Five title-camera handoff cases also passed.
- `sloppy/bin/sloppy tools/wake_contact_check.jo`: both hero models passed.
  Left-wrist drift is 0.014 mm, maximum joint step is under 26.8 mm at 60 Hz,
  and minimum free-wrist/head clearance is 446 mm across 1.6–4.4 seconds.
  Fingertip clearance, thigh support, planted-palm orientation, water/lip
  contact, lift-off and the existing bounded surface corrective also pass.
- `sloppy/bin/sloppy tools/contact_check.jo`: passed, including mantle grips.
- `sloppy/bin/sloppy tools/hero_surface_check.jo`: passed.
- Weather silhouette capture/check: all 12 meadow/canopy/pond cases passed;
  minimum contrast 0.174, above the 0.12 floor. Results are in
  `build/round74/silhouette-final.log` and `silhouette/contrast.json`.

The old contact assertion explicitly required the temple gesture. It now tests
face/fingertip clearance and a hand over the raised thigh; the original timing,
left-palm and continuity requirements remain in place. The continuity sweep also
covers the right shoulder/elbow and mid-spine.
