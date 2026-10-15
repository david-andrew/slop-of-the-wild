# Tower-base capture regression

The failure on `1728e20` is a stale capture assertion, not a tower visibility
regression. The original check fails at frame 407 on scene alpha **-16** at
pixel `(978, 536)` (OpenGL bottom-up coordinates). Architecture's partially
cleared pigment marker is **-8**. Vegetation's **-16** marker also covers distant
leafy-tree LOD transitions at 55–70 m, added in `ebb7e83` to remove canopy grids.
A background tree near the right edge of the capture envelope triggers the old
blanket ban on negative alpha.

At that frame Jo is unobstructed. A diagnostic using the production skinned
hero vertex shader measured **58,076 / 58,076** body pixels passing production
scene depth, with no negative-alpha scene pixel within three pixels of his
silhouette. The matched production screenshot confirms his head, torso, arms
and legs remain visible. The failing marker comes from the vegetation coverage
resolve, rather than the sunken-crown corridor or masonry clearance shader.

The capture now accepts only the vegetation coverage marker in addition to
nonnegative responses. It still rejects structural **-8** pigment and unknown
negative responses over the original full-body one-metre screen envelope on
every frame of the complete base circuit. Its output counts vegetation coverage
pixels separately. No game or asset inputs changed, and the masonry fade keeps
its soft edge rather than acquiring a hard cutaway.

All four validation commands passed:

- `tools/run_all_checks.sh --only tower_base_climb_capture`
- `tools/run_all_checks.sh --only tower_base_climb_check`
- `tools/run_all_checks.sh --only climb_occluder_check`
- `tools/run_all_checks.sh --only task69_tower_check`

The rendered circuit checked **463,085,165 HDR pixels** with zero structural
occluder markers, recording **600,313 vegetation coverage pixels** separately.
Its log and final screenshot are in `build/all-checks/run-oTtVqX0z/`. The other
logs are in `run-72jogILr` (controller), `run-R2c1vrUn` (shader fixture), and
`run-euyMznLa` (sunken tower) under `build/all-checks/`.

The shader fixture in `climb_occluder_check` also requires both retained and
removed pixels at the masonry clearance edge, along with fully cleared supports
and retained held stone/shadows.

The additional silhouette diagnostic was stopped after frame 960 once the
first-failure comparison was established; the standard capture checks the
complete 2,600-frame route.

Diagnostic evidence is in `build/tower-base-fix/`: `investigate.log`,
`first-failure.png`, `mask-investigate.log` and `first-masked-failure.png`.
