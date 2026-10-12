# Round 68 — cliff, cloud and camp outcrop corrections

Worktree: `botw-clone-sol3`, branch `sol3/work`. Merged master `0af23bf`
without conflicts in `aee1012`. The merge and implementation commits carry
`Co-Authored-By: GPT-6.1-Sol <noreply@openai.com>`.

Removed Round 67's small-cell cliff plate pigment and independent normal
perturbation. The waterfall faces again keep the continuous mineral wash,
large buttresses and tilted bedding. The waterfall bench foam/spray, grass
variety, seed heads, flowers, muted volcanic foothills and warmer dawn remain.

Clouds have smaller lobes, narrower painted boundaries, lit upper rims and
cool grey-violet bases. Their light is evaluated from the smooth underlying
volume rather than the thresholded silhouette, so the shading avoids hard
contour bands. A feathered reserve follows the title atlas bounds, settles
before lettering appears, stays fixed through both fades, and restores clouds
after the lettering disappears and before the normal camera handoff.

The camp slab was an ordinary procedural cliff outcrop, not far-land or a
terrain skirt. Grid `(7,7)` samples terrain at `(-1455.6678,1541.5619)`;
its centre is `(-1455.4777,218.4097,1543.6865)`, with radii
`(7.4068,17.6023,4.4441)`, material `(0,0.25,0,4)`, chunk `-11988`.
Its clipped crown rose about 8.7 m above the terrain. Reducing its cap from
`.72` to `.32` puts the crown at `224.0424 m`, or `2.1123 m` above terrain.
The rooted face, 960 vertices and existing collider remain. Ordinary cliff
outcrops also receive tilted beds, continuous mineral washes and sparse joints.
The previously obstructed mountain view is visible beyond the camp wall.

`tools/title_panorama_check.jo` now asserts that the sky reserve stays settled
through every visible lettering frame. When `BOTW_TITLE_BACKGROUND` supplies
a matching render with just the atlas overlay suppressed, it also measures
sRGB-decoded linear Rec.709 contrast at every atlas-core pixel with opacity
at least `.98`, requiring a minimum ratio of `3:1`. The measured minimum
in the matched title shot improves from master's `1.4832:1` to `3.7721:1`
across 5,177 opaque atlas pixels. A deliberately white
background correctly fails this assertion.

`tools/camp_outcrop_check.jo` measures the actual generated crown and root,
preventing the oversized slab from returning. Existing cliff mesh/climbing,
water coverage, landscape and complete prepared-asset equivalence checks pass.
Both `prepare_assets.sh` and `prepared_assets_check.sh` ran after the geometry
and material changes.

Evidence is in ignored `build/round68/`: ten matched production views from
master `0af23bf` and this branch, a title-background companion for each,
source/binary hashes, capture settings, check logs, `summary.json`, `report.txt`
and interactive `report.html`. The waterfall has native 1× images, full 200%
enlargements and separate left/right 200% crops. Raw screenshots retain exact
1280×720 pixels and scene scale 1, with the Round 67 cameras, inputs and frames.

Reproduce from this worktree:

```sh
mkdir -p build/round68
python3 tools/round68_art_check.py prepare before
python3 tools/round68_art_check.py prepare after
python3 tools/round68_art_check.py capture before
python3 tools/round68_art_check.py capture after
BOTW_TITLE_BACKGROUND=build/round68/after/title-background.png \
  sloppy/bin/sloppy tools/title_panorama_check.jo \
  > build/round68/title-panorama-check.log 2>&1
sloppy/bin/sloppy tools/camp_outcrop_check.jo \
  > build/round68/camp-outcrop-check.log 2>&1
sloppy/bin/sloppy tools/cliff_mesh_check.jo > build/round68/cliff-mesh-check.log 2>&1
sloppy/bin/sloppy tools/cliff_climb_check.jo > build/round68/cliff-climb-check.log 2>&1
sloppy/bin/sloppy tools/water_coverage_check.jo > build/round68/water-coverage-check.log 2>&1
sloppy/bin/sloppy tools/landscape_check.jo > build/round68/landscape-check.log 2>&1
tools/prepare_assets.sh > build/round68/prepare-assets.log 2>&1
tools/prepared_assets_check.sh > build/round68/prepared-assets-check.log 2>&1
python3 tools/round68_art_check.py negative
python3 tools/round68_art_check.py report
```

Capture mode owns one `flock /tmp/botw-render.lock` per game invocation; never
wrap it in another lock. CPU-only checks and asset preparation do not render.
The report also verifies the white-background negative-control rejection.
Build output is not committed.
