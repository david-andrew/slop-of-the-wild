# Round 68 sol3 third visual-gate follow-up

Baseline: current master `d79d456`, on `sol3/work`. Evidence, frozen sources,
raw logs and rejected visual iterations are under `build/round68-sol3-c/`.

Husk cuffs are now part of the same rounded, tapered sleeve surface. Separate
rib and end-collar meshes are removed. Joint domes and axles scale with the
adjoining 0.40/0.30/0.22 m limb radius and use the shell's pigment. Ankles and
feet sit above their sampled terrain, preserving the distant silhouette.
The bounded centerline retains its protection against terrain spikes. The
assembled husk audit reports 259,965 vertices, down from master's 291,525.
Original random draws and later actor placements are preserved.

A diagnostic capture paints only sleeves red. It confirms that the brown block
at the left of both bird views is a sleeve, and that the dark triangle over it
is foliage. The sleeve now has unequal rounded sections and attached joints.
An isolated stronger-profile probe gave little benefit and was not adopted.

The receiving pool feathers against the visible rock's scene depth, replacing
the coarse bed-distance field and fixed across-flow edge. The contact has small
moving irregularity and restrained neutral foam. The wide green shallow pigment
is removed. The real canyon rock receives a narrow irregular, neutral dark wet
band. The obsolete baked bank field and its field-only audit are removed.

The depth lookup is specialized into a separate shader for 472 local pool
triangles. The ordinary water shader specializes that branch away. The extra
pool batch has a compact vertex buffer and is frustum culled; spray remains in
the later transparent draw. The partition audit verifies complete index coverage,
no duplication, original winding and exclusion of mist triangles. Pool, husk,
bird and bird-flight captures are RGB-identical before/after shader isolation
(`split-target-pixel-comparison.json`).

Final validation passes:

- `prepare_assets.sh` and `prepared_assets_check.sh`: complete prepared/generated
  audio/world/mesh/collision/ownership/RNG/texture byte equivalence and named draw
  order. Logs: `prepare-split-final.log`, `prepared-split-final.log`.
- Eight targeted checks: `round68_sleeve_check`, `round68_lawn_check`,
  `round66_stone_check`, `round67_art_surface_check`, `temple_roof_check`,
  `vegetation_lod_check`, `water_coverage_check`, `waterfall_shape_check`.
  Logs: `checks-split/`. The sleeve audit covers 180 triangles, including
  100 interior faces, outward winding, closed volume, unit normals, bounded
  thickness over a 35 m terrain spike and absence of internal cap teeth.
- Complete critic pack: `split-final-pack/`, status PASS. It includes 45 captures,
  cold/warm/rebuilt-startup checks, 120-second production pacing, 13 audio clips
  and all eight pack regressions. At 2133x1200, present-return p99 is 14.968 ms
  and callback-thread CPU p99 is 7.327 ms.

Final visual review covers all 45 matched shots against both frozen current
master and the original shared master pack, at 640x360 per complete image.
Thirty-eight final shots have exact RGB equivalence to the already personally
reviewed comparisons; all seven remaining shrine/interface comparisons were
personally viewed on the final tree. Relevant final pool/husk/bird captures were
also viewed directly. No new visual artifact was found. `final-visual-review.json`
records every final PNG hash and review basis. All 90 comparisons are in
`pairs-split-current-master/` and `pairs-split-original-master/`. `master-pack/`
is the complete frozen `d79d456` baseline. `handoff/` contains focused comparisons.

The CPU comparison uses frozen sources compiled at a common entry/module path,
fixed critic fixtures, generated assets for both revisions, full 1280x720 X11
Vulkan and three seconds for context retirement before each process. Each run
renders 1,440 frames; every frame 481–1,440 is retained. Five alternating AB/BA
pairs provide 4,800 steady samples per revision/view. Nearest-rank pooled p99
uses the existing 3% plus 0.10 ms tolerance. All raw tails and hashes remain.

| View / affinity | Master p99 ms | Final p99 ms | Budget result |
|---|---:|---:|---|
| Bird / production | 5.017 | 5.418 | Miss |
| Bird flight / production | 5.676 | 4.856 | Pass |
| Pool / production | 5.978 | 4.213 | Pass |
| Temple / production | 4.926 | 4.871 | Pass |
| Husks / production | 5.107 | 5.541 | Miss |
| Bird / main thread on core 2 | 5.747 | 4.349 | Pass |
| Husks / main thread on core 2 | 4.754 | 4.817 | Pass |

Normal-affinity logs are in `performance-split/`; both budget misses remain in
its summary, whose overall assertion deliberately fails. Controls use the same
five-pair protocol and binaries, pin the main thread after the first frame and
retain production GPU-worker affinity. They are in `performance-split-core2/`
and `performance-split-husks-core2/`. A diagnostic normal-affinity bird pair with
stage tracing improves at 3.853/3.657 ms; neither revision has a steady-frame
stage trace above 4.5 ms (`trace/`). Controls are not substituted into the normal
summary. Remaining limitation: the two production-affinity budget misses persist;
controlled checks pass, so a repeatable CPU regression was not established.

Retained diagnostics include the rejected fixed-width pool mask (`v3/`, dark
scallops), unisolated depth-shader timing (`performance/`, bird 4.043/4.929 ms),
and its incomplete pinned diagnostic (`performance-core2/`). The superseded
`final-pack/` captured 45 views but correctly rejected a changed source hash
after shader isolation; it is not the final pack. An early prepared-assets
check likewise failed when source changed during preparation. Final checks were
run independently on frozen final sources.

The final capture job resumed from 21 completed captures while its coordinator
was blocked on the shared lock without a child. Supported eight-scene batches
retain the tool's 60-second lock cap; no active render was interrupted.
`batch-resume-audit.json` records this. `implementation-report.json` ties together
final source hashes, captures/review, check logs, CPU results and limitations.
