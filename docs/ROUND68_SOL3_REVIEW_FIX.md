# Round 68 sol3 visual-review corrections

This follow-up corrects the independent rejection of `60e8d89`. The complete
critic pack passes, all 45 final shots were personally compared beside master,
13 targeted checks pass, prepared-data byte equivalence passes, and all seven
CPU p99 budgets pass in the consistent source-path comparison. The passage
rings/stripes removal and darkness, radial waterfall mist/broken foam, and
continuous terrain-seated husk limbs remain.

The short fir-cluster experiment is reverted byte-for-byte to master `f06ffaf`'s
`game/fir_boughs.jo`, as the reviewer allowed. The global shrub albedo floor is
removed. The forest, both storm frames, night, snow, firs, tent-fire and camp
180/640 final captures are RGB-identical to master; the boar shrub also retains
its master hue. This restores the fir-shadow contribution at the broadleaf left
edge, without another global pigment change.

The Temple lawn marks were three actual meadow-scatter instances: `Bush_Common`
at `(-789.13416, 219.60077, 1952.4242)` and `Bush_Common_Flowers` at
`(-787.9929, 218.34602, 1948.4215)` and `(-788.37933, 217.98676, 1947.0315)`.
Brightening them still made teal balls. They now use open `Fern_1` frond geometry
at their unchanged roots, rotation, height and leaf tint. Placement RNG and the
surrounding shrubs are preserved. The new CPU check inspects those real roots
and heights and the ordinary forest shrub population.

A matched capture with `BOTW_PAINT=0` still showed the stair bands. Flat
riser/top lighting, rather than mortar texture, caused the barcode. The same 23
steps now have closed bevelled noses and smooth normals, retaining the original
walking collision dimensions. In the fixed raw crop `(540,480)-(675,620)`, mean
absolute adjacent-row Rec.709 luminance contrast is 17.26 on master, 17.46 on
the rejected branch and 2.69 on the bevelled steps. This diagnostic crop differs
from the reviewer's crop.

Husks render in the opaque pass. Lifted patina together with inward-wound legacy
collars exposed nested armor and cone interiors, producing the ghostly appearance.
Master patina/light floors are restored. Husk-only tube cap normals are corrected,
then actual husk triangle winding is checked against outward normals. Continuous
seated sleeves remain. The surface regression audits every nondegenerate actual
husk face, including collars and caps. The final bird and Temple crops show solid,
darker husks without the washed-out interior overlay.

The receiving pool's rotated, warped flowing noise breaks aligned foam cells
into unequal rafts. The approved radial mist and broken foam remain.

Final evidence is in ignored `build/round68-sol3-revision/`:

- `implementation-report.json`: changes, source hashes, checks, timing protocols
  and every initial and controlled timing result.
- `full-pack-pairs/` and `visual-review.json`: all 45 master/final comparisons,
  640x360 per image, with recorded findings for every shot.
- `temple-unpainted.png`, lawn/stair/husk crops, `lawn-probe.log`,
  `stair-contrast.json` and `restored-pixel-checks.json`: cause isolation and
  targeted visual verification.
- `prepare-assets-final.log`, `prepared-assets-final-check.log` and individual
  targeted-check logs: final bake/equivalence and CPU regressions.

The complete final pack is `build/round68-sol3-repaired-final-pack/`, including
captures, startup, 120-second production pacing, audio and its checks. Captured
game source hashes match the committed game tree. Existing camp occluder
checkerboarding and comet-like grass-fire particles remain unchanged.

Primary CPU evidence is `build/round68-sol3/performance-common-path/`. Both
revisions were rebuilt at identical entry/module paths. Each scene retains three
AB/BA alternating pairs of 720 fixed production frames, 240 warmup frames and
480 steady samples per run, with the main thread on core 2. Nearest-rank pooled
p99 uses every sample, with the existing 3% + 0.10 ms budget. Before/after CPU
p99 in milliseconds: passage 4.717/4.725, pool 6.307/6.167, Temple 6.461/6.557,
husks 6.193/6.060, snow 8.047/8.387, firs 7.218/5.392 and camp 9.455/8.534.
All pass; snow is close to the tolerance boundary.

Earlier different-path snapshot runs failed some master budgets. Those raw
samples, extended five-pair sets, production-affinity control and stage profiles
remain in the report and `build/round68-sol3/performance-repaired-v2/`. Separate
pre-revision controls against `60e8d89` pass for passage (5.071/4.649) and snow
(9.425/8.623). The consistent-path comparison is the primary assessment; these
experiments do not establish the precise cause of the earlier timing variation.
The frozen common-source manifests and binaries are retained. A Temple crop
from the controlled binaries confirms master still renders its original stairs
and final renders the bevelled steps, despite sharing build paths.

`critic_pack.py --capture-batch-scenes N` optionally selects one to eight scenes
per short batch (default four). The existing 60-second release condition and
90-second child timeout remain. Resuming the final pack with eight scenes
retained all byte-verified captures and reduced repeated shared-lock queue waits.
The convenience `--only captures OUT` argument order is also checked with the
new option. No game changes were made during these timing/tooling controls.
