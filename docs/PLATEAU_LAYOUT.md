# Grate Plateau layout (from the original's map data: zeldamods radar/objmap; zeldawiki)
Coordinates are the original's: x east, z south, y up, meters. Raw actor table: assets/actors.tsv
(tools/extract_actors.py), climate areas: assets/area.u8 (tools/extract_areas.py; 46 temperate,
47 snow, 50 shrine exit), heightfield: assets/height.f32 (tools/heightmap.jo).

Barrier before the paraglider: x in [-1600, -350], z in [1400, 2400]; respawn (-1021.7, 253.3, 1792.6).
Plateau top ~ x -1535..-410, z 1475..2360. Surroundings: north field ~124-130, east ~118-125,
west canyon 70-110 (waterfall drops 186 m), SE Lake Hylia (~60-80), south 175-195.

## Landmarks
| Landmark | x, y, z |
|---|---|
| Restoration room bed | -1133, 237, 1918 |
| Slate pedestal | -1125, 238, 1903 |
| Door 1 | -1119, 237, 1900 |
| Chests (Old Shirt / Trousers) | -1113, 237, 1891 / -1112, 237, 1894 |
| Second room terminal / door 2 | -1096, 235, 1879 / -1097, 235, 1873 |
| Shrine of Reheating mouth (faces NE) | -1068, 248, 1845 |
| Cliff overlook (title card) | -1024, 253, 1799 |
| Old man first meeting | -980, 234, 1870 |
| Campfire (baked apples, torch) | -943, 225, 1880 |
| Woodcutter's axe in stump | -921, 221, 1872 |
| Grate Plateau Tower (rises 103 -> 172; top 246) | -560, 172, 1695 |
| Temple of Thyme (long axis N-S, rot 170 deg) | -818, 221, 2001 |
| Goddess statue | -823, 225, 2031 |
| Temple roof (old man reveal) | -809, 264, 1964 |
| Abbeys: Courage / Power / Wisdom | -837,193,1842 / -803,207,1914 / -746,200,1857 |
| Old grand staircase / fountain | -695,177,1731 / -775,189,1774 |
| Eastern Abbey ruins | -526..-471, 178, 1945..2031 |
| Mount Jolia summit | -1288, 417, 2221 |
| Old man's cabin (pot -804,193,2263) | -784, 193, 2255 |
| River of the Dread (water ~250) | -1228, 1981 |
| River source waterfall | (-1113, 306->249, 2153) |
| West waterfall (river exit) | (-1445, 253->67, 1802..1834) |
| Broken wooden bridge | x -1378, z 1828..1865, y 249 |
| Dock with raft | -1082, 249, 2051 |
| Ruined house with pot | -1041, 251, 1999 |
| Forest of Sprites | x -1350..-850, z 1530..1780, y ~187 |
| Giant hollow log | -984, 184, 1646 |
| Hopper Pond | -1230, 187, 1650 |
| Pond NW of temple | -874, 215, 1936 |
| Snow gate arch | -982, 248, 2017 |
| Broken bridges temple->abbey | -636,183,1898 ; -677,191,1952 |
| Stone towers | -1435,245,1734 ; -1266,172,1564 |

## Shrines (orange glow -> blue when done; monk + sprite orb at the end)
| Shrine | Entrance | Setting |
|---|---|---|
| Ohman Ow | -673, 172, 1513 | NE wetland near the tower; Old Sentinel Scout I; Wanderer's Bow chest |
| Jaba Badge | -447, 179, 1990 | inside the Eastern Abbey walls; 3 decayed old sentinels; Wanderer's Claymore + Amber |
| Owa Dime | -925, 273, 2321 | on an ~80 m rock pillar off the south edge; Wanderer's Shield chest |
| Kay Nomut | -1436, 337, 1991 | snowy western ridge, frozen pond; Old Sentinel Scout I; Wanderer's Spear |

## Enemy camps (red Bonkoblins unless Blue)
| Camp | Centre | Notes |
|---|---|---|
| Skull rock NW | -1437, 194, 1600 | 3 + bow lookout; Fire Arrow chest |
| Hopper Pond | -1213, 188, 1641 | 3 + 2 lookouts |
| Promontory above Hopper Pond | -1280, 290, 1676 | 3 + lookout |
| Ridge above forest | -1147, 257, 1771 | 3 |
| Waterfall stronghold | -1452, 258, 1792 | Blue (Soldier's Broadsword) + 2 spear + lookout |
| Forest north | -975, 190, 1560 | 2 + lookout |
| West of temple | -953, 238, 1954 | 3 |
| North of tower | -563, 173, 1595 | 3 + lookout |
| SW of tower | -741, 172, 1715 | 2 + 2 gloops |
| Tower guards | -617,178,1748 ; -596,173,1702 | 2 bows |
| Skull rock W of abbey | -629, 171, 1918 | Blue + 3; 2 squeese |
| South of abbey | -649, 190, 2190 | 2 |
| West of cabin | -898, 179, 2213 | 3 + lookout |
| Kay Nomut ridge | -1394, 317, 1997 | 3 |
| Snow camps | -1020,287,2166 ; -1043,294,2263 | 3 each |
| Lone blue (snow) | -1074, 327, 2233 | 1 |
| Below Owa Dime | -920, 190, 2343 | 2 |
Others: ice gloops x12 along River of the Dread banks; ice squeese on Hylia/Kay Nomut cliffs;
gloops (-838,208,1812), (-742,186,1756); stalkbonks at night (pairs) on Owa Dime pillar, abbey,
near Ohman Ow; 3 active decayed old sentinels at the abbey (-500,177,1995), (-458,177,1950), (-446,176,2030);
~18 inert old sentinel husks (temple, abbey, NE).

Not spawned, on purpose: the exported actor data also places Lizalfos, Moblins and an Ice
Wizzrobe on the plateau, in three tight groups (by the Eastern Abbey around (-545, 1875); an
"ambush" group south of the Temple around (-780, 2125); Mount Jolia's summit around
(-1230, 2210)), and Lynels, Hinox, Talus and Octoroks below its cliffs. None of these is met on
the original game's Great Plateau, whose roster is the one above; they are placements gated by flags
the extractor does not model (Master Mode actors are already filtered out by
`IsHardModeActor`). Checked against `assets/edge.f32`: 16 Lizalfos, 5 Moblins and 1 Wizzrobe lie
inside the plateau's edge.

The one exception is `Enemy_Golem_Junior` at (-1087.75, 179.14, 1663.18): the Stone Tantrum of the
Forest of Sprites, a real encounter on the base game's plateau (an earlier version of this note
wrongly called it a Pebblit, which is `Golem_Little`). It now spawns as a dormant painted
rock mound on the local terrain at that x/z. Approaching within 8 m triggers a 2.4 s reveal
into a 6.28 m climbable Stone Tantrum (about 7 m including ore, 300 HP). Eleven articulated
rock colliders carry Jo on its back, shoulder deck and fists. Normal climbing drains
stamina; after 4.2 s of attachment, a telegraphed 1.1 s shake costs 200 stamina on the
deck or 120 while climbing. It ejects Jo only when his stamina is exhausted. The pink-purple back/top ore takes full weapon/arrow
damage; body blows chip at most 1 HP. Alternating fists telegraph for 1.1 s, then sweep
their drawn paths for 8 quarter-hearts, with solid cover protection. The slow 0.8 m/s
walk stays within 12 m of home. The tested journey includes its live colliders/AI
and passes at least 70.31 m from home without waking it. Death crumbles the
body and drops two Flint, three Amber and one Opal as collectible inventory materials.
The existing engaged combat tier provides the short drum cue. CPU regressions run in
`tools/talus_test.jo` (also included by fauna/integration); serialized visual evidence:
`flock /tmp/botw-render.lock tools/talus_visual_check.sh`, under `build/talus-visuals/`.

Encounter restore and material-specific blast helpers live in `game/talus.jo`.
The production hooks are integrated in `game/save.jo` and `game/elements.jo`:
normal saves retain encounter phases and remaining loot, and fire, lightning
and bombs use rock-specific responses with cover checks. `tools/talus_save_element_check.sh`
verifies the integrated hooks; the retained patch is historical integration evidence.

## Items
Tree branches outside the shrine: (-1059,1805) (-1053,1803) (-1025,1813) (-1034,1847) (-1012,1892) y 249.
Torches: campfire, stronghold (-1457,1789), forest camp (-896,182,1671), cabin (-799,193,2262).
Woodcutter's axe: stump, cabin (-778,195,2254), river (-1020,252,2044).
Wanderer's bow: forest camp (-901,182,1671), temple chest (-832,222,1963). Soldier's bow: temple roof chest.
Rusty broadsword: (-889,213,1908), (-1134,180,1683). Warm doublet: old man / cabin chest (-786,194,2256).
Apples: south grove (-895,195,2312) x11, campfire (-937,225,1867), NW (-1436,1571), forest.
Spicy peppers: stronghold (-1453,254,1784) x9, snow gate (-975,245,1973..2025) x15.
Jolian shrooms: forest (-1086,180,1661), shrine ridge (-1052,251,1822). Herbs: forest (-1199,188,1709).

## Wildlife
Woodland boars x9 in the forest around (-943,186,1648); bass in temple pond and NE ponds; sparrows,
pigeons, hawks, squirrels, frogs, lizards, crickets, butterflies, beetles, fireflies (Hopper Pond).
No foxes, crows, deer, wolves or horses in the data; the game adds a few foxes in the open country and
crows round the camps and the dead Old Sentinels for life between the set pieces.

## Biomes
Forest of Sprites: deciduous broadleaf (~410 large) with dead trees, logs, stumps, ferns, brown-stone
arches. NE meadows/bog: ponds with reeds and lilies, flowers, juniper/hop bushes, broken pillars along
the old road. Birch woods + apple trees around the cabin. Rocky shrine ridge and river banks with low
cypress and conifers. Snow: Mount Jolia, Kay Nomut, SW of the river: snow conifers, pampas grass.
Ruins: grey ivy-covered Temple-of-Time stone (perimeter walls, temple, abbeys) and brown-stone arches.

## Story beats
1 "Open your eyes" -> wake in the restoration room. 2 take the slate, door opens. 3 chests (shirt,
trousers), terminal opens exit. 4 run out to the overlook: camera sweep + title card. 5 old man at
the campfire. 6 tower rises; shrines appear. 7 old man offers the paraglider for the shrines' treasure.
8 four shrines (sprite orbs). 9 old man: "X" through the shrines -> Temple of Thyme. 10 roof: the old
man (king) gives the paraglider.
