# BotW movement reference (target values for the clone)

Sources: game data dumps (leoetlino/botw YAML: Player_Link.gparamlist / aiprog / Player_Move AS,
physics), zeldamods wiki (camera, time), Echocolat/botw-bgparamlist (enemy & weapon stats),
fontanierh/atelier (third-party reimplementation reading the same files), ntngel1/botw-renderer
(docs/research/wiiu-as-frame-ctrl.md: root motion of the Wii U build's clips x their AS rates). Raw files in docs/ref/.

Units: the referenced original builds run at 30 fps; established movement speeds are m/frame
(x30 = m/s), established frame durations /30 = s. These conversions do not establish the
semantics of every field with `Speed`, `Cus`, or `Rate` in its name;
stamina per second, 1 wheel = 1000. Conf: H sourced+clear, M sourced/inferred units, L limited or secondary evidence, G guess.
Confidence is independent of evidence class: `data`, `footage`, `inferred`, `guess`, or
`behavior`. Only `data` and compatible frame-timed `footage` enter reference agreement.
The 2026-10-09 evidence audit and reproduction instructions are below.

## Movement response comparison — 2026-10-11 (critics 91/92)

The harness now measures all six requested response families. **None has an accepted
controlled BotW input/output baseline yet**: the 36 response rows below are **GAP**,
not passes. The retained parameter/clip/footage agreement is **99.8/100 on 25 rows,
25 PASS and 0 FAIL**; behavioral checks are **29/29**. The old 26th row compared physical
180° heading time with an 8-frame reversal animation. That is now an unscored proxy.
The higher aggregate is a changed evidence set/tolerances, not improved fidelity.

Policy for a sourced controlled comparison: **±5% displacement/speed and ±2 BotW
reference frames (2/30 = 0.066667 s) response timing**. Heading response means first
sample within 5°; velocity heading also requires speed >0.05 m/s. Stop means first
sample below 0.05 m/s. A missing reference has no computed allowance. The policy in
a GAP row is the requirement for a future comparison, not evidence that ours passes.
Legacy climb footage durations retain their ±0.134 s annotation uncertainty and do
not meet the controlled two-frame evidence requirement.

### Sources and exactly what they establish

- [Player_Link parameters](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml): MaxSpeedInAir=0.3; TurnEnableDirSub=120; TurnEnableStickSub=30; TurnEnableSpeed=0; LookPosOffsetY=1.5. **Limit:** No ground acceleration/release-braking equation or air steering trajectory; turn thresholds are not response rates.
- [Player_Link action parameters](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml): PlayerParashawlGlide Action_35: GlideSpeedMax=0.02, Lv2GlideSpeedMax=0.35, GlideRotRate=0.2, GlideRotSpeed=20, OverSpeedDec=0.002; EnergyGlide=28. **Limit:** Glide runtime units/consumers unresolved; no defensible forward speed, sink or turn conversion.
- [GameRomCamera action parameters](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/GameRomCamera.aiprog.yml): DefaultNormal CameraChase: radius=5.3; Fovy=0.872665 rad; lngCus=0.1; AtHCusMin/Max=0.6/1.0; atVCusMin/Max=0.4/1.0. **Limit:** Radius and FOV usable; response coefficients have no validated update equation.
- [Player_Move animation state tree](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AS/Player_Move.as.yml): Startup and turn animation selectors/blenders, including InputLimit. **Limit:** Animation blending is not a calibrated input-to-position curve.
- [Switch 1.5.0 PlayerMove decompilation](https://github.com/zeldaret/botw/blob/49c6b5c18344de6555163b3af7044970ad9d7c5e/src/Game/Actor/Player/Action/actionPlayerMove.cpp): Parameter loading; calc_ calls PlayerAction::calc_. Current master web copy still has this stub. **Limit:** No completed normal on-foot movement equation.
- [Switch 1.5.0 PlayerJump decompilation](https://github.com/zeldaret/botw/blob/49c6b5c18344de6555163b3af7044970ad9d7c5e/src/Game/Actor/Player/Action/actionPlayerJump.cpp): Parameter loading/delegation to base calculation. **Limit:** No completed jump air-steering equation.
- [Switch 1.5.0 PlayerParashawlGlideBase decompilation](https://github.com/zeldaret/botw/blob/49c6b5c18344de6555163b3af7044970ad9d7c5e/src/Game/Actor/Player/Action/actionPlayerParashawlGlideBase.cpp): Loads native glide parameters; calc_ calls PlayerAction::calc_. Current master web copy still has this stub. **Limit:** No runtime speed/sink/rotation equation.
- [Switch 1.5.0 CameraChase decompilation](https://github.com/zeldaret/botw/blob/49c6b5c18344de6555163b3af7044970ad9d7c5e/src/Game/Actor/Camera/Action/actionCameraChase.cpp): Constructor/destructor only in pinned file. **Limit:** No follow/lag update equation.
- [Published Wii U v208 root-motion research](https://github.com/ntngel1/botw-renderer/blob/656ceeb6ab2dd0eb0d6fa352cd1a3adddf0ec10b/docs/research/wiiu-as-frame-ctrl.md): 24-frame run loop: 2.963 m at rate 1.5 => 5.556 m/s; sprint 3.703 m at rate 1.75 => 8.10 m/s. Reversal Brake clips: walk 9 frames at rate 0.9; run 8; sprint 18. Wait uses separate 18-frame stop clips and a blend. **Limit:** Clip/research evidence, not a synchronized retail trajectory. Brake duration is not physical heading time; Wait is not an 8-frame release stop.
- [Published BotW TAS input script](https://github.com/MCMi460/BOTW-TAS/blob/b09637c3e9b452f577cbfdfeee845fafe04ddced/any%25/SoR/script1.py): 90 one-frame B-held calls with left stick (-6113,32033), right stick (0,0), then KEY_A and neutral left stick. **Limit:** Input-only; no synchronized world position/velocity trace, frame-rate/start-state linkage or published response measurement.
- [Player_Link bphysics dump](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/Physics/Player_Link.physics.yml): CharacterController shape/capsule data and rigid-body damping; nav_mesh_character_max_acceleration=0.0. **Limit:** Rigid-body/navmesh settings do not establish player-controller acceleration or stick-release braking.
- [ZeldaMods bgparamlist schema](https://zeldamods.org/wiki/Bgparamlist): Parameter field names/types and DEFAULT values; points readers to actor-specific game data. **Limit:** Schema defaults are not Player_Link per-build parameters.
- [McKee et al., Paragliding through Hyrule, 2019-12-06](https://journals.le.ac.uk/index.php/pst/article/download/3330/3017/8787): Vertical-only tower drop, approximately 70 m in around 22 s: approximately 3.2 m/s sink; visually settles in 2-4 frames at 30 fps. **Limit:** Estimate; original video, input trace, build and error bounds absent. No horizontal-speed or forward-input sink/turn measurement. Neutral stick in our trial retains 5.845 m/s horizontal speed and is not the same protocol.
- [Author stopwatch movement-speed study](https://www.reddit.com/r/botw/comments/xlrzrq/): Dry-weather travel comparisons along the road from Dueling Peaks to Proxim Bridge; glide follows the minimap road. **Limit:** No synchronized input/world response or calibrated straight-line speed/sink pair acquired; no numeric response baseline adopted.

Native scalar candidates are retained without converting unexplained `Speed`, `Rate`
or camera `Cus` fields into physical units. Source build limitations remain: the
parameter dump's exact ROM/patch is unverified; the decompilation targets Switch
1.5.0; root-motion research describes Wii U v208. The current public Move/Glide
calculation files still delegate to base stubs. TAS input without synchronized
output cannot supply stop/start or camera timing. Broad web searches also found
TotK movement measurements; those were rejected as another game's data.

### Measured response table

Full-forward flat-ground commands, neutral right stick, 60 Hz production player and
camera updates. The course/reset is the fixture; no speed/state/position is assigned
after initial placement. World-direction inputs are recomputed against the camera
yaw each step. Sources in GAP rows are the closest inspected candidates, **not
numeric references**. Every response metric is exported, including initial `t=0`,
in `measurements.tsv` and its scenario CSV under `build/movement-quantification/after/`.

| Measure | BotW reference and source | Ours | Tolerance if sourced | Verdict |
|---|---|---:|---|---|
| time to 90% run | Not identified; [Move data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.233333 s | ±0.066667 s; no baseline | GAP |
| run release stop time (<0.05 m/s) | Not identified; [Move data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.200000 s | ±0.066667 s; no baseline | GAP |
| run release stop distance | Not identified; [Move data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.547208 m | ±5%; no baseline | GAP |
| 180 run heading response (<5 deg) | Not identified; [Move data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.250000 s | ±0.066667 s; no baseline | GAP |
| glide forward speed (0.5 s warmup) | Not identified; [Glide data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml) | 7.678070 m/s | ±5%; no baseline | GAP |
| glide forward sink rate | Not identified; [Glide data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml) | 2.600012 m/s | ±5%; no baseline | GAP |
| neutral glide horizontal speed | Not identified; [Glide data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml) | 5.844830 m/s | ±5%; no baseline | GAP |
| run startup displacement at 6/60 s | Not identified; [Move data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.119167 m | ±5%; no baseline | GAP |
| run startup displacement at 12/60 s | Not identified; [Move data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.458333 m | ±5%; no baseline | GAP |
| run startup displacement at 30/60 s | Not identified; [Move data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 2.099418 m | ±5%; no baseline | GAP |
| run startup displacement at 60/60 s | Not identified; [Move data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 4.877414 m | ±5%; no baseline | GAP |
| 90 run heading response (<5 deg) | Not identified; [Move/jump data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.183333 s | ±0.066667 s; no baseline | GAP |
| jump 90 steer lateral displacement | Not identified; [Move/jump data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.895928 m | ±5%; no baseline | GAP |
| jump 90 steer forward displacement | Not identified; [Move/jump data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 1.723463 m | ±5%; no baseline | GAP |
| jump 90 steer airtime | Not identified; [Move/jump data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.533333 s | ±0.066667 s; no baseline | GAP |
| steady run look-point lag | Not identified; [Chase data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/GameRomCamera.aiprog.yml) | 0.088288 m | ±5%; no baseline | GAP |
| 90 world turn camera reaches 45 deg | Not identified; [Chase data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/GameRomCamera.aiprog.yml) | 1.350000 s | ±0.066667 s; no baseline | GAP |
| 90 world turn peak yaw rate | Not identified; [Chase data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/GameRomCamera.aiprog.yml) | 46.752940 deg/s | ±5%; no baseline | GAP |
| 90 world turn settles within 5 deg | Not identified; [Chase data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/GameRomCamera.aiprog.yml) | 5.333333 s | ±0.066667 s; no baseline | GAP |
| time to 90% sprint from rest | Not identified; [Move data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.333333 s | ±0.066667 s; no baseline | GAP |
| sprint startup displacement at 6/60 s | Not identified; [Move data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.119167 m | ±5%; no baseline | GAP |
| sprint startup displacement at 12/60 s | Not identified; [Move data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.458333 m | ±5%; no baseline | GAP |
| sprint startup displacement at 30/60 s | Not identified; [Move data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 2.592501 m | ±5%; no baseline | GAP |
| sprint startup displacement at 60/60 s | Not identified; [Move data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 6.642508 m | ±5%; no baseline | GAP |
| sprint release stop time (<0.05 m/s) | Not identified; [Move data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.300000 s | ±0.066667 s; no baseline | GAP |
| sprint release stop distance | Not identified; [Move data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 1.206112 m | ±5%; no baseline | GAP |
| 90 run velocity heading response (<5 deg) | Not identified; [Move/jump data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.183333 s | ±0.066667 s; no baseline | GAP |
| 90 run minimum speed during turn | Not identified; [Move/jump data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 4.256000 m/s | ±5%; no baseline | GAP |
| 180 run velocity heading response (<5 deg) | Not identified; [Move/jump data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.250000 s | ±0.066667 s; no baseline | GAP |
| 180 run minimum speed during turn | Not identified; [Move/jump data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 0.000000 m/s | ±5%; no baseline | GAP |
| steady forward displacement over 2 s | Not identified; [Glide data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml) | 15.547119 m | ±5%; no baseline | GAP |
| steady forward speed (2 s window) | Not identified; [Glide data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml) | 7.773560 m/s | ±5%; no baseline | GAP |
| steady forward sink (2 s window) | Not identified; [Glide data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml) | 2.600098 m/s | ±5%; no baseline | GAP |
| 90 glide heading response (<5 deg) | Not identified; [Glide data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml) | 0.783333 s | ±0.066667 s; no baseline | GAP |
| 90 glide velocity response (<5 deg) | Not identified; [Glide data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml) | 2.100000 s | ±0.066667 s; no baseline | GAP |
| 90 glide peak heading rate | Not identified; [Glide data](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml) | 108.861981 deg/s | ±5%; no baseline | GAP |

### Sourced steady values and explicit estimates

These checks constrain parameters or steady modes; they do not fill the response
GAPs. Movement speed/height and camera geometry tolerances now use 5% where changed.

| Measure | BotW reference and source | Ours | Tolerance | Verdict |
|---|---|---:|---:|---|
| run speed | [5.556 m/s, run clip root × AS rate](https://github.com/ntngel1/botw-renderer/blob/656ceeb6ab2dd0eb0d6fa352cd1a3adddf0ec10b/docs/research/wiiu-as-frame-ctrl.md) | 5.556000 m/s | ±0.277800 m/s | PASS |
| sprint speed | [8.10 m/s, sprint clip root × AS rate](https://github.com/ntngel1/botw-renderer/blob/656ceeb6ab2dd0eb0d6fa352cd1a3adddf0ec10b/docs/research/wiiu-as-frame-ctrl.md) | 8.100000 m/s | ±0.405000 m/s | PASS |
| walk speed (light stick) | [1.575 m/s, walk clip root × AS rate; stick mapping not established](https://github.com/ntngel1/botw-renderer/blob/656ceeb6ab2dd0eb0d6fa352cd1a3adddf0ec10b/docs/research/wiiu-as-frame-ctrl.md) | 1.575000 m/s | ±0.078750 m/s | PASS |
| standing jump height | [0.58 m, PlayerJump](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml) | 0.578995 m | ±0.029000 m | PASS |
| running jump height | [0.58 + 2 × 5.556/30 = 0.9504 m](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml) | 0.950333 m | ±0.047520 m | PASS |
| swim speed | [1.56 m/s](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml) | 1.560011 m/s | ±0.078000 m/s | PASS |
| camera distance | [5.3 m, DefaultNormal radius](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/GameRomCamera.aiprog.yml) | 5.299999 m | ±0.265000 m | PASS |
| field of view | [0.872665 rad ≈ 50°](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/GameRomCamera.aiprog.yml) | 50.000000 deg | ±1.000000 deg | PASS |
| look point above feet | [1.5 m, LookPosOffsetY](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml) | 1.500000 m | ±0.075000 m | PASS |
| 180 heading vs Brake clip (proxy) | [8/30 = 0.266667 s animation, not physical response](https://github.com/ntngel1/botw-renderer/blob/656ceeb6ab2dd0eb0d6fa352cd1a3adddf0ec10b/docs/research/wiiu-as-frame-ctrl.md) | 0.250000 s | ±0.066667 s | UNSCORED |
| neutral sink vs vertical-only (estimate) | [~3.2 m/s vertical-only estimate, different input/output conditions](https://journals.le.ac.uk/index.php/pst/article/download/3330/3017/8787) | 3.201302 m/s | ±0.160000 m/s | UNSCORED |

The sink comparison is an **estimate**, not datamined: authors report ~70 m/~22 s
and no horizontal motion. Ours still travels horizontally at **5.844830 m/s** with
neutral stick. Even matching the sink number does not make the trials equivalent.
No new forward-speed estimate is invented. The run/sprint reversal clip duration
and native threshold do not supply body/velocity response through a controlled turn.

No player.jo or camera.jo constants changed: known steady values fit the declared
allowances, while no validated dynamic reference demonstrates what to tune toward.
Run acceleration remains 22 m/s² in the controller; this is an implementation value,
not a BotW reference. Startup distances integrate actual positions, not terminal
speed multiplied by time. Horizontal measures explicitly project x/z and exclude y.

### Reproduce and validate

```sh
mkdir -p build/movement-quantification
sloppy/bin/sloppy tools/feel_test.jo --csv build/movement-quantification/after
python3 tools/feel_trace_check.py build/movement-quantification/after
python3 docs/ref/verify_movement_response_sources.py
tools/traversal_check --headless --out build/movement-quantification/traversal
tools/journey_check.sh
sloppy/bin/sloppy tools/stride_check.jo
sloppy/bin/sloppy tools/contact_check.jo
```

All commands above are CPU-only; no render lock is needed. The trace checker
independently recomputes position differences, threshold times, glide states and
world commands rather than trusting controller constants. Result: **203 trace/evidence
checks**, **36 pinned source hashes / 12,299,189 bytes**, **1,607/1,607 traversal
checks**, and a **67,487-frame journey with zero stuck points, zero hard falls and
zero stamina outs**. Maximum stride slip **0.047%**; contact check passed. The harness
now exits nonzero on an accepted reference failure as well as a behavioral failure.

[movement-quantification.json](ref/movement-quantification.json) stores source URLs,
exact field values/limits, null response baselines, measured results, protocol details
and log hashes. Earlier audit/results below are retained as history. To close these
GAPs requires per-frame calibrated BotW position/velocity/body/camera output tied to
known stick/button input and a declared game build. The current score cannot justify
“identical feel” or a 100 movement rating.

## Ground
| Item | Value | Conf |
|---|---|---|
| Run speed | 5.556 m/s (2.963 m per 24-frame clip x rate 1.5; PlayerMoveNoise MaxSpeed 0.185) | H |
| Walk speed | 1.575 m/s (1.400 m per clip x 0.9); the stick blends walk into run | M |
| Sprint speed | 8.10 m/s (3.703 m per clip x 1.75) | M |
| Sneak max | 2.1 m/s | M |
| Exhausted / sand multiplier | x0.85 to speed and stick (~3.76 m/s) / x0.8 | M |
| Quick turn (skid) | stick vs facing > 120 deg; brake 9 / 8 / 18 frames (walk / run / sprint) | M |
| Capsule | r 0.35, h 1.6 (1.0 crouch, 1.2 climb) | H |
| Climbable | slopes >= 50 deg | H |
| Slope slide | starts 25 deg, max slip 12 | M |
| Shield surf | max 12 m/s, jump 0.98 m | M |

## Air
| Jump height | 0.58 m + 2.0 x speed(m/frame) (~+0.35 m running) | M |
| Side hop | 5.4 m/s, 0.8 m high; backflip 4.5 m/s, 1.11 m high; i-frames 1.33 s | M |
| Jump attack | 4.8 m/s forward, 1.5 m high | M |
| Gravity | ~29 m/s^2, terminal ~60 m/s (timed long drops onto known heights: El Duende 05, "Terminal Velocity Test", youtube.com/watch?v=FnxJDqP8f6w; 27.5 in an earlier video, 28.2 measured in TotK) | M |
| Fall damage | from 20 m: 4 quarter hearts + 0.6/m, 2/m past 50 m, 100 m kills; none into water >= 1.4 m deep | H |

## Climb
| Climb stamina | 36.5/s (27 s per wheel); sideways/down x0.5 | M |
| Climb jump | 310 stamina | M |
| Rain | slip every 2-4 s, costs 150 | M |
| Climb speed | 0.731 ± 0.30 m/s, **conditional** scenery-registered retail-footage estimate; capsule/torso scale proxy, excluded from measured-only score (sprint-climb AS rate x1.5 is native data) | L |
| Upward lunge rise | 1.794 ± 0.60 m, **conditional**, edge-limited Nintendo shot; not a maximum free-wall jump-height measurement | L |
| Visible upward lunge interval | 14 decoded frames: 0.467 s, bounds 0.334–0.601 s | L |
| Edge pull-over interval | 24 decoded frames: 0.801 s, bounds 0.667–0.934 s | L |

## Stamina
| Wheel | 1000 (starts 1 wheel) | H |
| Sprint drain | 300/s + 20 on press (~3.3 s/wheel per data; time it) | M |
| Recovery | 300/s after 10 frames (30 when exhausted), none airborne; no sprint for 60 frames after running out | M |
| Paraglider | 28/s | M |
| Swim | 30/s, dash 125 | M |
| Charge attack | 250 start | M |

## Swim: 1.56 m/s, dash 2.27 m/s, starts at depth 1.4 m.
## Glider: sink ~3.2 m/s with no stick input, reached in 2-4 frames (frame-timed 70 m drop: "Paragliding through Hyrule", Leicester J. Phys. Special Topics 2019, journals.le.ac.uk/index.php/pst/article/view/3330) (M); forward ~7-9 m/s and sink while moving ~2-3 m/s (G, no published measurement); min open height 1.2 m (ParashawlInvalidHeight).

## Camera
| FOV | 50 deg vertical | H |
| Distance | 5.3 m (1.2-12) | H |
| Target offset | +0.3 m | H |
| Pitch limits | -85..+89 | M |
| Dynamic follow | Auto-yaw rate and target-lag time constant **not identified from acquired footage**; see camera audit below | G |

## Combat
| One-hand combo | 4 hits (S1,S2,S3,finisher); S1 ends ~frame 17-18 at rate 1.15 | M |
| Guard | 120 deg front | M |
| Flurry rush | 80 frames slow-mo | M |
| Bow | 135 m/s initial, gravity -9.8 | M |

## Health / enemies / weapons
Jo: 3 hearts (12 quarters). Red Bonkoblin 13 HP / 4 atk; Blue Bonkoblin 72; Moblin 56; Squeese 1;
Gloop small 3 / med 20 / large 48 (dmg 2); Decayed Old Sentinel 500; Old Sentinel Scout I 13 / 12.
Weapons (atk): Bonko Club 4, Spiked Bonko Club 12, Bonko Spear 2, Tree Branch 2, Torch 2,
Woodcutter's Axe 3, Wanderer's Sword 5, Wanderer's Claymore 10, Wanderer's Spear 3, Wanderer's Bow 5.

## Time: 1 game minute = 1 real second (24 min day); game starts 05:15.

## Animation playback (foot sliding)
`tools/stride_check.jo` measures how fast each locomotion clip carries the body at rate 1 (the
planted foot's backward speed mid-stance). Current clips: walk 0.900, run 3.218, sprint 5.891,
sneak 1.105 m/s; these include the gait-amplitude correction described below.
The game plays each at speed / that rate (`game/chars.jo`), so the feet stay planted at every
speed (they slid 36% at a walk and 8% at a run with the earlier guessed rates).

## From Player_Link.gparamlist (docs/ref)
| Camera look point above the feet | 1.5 m (LookPosOffsetY; 2.5 on horseback, 0.1 swimming) | M |
| Hit-stop | small 2 frames, large 6 frames at rate 0.1 (HitStopTimeS/L, HitStopRate): 0.07 s and 0.2 s | M |
| Hit slow-motion | 1.5 / 3 / 4.5 frames at 0.1 (HitSlowTimeS/M/L) | M |
| Climbable | from 50 deg (ClimbEnableAngle) | H |


## From footage: the stride cycle
Nintendo's own exploration video (https://www.nintendo.com/jp/zelda/botw/assets/movie/run.mp4, a
rear camera running toward the Temple of Thyme) shows one foot coming round again every **0.541 s**
(five cycles frame-counted, +-0.034 s; the annotation and its limits are in
`ref/footage/gait-reference.json`, made for the parallel JotW attempt and reviewed there). Whether
Jo is running or sprinting in that shot is not known. At 5.56 m/s a 0.541 s cycle is 3.0 m of
ground; the run clip as made covered 4.9 m a cycle (0.875 s at a run: long, slow bounds). The game
now plays the run and the sprint with their limb swing shortened about each bone's mean pose
(`load_humanoid_anims` in `game/clips.jo`: the run to 62%, the sprint to 79%) and their ground speed
measured again, so the feet stay planted:

| gait | speed | stride cycle | ground a cycle |
|---|---|---|---|
| run | 5.56 m/s | 0.541 s | 3.0 m |
| sprint | 8.1 m/s | 0.485 s | 3.9 m |

`tools/stride_check.jo` prints these; `tools/feel_test.jo` displays the cycle against its
±0.034 s annotation allowance, but excludes it from measured-only agreement because the
source gait mode is unidentified. Faster sprint steps and foot-slip limits are behavioral
checks. Neither foot-slip checks nor this provisional cadence establish matching movement feel.


## Traversal evidence audit — 2026-10-09

[traversal-reference.json](ref/footage/traversal-reference.json) retains source URLs, SHA-256,
decoded stream metadata, zero-based frame windows, manual image points, registration quality,
arithmetic and limitations. No video or extracted image is committed. New retail sources are
Mega64's first-person [climbing demonstration](https://mp4.mega64.net/botw/u02/014.mp4) and
[running/falling demonstration](https://mp4.mega64.net/botw/u02/004.mp4), linked by the author in
[update 2](https://www.lp.zone/t/1969/10). Both are 896×504, 30 fps, with the stamina/heart HUD
visible and no controller overlay. The author describes the first as climbing. Platform,
patch, stick magnitude, jump charge, controller synchronization and playback provenance remain
unverified. Nintendo's exploration source is the same prerelease source as the gait study.

### New annotations and what they support

| Observation | Frames and method | Result and allowance | Use in harness |
|---|---|---|---|
| Sustained retail climb | Frames 30–150, 120 intervals / 4.000 s; four adjacent 30-frame intervals. SIFT on rock texture outside Link/HUD/foliage, 5-frame chained homographies, then local head-to-hip scale. | 0.921 torso lengths/s; conditional **0.731 ± 0.30 m/s**, L | Former G → L, `inferred`; excluded from reference score |
| Nintendo upward lunge rise | Frames 1386–1400; scenery registration (94 inliers), manually marked head and hip at both ends. Registered rise 236.1 px / 104.5 px per torso. | 2.259 torso lengths; conditional **1.794 ± 0.60 m**, L | Former G → L, `inferred`; edge-limited, excluded from reference score |
| Visible upward lunge interval | Initiation window 1384–1388; hands at upper edge 1398–1402. Centers 1386→1400, **14 frames**; original PTS, not assumed exact 30 Hz. | **0.467134 s**, bounds 0.333666–0.600600 s; tolerance ±0.134 s, L | `footage`; visible motion interval, not input latency |
| Edge pull-over interval | Hands at upper edge 1400–1404; supported movement on top 1424–1428. Centers 1402→1426, **24 frames**. | **0.800800 s**, bounds 0.667334–0.934266 s; tolerance ±0.134 s, L | `footage`; prompted mantle-duration tuning |
| Net camera sweep during retail run | Frames 0–10 (0.333333 s); two 5-frame homographies of the distant skyline; K⁻¹HK projected to a rotation with SVD. | **25.0 ± 5°**, L, conditional on 50° vertical FOV | Diagnostic only: right-stick input unknown, so this is not an auto-follow rate |

The duration windows were independently re-inspected at original resolution around all
three boundary windows; they
agree with the earlier JotW windows. These are adjacent samples in single shots, not repeated
controlled trials. Allowances are conservative visual/model bounds, not statistical confidence
intervals or guarantees across builds. Lunge and mantle share an uncertain boundary.

**Metre-scale limitation:** the standing character-controller prism has a native height of
1.6 m in `ref/phys.yml`, `CharacterController/Forms/Form_0/ShapeParam_0`, `translate_0.y`.
A capsule is not a mesh-height ruler. The running pose at retail frame 0 gives head-to-hip
length 78.4 px and head-to-foot height 158 px; treating that height as 1.6 m gives a **0.794 m
head-to-hip proxy**. Both metre results are conditional on that proxy. Torso flexion, camera
pitch, wall slope, depth separation from the rock plane, nonplanarity and pose calibration
motivate the broad allowances. A homography removes camera motion but does not supply metric
rectification. These results replace unsupported point guesses with reproducible observations
and explicit assumptions; they do **not** become independently measured world-speed/height
references. The lunge is capped by an edge and cannot determine unconstrained maximum height.

The harness now samples actual steady climbing displacement over 10 s, rather than assuming
18 m travelled and dividing by approach/edge timing. The climb was 0.945 m/s and the lunge
0.550 s against the footage's 0.731 m/s and 0.467 s: `CLIMB_SPEED` is now 1.2 (a steady
0.81 m/s, the reach cadence and the climbing clip slowed with it, so each reach covers the
same height of wall) and `CLIMB_LUNGE_TIME` 0.467 s (as high as before: 2.0 m). The pull-over
was 0.550 s, below the observed 0.667 s lower bound; `MANTLE_TIME` is now **0.800 s**. No camera,
acceleration, braking, jump-steering, or glide constants were changed.

### Camera measurement and the unresolved comparison

The retail run's first ten frames rotate the camera by approximately 25°, but do not reveal
whether that motion came from the right stick, auto-follow, or both. Later panorama registration
was rejected: too few horizon inliers and stronger translation/pitch contamination. There is
no camera-input overlay in this clip or Nintendo's rear-running shot. A straight-running view
can show stable framing without identifying world-space target lag or the yaw response to a
controlled turn. Consequently **no camera lag/auto-follow reference score is claimed**.

`feel_test --csv DIR` now records body heading, camera yaw, camera target and camera position
alongside the movement samples. Its `camera_world_turn.csv` scenario maintains an absolute
world heading while the camera rotates; holding a fixed screen-relative direction would turn
the commanded trajectory with the camera and contaminate the response. The clone measures:

- Steady run look-point lag: **0.0661 m** behind the body look point.
- Camera reaches 45° **1.350 s** after the 90° world-direction command; the body reaches that
  heading after **0.183 s**. Residual camera/body yaw after six seconds: **3.438°**.

These are implementation diagnostics with no accepted BotW baseline. No guessed response
constant is rewarded by the score. A known fixed camera input (or synchronized controller
trace) and calibrated world geometry are needed to measure the requested lag/auto-follow
agreement, stop distance, acceleration and air steering reliably.

### Native parameter provenance and rejected shortcuts

[movement-sources.json](ref/movement-sources.json) pins the public
[leoetlino/botw parameter dump](https://github.com/leoetlino/botw/tree/f50b984f5e645dcf71b1c6340a8834bb1dee0153)
and records byte-identical upstream/local hashes for the player AI, player general parameters,
and physics file. `PlayerActionClimb` has `DashAnmSpdRate=1.5`, stamina values and rain controls;
its AS has rate 0.8 on `Climb_Wall_Move_U`, but **no clip root displacement is present**.
A rate without root motion cannot establish climb m/s or jump metres. `PlayerParashawlGlide`
has `GlideSpeedMax=0.02` and `Lv2GlideSpeedMax=0.35`; their action semantics are not established
here, so multiplying either by 30 and calling it forward speed would be unsupported.
`TurnEnableDirSub=120` is the skid trigger angle, not a turning rate.

The pinned [Wii U root-motion research report](https://github.com/ntngel1/botw-renderer/blob/656ceeb6ab2dd0eb0d6fa352cd1a3adddf0ec10b/docs/research/wiiu-as-frame-ctrl.md)
distinguishes `Wait` stop clips from reversal `Brake`. Its 8-frame run-brake clip supports the
existing reversal-duration reference, but does not measure stick-release stop time/distance.
An animation blender's `InputLimit` is not player acceleration, nor a 90° facing-time curve.
The inherited Leicester no-input sink estimate is literature/model evidence (`inferred`),
not our decoded measurement of gliding with forward input.

Eight G rows remain: time to 90% run; stop time; stop distance; forward glide speed; forward
sink rate; run-up curve; 90° turn; sideways drift in a running jump. Acquired jumps hit water,
leave different elevations or deploy a glider. Glide shots have uncalibrated depth motion.
Footage starts already running or lacks an identifiable release; the ten-frame running camera
sweep cannot reveal joystick onset. Those clips do not justify substituting animation phase
counts for input-response or world-displacement measurements. Candidate clips u03/009,
u03/049, u04/007 and u04/015 were inspected but rejected for those purposes (tower descent,
cutscene, magnesis and bog entry respectively).

### Scores and verification

Final headless results: **99.1/100 agreement** (26 references: 24 data, 2 timed footage),
**100.0/100 correctness** (25/25 contracts). Contact check passed, including worst mantle
hand drift 0.000010 m; stride slip was at most 0.047%. The locked passage check passed:
(-1071.9, 246.8, 1847.8), 4.8 m from the cave mouth after 760 frames. Eight guesses and seven inferred rows
are displayed but excluded.

The output contains exactly two aggregate scores:

1. **Agreement with measured references only**: confidence-weighted Gaussian agreement with
   native parameters, documented root-motion observations and compatible frame-timed intervals.
   Guesses, conditional scale results, unclassified gait mode, literature-derived ballistic
   predictions and implementation checks are excluded. This is agreement on the supported
   subset, not a holistic BotW movement-fidelity rating.
2. **Behavioral correctness**: equal-weight pass/fail count for 25 binary or bounded contracts,
   including safe falls, ledge grabs, foot-slip limits, shield behavior and raised-floor dodges.
   Failed correctness checks give the tool a nonzero exit status.

State samples are timestamped at the **end** of each 60 Hz update (first sample 1/60 s).
Stop time is measured from release to the first speed below 0.05 m/s; the previous harness
lost one frame. Glide diagnostic sampling starts after deployment acceleration. The gait
annotation tolerance is now 0.034 s rather than an unexplained 0.100 s.

To reproduce the source analysis (Python with NumPy/OpenCV and ffprobe; no game render):

```sh
mkdir -p docs/ref/footage/raw
curl -fL https://mp4.mega64.net/botw/u02/014.mp4 -o docs/ref/footage/raw/u02-014.mp4
curl -fL https://mp4.mega64.net/botw/u02/004.mp4 -o docs/ref/footage/raw/u02-004.mp4
curl -fL https://www.nintendo.com/jp/zelda/botw/assets/movie/run.mp4 -o docs/ref/footage/raw/nintendo-run.mp4
python docs/ref/footage/measure_traversal.py \
  --climb docs/ref/footage/raw/u02-014.mp4 \
  --run docs/ref/footage/raw/u02-004.mp4 \
  --nintendo docs/ref/footage/raw/nintendo-run.mp4 \
  --out docs/ref/footage/traversal-reference.json
sloppy/bin/sloppy tools/feel_test.jo --csv docs/ref/scratch/feel-traces
sloppy/bin/sloppy tools/contact_check.jo
sloppy/bin/sloppy tools/stride_check.jo
flock /tmp/botw-render.lock bash tools/passage_check.sh
```

Only the last command renders the game. Raw footage and scratch results are ignored by
`docs/ref/.gitignore`. Verify source SHA-256 before reusing the annotations on any replacement
video. The committed JSON retains the manual annotations and registration settings, so the
analysis can be audited independently of this checkout's scratch files.

## Movement response research — 2026-10-10

**No guessed response row was promoted.** The eight rows below remain `G` / `guess` and
excluded from measured agreement; camera auto-follow and target lag also have no accepted
baseline. No `player.jo` or `camera.jo` constants changed. This records a completed search,
not a claim that no usable source exists anywhere.

[movement-response-audit.json](ref/movement-response-audit.json) records the per-row decisions,
web queries, inspected video times, exact candidate parameters, 36 pinned file URLs/hashes,
and before/after clone results. The clone values below are diagnostics, **not BotW values**.
The provisional targets remain hypotheses, not measurements with validated uncertainties.

| Guessed harness row | Provisional target | Clone before → after | Search result / missing evidence |
|---|---|---|---|
| Time to 90% run | 0.300 s | 0.233 → 0.233 s | Player general/AI parameters, `PlayerMove`, AS `Move`, root-motion report, TAS input script: no known-input speed trace or ground acceleration equation. |
| Stop time | 0.250 s | 0.200 → 0.200 s | `Wait` release versus `Brake` reversal inspected; the 8-frame reversal is not a release-stop measurement. TAS release has no paired output. |
| Stop distance | 0.600 m | 0.530 → 0.530 m | Same sources; no calibrated world displacement after an identified stick release. |
| Glide forward speed | 7.800 m/s | 7.679 → 7.679 m/s | Native glide parameters and action stubs, community course timings, ZSR TAS glide shot: no proven full-forward speed equation or synchronized calibrated flight. |
| Glide sink with forward input | 2.600 m/s | 2.600 → 2.600 m/s | Native glide parameters and Leicester paper: the paper's vertical-only trial cannot establish forward-input sink. |
| Run-up curve RMSE / top speed | 0, versus a guessed exponential | 0.062 → 0.062 | AS blends/start clips and TAS script lack the complete output trajectory. Existing hypothesis is `5.556*(1-exp(-t/(0.3/2.3)))`; it is not a BotW curve fit. |
| 90° turn at a run | 0.250 s | 0.183 → 0.183 s | Reversal thresholds, AS angle blends/root rotations, TAS candidates: no synchronized 90° input step/body-yaw response. |
| Sideways drift in a running jump | 0.900 m | 1.065 → 1.065 m | `MaxSpeedInAir`, jump/fall parameters and stubs, TAS candidates: no steering coefficient or paired sideways-jump trajectory. |

### What the native sources actually contain

The public [player parameter dump](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/GeneralParamList/Player_Link.gparamlist.yml)
contains `MaxSpeedInAir=0.3`, `TurnEnableStickSub=30`, `TurnEnableDirSub=120`,
`DashToRunStickValueDec=0.03`, and attention-position interpolation values `0.2 / 0.01 / 0.2`.
The turn values are reversal thresholds, not yaw rates. An airborne speed cap, even if
confirmed as `0.3 m/frame * 30 = 9 m/s`, would not determine the requested lateral drift.
Dash-to-run stick decay is not acceleration from rest. Attention interpolation names do
not establish chase-camera target smoothing.

The [glide action parameters](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/Player_Link.aiprog.yml#L664)
give `GlideSpeedMax=0.02`, `Lv2GlideSpeedMax=0.35`, `OverSpeedDec=0.002`,
`GlideRotSpeed=20`, `GlideRotRate=0.2`, and `WindScale=10`.
The [public glide implementation](https://github.com/zeldaret/botw/blob/49c6b5c18344de6555163b3af7044970ad9d7c5e/src/Game/Actor/Player/Action/actionPlayerParashawlGlideBase.cpp)
loads those fields but provides no glide calculation. Multiplying them by 30 to invent
forward or sink m/s would be unsupported. Likewise, public
[`PlayerMove`](https://github.com/zeldaret/botw/blob/49c6b5c18344de6555163b3af7044970ad9d7c5e/src/Game/Actor/Player/Action/actionPlayerMove.cpp),
jump and fall action calculations defer to base action stubs; `PlayerBase` remains TODO.
The root-motion report explicitly leaves startup/release trajectories and stick smoothing
unresolved. Its AS `InputLimit=15°/frame` limits an animation input, not a measured facing rate.

The [default camera AI parameters](https://github.com/leoetlino/botw/blob/f50b984f5e645dcf71b1c6340a8834bb1dee0153/Actor/AIProgram/GameRomCamera.aiprog.yml#L359)
(`Action_2`, `DefaultNormal`) contain `lngCus=0.1`, `lngCusSpeedEffect=0.2`,
`AtHCusMin/Max=0.6/1.0`, `atVCusMin/Max=0.4/1.0`, `atMoveOffset=0.5`,
and `keepManual=true`. The existing radius `5.3` maps directly to clone metres;
`Fovy=0.872665 rad * 180/pi = 50.000021°` supports the existing FOV.
The [camera action](https://github.com/zeldaret/botw/blob/49c6b5c18344de6555163b3af7044970ad9d7c5e/src/Game/Actor/Camera/Action/actionCameraChase.cpp)
has only its constructor/destructor. No update equation establishes coefficient units,
auto-yaw activation, rate, or target-lag time constant. These coefficients stay unscored.
The [ZeldaMods camera page](https://zeldamods.org/w_botw/index.php?title=Camera&oldid=7257)
is a subsystem stub, not a dynamic-follow reference.
`GameRomCamera.gparamlist` additionally has event-return connection settings:
`LatConnectRateAfterEvent=0.75`, `LngConnectRateAfterEvent=0.325`,
`ConnectAfterEventMin/Max=30/90`. These do not establish ordinary chase response.

All 18 public `GameData/Flag` YAMLs (11,919,805 bytes), plus `GlobalParameter.gparamlist`,
were searched for acceleration, deceleration, player/link speed/movement/turn/air, glide,
parashawl and camera names. Hits include camera settings, mini-game cameras and paraglider
quest flags; none establishes these response rows. The independent Echocolat player JSON
and leoetlino reverse-engineering notes were also inspected; neither supplies the missing
runtime response. Full source hashes and the search expression are in the audit.

### Community measurements and input-footage leads

The Leicester [2019 paper, page 2](https://journals.le.ac.uk/index.php/pst/article/download/3330/3017/8787)
reports approximately 70 m in 22 s, about 3.2 m/s, explicitly without horizontal motion.
It reports 2–4 video frames of acceleration but supplies no recording or boundary timestamps.
This supports the existing unscored no-input literature estimate, not forward-input sink.

The author's [2022 movement-speed study](https://www.reddit.com/r/botw/comments/xlrzrq/)
uses stopwatch trials along a road from Dueling Peaks to Proxim Bridge, with glides following
the minimap road. It does not supply synchronized stick input, trajectory samples or sink
measurements. No numeric table values were transcribed or promoted from its embedded images.

A real [TAS input script](https://github.com/MCMi460/BOTW-TAS/blob/b09637c3e9b452f577cbfdfeee845fafe04ddced/any%25/SoR/script1.py)
issues 90 one-frame input calls holding B with left stick `(-6113, 32033)` and right stick
`(0, 0)`, followed by A with neutral sticks. It has no paired footage/position log or
verified initial state; its comment flags the angle/run length. It cannot yield acceleration,
release timing in seconds, stopping metres, or a camera response.

The [ZSR exterior TAS index](https://www.zsr.gg/botw/tas/exterior) led to two playable videos:
[Old Man's dialogue at 9.000 s](https://www.youtube.com/watch?v=cN_TODTOYn4&t=9s)
(45.001 s stream duration, 1280×720: a glider above Plateau Tower), and
[SOR Clip at 78.000 s](https://www.youtube.com/watch?v=Csc6BdsjZjY&t=78s)
(113.281 s, 1280×720: wake chamber; 68.000 s was black).
Both pages state that no description is supplied, and no input overlay is visible in the
inspected images. No paired input log, downloaded original, calibrated displacement or
decoded frame timing was acquired. The `42.300` segment title is not a movement response
measurement. No frame counts or FPS were invented from these pages.

An acceptable future acquisition needs paired frame-indexed left/right-stick input and
body position/yaw plus camera pose, or footage with synchronized input and calibrated world
geometry. Record rest → full run → neutral release, a separate sustained 90° world turn,
and a sideways-input running jump through landing/settling. A normal full-forward glide
needs known world endpoints/heights, original timestamps and wind/updraft conditions.
Fit entire responses and retain residuals/overshoot/settling; a final speed or endpoint alone
does not validate acceleration, air control or camera response.

### Harness changes and verification

`feel_test --csv DIR` now exports the initial state at `t=0`, then each state at the end
of a 60 Hz update. Input fields on a row apply during `(t-DT, t]`: move/look axes,
jump/jump-held/sprint, and the pre-update world wish vector from the player's own function.
Velocity and camera pitch are included; original columns retain their names/order.
The initial row has neutral input placeholders and is not an executed input interval.
It is excluded from the metric sample arrays so existing timing arithmetic is preserved.

`turn_90_world.csv` retains six seconds after the world-direction step;
`jump_side_world.csv` retains the jump and one second after landing. Both compensate the
stick for camera yaw, so the command remains east as the camera turns. `run_stop.csv` retains
the full run-up and release tail; `run_curve.csv` retains every speed sample. Guess and
inferred rows display `n/a` instead of an `ok` against an unsupported target.

Camera diagnostics remain unscored: lag **0.0661 m**, 45° response **1.350 s**, body heading
threshold **0.183 s**, residual **3.438° after 6 s**. The added full-response diagnostics
give peak yaw rate **47.042°/s**, overshoot **0°**, and settling within **5° from 5.333 s
through the end of the 6 s observation**. This is finite-window settling, not a guarantee
beyond the recording and not an identified BotW time constant.

Before → after: **99.6 → 99.6/100 measured agreement**, still **26 references (24 data,
2 footage)**; **29/29 → 29/29 behavior checks**. Eight guesses and seven inferred rows
remain excluded. The 2026-10-09 scores above are historical results from that audit.
Source verification and trajectory reproduction:

```sh
python3 docs/ref/verify_movement_response_sources.py
sloppy/bin/sloppy tools/feel_test.jo --csv docs/ref/scratch/feel-response-traces
```

These commands do not render the game. `slot_check.jo` imports game initialization and
requires the render lock, as do `shrine_exit_check.sh` and `passage_check.sh`;
`opening_check.sh` locks itself.

Validation: all **18/18 requested tools passed**: `feel_test`, `fauna_test`, `element_test`,
`element_check`, `save_test`, `architecture_test`, `contact_check`, `integration_test`,
`slot_check` (locked rerun), `input_check`, `camera_check`, `combat_check`,
`title_handoff_check`, `shrine_route_check.sh`, `shrine_exit_check.sh`, `passage_check.sh`,
`opening_check.sh`, and `late_story_check.sh`. All 70 printed metric values were unchanged
from the baseline. The CSV initial row, step timestamps, neutral look axes and fixed-world
wish vectors were checked. Source verification passed for **36 files / 12,299,189 bytes**.

## Round 71: body-normalized climbing hypothesis

`feel_test` now reports steady climbing displacement divided by the actual
standing hero mesh height, in body heights per second. The proposed BotW
reference **1 / 1.1 = 0.909 body heights/s** has no supplied footage URL or frame
window identifying the stamina-free cycle. It remains **G / guess**, excluded
from measured agreement. The implementation measures **0.489 body heights/s**;
this comparison does not justify a speed change.

The existing retail climb annotation (Mega64 `u02/014.mp4`, SHA-256
`e5680dabadb74722c8229ac06a74643ab55c650bc488b59f97c614863b727852`,
frames 30–150) establishes **0.921 head-to-hip lengths/s**, not standing body
heights/s. Its full-body conversion uses a separate running pose and cannot
remove pose, projection and plane assumptions. The source URLs remain in
[`traversal-reference.json`](ref/footage/traversal-reference.json); no new
frame annotation or independent body-height ruler was obtained in this round.
The two existing duration observations retain their `footage` status. Agreement
remains **99.6/100**, **26 measured references**, **29/29 behavior checks**;
the new hypothesis increases the guess pool from eight to nine.
