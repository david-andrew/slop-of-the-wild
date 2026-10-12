# Music and sound evidence

Exploration uses sampled piano, open intervals and long rests, with no continuous
pad. The original F# A B E D plateau motif remains in discovery and set pieces.

## Field, alert and combat transitions

Enemy notice plays its short rising piano cue immediately, with an eight-second
retrigger cooldown. The field phrase stops scheduling new strikes and its
sounding notes fade over **0.30 s**. Combat then enters at 55% score gain, reaching
full gain over **0.113 s** (the 0.25 s full-range ramp). Every automated score gain
uses a **20 ms sample ramp baked by game code into each voice's private unplayed
samples**; interrupted ramps continue from their current gain, and outgoing handles
survive their final release. Sloppy 0.6.0's live mixer is the unmodified release. The
entry drum has a **4 ms attack / 25 ms terminal release**. Independent notice and
story cues retain their natural tails. The interrupted field phrase does not
finish its remaining melody; its already sounding notes receive the fade.

Combat begins in the sparse alert tier. Close threats or player strikes select
engaged music on the **next beat**, at **152 BPM**, without restarting the cell or
cutting notes. Engagement holds for four seconds after the last close threat.
When combat ends, the score fades over **0.90 s**. Defeated pursuers trigger the
victory cue; surviving pursuers beyond the combat radius count as escape and do
not trigger victory. Field gain recovers over **1.20 s** during the ensuing rest.

Escape leaves **seven seconds** after the combat fade before scheduling a new
field phrase. Victory waits for the longer of that rest or the remaining cue
tail plus **1.5 s of actual silence**. The fixed transition captures resume their
first field note **7.017 s** (escape) and **10.700 s** (victory) after the handoff;
ambient world sound remains free to continue throughout this musical rest.

`sloppy/bin/sloppy tools/music_transition_check.jo build/round89/music-after-clips`
exports both 35-second production-sequencer/mixer clips and frame traces. It
checks real pursuer survival, both combat tiers, the quiet gap, zero-ended drum
samples, and the mixer at 127/400/800/1600-sample block sizes. State-induced
sample-boundary gain steps must stay below **3 dB** above approximately -50 dBFS and absolute
boundary error below **0.0001** full scale; the current clips measure zero for
both. This isolates automation clicks from intentional note attacks and natural
waveform motion; it is not a loudness-normalization rule for successive phrases.

## Sloppy 0.6.0 verification (2026-10-12)

The eight 45 s listening contexts retain the existing LUFS targets: day **-24.6**, night **-25.1**,
rain **-26.0**, engaged **-22.0**, low health **-22.9**, shrine **-27.2**, title
**-20.4**, cave exit **-20.9**. Their worst true peak is **-3.3 dBTP**; the longer repeat/texture audits peak
at **-2.8 dBTP**. Sample ramps
at 127/400/800/1600-sample mixer blocks have maximum step **0.0001500** full scale;
the full transition captures retain zero automation-boundary discontinuity and
the same musical handoff times. The 60 Hz volume targets therefore remain smoothed.

The game-side soft-knee guard (knee 0.65, ceiling 0.84) remains on offline score
exports. Live integration captures instead exercise the release mixer, which uses
`tanh` only above full scale. They verify the reconstructed linear stem sum against
that actual mixer to 0.000001. The 600 s field mix measures **-24.0 LUFS / -1.3 dBTP**;
40 s engaged and low-health mixes measure **-21.2 / -3.6** and **-21.3 / -3.4**.
The 180 s rain/fire/wildlife/combat/shelter scenario also passes. The worst live
peak is **-1.3 dBTP**, below the **-1 dBTP** ceiling, without changing authored gains
or adding a master trim. Results remain in `build/sloppy060/listen/` and
`build/sloppy060/live-audio/`; reproduce with `tools/listen.py` and
`tools/live_audio_check.py`, then `tools/mix_loudness_check.py --check`.

The live cue analysis retains its raw onset metric and applies the unchanged
**6 dB** margin to the settled 100 ms cue body, beginning at **33.3 ms** (two
60 Hz rows, beyond the 20 ms ramp). At the engaged 13 s windup, the old patched
mixer and game-side ramp give **-2.68671 / -2.68675 dB** over the immediate onset:
a difference of only **0.000042 dB**. That older assertion also fails on master.
The settled body clears music by **11.62 dB** and all background by **11.60 dB**;
no cue or score gains change. Both windows remain in the CSV evidence.

## Previous music and sound pass (2026-10-12)

Field figures now occasionally add a quiet left-hand note or open fifth. Four
bass colours rotate without consecutive reuse for the same figure; their gains
are 0.30/0.23 of the normal piano strike. Independent, ordered rubato varies note
gaps without changing melody identity. The 20-minute field capture has **34
phrases / 133 melody notes**, with bass in **10 phrases**, all four colours, and
at most **7.77 s** per gesture. Authored rests remain **22–40 s**.

Both **20-minute production captures** pass the **180 s minimum melodic-repeat
interval**: field **186.20 s**, shrine **202.30 s**. Shrine has **27 phrases / 91
melody notes**. Identity ignores timing, velocity, bass, rolled dyads and glass;
partial/single-note figures and the initial shrine handoff count. The source
check also passes 20 minutes in all eight exploration/shrine contexts. These
measurements establish the three-minute rule, not a blind-listener score of 100.

The shrine hum moves **-45.4 → -29.4 LUFS-I**; hum plus room moves **-44.2 →
-29.4**. Sparse, finite inharmonic glass answers join the piano. Full shrine
mix is **-27.2 LUFS**, below day field's **-24.6**, with **-7.1 dBTP** headroom.
The Resurrection passage retains its quiet hum. [LISTEN](LISTEN.md) gives every
context's measured before/after values. The separate 600 s forest capture is
**-23.3 → -24.0 LUFS** after a 1 dB forest trim. All **65 music/SFX exports**
pass the true-peak ceiling; the highest is **-1.2 dBTP**.

Repeated creature encounters exposed identical boar/fox samples and a fixed crow
caw rhythm. Each animal identity now has four prebuilt articulations; crow takes
vary two/three caws, their gaps and pitch contours. Bonkoblin synthesis already
varied its envelope/formants and is retained. Spatial pitch jitter now uses the
audio RNG. All four species pass **12 encounters, four samples, zero adjacent
sample repeats**, plus independent pitch and source-duration variation. Spectra
retain low boar grunts, high fox contours, nasal crow harmonics and rough Bonkoblin
formants. These are synthesized voices; no perceptual realism claim is inferred
from spectral checks alone.

Combat retains the **152 BPM** cell, **8/8** changed source bars from the first
round to the second in every tier, **7/7** changed non-entry rendered spectra,
and a digitally silent whole-bar rest. Insects retain spectral variance
**12.6064**, dominant-line occupancy **5.56%**, and **60.56%** silent windows.

## Sources and reproduction

The 63 mono PCM16/48 kHz piano samples (pp/mf/ff, C2–C7) come from the University
of Iowa MIS Steinway Model B recordings. URLs, hashes and processing are in
`assets/audio/piano-import.json` and `tools/import_piano.py`; foley credits are
in [audio credits](../assets/audio/LICENSE.txt). Piano/reverb, glass and creature
takes are prepared at load, including lossless cache and spatial-filter paths.

Run `python3 tools/listen.py` for WAVs, spectra, repeat traces and meters in
`build/listen/`. Baseline evidence is in `build/music61-before/` and
`build/music61-before-creatures/`; targeted checks/exports are in
`build/music61-checks/` and `build/music61-tmp/`. See [LISTEN](LISTEN.md) for
commands and validation scope. [Music history](rounds/MUSIC_HISTORY.md) retains
earlier passes; this is a targeted audio pass, not a new whole-game evaluation.
