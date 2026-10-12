# Archived music development evidence

Historical measurements and scoped implementation notes through rounds 50–71.
Use [current music evidence](../MUSIC.md) for shipped behavior and current listening results.
Older scope statements, levels, paths and timings below describe their recorded revision.

# The score

Exploration is solo sampled piano: a short, irregular figure, then 22-40 seconds without a
new strike in ordinary exploration. Figures contain four or five notes and at most one
gently rolled dyad; motif variations can be three-note partial statements. Fifths,
fourths, ninths, sixths and octaves supply the space; there is no continuous left hand or pad.
The original plateau motif (F# A B / A F# E D) survives in the set pieces and as the five-note
fragment F# A B E D, coloured by context. It returns on the second figure of each four-figure
cycle and when approaching key landmarks: on its own at most every 180 seconds, on arriving at a landmark (once a visit) at most every 90.
Discovery cues now use that same five-note identity. These are original compositions, not
Nintendo melodies.

The model is the restraint of BotW's field score: isolated piano gestures and room for the
land's sounds. JotW's `src/play.jot:216-229` and `src/systems.jot:620-700` were read as a local
reference for its open five-note figures, unequal gaps and 22-41 second waits. Our exploration
figures are newly composed; its exact four figures appear only in the offline comparison.

## Context and silence

| mood | register / colour | gap after the last strike |
|---|---|---|
| field day | D4, occasionally an octave higher; fifths and ninths | 22-34 s |
| golden hours | G3, occasionally G4; warm major sixths | 24-36 s |
| field night | A3; hollow fifths, minor sixth colour | 28-40 s |
| rain | B3; lower ninths and sixths, softer attacks | 26-38 s |
| forest | D3, occasionally D4; fourths, fifths, minor colour | 24-36 s |
| snow | E5; upper fifths, ninths and octaves | 28-40 s |
| ruins | E3; low fifths, octaves, minor sixth colour | 26-38 s |
| shrine | C3; low fifth dyads answering distant upper notes | 28-40 s |

Day's base gaps are 0.65, 1.7, 0.95 and 2.8 seconds, individually varied and stretched by
context; every third ordinary figure delays its inner answer by another 30%. The final note
is 12% softer. Ordinary figures vary in length: about one in eight is skipped entirely (the turn
passes in silence), one in eight is a single note, one in six is cut to two or three notes, and
one in six adds a sixth note an octave over the second. Velocities are mostly 0.30-0.46, quieter at night, in rain and in shrines. The pp/mf
blend gives these soft strikes a little colour without a sudden layer switch. Small stereo
positions are stable by pitch. Standing still for ten seconds reduces a figure to two soft
notes, omits the dyad and adds 8-16 seconds to the wait. Motif statements rotate through
complete, upper-register, inverted-around-the-first-note and three-note versions. The upper
register is lifted once, and added dyads are bounded by the recorded C7 bank.

A once-per-second check uses five squared distances: Temple of Time (-818,1950), tower
(-560,1722), old man's fire (-946,1883), Resurrection mouth (-1068,1845), and Eastern Abbey
(-495,1990). Their radii are 85/75/45/45/85 metres. A landmark requests a statement once per
visit, on entering its radius (re-armed only after leaving beyond 1.3 times the radius), and at most
once per 180 seconds. The request waits for the current figure, respects the 90-second landmark motif
cooldown, and can shorten the remaining rest to eight seconds only after at least 18 seconds
without a strike. It neither interrupts a figure nor queues several motifs for overlapping
radii. Combat, title, silence and shrine interiors skip proximity checks. The live player
position comes directly from `player.jo`; no scene or art hooks changed.

Context changes fade the actual active score voices, rather than only changing future strike
gains. Outgoing notes stop during the fade: 0.3 seconds for combat/silence, 0.9 seconds for
other contexts. Combat starts with a half-strength stab and reaches full gain over 0.25
seconds; exploration rises over 1.2 seconds. Weather/place changes introduce the new register
with two soft notes, the first 0.45 seconds after hand-off, then resume a full contextual
rest. This response has an 18-second cooldown and waits if a discovery just sounded. Leaving
combat waits seven seconds for victory or the danger to recede. Independent story cues keep
their natural releases. Discovery plays an open-fifth chime, D A D A rising (MIDI 74/81/86/93) over 1.3 seconds,
and delays the next field figure at least 22 seconds after its final strike.

These gaps measure **no new strikes**, not literal digital silence: the piano and room still
ring into them. `p_phrase` and `phrase_rest` are shared by gameplay and the renderer, including
the standing-still rules. Rain selects its mood in open day/golden terrain; night, forest,
snow, ruins, shrine and combat retain their contextual priority.

## Texture and recurrence (2026-10-11)

Every exploration context now has eight authored open-interval figures. Each figure
has a 180-second cooldown; emitted melody pitches also have a three-minute history,
including partial and single-note statements. Timing, velocity and rolled-dyad changes
do not bypass it. An unavailable/repeated turn passes in silence. Piano recordings,
soft velocities, contextual rests and the plateau motif remain.

Combat's first eight bars retain the A A / C ... G# identity at 152 BPM. Each next
eight-bar round changes the answers' register and thins bars 4/8; the fourth round
leaves bar 4 empty. A clean player impact requests one empty next bar, at most once
per eight bars. Traded hits do not request it, and the clock/tails keep running.

The former night bed was a four-second loop of fixed 3.9/4.3 kHz carriers. Insects
are now short irregular chirplets with pitch glides, played once with independent
pitch, level, pan and gaps. Synthesis stays at load; the prepared audio schema and
real-piano banks are unchanged. Night piano is trimmed 1.5 dB from the previous
listening pass (+0.5 dB over round 65) to retain the mix target after the bed/figure
change. Forest piano gains 1.8 dB to retain the full-capture exploration range
with the sparser new sequence. `listen.py` runs audio/phrase checks and writes
`build/listen/textures.json`: five of eight combat bars change, insect variance
12.6064 (threshold 0.35) with 60.56% silent windows, and the ten-minute day field
minimum repeat is 238.57 s. The forest production capture has no repeated phrase
in 600 s. Combat stays -21.9 LUFS/-2.8 dBTP; all regenerated clips pass headroom. See [LISTEN](../LISTEN.md) for thresholds and results.

## Piano bank

The bank uses the freely usable [University of Iowa MIS Steinway & Sons model B recordings](https://theremin.music.uiowa.edu/MISpiano.html),
with **pp, mf and ff** strikes at 21 pitches, C2-C7, spaced three semitones apart. The ff set
supplies all required individual AIFFs, just like pp/mf. The bank has 63 mono PCM16 WAVs at
48 kHz, totaling **39,314,772 bytes (37.49 MiB)**, versus 42 files / 12.50 MiB before.

The importer preserves 8 seconds of dry tail at C2, falling to 5 seconds at C7 (previously
4.5-2 seconds), with 0.8/0.5 second end fades. Each loaded note has two additional seconds for
stereo reverb, hence a 10-7 second buffer. Pitching a sample also pitches its decay. There are
no sample loops or synthesized sustain extensions. The recordings keep their original room
sound and stretch tuning. Filtering remains 25 Hz / 11 kHz, attack fade 1 ms, and normalization
uses the first half-second RMS. pp/mf/ff target RMS is 0.028/0.050/0.070, with dry peak caps
0.12/0.21/0.29 and the existing register compensation.

Both gameplay and offline rendering use `piano_blend`: equal-power pp -> mf between velocities
**0.35-0.65**, full mf through 0.70, then equal-power mf -> ff at **0.70-0.95**. Only the active
one or two layers become voices. Missing recordings retain the additive-synthesis fallback.
All 63 output hashes and mono/PCM16/48 kHz headers were validated. Pitch checks span -1 to +23
cents; first nonzero PCM is within 0.55 ms, the -40 dB attack within 1.88 ms, and the sustained
attack within 5 ms.

Rebuild with Python 3, NumPy and ffmpeg:

```sh
python3 tools/import_piano.py --download
python3 tools/import_piano.py
# Or, without NumPy installed globally:
uv run --with numpy python tools/import_piano.py --download
```

Sources remain in ignored `assets/src/piano/`. The importer refuses a cache symlink into
another checkout; this worktree's former `assets/src` symlink was replaced with a local cache.
Source/output hashes, URLs, trims, filters, gain, pitch and onset checks are recorded in
`assets/audio/piano-import.json`. Library permission and recording/performer credits remain in
`assets/audio/LICENSE.txt`.

## Set pieces and combat

All synthesized music pads have been removed, including the looping ruins/shrine beds and
title/wake/tower pads. Sustained low piano fifths under the title and octaves/fifths under the
tower now provide weight through the recording's natural decay and existing reverb. Shrine
figures start with a quiet low fifth. Waking needs no replacement bed: its distant notes ring
on their own. A continuous synthetic drone would mask the quiet attacks and fill the very
silences this revision restores. The ambient shrine hum remains a world sound in `sfx.jo`.

The full original title/tower/wake motifs, orb, victory, alert, item and secret cues remain.
Discovery now states the five-note plateau fragment. Combat retains its 152 bpm rotating
A-minor harmony and eight-bar dynamic swell, but replaces the ostinato with syncopated
stabs: four upper notes in most bars, two in the fourth/eighth, and two bass strikes per bar.
The first round has 44 piano strikes per eight bars (104.5 notes/min); 89 of 128 eighth-note steps
have no piano attack. Short pp/mf/ff banks keep the first 100 ms and close the damper with
a smooth 160 ms fade. They are built once from the reverberated recordings, not sliced or
synthesized during a fight. The low drum sounds on steps 0/7, and the slap on step 12 of
alternate bars, leaving percussion rests too. Low drum levels fall from 0.55 to 0.16 and slap levels from 0.35 to
0.09 before their dynamic multiplier; sharp piano accents carry the fight. Both drum sounds
are built in `piano_init`, so entering combat cannot synthesize them on a frame.

## Final listening mix (2026-10-11)

The texture revision above supersedes this pass’s night/forest trims and phrase
counts; the level table below is regenerated. This older mix pass supersedes the round-65 gains below. The original 45-second daytime clip's
loudness came from bright piano figures: its largest attack at 4.623 s is dominated by
A5. The night peak at 36.462 s contains the F4/G5 rolled ninth, not an owl or creature
call. The ten-minute forest capture averages a different register and many more rests;
it cannot stand in for that short daytime excerpt. Likewise, the previous -22.1 LUFS
combat capture includes recurring wind-up, hit, parry and hurt effects, whereas the
listening combat clip contains the score, ambience and footsteps. Its score alone
was about -26.5 LUFS. These differences explain the earlier apparent level reversal.

Context trims relative to round 65 are day **-2 dB**, night **+2 dB**, rain **+5 dB**,
combat **+4.5 dB**, with another **+1.7 dB** for the sparse last-heart arrangement.
Title/cave-exit music gains **1.5 dB**. The combat entry accent is **1.5 dB** below the
new sustained-combat gain. Phrase timing, note velocities, rest lengths, motif
cooldowns and the **22/44/36** alert/engaged/last-heart strike counts stay unchanged.
Danger-cue sidechain floors become **0.11318 / 0.07836** for engaged/last-heart, retaining
the previous absolute music level during their held duck. Recovery remains 240 ms.

The production master now has a continuous, stereo-linked soft knee above **0.65**
and a **0.84** sample ceiling (-1.51 dBFS), reserving intersample headroom. Samples below
the knee pass unchanged. This replaces the old discontinuous, above-full-scale-only
`tanh` switch. Manually assembled offline scores use the same guard once; production
mixer exports already contain it. This is runtime mix processing, with master **0.8**
and export gain **1.0**, never per-clip normalization. FFmpeg `ebur128=peak=true`
measures every listening clip and every music/sound export against **-1 dBTP**.

Shrine hum retains its existing level. Room tone rises **2.5 dB**: it sits about
**4.3 dB below walking footsteps** and **15.6 dB below music** in whole-stem RMS,
with footstep transients over **12 dB** above it. The isolated hum/room/steps/music
sum still reproduces the full shrine mix to PCM rounding. The listening checker
also enforces exploration/combat/set-piece ordering instead of only sample headroom.

All clips below are 45 seconds, master 0.8/export 1.0, without normalization.

| Clip | Seconds | LUFS-I | RMS dBFS | Peak dBFS | True peak dBTP |
|---|---:|---:|---:|---:|---:|
| [field_day](../../build/listen/field_day.wav) | 45 | -24.50 | -31.49 | -5.58 | -5.60 |
| [field_night](../../build/listen/field_night.wav) | 45 | -25.40 | -30.95 | -5.13 | -5.10 |
| [rain](../../build/listen/rain.wav) | 45 | -26.00 | -29.11 | -3.32 | -3.30 |
| [combat_engaged](../../build/listen/combat_engaged.wav) | 45 | -21.90 | -25.08 | -2.76 | -2.80 |
| [low_health](../../build/listen/low_health.wav) | 45 | -22.80 | -25.56 | -4.01 | -4.00 |
| [shrine](../../build/listen/shrine.wav) | 45 | -27.90 | -33.21 | -7.41 | -7.40 |
| [title](../../build/listen/title.wav) | 45 | -20.40 | -26.88 | -4.56 | -4.60 |
| [cave_exit](../../build/listen/cave_exit.wav) | 45 | -20.90 | -26.75 | -4.39 | -4.40 |
| [shrine_hum](../../build/listen/shrine_hum.wav) | 45 | -45.40 | -45.28 | -39.53 | -39.50 |
| [shrine_room](../../build/listen/shrine_room.wav) | 45 | -50.40 | -49.14 | -34.82 | -34.80 |
| [shrine_steps](../../build/listen/shrine_steps.wav) | 45 | -43.50 | -47.92 | -21.78 | -21.80 |
| [shrine_music](../../build/listen/shrine_music.wav) | 45 | -23.10 | -33.77 | -7.48 | -7.50 |

All **65 music/sound exports** pass the true-peak ceiling. 40 music exports: highest **-1.2 dBTP** (`music/combat_alert.wav`); 25 sound exports: highest **-3.7 dBTP** (`sfx/combat_mix.wav`).
Raw per-file readings are in `build/audio-rebalance/export-loudness.json` and `.log`.

The requested `music_render`, `combat_music_check`, `sound_render`,
`soundscape_check`, `live_audio_check` and `mix_loudness_check` all passed, as did
`listen.py` and `analyze_live_audio.py --check`. The encounter comparisons account
for the incoming rain/shrine gain when comparing those windows with trimmed day
piano; their authored margins and the absolute true-peak ceiling remain checked.

| Production capture | Seconds | LUFS-I | True peak dBTP | Pre-limiter overloads |
|---|---:|---:|---:|---:|
| field | 600 | -25.9 | -3.5 | 0 |
| engaged | 40 | -20.9 | -3.1 | 0 |
| low_hp | 40 | -21.2 | -4.0 | 0 |
| scenario | 180 | -22.5 | -1.8 | 0 |

Minimum 100 ms danger-cue/music and cue/all-background margins are **7.05 / 7.04 dB** (requirement 6 dB). Scenario footsteps stay at least **1.42 dB**
above rain/fire. Engaged/last-heart music occupancy above -40 dBFS in 100 ms
windows is **45.50% / 40.25%**. The clear field retains **72 strikes in ten minutes (7.2/min)**. All four full captures have zero clipped PCM samples.

Evidence: `build/listen/LEVELS.md`, `levels.json`, and `index.html`;
`build/audio-rebalance/live-final/` contains WAVs, frame/event CSVs, `metrics.json`,
`loudness.json` and raw meter summaries. Final audio assertion logs are under
`build/audio-rebalance/checks/`; original listening WAVs/meters remain in
`build/audio-rebalance/before/`.

## Round 65 loudness and combat identity (2026-10-11)

The published reference is [Sony ASWG-R001 v1.10, August 2013](https://gameaudiopodcast.com/ASWG-R001.pdf),
recommendations 4, 5, 7, 9 and 10: home-platform **-24 ±2 LKFS**, portable **-18 ±2 LKFS**,
true peaks no higher than **-1 dBTP**, and measurement of the complete mix rather than
individual stems. LKFS and LUFS are the same units. The document explicitly revised its
previous -23 target to -24. [ITU-T H.872 (2024)](https://www.itu.int/epublications/publication/itu-t-h-872-2024-10-safe-listening-for-video-gameplay-and-esports)
also distinguishes home/portable playback levels. These are published engineering
references, not a measurement of Nintendo's soundtrack.

Our dialogue-free moving exploration target is **-26 to -22 LUFS integrated**; engaged
and last-heart combat should be louder, with every measured full mix below **-1 dBTP**
and no pre-limiter overloads. Default master remains 0.8 and export gain remains 1.0.
Exploration note selection, velocities, rests and density stay sparse. Captures use
`live_audio_scenario` with the current production event dispatcher, sequencer, spatial
filters, cue ducking, ambient preparation and mixer; no per-export normalization.
FFmpeg `ebur128=peak=true` supplies gated BS.1770 integrated loudness and oversampled true
peaks. The 180-second varied scenario, 600-second clear field and 40-second combat-tier
captures are regression samples, **not the reference's recommended 30-minute gameplay audit**.

Exploration gain is **+8.7 dB** over round 61, with **+2 dB** for combat and
resolved danger cues. The non-low-health cue sidechain floor is now **0.19** rather
than 0.25; last-heart retains 0.16. Cue attacks still duck existing and newly struck
voices in the same mixer block and recover over 240 ms. No audio sample is normalized
or compressed for export. All **40 music exports** pass the true-peak ceiling; the
largest is **-1.3 dBTP** in the ten-minute biome reel. All **25 sound exports**
also stay below the ceiling (highest **-2.4 dBTP**, `field_piano.wav`).
The authored encounter RMS
window moves by the intentional 2 dB combat gain; its width and absolute peak guards
remain. Full-mix LUFS and cue audibility have separate checks.

Measured stereo full mixes at fixed master 0.8/export 1.0:

| Capture | Seconds | Before LUFS-I | After LUFS-I | Before dBTP | After dBTP |
|---|---:|---:|---:|---:|---:|
| Clear moving field/forest | 600 | -35.7 | -26.0 | -11.8 | -3.5 |
| Engaged combat | 40 | -24.0 | -22.1 | -6.4 | -4.4 |
| Last-heart combat | 40 | -24.2 | -22.2 | -6.4 | -4.4 |
| Rain/fire/wildlife/combat/shelter scenario | 180 | -26.8 | -24.3 | -5.6 | -4.1 |

The field piano stem's whole-capture RMS rises **-40.50 → -31.80 dBFS**.
The live field capture retains **72 notes in ten minutes (7.2/min)** before and after;
its rest and phrase sequence is unchanged. This is a gain adjustment, not added density.
Every full capture has **zero pre-limiter overloads and zero clipped PCM samples**.
The minimum 100 ms danger-cue/music ratio is **7.05 dB**, above the retained 6 dB
requirement; cue/all-background is **7.04 dB** minimum. Engaged/last-heart music
occupancy above -40 dBFS in 100 ms windows is **42.00% / 31.75%**.

Evidence is in `build/round65/before/audio/` and `build/round65/after/audio/`:
WAVs, per-frame stems and events, `metrics.json`, `loudness.json` and raw meter summaries.
`build/round65/after/music-loudness.json` meters all 40 music exports. Short scenario
phase readings are also retained, including quieter rain-walking passages; the moving
600-second field capture is the representative exploration target measurement.

Combat now has an original repeated-note pickup **A4 A4 / C5 ... G#4**, on eighth steps
**0, 1, 4, 10** at the retained 152 BPM. The leading note resolves into the next A statement.
Bars 1, 3 and 5 repeat it; the E-register answer, displaced B cell, wider ascending development
and two partial statements retain the identity across the eight-bar swell. Last-heart answers
transpose the complete cell up an octave, preserving its contour and rhythm, with the existing
muted attacks and 140 ms bass damping. Alert/engaged/last-heart retain **22/44/36 piano
strikes per eight bars**, and the tier hysteresis, next-beat changes and cue sidechain remain.
`combat_music_check` now verifies the recurring notes, rhythmic positions and complete-cell
last-heart transposition as well as the existing gameplay boundaries.

Reproduce the full-mix evidence (the capture script acquires the render lock itself):

```sh
python3 tools/live_audio_check.py build/round65/after/audio
python3 tools/analyze_live_audio.py build/round65/after/audio --check
python3 tools/mix_loudness_check.py build/round65/after/audio --check
```

## Round 51 sound and music (2026-10-09)

Frequent action sounds now combine compact **Kenney CC0 foley** with prebuilt noise,
resonant bodies and surface colour. There are five takes per grass/stone/snow/wood footstep,
swing, impact, shield block, bow release and splash. Existing direct and spatial gameplay
Sound handles resolve to those takes in the existing ambient update, before the frame mixer;
wood is selected from the current contact surface even though the legacy event dispatch groups
stone and wood. All 24 registered banks avoid consecutive repeated takes and vary playback
pitch by ±3.5% and gain by -6%/+4%. Creature calls, cloth, landing, climbing, arrow impacts
and parries also vary their prefiltered takes. Variation has its own RNG and preserves the
world/score RNG. Samples are never synthesized, sliced or filtered on a gameplay frame.

Aiming starts a short creak/leather draw sound once, and releasing or cancelling stops it.
The release combines a plucked string body, finger transient and leather. Moving through
grass adds a soft, varied brush between footfalls, with reduced gain while sneaking and no
brush while stationary or on bare surfaces. Splash now layers a filtered water transient,
low displacement body and seven separately timed, pitching droplets. Creature voices remain
original formant synthesis. Impacts keep body weight while reducing the old sharp peaks.

Combat piano and drums gain **4 dB** through one shared constant, including both offline
score and live exports. A prebuilt skin/low-body entry accent sounds at the combat hand-off;
entry still fades out the outgoing score over 0.3 seconds. Automatic field and landmark
motifs share a minimum start-to-start gap: **180 seconds** on their own, **90 seconds** on arriving at a landmark, once a visit. Authored title/wake/tower and
cues remain set pieces. A place found for the first time plays a short open-fifth chime (D, A, D, A rising), not the motif: it had been the motif itself, so a walk past three new places stated the theme three more times. The three-minute landmark walk now states the motif twice.
The seeded field reel happens to produce two statements 132.10 seconds apart. The focused
boundary check rejects a pending landmark statement at 44.99 s and accepts it at 45.00 s.

### Foley provenance and rebuild

Sources: [Kenney Impact Sounds 1.0](https://kenney.nl/assets/impact-sounds) and
[Kenney RPG Audio](https://kenney.nl/assets/rpg-audio), by Kenney / Kenney Vleugels.
Both downloaded archives include explicit **CC0** grants. Their original licence files are
`assets/audio/kenney-impact-sounds-LICENSE.txt` and `kenney-rpg-audio-LICENSE.txt`.
`foley-import.json` records the official archive URLs, archive/page/licence hashes,
per-member source hashes, output hashes and processing settings. The 41 mono 48 kHz PCM16
adaptations total **891,344 bytes (0.85 MiB)**; all new audio-directory files, including
provenance/licences/importer, remain below 1 MB. Filtering at 35 Hz / 9.5 kHz, conservative
silence trimming, short fades and RMS/peak limits happen offline. Recorded elements include
four footstep surfaces, punches, metal/wood contacts, knife movement, creaks and cloth.
Grass brush, water droplets and creature calls are synthesized, not claimed as recordings.

```sh
python3 assets/audio/import_foley.py --download
sloppy/bin/sloppy tools/sound_render.jo /tmp/sol3/sfx/after
sloppy/bin/sloppy tools/music_render.jo /tmp/sol3/sfx/music-after 75
```

The standard-library Python importer needs ffmpeg. Sources/evidence are cached at
`/tmp/sol3/sfx` (override `--source`); only compact outputs, licences and provenance ship.
The runtime keeps its layered synthesis fallback if a recorded file is missing. Output
and licence hashes were verified after import. Prebuilt variation payload is **14,892,664
bytes (14.20 MiB)** of resident stereo floats, separate from the small on-disk PCM sources.

### Fixed-gain listening reel and levels

`/tmp/sol3/sfx/comparison.wav` plays **before then after** for each category, with one second
between clips. Its cue index is `reel.txt`. Individual files are in `before/` and `after/`:
`footsteps_grass.wav`, `footsteps_stone.wav`, `footsteps_snow.wav`, `footsteps_wood.wav`,
`sword_combo.wav`, `shield_block.wav`, `bow.wav`, `bow_draw.wav`, `bow_release.wav`,
`splash.wav`, `grass_rustle.wav`, `creature_calls.wav`, `combat_music.wav`, `combat_mix.wav`
and `field_piano.wav`. Effects are 9 s, combat excerpts 30 s, field piano 180 s. Bow draw
and independent grass brush are silence before: those layers did not exist. The grass
footstep reel includes the new movement brush; the wood baseline faithfully uses stone.

All use the actual mixer with **master 0.8, music volume 1.0, gameplay event gains, export
gain 1.0**. Neither renderer normalizes clips. Baselines are compiled from master 5fe01e9
with the same offline event schedule. Float-render logs are `before-render.log` and
`after-render.log`; PCM16 levels and timing summaries are in `metrics.json` / `metrics.txt`.
No listening-capable analysis tool was available; the balance decisions below use transient,
RMS and headroom measurements. The reel is provided for a human tonal/listening pass.

Before → after peak / RMS in linear full scale, with RMS dBFS in parentheses:

- Grass footsteps: 0.093719 / 0.008060 (-41.87) → 0.081543 / 0.004933 (-46.14).
- Stone footsteps: 0.126221 / 0.005531 (-45.14) → 0.080597 / 0.004079 (-47.79).
- Snow footsteps: 0.140320 / 0.004665 (-46.62) → 0.143463 / 0.008346 (-41.57).
- Wood footsteps: 0.133514 / 0.005522 (-45.16) → 0.139252 / 0.007957 (-41.99).
- Sword combo: 0.865417 / 0.052163 (-25.65) → 0.455353 / 0.032419 (-29.78).
- Shield block: 0.390045 / 0.033023 (-29.62) → 0.248322 / 0.013173 (-37.61).
- Bow draw/release: 0.150146 / 0.017634 (-35.07) → 0.216492 / 0.016481 (-35.66).
- Splash: 0.302948 / 0.029675 (-30.55) → 0.187225 / 0.019446 (-34.22).
- Grass brush alone: absent → 0.030548 / 0.002089 (-53.60).
- Creature calls: 0.323090 / 0.053189 (-25.48) → 0.295410 / 0.044972 (-26.94).
- Combat music, 30 s: 0.159393 / 0.014795 (-36.60) → 0.335358 / 0.024818 (-32.10).
- Combat mix, 30 s: 0.871063 / 0.055295 (-25.15) → 0.525818 / 0.043960 (-27.14).
- Field piano: 0.356537 / 0.011201 (-39.01) in both reels.

Every clip has **zero clipped samples**. Excluding the entry, combat music RMS rises exactly
**4.00 dB** over seconds 2–30 (-36.49 → -32.49 dBFS). The 1.3–1.5 s entry window rises
**8.92 dB** (-28.99 → -20.07 dBFS), giving the transition a separate accent. The action mix
has more than 5.5 dB peak headroom while frequent impacts and calls retain variation.

### Verification and performance

All required checks passed: `feel_test` (25/25 behavioral checks, 100/100), `fauna_test`,
`element_test`, `element_check` (19 checks), `save_test`, `integration_test` (56/56),
`slot_check` and `opening_check` (12 uninterrupted wake-to-control checkpoints). Logs are
in `/tmp/sol3/sfx/checks/`; opening captures remain in `build/opening-check/`.
The sound renderer additionally checks all 24 variation banks with 24 selections each,
wood dispatch, gameplay RNG preservation, bow draw start/cancel and the 90 s / 180 s motif boundaries.

Three alternating before/after runs use the same camp preset, 960×540 X11 window and
480 frames, with `BOTW_CPU=1` and `BOTW_LOADTIME=1`, compiled baseline/current binaries and
the shared render lock held throughout. Median whole-game load is **2.98 → 3.06 s**
(+0.08 s, +2.7%); SFX initialization **0.35 → 0.43 s** (+0.08 s); piano initialization
**0.57 → 0.56 s**. Median of the six 240-frame CPU averages is **5.92 → 5.57 ms**.
This establishes no measured frame-cost regression, not a claimed CPU optimization: shared
machine and gameplay variance affect wall times. First-pair loads were 6.17/6.30 s from
unrelated graphics/cache work; both subsequent pairs were 2.98/3.06 and 2.98/3.04 s.
Raw logs are `before-perf-{1,2,3}.log` / `after-perf-{1,2,3}.log` under `/tmp/sol3/sfx/`.

In the offline action reels, the existing ambient update including variation has medians
about **0.003 ms** and p99 about **0.017 ms**, comparable to baseline. The complete music
renderer measured update+jingles medians **0.0009–0.0010 ms**, p99 **0.0023–0.0024 ms** on
the walking/combat routes. Occasional shared-machine scheduling pauses reached 19 ms;
those wall-time outliers are not attributed to audio computation. No new samples, DSP,
file reads or reverb occur on frames; the only additional mixer voices are a grass brush,
one short bow draw and the single combat-entry accent.

## Round 50 rendering and measurements (2026-10-09)

```sh
sloppy/bin/sloppy tools/music_render.jo /tmp/sol3/round50-after 180
flock /tmp/botw-render.lock env SLOPPY_SCREENSHOT=/tmp/sol3/round50-after/game.png \
  SLOPPY_FRAMES=300 BOTW_SKIP=1 BOTW_AT=-946,1883,0 BOTW_LOADTIME=1 BOTW_CPU=1 \
  sloppy/bin/sloppy game/main.jo
```

The renderer opens no playback device. It exports all eight exploration moods, nine cues,
40 seconds of combat plus release, and the JotW comparison. It also runs the real sequencer,
cue queue and 800-frame mixer blocks at 60 Hz, exporting a three-minute landmark walk,
a landmark walk without discovery cues, a standing-still excerpt, live combat and context
hand-offs. The score/mix pairs use identical score randomness; ambience has a separate
seed solely in the offline harness so bird scheduling cannot change the compared piano.
All exports are at music volume 1 and master 1, with gameplay gains/pans, without loudness
normalization. The default game's master 0.8 lowers every level by another 1.94 dB.

The walk is **score simulation, not a terrain/collision walk**: linear movement from the
Resurrection mouth at 0s through the fire at 30s, temple at 60s, tower at 120s and abbey at
175s. It holds `field_day` throughout to isolate identity, with discoveries at 60/120/175s.
The separate `contexts` excerpt changes day -> rain (20s) -> shrine (40s) -> combat (60s) ->
shrine/victory (85s) -> day (105s), ending at 125s. CSV timelines accompany every live export.

(History: the table below is round 50's measurement; the motif and discovery rules have since
changed as described above, and the current walk states the motif twice in three minutes.)
Before is the merged sparse score at `3c0e19f`, using the same current pp/mf/ff recordings,
route, discoveries, master, gains and ambience inputs. Its copied sources and baseline live
harness are retained in `/tmp/sol3/round50-before/`. These compare this round's scheduler/mix
changes, without reverting the sample bank. Silence is audio RMS below -60 dBFS in 100 ms
windows; it includes the release tails and is not an estimate from phrase spans.

| excerpt | piano notes/min before -> after | motif statements before -> after | silence % before -> after | RMS dBFS before -> after | raw peak before -> after |
|---|---|---|---|---|---|
| field day, 180s | 10.0 -> 9.7 | 1 -> 2 | 68.8 -> 65.7 | -40.84 -> -38.33 | 0.217450 -> 0.300184 |
| landmark walk with discoveries, 180s | 16.0 -> 15.0 | 1 -> 5 | 57.8 -> 62.7 | -37.27 -> -36.47 | 0.361221 -> 0.334908 |
| same walk with ambience | 16.0 -> 15.0 | 1 -> 5 | 0.0 -> 0.0 | -35.63 -> -35.23 | 0.369429 -> 0.338376 |
| combat, 40s + release | 183.0 -> 105.0 | — | 6.2 -> 48.4 | -28.40 -> -35.51 | 0.293233 -> 0.199286 |
| standing still, 180s | 4.0 -> 4.0 | 0 -> 1 | 85.2 -> 81.9 | -45.19 -> -41.73 | 0.187516 -> 0.270153 |

The landmark-only walk has 29 notes (9.7/min), three motif statements, 65.9% silence,
-37.86 dBFS RMS and peak 0.400768. The context excerpt has 70 notes (33.6/min), one motif,
48.2% silence, -34.15 dBFS RMS and peak 0.645921; with ambience it has 0% silence,
-31.91 dBFS RMS and peak 0.645699. Its notes/min includes 25 seconds of battle plus victory.
The 50-second live combat excerpt measures 104.4 notes/min, 37.0% silence, -34.51 dBFS RMS,
peak 0.199286 and at most six simultaneous voices, versus 59 before.

All exports have **zero clipping and gain 1**. The largest peak remains the unchanged alert
cue, 0.711312. PCM16 files were independently checked against the raw logs; silence can
shift by 0.1 percentage point after quantization. Live peaks stay below the mixer's minimum
soft-limited value, tanh(1), so the live exports never invoke its limiter either.

Listen at unchanged playback volume:

- `/tmp/sol3/round50-before/combat.wav` and `/tmp/sol3/round50-after/combat.wav`: matched 40s battle/release.
- `/tmp/sol3/round50-after/field_day_walk.wav` and `field_day_walk_mix.wav`: three-minute route, score and actual ambience mix; matching before files share the same names.
- `/tmp/sol3/round50-after/landmarks.wav`: same route without discovery cues.
- `/tmp/sol3/round50-after/contexts.wav` and `contexts_mix.wav`: weather, shrine, combat, victory and exploration hand-offs.
- `/tmp/sol3/round50-after/cue_discovery.wav`: the changed discovery statement.

Full raw/PCM metrics are `/tmp/sol3/round50-metrics.json`, with readable results in
`round50-metrics.txt`; render logs are `render.log` (after) and `render-live.log` (before).
These measurements establish density, headroom and mix balance; musical preference needs
listening by the user.

## Previous sparse-score revision measurements

### Earlier comparison against the original dense score

```sh
sloppy/bin/sloppy tools/music_render.jo                    # /tmp/botw_music, 75s moods
sloppy/bin/sloppy tools/music_render.jo /tmp/sol3 180        # 3-minute moods + comparison
flock /tmp/botw-render.lock env SLOPPY_SCREENSHOT=/tmp/sol3/x.png SLOPPY_FRAMES=60 \
  BOTW_SKIP=1 BOTW_LOADTIME=1 BOTW_CPU=1 sloppy/bin/sloppy game/main.jo
```

The renderer exports every mood and all nine cues, combat, a 180-second field excerpt (when
mood length differs), and a 180-second JotW-style reference. It uses gameplay layer weights,
voice gains and pans, before master-volume scaling and ambience. Field/cue gain was corrected
from the old renderer's blanket 0.55 to gameplay's 0.8; combat uses its own 0.55/0.5 gains and
drum pans. Cue exports leave twelve seconds after the final note for releases. Raw peak, RMS,
100 ms audio silence below -60 dBFS, export gain and clipping are printed. No new export needs
normalization; all have zero clipped raw samples.

The comparison below uses 180-second, seed-7 exploration renders. Before is master `64a6e53`
with its original short pp/mf bank restored in `/tmp/sol3/baseline-bank`, but rendered at the
same gameplay voice gains; old pad gains were also matched to gameplay. The old field panning
is centred in that offline renderer; the new renderer includes its quiet pitch-based pan.
Silence here is measured on exported PCM in 100 ms windows below -60 dBFS, with any export
normalization undone. This replaces the old phrase-span estimate, which counted pad-filled
rests as silence. Longer tails can reduce silence percentage despite fewer attacks.

| mood | notes/min before -> after | audio silence % before -> after | raw peak before -> after |
|---|---|---|---|
| field day | 31.3 -> 10.0 | 65.9 -> 68.8 | 0.538 -> 0.217 |
| golden | 29.0 -> 8.3 | 67.4 -> 64.9 | 0.569 -> 0.211 |
| night | 33.7 -> 6.7 | 54.6 -> 71.7 | 0.523 -> 0.168 |
| forest | 36.0 -> 8.3 | 56.3 -> 64.6 | 0.536 -> 0.235 |
| snow | 31.0 -> 6.7 | 57.4 -> 74.7 | 0.545 -> 0.282 |
| ruins | 28.3 -> 6.7 | 3.2 -> 71.4 | 0.628 -> 0.187 |
| shrine | 25.7 -> 6.7 | 4.8 -> 77.6 | 0.560 -> 0.159 |
| rain (new) | — -> 6.7 | — -> 73.3 | — -> 0.174 |

The highest raw peak across the exports falls from **0.902486** (old tower) to **0.711312**
(alert with the ff blend); no samples clip before or after. Combat rises from 169.5 to 183.0
piano notes/min while its raw peak falls from 0.464435 to 0.293233. Title peak falls from
0.774544 to 0.642668; tower from 0.902486 to 0.668821. Cue/combat silence percentages are not
directly comparable because the new exports include longer release windows.

For listening, all current three-minute moods/cues are `/tmp/sol3/*.wav`, and the usual short
exports are `/tmp/botw_music/*.wav`. Compare these at unchanged playback volume:

- `/tmp/sol3/field_day.wav`: 30 notes / 180 seconds, 10.0 notes/min, 68.8% audio silence.
- `/tmp/sol3/jotw_reference_180.wav`: all four JotW figures in rotation, A4 root, its exact day
  gaps and 22-41 second waits; 25 notes, 8.3 notes/min, 76.1% silence, peak 0.188654. This uses
  our pp bank at velocity 0.35 and the same 0.8 voice gain, to compare phrasing; it does not
  claim to reproduce JotW's source-bank loudness or its complete context scheduler.
- `/tmp/sol3/before-matched/field_day.wav`: original score/bank at gameplay gain, 180 seconds.
- `/tmp/sol3/cue_title.wav`, `/tmp/sol3/cue_tower.wav`, `/tmp/sol3/combat.wav`: changed set pieces.

Full audio statistics are `/tmp/sol3/metrics.json`, with raw render logs in
`after-render.log` and `before-matched-render.log`. Tone and musical preference still require
listening; these measurements establish density, release length and headroom.

## Memory, loading and frame cost

Round 50 adds **6,289,920 bytes (6.00 MiB)** of short combat samples, for total resident piano
payload **211,921,848 bytes (202.10 MiB)**. The 300-frame game check passed with `BOTW_CPU=1`: load
was 3.05 s, piano initialization 0.58 s, average CPU frame 6.65 ms. Music did not appear in
the six largest costs of any logged long frame or the ten largest average costs.

The live route/context/stationary/combat runs measured update+jingles wall-time medians
0.0009-0.0011 ms and p99 0.0018-0.0037 ms. Shared-machine wall-clock maxima reached 3.11 ms;
a Linux `CLOCK_THREAD_CPUTIME_ID` harness measured medians 0.0026-0.0027 ms, p99
0.0156-0.0159 ms and max **0.0283 ms**, including timer/bookkeeping overhead. Its raw log is
`/tmp/sol3/round50-cpu.log`; it separates work time from scheduling interruptions. No samples,
drums or reverb are generated by `music_update`; location checks run at 1 Hz and active
voice envelope work is bounded by the currently ringing score voices. The focused harness
`/tmp/sol3/round50-check.jo` verifies all four motif variants, cooldown, 44 strikes/89 rest
steps per combat round, actual active-voice fading, absence of outgoing strikes during
hand-off, the two-note response and audible combat entry within 317 ms.

Earlier sample-bank measurements follow for history:


Resident stereo float piano sample payload grows from **104,832,000 bytes (99.98 MiB)** to
**205,631,928 bytes (196.11 MiB)**. Removing the five pads frees **28,416,000 bytes (27.10 MiB)**;
the net sustained music payload increase is about 69 MiB. Prebuilding the two short drums
adds about 0.25 MiB. Isolated bank-init processes measured maximum RSS of 164,180 -> 305,648
KiB (160.33 -> 298.48 MiB), including runtime, compilation and temporary reverb buffers;
initialization in those processes took 1.481 -> 2.830 s on this shared machine.

The requested 60-frame game check passed and produced `/tmp/sol3/x.png`. Its `BOTW_LOADTIME=1`
piano initialization was **0.31 -> 0.60 s**, while the former **1.30 s** pad build disappears.
Whole-game load was 8.80 -> 4.28 s; GPU/cache/load variation contributes to that difference.
A 240-frame tower-rise check also passed (`/tmp/sol3/tower.png`): piano initialization was
1.14 s in that run, full load 7.13 s. Instrumented `music_update` cost was median **0.0011 ms**,
p99 **0.0146 ms**, max **0.0226 ms**. `BOTW_CPU=1` long frames were attributed to rendering
and culling rather than music.

An isolated harness ran the real sequencer, cue updates and 800-frame mixer blocks at 60 Hz
through 180 s each of field/shrine, combat and all three long cues. With physical audio-device
opening excluded (`SLOPPY_NO_AUDIO=1`), update+jingles max was **0.0266 ms**, and mixer max
**0.7803 ms**; tower reached 70 voices. Its first-use 23-41 ms pause with the device enabled
was ALSA opening, already done during ambience loading in the game. There is no on-frame pad
or drum generation. Raw timing logs are `profile-no-audio.log` and `tower-game.log` in
`/tmp/sol3/`.

## Ambience

Wind, rain, crickets, birds, water, fire, hollow wind in the ruins and the ambient shrine hum
remain in `sfx.jo`; the spaces between figures leave them audible. Sound effects take the room
they are heard in: in the cave, five close echo taps (30-215 ms); in a shrine chamber, the same
taps spread over 60-430 ms; none in the open. Each tap varies a little in time and pitch so it
reads as a room, not a comb. Exploration piano gain
is now 1.13003 instead of 0.8 (**+3 dB**); independent cues retain their existing gain and
headroom. A note activity envelope rises at rate 5, holds through each note's first four
seconds (0.35 seconds for battle stabs), and recovers at rate 0.7. It reduces weather/world
beds by up to **3 dB** while the piano speaks, including the shrine hum. Muting music
disables this reduction. Nearby fire and action effects keep their own spatial levels.

The live walk's ambience-only difference measures -41.27 dBFS RMS, against music at -36.47
dBFS. In 100 ms windows where the piano exceeds -45 dBFS, median piano/ambience ratio rises
from +5.93 to +9.81 dB. Rain remains much stronger than clear wind: in the 20-40s rain
segment, ambience measures -28.66 dBFS and piano -39.54 dBFS averaged over the rests. The
strongest ten piano windows range from -2.6 to +8.0 dB relative to the rain. This preserves
weather presence while giving new strikes room; it does not claim the quiet decays will
remain prominent in heavy rain. Monsters' grunts and cries
and crows' caws retain their formant-based voices.


## Round 54 spatial colour, night cues and route checks (2026-10-10)

Tower activation chooses a quieter arrangement when `env.night > 0.5`: four low
pulses instead of twelve, two-note rising chords, and the seven-note motif one octave
lower at velocity 0.34. The night Spirit Orb ceremony uses the same rising intervals
one octave lower, a three-note open chord and velocities 0.26–0.32. Ordinary shrine
figures smoothly lose another 25% of strike velocity as night approaches. These use the
existing pp/mf piano banks and add no recorded note or pad payload.

Two short, seamless wind/rain texture loops now follow the **same `env.gust` that
moves trees and slants rain**, with eased gains. Forest shelter, roofs, indoor suppression
and the existing piano activity ducking also apply to these layers. The old snow-only
wall-clock gust oscillator is removed, making weather comparisons reproducible.

### Spatial filtering and load budget

All 22 handles currently passed to `sfx_at`, including shrine doors, machinery, fire,
Guardian shots and the creature/action variation banks, have prebuilt distance and
obstruction colours (67 resolved takes). A two-pole 3.5 kHz low-pass precedes 2:1
resampling for distant takes; a two-pole 950 Hz low-pass precedes 4:1 resampling for
wall takes. They retain stereo. Playback pitch is multiplied by 0.5/0.25 to preserve
the original duration and pitch; room echoes retain the same filtered handle/rate.
There is no peak renormalization after filtering. Clear effects beyond the larger of
6 metres or 25% of their authored range receive the distance colour. A blocked ray
receives the wall colour plus the existing 0.22 volume multiplier. This is a cheap,
discrete colour choice per event, not a moving-source propagation simulation; rays
still test colliders rather than terrain.

Spatial dispatch resolves a non-repeating take **before** selecting its colour.
The subsequent ambient variation pass cannot turn it back into an unfiltered take.
Direct handles keep their existing variation routing. No samples are allocated or
filtered during gameplay. `sound_render` tests actual near/far/blocked rays with a
wall collider, post-dispatch variation, echoed playback rates and duration retention,
as well as 24-bank non-repetition and wood/bow/motif boundaries.

The spatial copies occupy **13,074,520 bytes (12.47 MiB)**, versus approximately 33.25 MiB
if both colours retained 48 kHz stereo. The two gust loops add **1,536,000 bytes
(1.46 MiB)**. Richer creature takes increase the existing take payload from
14,892,664 to 15,418,344 bytes. A render-run spatial build took **0.107 s**.
Five alternating isolated native startup measurements, with audio-device opening
disabled, measured median SFX initialization **0.785 -> 1.107 s (+0.322 s)** and
median maximum RSS **57,512 -> 73,492 KiB (+15.61 MiB)**. This includes the gusts
and new creature design as well as the filters. Raw samples and temporary/runtime
allocation are distinct: RSS is not a measurement of sample payload alone.
Logs: `build/r54/load-profiles.log`; whole-game after-load: `build/r54/load-after.log`.

### Creature recordings and scope

No recording assets were imported in this revision: the assigned write scope is
`game/sfx.jo`, `game/music.jo`, this document and the two audio render tools, excluding
new WAVs and a recording import manifest. The search did find prospective CC0
mouth-recorded packs, including [16 Monster Growls by StarNinjas](https://opengameart.org/content/16-monster-growls)
and [Boar by fvcalderan](https://opengameart.org/content/boar-0), described by its author as a voice
performance with EQ. These are candidates for a separate asset/provenance pass,
not licensed recordings shipped here or verified recordings of actual wild boars.
Kenney's imported packs provide action foley, not this creature-voice replacement.

The permitted synthesis fallback broadens creature formants, uses substantially more
filtered turbulent breath, varies correlated pitch drift and individual glottal pulse
strength, and reduces bright upper resonance/peak level. Each grunt/notice bank now
contains four independently generated duration/pitch/vowel/breath performances, rather
than four EQ copies of one performance. Calls retain the isolated variation RNG and
non-repetition rules. **Boars currently have no sound event dispatch in `wildlife.jo`:**
only crows feed `wild_calls`, which `main.jo` routes to `sfx.caw`. The offline
`creature_calls.wav` includes lower-pitched grunt auditions, but this revision does
not claim to add boar vocals to gameplay; that would require changes outside scope.

### Reproduction and route coverage

Create the output parents explicitly: Sloppy's `mkdir` is not recursive. Both WAV
writers now assert success so a failed export cannot silently report a usable WAV.
All exports use gameplay master **0.8**, export gain **1.0**, and no normalization.
The old `music_render` master of 1.0 has been corrected, including its manual score
and drum buffers, so comparisons against `sound_render` retain the actual mix.

```sh
mkdir -p /tmp/sol3/r54/sfx /tmp/sol3/r54/music
flock /tmp/botw-render.lock sloppy/bin/sloppy tools/sound_render.jo /tmp/sol3/r54/sfx
flock /tmp/botw-render.lock sloppy/bin/sloppy tools/music_render.jo /tmp/sol3/r54/music 75
```

The paired `biome_route_600.wav` / `biome_route_600_mix.wav` run the real score,
ambience updates and mixer for ten minutes, across field, forest, snow, ruins and
shrine, then repeat the outdoor biomes with forest rain and a night field ending.
This prescribed straight-line audio-state itinerary does not assert physical walking
reachability. CSV timelines record every score strike, phrase/motif count and mood
change. Both runs produced **71 notes (7.1/min), six motif statements**, and a
**93.167 s** minimum motif start gap. Accepted landmark visits in
Temple/tower/fire/mouth/abbey order were **[2, 1, 3, 2, 2]**. Score update+jingles
p99 stayed below **0.003 ms** in those runs; maximum active voices were 10 dry / 20
with ambience. Dedicated checks reject lingering/1.29-radius excursions, accept
1.31-radius re-entry, reject a repeat at 179.99 seconds, accept it at 180, and
suppress outdoor landmark requests inside a shrine. Existing 90/180-second motif
boundary checks remain in `sound_render`.

The matched spatial impact auditions confirm colour independently of gain: in the
first 375 ms impact window, normalized spectral energy above 1 kHz was **0.279% nearby,
0.179% distant, 0.029% behind the wall**. Fixed-gain nine-second reel peaks were
**-9.33 / -17.02 / -30.51 dBFS**, respectively. These are different spectra as well
as the existing distance/obstruction volume attenuation.


### Fixed-gain mix levels and masking flags

Measured from the exported stereo PCM16/48 kHz WAVs at master 0.8/export 1.0.
Peak/RMS are dBFS. Loudness uses FFmpeg's gated, K-weighted `ebur128` integrated
LUFS; it omits sufficiently quiet rests, so it is not interchangeable with whole-
segment RMS. The shrine-return segment includes the authored victory stinger.
No exported reel clipped. Raw measurements: `build/r54/levels.json` and
`build/r54/levels.log`; float pre-export checks: `sound-final.log` / `music-final.log`.

| Context (actual score + ambience) | Peak dBFS | RMS dBFS | LUFS-I |
|---|---:|---:|---:|
| Clear field (0–20 s) | -15.84 | -38.24 | -34.8 |
| Full rain (20–40 s) | -15.06 | -30.26 | -25.6 |
| Shrine (40–60 s) | -20.04 | -40.94 | -39.1 |
| Combat, ambience (60–85 s) | -9.12 | -31.83 | -29.0 |
| Victory/shrine return (85–105 s) | -5.74 | -30.28 | -24.1 |
| Clear field return (105–125 s) | -20.06 | -41.41 | -39.0 |
| Forest, long route | -14.30 | -38.51 | -33.0 |
| Snow, long route | -17.43 | -35.87 | -35.4 |
| Ruins, long route | -14.35 | -37.98 | -35.8 |
| Shrine, long route | -13.35 | -37.94 | -35.4 |
| Forest rain, long route | -15.67 | -33.11 | -28.5 |
| Night field, long route | -18.16 | -38.26 | -34.9 |

To separate score from ambience, subtract the identically seeded dry WAV from its
mixed pair. Measure stereo energy in 100 ms windows, considering piano active above
-45 dBFS RMS. This is a **masking proxy**, not a listening verdict or a spectral
masking model. Clear field and shrine median piano/ambience ratios are **+9.67 and
+10.24 dB**, with no below-bed active windows in the short contexts. Outdoor battle
score is **+16.31 dB** over the ambience alone.

**Flags:** full rain is **-3.75 dB** piano/ambience in the median active window;
**75.8%** of active windows fall below the rain, including a minimum **-2.34 dB**
among the ten strongest piano windows. Whole rain-bed RMS is -30.61 dBFS versus
piano -41.48 dBFS. Long-route forest rain is **-0.88 dB** median / **54.4%** below.
Snow wind is **+2.23 dB** median, but **35.6%** of active windows fall below the
bed; its ten strongest attacks stay at least **+3.58 dB** above it. Forest/ruins/night
have **15.7% / 19.7% / 5.6%** below-bed windows, mostly quieter tails; their ten
strongest windows remain above the beds. Existing weather gains and the 3 dB activity
ducking are retained, so these flags remain for the listening/mix review rather than
being presented as resolved by the new filtering or gust layers.

Follow-up (same day): the rain bed's gain went from 0.9 to 0.7 (-2.2 dB), and rain and wind
now duck about 6 dB while the piano speaks (the other beds keep 3 dB). Together that moves the
full-rain median piano/ambience ratio by roughly +5 dB, from -3.75 dB to above the bed; the
table above predates it.

| Authored audition | Peak dBFS | RMS dBFS | LUFS-I |
|---|---:|---:|---:|
| `tower.wav` | -5.43 | -25.44 | -20.0 |
| `tower_night.wav` | -15.97 | -34.77 | -29.5 |
| `orb.wav` | -5.96 | -31.68 | -20.8 |
| `orb_night.wav` | -13.61 | -37.99 | -28.6 |
| `combat_music.wav` | -9.16 | -32.10 | -29.1 |
| `combat_mix.wav` | -5.58 | -27.83 | -25.6 |
| `creature_calls.wav` | -13.33 | -32.52 | -29.0 |
| `spatial_near.wav` | -9.33 | -30.05 | -24.8 |
| `spatial_far.wav` | -17.02 | -37.76 | -32.5 |
| `spatial_wall.wav` | -30.51 | -51.47 | -46.3 |

The night tower's whole-reel RMS is **9.33 dB** lower than day, the night orb's
**6.31 dB** lower. Creature-call reel peak/RMS changed from **-10.59/-26.94** to
**-13.33/-32.52 dBFS**. Combat action effects raise the combined reel from
-32.10 to -27.83 dBFS RMS, with -5.58 dBFS peak headroom; transient action masking
is evaluated separately from the quiet ambience comparison above. The matched combat
action residual is **-29.88 dBFS RMS**. Piano/action median in active windows is
**+7.74 dB**, with **28.5%** below-action windows; even one of the ten strongest
piano windows is **-2.93 dB** below an overlapping action transient. This is a
foreground-hit/call overlap flag, not a sustained ambience-bed failure.

Listen to:

- `/tmp/sol3/r54/music/biome_route_600_mix.wav` (ten minutes, with matched dry WAV and CSV).
- `/tmp/sol3/r54/music/contexts_mix.wav` / `contexts.wav` (field/rain/shrine/combat hand-offs).
- `/tmp/sol3/r54/music/cue_tower_night.wav`, `cue_orb_night.wav`, `shrine_night.wav` (day counterparts beside them).
- `/tmp/sol3/r54/sfx/spatial_near.wav`, `spatial_far.wav`, `spatial_wall.wav` (same source/take sequence).
- `/tmp/sol3/r54/sfx/creature_calls.wav` and `/tmp/sol3/r54/before-sfx/creature_calls.wav`.
- `/tmp/sol3/r54/sfx/combat_mix.wav` / `combat_music.wav` (action overlap).

A reproducible loudness measurement for a context segment:

```sh
ffmpeg -hide_banner -nostats -ss 20 -t 20 -i /tmp/sol3/r54/music/contexts_mix.wav -af ebur128=peak=true -f null -
```


### Regression results

All requested tools passed on `sol3/work`: `sound_render`, `music_render`,
`feel_test`, `fauna_test`, `element_test`, `element_check`, `save_test`,
`integration_test`, `slot_check`, `input_check`, `shrine_route_check.sh`,
`shrine_exit_check.sh`, `passage_check.sh`, `opening_check.sh`, and
`late_story_check.sh`. `opening_check` captured all twelve ordered wake-to-control
milestones and passed its five production title approaches. All four shrine exit
cameras were outside their hoods; the passage run ended 4.8 metres from the mouth.
Logs live under `build/r54/checks/`; audio assertion/statistics logs are
`build/r54/sound-final.log` and `build/r54/music-final.log`.

A separate 60-frame native after-load run recorded **0.75 s SFX initialization,
0.80 s piano initialization and 9.34 s total load**, including a 1.00 s render
warm-up, on the shared machine. This total is not an isolated before/after game-load
comparison; use the alternating SFX startup measurements above to attribute the
new audio cost. Every game render used `/tmp/botw-render.lock`; the opening script
acquires that lock itself. No on-screen text or files outside the five assigned
tracked paths changed.

**Round 55 cue levels.** The victory stinger and the Spirit Orb cue now play at cue volume
0.5/0.55 (was 0.8) with softer chord velocities: the contexts reel's shrine-return peak falls
from -5.7 dBFS to about -11 dBFS at master 0.8, near the exploration bed's -16 to -20 dBFS
peaks instead of 10-15 dB over them. The title and tower set pieces keep their full gain.
