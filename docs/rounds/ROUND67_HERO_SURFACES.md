# Round 67: waking hero surfaces

Baseline: `d46710a`. Evidence and the self-contained comparison page are in
`build/round67/comparison.html`; raw before/after images and isolated arm,
knee and ankle crops are in `build/round67/{before,after}/`.

## Changes and diagnosis

The sharp waking cuffs include intersections with constant-opacity pool and
mist sheets. Disabling those sheets isolates the artifact without changing
the model. The bare lower body is already closed, with matching normals at
all 54 coincident leg groups. Both outfits have matching skin weights at
coincident leg vertices (3,100 groups on the dressed model). Neither baked
model changed.

Pool opacity now fades over 2–55 mm of view-depth separation at skin/cloth
pixels. The existing HDR material marker preserves stone and bed coverage.
Water tint and caustics remain; their contact boundary is softer. Anatomical
shading and intentional leather creases remain. The change is confined to
the pool shader in `interiors.jo`; cave geometry is untouched.

The existing lit/shadow wake corrective now lifts the right humerus surface
with a continuous bind-space field, adding at most 15 mm vertically and
12 mm along negative Z. It tapers through the shoulder and forearm, is zero
at grips/soles, and only runs during the wake. Existing finite-difference
normals follow the displaced surface. Skeleton, contact transforms, triangle
counts and Old Shirt material values are unchanged.

## Evidence and checks

- Matched 1280×720 scale-1 wake frames 330/420/520, with body/arm/knee/ankle
  crops and full frames.
- Production idle/run in both outfits, plus close-up idle/run/climb using
  `load_humanoid_anims`, frozen at `t=0.34`. The viewer uses Old Shirt variant
  2 and the production bare-body scale. All ten non-wake comparisons are
  pixel-identical before/after.
- The production cliff-camera capture was occluded; it remains a diagnostic,
  not acceptance evidence. The close-up production clips expose the knee,
  ankle and boot transitions. `contact_check` separately passes gameplay
  grounded contacts and mantle hand drift; its climb state disables ground
  contacts, so the close-up clip is the visual climb check.
- `hero_model_check`: PASS, including new closed bare-leg topology, shared
  normal and seam-weight checks. A deliberately split unit normal fails the
  negative control. Baseline model comparison reports zero vertex change.
- `hero_surface_check`: PASS on the GPU; maximum adjacent contact-alpha step
  **0.022105**, versus **1.0** for the former edge. Skin/cloth agree and stone
  coverage is exact.
- `wake_contact_check`: PASS for both outfits; exact grip/sole mask, maximum
  total surface correction **0.03465 m** (existing limit 0.045 m), maximum
  joint/contact drift **0.0000003 m**, wrist drift at most **0.000019 m**.
- `opening_test`: PASS. `opening_check.sh`: PASS for the continuous opening
  and all five production title approaches. Its executable matches the
  final capture executable byte-for-byte.
- `weather_silhouette_check`: **12/12** at its existing 10% floor, but the
  requested 12% margin is **not met**: canopy rain measures **10.1325%**.
  See `build/round67/results.json` and `weather_silhouette_check.log`.
  The report writes the evidence, then exits unsuccessfully for a minimum
  below **12%**; it does not weaken the requested margin.
  Fresh `d46710a` canopy captures (visible/hidden/mask) are pixel-identical
  to this patch, including canopy rain. This shortfall is inherited from
  the merged baseline, rather than introduced by the wake change. The older
  round-66 result of 13.08% predates the merged terrain changes. Forest-floor
  color remains with Sol3's active task; the 12% requirement remains open.
  Baseline evidence: `weather-baseline-canopy/` and
  `weather-baseline-comparison.json` under `build/round67/`.

Diagnostic iterations are retained under `build/round67/iterations/`.
A general normal-facing experiment is absent from the final source. The
original two-sided shading rule is retained.

## Reproduce

From this worktree:

```sh
python3 tools/round67_hero_check.py prepare before
python3 tools/round67_hero_check.py prepare after
python3 tools/round67_hero_check.py batch before
python3 tools/round67_hero_check.py batch after
python3 tools/hero_model_check.py --baseline build/round67/before/assets/models
sloppy/bin/sloppy tools/wake_contact_check.jo
sloppy/bin/sloppy tools/contact_check.jo
sloppy/bin/sloppy tools/opening_test.jo
sloppy/bin/sloppy build tools/hero_surface_check.jo -o build/round67/hero-surface-check
flock /tmp/botw-render.lock build/round67/hero-surface-check
tools/opening_check.sh
python3 tools/weather_silhouette_check.py --output build/round67/weather-silhouette
python3 tools/round67_hero_check.py report
```

Save check output to the corresponding `build/round67/*_check.log` files
(`opening_test.log` for that test) before regenerating the report. The
round-67 capture script, opening script and weather script own their render
locks; do not wrap them in another `flock`. CPU-only checks need no render
lock. No generated build evidence is tracked in Git.
