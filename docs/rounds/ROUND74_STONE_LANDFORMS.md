# Round 74 — stone and landforms

Baseline `5d1367b`, work on `sol3/work`. Evidence is local under `build/round74/`.

The natural cave lining now groups pigment into broad cool recesses and exposed
stone planes. Its custom material removes the dense oblique crack lattice. Shared
vertex washes, shallower relief and mostly continuous normals keep the mesh's
planes subordinate to the wall's larger form. The wake chamber and temple use the
existing mineral response with less fine tooth. Sky, water, skin and foliage keep
their existing material handling.

Temple courses are 0.48 m tall instead of 1.2 m; interior paving uses 0.8 m instead
of 2.4 m. Thin mortar, unequal course lengths and irregular bond offsets replace
wide, high-contrast grids. The existing ivy, damaged wall geometry and broad
lighting carry the larger masses.

The prominent overview cone is the northern hill around `(-1250,1363)`. A lower
crown, west shoulder, east spur, saddle and oblique drainage cut are baked into
its heightfield. The opening ridge's lower shoulders and the western crown also
receive broad relief. Five distant field bumps become unequal ridges with lateral
shoulders and saddles in the existing farland mesh.

Terrain-dependent scatter changed the tower's loose debris and broke the full
journey. Its sixteen stones now retain the previously walkable layout, independent
of preceding scatter. The old five RNG draws per stone are advanced in a separate
stream, preserving subsequent placement consumption. No startup-loader code was
changed.

The coordinator's additional exterior review exposed a material mismatch: the
brow was a dark, gridded patch on a pale, striped host cliff. The exposed brow and
nearby terrain now share a cool mineral wash, with the interior value retained at
the recessed lip. One shoulder, a central hollow and a lower lip articulate the
existing brow mesh. Local terrain displacement is suppressed beside this authored
cut so its footprint
stays aligned with the seated brow. Vegetation and grass classification, followed
by a floating-point pixel readback, identified the green corner as turf at the
left footing around `(-1057,1842)`. That corner now continues into the jamb's stone,
and its grass footprint is cleared. The seating mask covers the complete outer
shell; it no longer overlays beige paving pigment on vertical stone. No foliage
loader code was changed.

The white passage-floor sliver remained when every daylight shaft was disabled.
CPU ray checks found a continuous floor. The terrain depth cut had stopped above
that floor, exposing a thin sunlit strip of hillside. It now continues below the
ramp, and the final stone tongues extend beyond the cut into uncut ground. Tiny
unlit decorative scree slabs were removed; larger seated stones retain the talus
mass and the passage collision is unchanged.

A diagnostic vegetation-colour render identifies the overview's black specks as
small bushes with a 420 m visibility override. The meadow clutter now has a 150 m
override. CPU ray probes identify the left-edge grey smear as the bare eastern
slope around `(-920,2145)`, not a structure. Distant automatic stone coverage now
uses continuous heightfield normals and omits fine breakup. Authored rock weights
and near stone detail retain their existing handling.

## Visual review

Matched 1280×720 captures: wake frame 420; passage frames 150, 300, 450, 600, 750,
and 830; exterior mouth from the meadow and an oblique cliff view; temple frame
200; overview frame 180; title overlook frame 650.
`*-pair.png` retains twelve native before/after pairs; `review.html` provides a
slider using compact JPEG display copies. The original native PNGs are retained.
Every game process takes its own render lock. CPU bakes and image assembly run
outside it.

Rejected: the first mouth pigment became pale and slab-like; gray mineral values
and quieter arch relief replaced it. An initial crown adjustment did not visibly
change the prominent northern summit. An experimental tower rubble relocation did
not restore traversal and was removed. Rejected captures and diagnostic probes
remain under `build/round74/`. The first exterior integration was also rejected for
becoming too pale and flat; cooler stone and broad mesh relief replace it.

## Validation

- Prepared assets: complete generated/prepared byte equivalence, including collision,
  roof maps and ownership/RNG data.
- Landscape: production and prepared peaks, gorge, volcano and Lanayru checks pass.
- Terrain: 131,072 GPU noise samples pass; controller climbing/falling checks pass.
- Traversal: 1,607 checks pass.
- Journey: 67,380 frames, 1123.00 s, 4865.54 m; zero stuck points and hard falls.
- Passage mesh: 476 sealing/seating and camp-clearance checks pass; 540 focused
  passage/floor-junction ray checks pass.
- Material paint: material isolation and grain-cache interpolation pass.
- Wake contact: support, palm and sole checks pass.
- Final opening: all twelve checkpoints and five camera handoffs pass.
- Final passage replay: 4.9 m from the mouth after 760 frames; pass.

## Frame timing

Fixed 1280×720 X11, scale 1, uncapped. Three fresh 720-frame processes per
build/view; frames 241–720 retained (1440 samples per cell). Nearest-rank pooled
percentiles. GPU medians omit the first two 120-frame batches. Terrain/architecture
packs are disabled for both timing builds so baseline cannot consume after geometry.

The independently queued triplicates retain CPU/presentation spikes:

| View | Frame p99 ms, before → after | GPU batch median ms, before → after |
|---|---:|---:|
| forest | 16.151 → 16.703 | 7.330 → 7.260 |
| overlook | 14.903 → 15.155 | 5.150 → 4.750 |
| temple | 14.502 → 14.940 | 4.890 → 4.990 |
| passage | 15.236 → 15.386 | 3.460 → 3.560 |

Consecutive baseline/final processes share one short render-lock batch per pair.
Order alternates across three pairs per view. No image assembly, browser preview
or source rebuild occurs between pair members:

| View | Frame p99 ms, before → after | GPU batch median ms, before → after |
|---|---:|---:|
| forest | 17.307 → 17.138 | 7.280 → 7.250 |
| overlook | 14.752 → 15.208 | 5.120 → 4.770 |
| temple | 14.727 → 14.629 | 4.860 → 4.950 |
| passage | 15.324 → 15.347 | 3.450 → 3.570 |

Worst-view paired p99 is 17.307 → 17.138 ms. Forest and temple improve; passage is
within 0.023 ms. Overlook rises 0.456 ms despite GPU median falling 0.350 ms; its
CPU/thread tail rises while the measured GPU batch cost falls. The independent forest repeats
range 15.546–18.823 ms on the same immutable final executable. No pacing, resolution,
GPU-queue or frame-cap code was changed. The per-view variation is retained rather
than represented as exact unchanged p99.

All raw logs, metadata and official pooled reports remain in `finish-performance/`
and `paired-finish/`, with `final-timing-summary.json` collecting both series. Earlier
stone candidates, the first forest control and superseded refined-build diagnostics
are also retained. Incomplete superseded runs are kept separately; no completed
final or matched timing run is excluded. Warm shader preparation is separate.

Baseline provenance: a shell launcher was added while the baseline queue was active
to isolate it from after packs. It always executes the unchanged `before-game-bin`
(SHA256 `0bdc4ff011ab186b52007ffaadf35465414913383a51f8c2213c9cefc63f7f28`). The
performance metadata is corrected to this actual binary hash; original launcher
metadata is retained in `baseline-original-metadata/`. No timing samples are removed.
