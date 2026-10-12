# Characters: models, animation, skinned rendering

The hero, Bonkoblins, animals and birds are skinned meshes baked offline from glTF into compact
binary files, animated on the CPU (clip sampling, blending, layering) and skinned on the GPU
(bone matrices in a float texture, read in the vertex shader).

| file | what |
|---|---|
| `game/gltf.jo` | glTF 2.0 reader (.glb / .gltf + .bin) with a small JSON parser. Offline only. |
| `game/skel.jo` | run time: `.mdl` / `.anim` loading, clip sampling, blending, layers, `Animator`, skinning, bone transforms, sockets, props, drawing |
| `game/hero_motion.jo` | hero contact anchors, two-bone leg IK, boot/sole alignment and braking support |
| `game/charshade.jo` | the character shader (lit + depth-only), `CharScene`, `CharParams` |
| `tools/bake_models.jo` | the baker: `assets/src/**` -> `assets/models/*` |
| `tools/model_viewer.jo` | viewer / test bench (keys and env options at the top of the file) |
| `assets/models/` | baked output (about 75 MB in this checkout, mostly raw RGBA textures) |

Rebake everything (about 4 s): `sloppy/bin/sloppy tools/bake_models.jo`. You can also bake a subset:
`... bake_models.jo anim hero bokoblin animals birds`.

## Conventions

* World and model space are y-up, in meters. **Every model faces +z** in model space and stands
  on y = 0 at its origin. To face a direction, use `translation(pos) * rotation_y(yaw)`; yaw 0
  faces +z.
* Sizes (rest pose, set at bake time): hero 1.66 m (top of the hood), Bonkoblin 1.42 m (drawn at 1.14x in game), fox 0.62 m,
  wolf 0.95 m, deer 1.45 m, stag 2.1 m (antlers), horse 2.0 m (ears), bull 1.6 m, fish 0.3–0.35 m
  long, eagle 2.0 m wingspan, seagull 1.25 m. The game's boar uses its own procedural
  mesh and motion in `game/wildlife.jo`; the bull remains a separate skinned viewer asset.
* Colors: textures and material colors are baked as display colors raised to the power 1.45
  (`ALBEDO_GAMMA`). The game lights albedos in the terrain's range (grass is 0.3 0.5 0.14 under
  a sun of about 2.9), and this keeps characters in the same value range. Use the same range for
  prop colors.

## Using it in the game

```jot
use 'gfx.jo'
use 'shade.jo'
use 'charshade.jo'
use 'skel.jo'

hero = load_model("assets/models/hero.mdl")          # 0.05 s
human = load_anims("assets/models/humanoid.anim")
boko = load_model("assets/models/bokoblin.mdl")       # same library as the hero
fox = load_model("assets/models/fox.mdl")
fox_anims = load_anims("assets/models/fox.anim")      # each animal has its own library
upper = bone_mask(human, "spine_01")                  # upper-body layer mask

hero_anim = Animator()

update = (dt: f64):
    anim_play(hero_anim, clip_index(human, (if speed > 4.0: "run" else: "walk")), 0.2)
    anim_update(hero_anim, dt)
    pose = anim_pose(human, hero_anim)
    if attacking:                                     # legs keep running, arms swing
        layer_into(pose, sample_clip(human, clip_index(human, "slash1"), attack_t, false), upper, 1.0)
    rotate_bone(human, pose, lib_bone(human, "spine_02"), v3(0, 0, 1), lean)   # lean into turns
    hero_skin = skin(hero, pose)                      # skin every frame you draw

draw = ():
    ...
    scene = char_scene(vp, cam_pos, env.light_dir, env.sun_color, env.sky_amb, env.ground_amb, env.haze,
        env.density, 0.004, cascades.vps[0], cascades.vps[1], cascades.vps[2],
        shadow_tex(0), shadow_tex(1), shadow_tex(2), elapsed())
    hero_world = translation(hero_pos) * rotation_y(hero_yaw)
    loop k in [0..3):
        shadow_begin(k)
        terrain_draw(su)
        draw_character_shadow(hero, hero_world, hero_skin, cascades.vps[k])
        shadow_end()
    bind_target(post_begin())
    ...
    gl_opaque_state()
    terrain_draw(tu)
    draw_character(hero, hero_world, hero_skin, scene)
    draw_prop(sword, socket_world(hero, hero_world, hero_skin, SOCKET_HAND_R), scene)
    draw_character(boko, boko_world, boko_skin, scene, CharParams(variant = 1))   # blue
    draw_sky(...)
```

`char_scene` takes the same values that `TerrU` gets. `draw_character` draws into whatever
target is bound (the HDR scene target), with depth testing on. It outputs linear HDR color and
leaves face culling enabled, as `gl_opaque_state` does.

## API (game/skel.jo)

### Loading
* `load_model(path) -> Model`: GPU meshes and textures. `m.ok` is false if the file is missing
  or stale (the error goes to stderr). The fields you will use: `bones`, `bmin`/`bmax`,
  `variants`, `parts`, `skeleton`.
* `load_anims(path) -> AnimLib`
* `clip_index(lib, name) -> int` accepts a clip name or an alias and returns -1 if unknown.
  Related: `clip_duration(lib, ci)`, `lib.clips[ci].looping` (a hint), `lib_bone(lib, name)`.
* `bone_index(model, name)` (case-insensitive fallback), `part_index(model, name)`,
  `model_height(model)`.

### Poses
A `Pose` has one entry per library bone:
* `r: vec4[]` is the local rotation.
* `t: vec3[]` is the translation offset from the rest pose.
* `s: vec3[]` is the scale factor.

Functions:
* `rest_pose(lib)`
* `sample_clip(lib, ci, t, looping) -> Pose`, or `sample_into(lib, ci, t, looping, mut pose)`
  to avoid allocating. Looping wraps; otherwise the clip holds its last frame.
* `blend_pose(a, b, w) -> Pose` / `blend_into(mut a, b, w)` crossfade (w = 0 gives a, w = 1 gives b).
* `bone_mask(lib, "spine_01") -> f32[]` is 1 for that bone's subtree. Feed it to
  `layer_pose(base, top, mask, w)` / `layer_into(mut base, top, mask, w)` to get legs from
  locomotion and the upper body from an attack, shield or bow clip.
* `add_pose(mut base, add, ref, w, mask = [])` is additive: it adds `add - ref` on top of base.
* `rotate_bone(lib, mut pose, bone, axis_model, angle)` rotates a bone (and everything below it)
  about a model-space axis. Use it for leaning, aiming the head or bow arm, and recoil.
* `pose_rot(lib, pose, bone)` gives a bone's model-space rotation.

### Animator (clip player with crossfades)
* `Animator()`
* `anim_play(mut a, ci, fade = 0.2, looping = true, restart = false, speed = 1.0)`: playing the
  clip that is already running does nothing unless `restart` is set.
* `anim_update(mut a, dt)`
* `anim_pose(lib, a) -> Pose`
* `anim_phase(lib, a)` gives 0..1 through the clip. `anim_finished(lib, a)` is true when a
  one-shot has ended.

### Skinning, bones, drawing
* `skin(model, pose) -> Skin` computes the model-space bone transforms (`sk.world`) and the
  skinning matrices, and puts them in this frame's GPU palette. Call it every frame you draw the
  character; a stale `Skin` still draws, but it is uploaded again.
* Related: `skin_cpu(model, pose)` (no GL calls) and `skin_rest(model)`.
* `bone_world(model, skin, bone_or_name) -> mat4` is model space; multiply by the character's
  world matrix to get world space. `bone_world(model, pose, bone)` walks the chain without a
  `Skin`.
* `draw_character(model, world, skin, scene, CharParams(...))`. `CharParams` fields:
  * `variant`: the texture set.
  * `tint`: multiplies the base color.
  * `rim`: rim light strength.
  * `fill`: self-light strength.
  * `flash`: `vec4(rgb, amount)` for a hit flash or freeze tint.
  * `dissolve`: 0..1, a dithered fade-out for death puffs and despawns.
  * `glow`: emissive mask strength (eyes).
  * `hide`: a bitmask of parts not to draw, for example `1 << part_index(boko, "club")`.
* `draw_character_shadow(model, world, skin, shadow_vp, params)`: call it between
  `shadow_begin(k)` and `shadow_end()`. `dissolve` and `hide` apply here too.

### Sockets and props
* `socket_world(model, world, skin, SOCKET_X) -> mat4` returns the world transform at which to
  draw a prop. The sockets are:
  * `SOCKET_HAND_R`: sword, club, spear. The prop's +y comes out of the fist on the thumb side.
  * `SOCKET_HAND_L`: bow, +y up along the bow.
  * `SOCKET_SHIELD`: on the left forearm (`lowerarm_l`); the shield's +z faces out.
  * `SOCKET_BACK`: on `spine_03`, for a sheathed sword or shield.

  To make your own: `Socket("bone", offset_mat4)`.
* Props are modeled with the handle at the origin, the blade or shaft along +y, and the front
  toward +z.
* `prop_boxes([PropBox(center, size, color), ...]) -> Model` builds a one-bone model out of boxes.
  It stands in until real weapon meshes exist; the viewer builds a sword and a shield this way.
* Draw props with `draw_prop(m, world, scene)` and `draw_prop_shadow(m, world, shadow_vp)`.

### Bones to attach to (humanoids: hero and Bonkoblin)
These are UE-style names on the canonical skeleton:

* Spine and head: `root`, `pelvis`, `spine_01..03`, `neck_01`, `Head`.
* Arms: `clavicle_l/r`, `upperarm_l/r`, `lowerarm_l/r`, `hand_l/r`.
* Fingers: `index/middle/ring/pinky/thumb_01..04_l/r`. The Bonkoblin has no pinkies.
* Legs: `thigh_l/r`, `calf_l/r`, `foot_l/r`, `ball_l/r`.

Uses:
* Sword or club: `hand_r`.
* Shield: `lowerarm_l` (or `hand_l` when held up front).
* Bow: `hand_l` (string hand `hand_r`).
* Paraglider: grip between `hand_l` and `hand_r` (the `glide` clip has both arms up), with the
  canopy above `Head`.
* Foot IK: `thigh`, `calf`, `foot`, `ball`.

Each bone frame (on every humanoid, since the models are re-oriented onto the canonical
skeleton) has its origin at the joint and +y along the bone toward the child. The Bonkoblin's
club is part `"club"` of its model, held in `hand_r`.

## How retargeting works

The canonical humanoid skeleton is the Quaternius UAL skeleton, 66 nodes including the
`Armature` parent. The baker re-orients every humanoid model onto it:
* Each bone keeps its own rest position (bone lengths and proportions) but takes the canonical
  bone's rest orientation.
* The mesh is re-bound to those frames (new inverse bind matrices), so it looks unchanged.

A clip's local rotations then apply to the hero and the Bonkoblin directly, with no work at run
time. This is the same as retargeting by world-space rotation deltas: a bone turns in the world
the way the source bone turned from its rest pose. That holds even where the rest poses differ a
lot (the Puglin's head and hunched spine).

Root and pelvis translations are offsets from rest. They are scaled per model by the hip-height
ratio (`Model.tscale`: hero 0.92, Bonkoblin 0.655).

Mesh2Motion clips (the source skeleton names its head `head` and has an extra `head_leaf`) are
retargeted onto the canonical skeleton at bake time with the same formula:
`L_dst = (Gd(parent)^-1 Gs(parent)) * L_src * (Gs(bone)^-1 Gd(bone))`.

Animals keep their own skeletons, and their libraries are made from their own clips. Eagles and
seagulls are re-oriented onto the `bird-animations.glb` skeleton.

## The hero

The hero is the Male_Ranger outfit plus the head, eyes and eyebrows of
`Superhero_Male_FullBody`:
* The head is cut by bone weights: triangles whose vertices have more than 50% of their weight
  on `Head` / `neck_01`.
* Both files use the same skeleton with identical head and neck joints, so the head is joined by
  bone name with no seam. The collar and hood cover the neck.

Bake-time edits:
* Removed the shoulder pauldron and a duplicate belt.
* Recolored to the BotW Hylian palette: the green hood, tunic and sleeves become slate blue. The
  trousers become brown; their texture area is found by rasterizing the `Legs` mesh's UVs.
* Painted blond hair onto the scalp of the head texture. The baker rasterizes the head
  triangles in UV space and tests each pixel's 3D position against a hairline: bangs parted in
  the middle just above the brows, locks in front of the ears.
* Tinted the eyebrows blond. Added a small ponytail mesh bound to `Head`; the hood is
  a separate part so the Old Shirt can hide it.

Textures:
* Outfit/head 1024², hands/brows 512² and eyes 128², plus a small auxiliary texture.
  Four texture variants cover the game's outfits.
* 7 parts (including separately hidden hood and tail), 25.8k vertices, 29.5k triangles.

## The Bonkoblin

The Bonkoblin is the Puglin (55 joints, no pinky fingers), driven by the humanoid clips. It is
scaled to 1.42 m. The emissive map is packed into the texture alpha, so the eyes glow.

| variant | texture |
|---|---|
| 0 | red (Puglin texture 2) |
| 1 | blue (texture 3) |
| 2 | black (the red texture with the reddish skin hues turned dark slate purple) |
| 3 | green (texture 1) |

Good clips for it:
* Attacks: `attack`, `slash1..3`, `heavy`, `ground_pound`.
* Behaviors: `taunt` (Angry), `dizzy`, `hit`, `knockback`, `die` / `die_a..c`, `run`, `sprint`.

## Files

All little-endian; strings are a u32 length followed by bytes.

**`.anim`**:
1. Header: `"JANM"`, version 1, skeleton name.
2. Bones: a count, then per bone the name, parent (i32), rest t (3 f32), rest r (4 f32) and
   rest s (3 f32).
3. The hip height (f32).
4. Clips: a count, then per clip:
   * name, fps (f32), frames (u32), looping (u8), removed root motion (3 f32);
   * per bone, three u32 key counts for rotation, translation and scale. A count of 0 means
     identity or rest, 1 means constant, and anything else means one key per frame.
5. All rotation keys as i16 x 4 (quaternion × 32767, continuous signs), then all translation
   offsets (3 f32 each), then all scale factors (3 f32 each), clip-major then bone-major.
6. Aliases: a count, then per alias the alias name and the clip index (u32).

**`.mdl`**:
1. Header: `"JMDL"`, version 1, name, skeleton (anim library name).
2. Bones: a count, then per bone:
   * name, parent (i32), library bone (i32, -1 = stays at rest);
   * takes pose translation (u8);
   * rest t, r, s, and the inverse bind mat4 (16 f32, column-major).
3. tscale (f32), bounds min and max (3 f32 each).
4. Texture slot count and variant count, then variants × slots textures. Each texture is w and h
   (u32; w = 0 means a 1×1 white texture) followed by raw RGBA8 pixels, with alpha holding the
   emissive mask.
5. Parts: a count, then per part:
   * name, texture slot (u32), two-sided (u8);
   * vertex count, then the vertices: 20 f32 each (pos 3, normal 3, uv 2, color 4, joints 4 as
     floats, weights 4), in the `ChVert` layout;
   * index count, then u32 indices.

**GPU skinning**:
* The palette rotates through three RGBA32F textures, each 384 × 256 texels: up to
  128 bones per model and 256 skinned instances per frame. Consecutive frames write different
  textures to avoid updating the palette still in use by the previous GPU frame.
* Each instance has a row, and each bone takes 3 texels (the rows of world × inverse bind).
* `skin()` writes into a CPU staging copy; drawing flushes rows dirtied since the previous
  flush in one `glTexSubImage2D`. Preparing several skins before drawing batches their upload.
* The vertex shader blends 4 bones with `glsl_fetch` (texelFetch).

## Clips

All clips are resampled to 30 fps. The flag below is the bake-time loop hint; any clip can be
sampled with `looping = true` or `false`.

### humanoid.anim (130 clips, hero and Bonkoblin)

**Aliases**:

| group | aliases |
|---|---|
| idle | `idle`=Idle_Loop, `idle_alt`=Idle_Subtle, `talk`=Idle_Talking_Loop, `sit`=Sitting_Idle_Loop, `sleep`=Sleeping, `cold`=Shivering, `tired`=Kneeling Tired, `hurt_idle`=Idle Hurt, `fight_idle`=Fighting Idle, `nod`=Head Nod, `victory`=Victory, `taunt`=Angry, `dizzy`=Dizzy |
| moving | `walk`=Walk_Loop, `run`=Jog_Fwd_Loop, `sprint`=Sprint_Loop, `walk_back`=Walk_Backwards, `strafe_l`=Strafe_left, `strafe_r`=Strafe_right, `crouch`=Crouch_Idle_Loop, `crouch_walk`=Crouch_Fwd_Loop, `sneak`=Walk_Stealth, `sneak_run`=Run_Stealth, `crawl`=Crawl, `push`=Push_Loop, `carry`=Walk_Carry_Loop |
| air | `jump`=Jump_Start, `fall`=Jump_Loop, `land`=Jump_Land, `land_hard`=Land_Three_Point, `run_jump`=Run Jump, `backflip`=Backflip, `glide`=Glide (arms up: paraglider) |
| traversal | `climb`=Climb Wall, `climb_up`=ClimbUp_1m, `ledge_hang`=Ledge Hang, `ladder`=Climb Ladder, `ladder_idle`=Ladder_Idle, `swim`=Swim_Fwd_Loop, `swim_idle`=Swim_Idle_Loop, `slide_start`/`slide`/`slide_exit`=Slide_* |
| evasion | `roll`=Roll, `dodge_back`/`dodge_left`/`dodge_right`=Dodge_*, `backflip` |
| sword | `sword_idle`=Sword_Idle, `attack`=Sword_Attack, `slash1`/`slash2`/`slash3`=Sword_Regular_A/B/C, `slash1_rec`/`slash2_rec`=Sword_Regular_A/B_Rec, `combo`=Sword_Regular_Combo, `heavy`=Sword_Heavy_Combo, `dash_attack`=Sword_Dash, `air_attack`=Sword_Attack_Air_Vertical, `ground_pound`=Attack_Ground_Pound, `punch`=Punch_Jab |
| shield | `block`=Sword_Block, `shield_idle`=Idle_Shield_Loop, `shield_break`=Idle_Shield_Break, `shield_bash`=Shield_OneShot, `shield_dash`=Shield_Dash, `defend`=Defend |
| bow | `bow_draw`=Bow Pull Back, `bow_hold`=Bow Pull Hold, `bow_release`=Bow Release (also `Bow`: the whole sequence) |
| actions | `throw`=OverhandThrow, `pickup`=PickUp_Table, `interact`=Interact, `open_chest`=Chest_Open, `eat`=Consume, `chop`=TreeChopping_Loop |
| damage | `hit`=Hit_Chest, `hit_head`=Hit_Head, `knockback`=Hit_Knockback, `die`=Death01, `die_a`/`die_b`/`die_c`=Death_A/B/C |

**From UAL 1**:

| clip | length |
|---|---|
| Crouch_Fwd_Loop | 2.00 s, loop |
| Crouch_Idle_Loop | 2.93 s, loop |
| Dance_Loop | 1.00 s, loop |
| Death01 | 2.40 s |
| Driving_Loop | 1.67 s, loop |
| Fixing_Kneeling | 5.20 s |
| Hit_Chest | 0.33 s |
| Hit_Head | 0.43 s |
| Idle_Loop | 2.50 s, loop |
| Idle_Talking_Loop | 2.93 s, loop |
| Idle_Torch_Loop | 1.27 s, loop |
| Interact | 2.00 s |
| Jog_Fwd_Loop | 0.93 s, loop |
| Jump_Land | 1.27 s |
| Jump_Loop | 2.50 s, loop |
| Jump_Start | 1.33 s |
| PickUp_Table | 0.83 s |
| Pistol_Aim_Down, Pistol_Aim_Neutral, Pistol_Aim_Up | 0.17 s each |
| Pistol_Idle_Loop | 1.67 s, loop |
| Pistol_Reload | 1.67 s |
| Pistol_Shoot | 0.63 s |
| Punch_Cross | 1.00 s |
| Punch_Jab | 0.87 s |
| Push_Loop | 2.67 s, loop |
| Roll | 1.47 s |
| Sitting_Enter | 1.30 s |
| Sitting_Exit | 1.03 s |
| Sitting_Idle_Loop | 1.67 s, loop |
| Sitting_Talking_Loop | 2.93 s, loop |
| Spell_Simple_Enter | 0.53 s |
| Spell_Simple_Exit | 0.43 s |
| Spell_Simple_Idle_Loop | 2.10 s, loop |
| Spell_Simple_Shoot | 0.50 s |
| Sprint_Loop | 0.67 s, loop |
| Swim_Fwd_Loop | 1.33 s, loop |
| Swim_Idle_Loop | 3.33 s, loop |
| Sword_Attack | 1.53 s |
| Sword_Idle | 1.67 s, loop |
| Walk_Formal_Loop | 1.33 s, loop |
| Walk_Loop | 1.33 s, loop |

**From UAL 2**:

| clip | length |
|---|---|
| Chest_Open | 1.37 s |
| ClimbUp_1m | 0.67 s |
| Consume | 1.33 s |
| Farm_Harvest | 2.50 s |
| Farm_PlantSeed | 2.77 s |
| Farm_Watering | 3.80 s |
| Hit_Knockback | 0.83 s |
| Idle_FoldArms_Loop | 2.50 s, loop |
| Idle_Lantern_Loop | 2.50 s, loop |
| Idle_No_Loop | 2.50 s, loop |
| Idle_Rail_Call | 2.50 s |
| Idle_Rail_Loop | 2.50 s, loop |
| Idle_Shield_Break | 1.07 s |
| Idle_Shield_Loop | 2.50 s, loop |
| Idle_TalkingPhone_Loop | 2.93 s, loop |
| LayToIdle | 1.53 s |
| Melee_Hook | 0.47 s |
| Melee_Hook_Rec | 0.60 s |
| NinjaJump_Idle_Loop | 2.00 s, loop |
| NinjaJump_Land | 1.27 s |
| NinjaJump_Start | 0.97 s |
| OverhandThrow | 1.33 s |
| Shield_Dash | 1.10 s |
| Shield_OneShot | 0.83 s |
| Slide_Exit | 0.50 s |
| Slide_Loop | 2.00 s, loop |
| Slide_Start | 0.83 s |
| Sword_Block | 1.23 s |
| Sword_Dash | 1.57 s |
| Sword_Heavy_Combo | 4.33 s |
| Sword_Regular_A | 0.43 s |
| Sword_Regular_A_Rec | 0.97 s |
| Sword_Regular_B | 0.53 s |
| Sword_Regular_B_Rec | 1.03 s |
| Sword_Regular_C | 2.00 s |
| Sword_Regular_Combo | 3.00 s |
| TreeChopping_Loop | 0.97 s, loop |
| Walk_Carry_Loop | 2.00 s, loop |
| Yes | 2.50 s |
| Zombie_Idle_Loop | 1.33 s, loop |
| Zombie_Scratch | 1.80 s |
| Zombie_Walk_Fwd_Loop | 1.33 s, loop |

**From Mesh2Motion (addon)**:

| clip | length |
|---|---|
| Angry | 0.83 s |
| Attack_Ground_Pound | 2.70 s |
| Backflip | 2.50 s |
| Bow | 3.77 s |
| Bow Pull Back | 1.27 s |
| Bow Pull Hold | 0.27 s, loop |
| Bow Release | 0.50 s |
| Climb Ladder | 3.63 s, loop |
| Climb Wall | 2.07 s, loop |
| Confused | 2.93 s |
| Crawl | 1.70 s |
| Death_A | 4.50 s |
| Death_B | 1.87 s |
| Death_C | 2.20 s |
| Defend | 0.97 s |
| Dizzy | 2.43 s |
| Dodge_back | 1.00 s |
| Dodge_left | 0.83 s |
| Dodge_right | 0.83 s |
| Fighting Idle | 1.70 s, loop |
| Glide | 0.80 s, loop |
| Greeting | 4.83 s |
| Head Nod | 0.87 s |
| Idle Hurt | 1.67 s, loop |
| Idle_Subtle | 2.57 s, loop |
| Jump_2 | 1.63 s |
| Kneeling Tired | 0.83 s |
| Ladder_Idle | 2.50 s, loop |
| Land_Three_Point | 1.07 s |
| Ledge Hang | 1.90 s, loop |
| Meditate | 1.50 s, loop |
| Pipe Climb | 1.87 s, loop |
| Power Up | 0.77 s |
| Run Jump | 1.27 s |
| Run_Stealth | 0.53 s, loop |
| Shivering | 0.27 s, loop |
| Sleeping | 1.67 s, loop |
| Strafe_left | 1.00 s, loop |
| Strafe_right | 1.00 s, loop |
| Sword_Attack_Air_Vertical | 4.83 s |
| Throw Object | 1.87 s |
| Tired Hunched | 1.03 s, loop |
| Victory | 1.67 s |
| Victory Fist Pump | 2.27 s |
| Walk_Backwards | 1.00 s, loop |
| Walk_Stealth | 1.50 s, loop |

**Root motion**:
* All of these clips play in place: root translation is constant, and pelvis translation keeps
  the body's own motion.
* The baker removes horizontal drift only when the whole body travels (both feet move with the
  hips). None of the source clips do, so `Clip.motion` is zero for every clip.
* Clips that end with the hips displaced while the feet stay put keep that offset, because it is
  part of the pose. These are Death01, Death_A/B, Sitting_Enter/Exit, LayToIdle, Melee_Hook(_Rec),
  NinjaJump_Start and Land_Three_Point.
* Vertical motion is kept: jumps, ClimbUp_1m, Slide_Start, deaths. During ClimbUp_1m the game
  must move the character up by about 1 m × `tscale`.
* Land_Three_Point is trimmed to start just before the hips come within 0.6 m of the ground (the
  source starts 4.4 m up).

### Animals (fox, wolf, deer, stag, horse, bull; one .anim each)

* Fox and wolf clips: Attack, Death, Eating, Gallop, Gallop_Jump, Idle_HitReact_Left/Right,
  Jump_ToIdle, Walk, Idle, Idle_2, Idle_2_HeadLow.
* Deer, stag, horse and bull clips: Attack_Headbutt, Attack_Kick, Death, Eating, Gallop,
  Gallop_Jump, Idle_HitReact_Left/Right, Jump_toIdle, Walk, Idle, Idle_2, Idle_Headlow.
* The source files have each clip twice (`Walk` and `AnimalArmature|Walk`); the duplicates are
  dropped.
* Aliases: `idle`, `idle_alt`, `graze` (head low), `walk`, `run` (Gallop), `jump`
  (Gallop_Jump), `land`, `eat`, `attack` (Attack or Attack_Headbutt), `kick`, `die`, `hit`,
  `hit_r`.

### Birds, fish

* `bird.anim` (eagle, seagull): Flap, Glide, Idle, Walk. Aliases: `fly`, `glide`, `idle`,
  `walk`. The source eagle is maroon and orange; it is remapped to browns (a bald eagle).
* `fish1/2/3.anim`: Swim (alias `swim`).

## Performance

Measured in `tools/model_viewer.jo` (GTX 1070, release build) with
`VIEW_CROWD=16 VIEW_PERF=1`, i.e. 29 characters. Each humanoid samples 3 clips (base, a
locomotion blend and an upper-body layer); each animal samples 2.

| | per frame |
|---|---|
| animation + skinning on the CPU, including the palette staging | 0.92 ms on average, 1.5 ms at most |
| draw submission: 4 passes (3 shadow cascades + lit) | 0.54 ms |

The frame stays at vsync (16.7 ms).

| per character | |
|---|---|
| sample a clip | 1.7 µs |
| blend | 1.1 µs |
| CPU skinning (66 bones) | 6.3 µs |

Load times: the hero takes 0.05 s; all 13 viewer actors and their libraries take 0.14 s.

## Viewer

`sloppy/bin/sloppy tools/model_viewer.jo`

Keys:
* left/right: humanoid clip; up/down: animal clip.
* 1..9: focus a character; F: face close-up.
* B: upper-body layer; space: pause.
* Right drag: orbit; wheel: zoom.

Screenshot env options:
* `VIEW_CLIP`, `VIEW_ANIMAL_CLIP`, `VIEW_FOCUS`, `VIEW_FACE`, `VIEW_BONE=hand_r`
* `VIEW_YAW`, `VIEW_DIST`, `VIEW_T`, `VIEW_HOUR`
* `VIEW_LAYER=slash1`, `VIEW_CROWD=n`, `VIEW_PERF=1`
* `VIEW_DISSOLVE=0.5`, `VIEW_FLASH=1`, `VIEW_NOPROPS=1`

Example:
`SLOPPY_SCREENSHOT=/tmp/x.png SLOPPY_FRAMES=5 VIEW_FOCUS=1 VIEW_FACE=1 sloppy/bin/sloppy tools/model_viewer.jo`

## Known issues and limits

* **Rendering:**
  * No normal maps: the painterly shading doesn't need them, and tangents aren't baked.
  * Two-sided parts flip normals that face away from the viewer (there is no `gl_FrontFacing` in
    the translator).
* **Hero:**
  * Most hair detail is painted on the scalp; a small modeled ponytail supplies the rear
    silhouette. The hood is hidden for the Old Shirt, rather than animated into a lowered pose.
  * The face is the base mesh's adult face; it is not reshaped to look younger.
* **Files:** textures are stored as raw RGBA8. In this checkout `hero.mdl` is about
  43 MB and `bokoblin.mdl` 17 MB (4 variants × 1024²); the hero includes additional outfit
  textures. The viewer load timings above describe the earlier asset set.
* **Bonkoblin:** its ears, jaw and club have no bones of their own; the club follows `hand_r`. The
  Bonkoblin has no pinky bones, so pinky tracks are ignored.
* **Clips:**
  * Mesh2Motion clips are resampled from 24 to 30 fps (linear).
  * To aim the bow (or look) up and down, use `rotate_bone` on `spine_02` / `neck_01` on top of the
    clip.
* **Palette:** limited to 128 bones per model and 256 skinned draws (distinct skins) per frame.
* **Foot IK:** `game/hero_motion.jo` implements two-bone leg solves, world-space planted
  contact anchors, boot/toe alignment and sole clearance for the hero. Contacts release
  when the leg cannot reach, when he turns or crosses his legs, or when movement leaves
  valid ground support. This is hero motion logic; the generic clip player and model viewer
  do not apply it automatically.

## Gameplay-scale hero surface checks

The hero baker keeps the source skeleton, influences, sole/grip positions and part
merging. Crown, outward-facing fringe and curved ponytail share the existing `tail`
draw (hidden for the hooded old man). The final scale is computed before the hair
adornment so grooming cannot rescale the skeleton. Skin edge normals, thinner brows,
blue irises and finger-joint crease shading are baked; no new runtime shader path or
texture slot is needed. Shirt and doublet skirts use their upper cloth palette, with
a slightly flared hem and a fitted belt.

Validate a rebake against prior assets with
`python3 tools/hero_model_check.py --baseline <prior-model-directory>` and
`sloppy/bin/sloppy tools/wake_contact_check.jo`. `tools/opening_check.sh` takes the
render lock itself and includes `opening_test.jo` (zero-time and sub-tick camera
handoffs), the complete fresh-game opening and `title_handoff_check.jo`. Do not wrap
that script in another `flock`. Round 61 comparisons and GPU samples live in
`build/round61/`; the four recipes use ordinary chase, running, greeting and front
free-camera views of the dressed hero.

## Gameplay-scale enemy surfaces

The Bonkoblin baker fixes scale before shaping the belly, ears and muzzle. The
single forward horn and shallow socket-aligned pupils share the existing plain
part. Finger creases and broad pigment variation are vertex colors. The 56-bone
rig, source topology, influences, soles and grips are unchanged: 4,913 vertices,
7,764 triangles across the same three asset parts (the imported club is hidden
in gameplay). Validate against a prior bake with
`python3 tools/enemy_model_check.py --baseline <prior-bokoblin.mdl>`.

Stalkbonks keep their body/skull split and exact Bonkoblin contact rig. A two-texel
texture replaces the plain texel in the same slot: matte ivory at UV (0.25, 0.5),
amber emission at (0.75, 0.5). Only the eyes sample the emissive texel. The tucked
cheek plates, sloping brows and taller horn retain the same 7,864 triangles.
Boars keep all eight mesh parts and the existing articulated leg/neck transforms;
the hump, swept mane and continuous tusks change only the mesh. At close range the
boar still issues fourteen draws. The club retains the same grip and 0.86 m reach,
with fitted bindings and a swollen striking end (+42 triangles, same draw).

Round 62 before/after acceptance captures, source snapshots, mesh budgets, check
logs and paired uncapped GPU measurements live in `build/round62/`; the report is
`build/round62/comparison.html`. Capture and timing scripts acquire
`flock /tmp/botw-render.lock` separately for every game process. Do not wrap these
scripts in another lock. Behavioral checks are `combat_check.jo`,
`contact_check.jo`, `fauna_test.jo` and `integration_test.jo` under `tools/`.
