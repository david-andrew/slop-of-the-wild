# Listening clips

Run from the repository root with Python 3, FFmpeg and Sloppy:

```sh
python3 tools/listen.py
```

`build/listen/index.html` contains players and log-frequency spectrograms.
`LEVELS.md` / `levels.json` report BS.1770 integrated LUFS, RMS, sample peak and
oversampled true peak (`ffmpeg ebur128=peak=true`). No normalization: master
0.8, music 1.0, export 1.0. Eight context clips are 45 s; four shrine stems
separate hum, room, footsteps/echoes and piano/glass, with a combined bed stem.
Stems sum to the full shrine mix within **3 PCM counts**.

The script owns one render lock for the sequential current-fixture batch and a 300 s game-process timeout; **do not wrap
it in another flock**. Each timeline resets the production mixer, sequencer,
foley and RNGs (seed 70070). Legacy baseline binaries keep the individual-clip protocol. Ten gameplay/cue WAVs were checked byte-for-byte between individual and batch captures after the piano extension. Walking clips emit steps at 0–12 s and 21–33 s.
The long captures maintain movement inputs; the scenario is scripted audio
integration, not a claim of autonomous traversal.

## Sloppy 0.6.0 rerun (2026-10-12)

`build/sloppy060/listen/levels.json` retains the unchanged targets and new
production-sequencer exports. Day/night/rain/shrine/title/cave-exit values below
are unchanged; engaged is now **-22.0 LUFS / -3.9 dBTP**, and low health is
**-22.9 / -4.7**. The eight-clip worst remains **-3.3 dBTP**. Game-owned 20 ms
score ramps replace the removed library ramp; the export peak guard belongs to
the game. Cue audibility keeps both the raw onset and the settled body after
the 20 ms ramp; the body retains the 6 dB margin (see MUSIC for master parity).
Separate live-mixer scenarios measure a worst **-1.3 dBTP** with the
unmodified release mixer; see [MUSIC](MUSIC.md) for levels and scope.

## Previous music-pass levels (2026-10-12)

Fresh baseline at `bf6f56e` versus this music/sound pass; same fixed 45 s timelines.
Baseline combined bed is the unnormalized sum of isolated hum and room stems.
Full-mix loudness and isolated-bed loudness must not be conflated.

| Context / stem | Before LUFS-I | After LUFS-I | After dBTP |
|---|---:|---:|---:|
| Field day | -24.5 | -24.6 | -5.5 |
| Field night | -25.4 | -25.1 | -5.0 |
| Rain | -26.0 | -26.0 | -3.3 |
| Combat engaged | -21.9 | -21.9 | -3.1 |
| Low health | -22.8 | -22.8 | -4.0 |
| Shrine full mix | -27.9 | -27.2 | -7.1 |
| Title | -20.4 | -20.4 | -4.6 |
| Cave exit | -20.9 | -20.9 | -4.4 |
| Shrine hum | -45.4 | -29.4 | -23.5 |
| Shrine room | -50.4 | -50.4 | -34.8 |
| Shrine footsteps | -43.5 | -43.5 | -21.8 |
| Shrine piano/glass | -23.1 | -23.2 | -7.5 |
| Shrine combined bed | -44.2 | -29.4 | -22.2 |

The hum/bed target is **-30 to -28 LUFS**. Full shrine remains at least 1.5 dB
below day field; footstep peaks remain above the hum. Exploration retains its
-26.5 to -23 LUFS range, engaged -22.5 to -20, low health within 2.5 dB of engaged,
and title/cave exit above combat. **Every clip and audit must stay ≤-1 dBTP.**
The continuous shrine bed is included in encounter RMS limits by adding its
energy; score-only cue/tail checks retain their original margins.

The separate **600 s forest** production capture measures **-23.3 → -24.0 LUFS**
and **-1.7 → -1.9 dBTP**. Forest music is trimmed 1 dB to balance the new bass
voices. The final live scenario/engaged/low-health captures are **-23.0 / -21.1 /
-21.3 LUFS**, with zero pre-limiter overloads or clipped samples. All **65 music
and SFX exports** meet ≤-1 dBTP; the highest is **-1.2 dBTP** (combat alert).

## Texture and repeated encounters

`field_1200.wav` and `shrine_1200.wav` each cover **20 minutes**. Minimum repeated
melody intervals are **186.20 / 202.30 s**, passing **≥180 s**, with **34 / 27**
nonempty phrases and **133 / 91** melody notes. Ordered MIDI melody pitches are
the identity; timing, velocity and accompaniment cannot disguise a repeat.
The check includes partial/single-note phrases and shrine entry, requires at
least 24 phrases/80 notes, and limits phrase duration and bass occupancy.
Field/shrine long-mix loudness is **-28.9 / -27.1 LUFS**; long captures and their
phrase population differ from the fixed 45 s clips. There are still **10 / 5**
melody repeats across the full 20 minutes; no blind listening result is claimed.

`combat_120.wav` changes all seven comparable non-entry bar spectra at the next
round; source checks require **8/8** changed bars in all three tiers. The entry
bar is excluded from spectral comparison because of its fade/accent. The
fourth-round rest has a **zero PCM peak**. The clean-hit rest and clock continuity
also pass. `night_insects.wav`: variance **12.6064**, dominant 20 Hz line occupancy
**5.56%**, silence **60.56%** (thresholds ≥0.35 / ≤35% / ≥25%). FFTs use 4096 points,
12 kHz PCM and 250 ms Hann windows.

Four `creature_*.wav` clips and their CSVs/spectrograms cover 12 close repeated
encounters with the same individual/source and frozen gameplay RNG. Arrival
times are fixture inputs; **internal take duration**, sample and playback pitch
are measured independently. Before, boar/fox had one sample and 11 adjacent
repeats; crow varied filters but not its rhythm; all spatial pitch spans were
zero. After, each species uses **four samples / zero adjacent repeats**:

| Creature | Pitch span (ratio) | Source-duration span | Spectral centroid range | Mean adjacent spectral distance |
|---|---:|---:|---:|---:|
| Boar | 0.0827 | 108 ms | 92–106 Hz | 0.419 |
| Fox | 0.0827 | 96 ms | 957–1064 Hz | 0.606 |
| Crow | 0.0864 | 380 ms | 564–649 Hz | 0.821 |
| Bonkoblin | 0.0864 | 121 ms | 228–437 Hz | 0.780 |

Creature clip LUFS before → after: boar **-35.6 → -35.5**, fox **-26.0 → -25.8**,
crow **-30.3 → -30.8**, Bonkoblin **-30.9 → -30.9**. All retain ≥15.4 dB true-peak
headroom.

Spectral tests catch repetition, silence and wrong voice handles; they do not
replace listening. For perceptual review, play the full 20-minute captures at
fixed gain, mark recognisable returns without the CSV, then compare timestamps.

## Reproduce checks

Python capture scripts own their locks; standalone renderers take exactly one.
Use a checkout-local `TMPDIR` for compiler scratch. The new headless
`music_harmony_check` is its own line in `run_all_checks.sh`'s `cpu_checks` array.

```sh
mkdir -p build/music61-tmp build/music61-checks/music build/music61-checks/sfx
export TMPDIR="$PWD/build/music61-tmp"
python3 tools/listen.py
python3 tools/music_texture_check.py build/listen
sloppy/bin/sloppy tools/music_harmony_check.jo
flock /tmp/botw-render.lock sloppy/bin/sloppy tools/combat_music_check.jo
flock /tmp/botw-render.lock sloppy/bin/sloppy tools/soundscape_check.jo
flock /tmp/botw-render.lock sloppy/bin/sloppy tools/music_render.jo build/music61-checks/music 75
flock /tmp/botw-render.lock sloppy/bin/sloppy tools/sound_render.jo build/music61-checks/sfx
python3 tools/live_audio_check.py build/music61-live
python3 tools/analyze_live_audio.py build/music61-live --check
python3 tools/mix_loudness_check.py build/music61-live --check
```

Validated: `listen.py`, `music_texture_check`, `music_harmony_check`,
`combat_music_check`, `soundscape_check`, `music_render`, `sound_render`,
`fauna_test`, production `live_audio_check`, `analyze_live_audio --check`, and
`mix_loudness_check --check`. Evidence: `build/listen/`, `build/music61-checks/`,
`build/music61-tmp/`, `build/music61-live/`; baseline forest is in
`build/music61-live-before/`. The full whole-game runner was not rerun.
