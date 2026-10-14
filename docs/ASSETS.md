# Asset sources and preparation

## University of Iowa piano

The piano is the [University of Iowa Musical Instrument Samples Steinway & Sons model B](https://theremin.music.uiowa.edu/MISpiano.html), recorded in 2001 by Evan Mazunik and Michael Cash. The collection is created by Lawrence Fritts and the University of Iowa Electronic Music Studios. The [MIS permission page](https://theremin.music.uiowa.edu/MIS.html) states that the recordings “may be downloaded and used for any projects, without restrictions.” This is the library's permission, not a Creative Commons license. Verified 2026-10-13.

Sources are individual `Piano.{pp,mf,ff}.<note>.aiff` files from `https://theremin.music.uiowa.edu/sound%20files/MIS/Piano_Other/piano/`. Raw AIFFs and cached source/permission pages live in **`assets/src/piano/`**, excluded by `.gitignore`. For this extension that directory was created empty in this checkout. Downloaded audio is treated as untrusted input and decoded only through `tools/import_piano.py` using FFmpeg with file/pipe protocols; it is never executed or loaded as code.

The bank spans nominal MIDI 21–108 (A0–C8), at three-semitone spacing, with 30 keys in each of pp/mf/ff. Existing C2–C7 WAVs remain unchanged. Added slots are 21, 24, 27, 30, 33, 99, 102, 105 and 108 (27 WAVs): C1/Eb1/Gb1/A1 and Eb7/Gb7/A7/C8 in each dynamic, plus the lowest available recording. Iowa has no pp A0 or mf A0/Bb0: the lowest recordings are **pp Bb0, mf B0, ff Bb0** (the latter is delivered under the filename `Piano.ff.A0.aiff`). Also, its pp C1 file sounds approximately B0; the importer uses the verified **pp Db1** recording for that slot instead. The mf A7 and C8 files sound Ab7 and B7 respectively; their measured treble stretch is +43/+45 cents. `piano_recording_midi` and `piano_slot` select and pitch each layer against its actual recording. Verified top-octave tuning reaches +50 cents; the importer allows this natural treble stretch while keeping its 40-cent guard elsewhere. A0 mf alone would need a two-semitone shift; the authored score starts above this unavailable extreme. The production slot mapping covers every pitch from C1 through C8 within one nominal semitone, and **1.50 semitones including measured source tuning**.


| Dynamic | Added source recordings (actual pitches) |
|---|---|
| pp | Bb0, Db1, Eb1, Gb1, A1, Eb7, Gb7, A7, C8 |
| mf | B0, C1, Eb1, Gb1, A1, Eb7, Gb7, Ab7 (file A7), B7 (file C8) |
| ff | Bb0 (file A0), C1, Eb1, Gb1, A1, Eb7, Gb7, A7, C8 |

`assets/audio/piano-import.json` records per-source URLs, SHA-256 hashes, actual recording pitches, filtering, attacks, gains, tuning checks and output hashes. Extension import preserves existing WAVs only after verifying their recorded hashes. Added lows use a 15 Hz high-pass (existing keys retain 25 Hz); all use an 11 kHz low-pass, onset alignment, short fades, bounded RMS/peak gains, mono downmix and 48 kHz PCM16 WAV conversion. Dry tails are capped at eight seconds; game reverb retains a bounded two-second tail.

```sh
python3 tools/import_piano.py --download --only-missing
# Complete reimport, fetching all sources when needed:
python3 tools/import_piano.py --download
sloppy/bin/sloppy tools/piano_storage_check.jo
python3 tools/piano_import_check.py
```

Only the compact **mono PCM16 WAVs**, provenance and credits are committed, matching the existing pipeline. `tools/prepare_assets.sh` generates **`assets/prepared/piano-compact.bin`** locally (ignored by git): seven per-note-scaled PCM16 stereo banks plus four float cue records. Native playback reads that pack directly into final arrays; only active voice rings decode to floats. Weather/reverse derivatives are regenerated after either load path. `tools/prepared_assets_check.sh` compares prepared/generated banks including these derivatives.

The browser's default package carries the traced mono WAVs in gzip archives and generates the same PCM16 stereo banks during startup. `tools/web_package.py` now rejects stale traces missing any recording in the import manifest. The default pack selection is unchanged; its traced WAV inputs remain available for generation/fallback. Raw sources are never included in native or web packages.

## Piano extension memory evidence (2026-10-13)

Measured by release `tools/piano_storage_check.jo`; MB below means decimal bytes/1,000,000. Shared sample data is distinct from peak process RSS, which includes allocator retention and temporary construction/check arrays.

| Resident sample payload | Before | After |
|---|---:|---:|
| Seven scaled PCM16 stereo banks | 106.53 MB | 152.18 MB |
| Derived weather/reverse samples | 15.32 MB | 30.01 MB |
| Total piano payload | **121.85 MB** | **182.19 MB** |
| Storage-check peak process RSS (`/usr/bin/time -v`) | 182.15 MB / 173.71 MiB | 281.10 MB / 268.08 MiB |

The compact prepared file grows from 108.54 to 154.19 MB. The committed mono WAV inputs total 56.16 MB. Storage assertions bound base banks to 155 MB, derived weather to 32 MB, and all piano-pack sample data, including its unchanged 2.01 MB of float cues, to 190 MB (184.20 MB after extension). Each active voice still decodes only an 8,192-output-frame lookahead with a pitch-scaled float ring and interpolation guards (about 64–68 KiB per score voice); no full-bank float expansion occurs in play. Packed/expanded fractional-pitch windows agree within 0.000000001 through ring wraps and gain changes. Weather selection retains its original MIDI thresholds (≤42 / ≥81), and reverse remains the C6 recording after the lower bank extension.

The default web build passes its actual wasm first-frame trace and archive byte/hash verification: all **90** WAVs, **193** total packaged files, five gzip archives, **95.51 MB** compressed assets, largest archive **30.24 MB** (below the 100 MB per-file limit). The complete game CPU trace allocates 1,118.24 MB of wasm memory; this is not the piano's resident payload. No raw AIFF is packaged. Evidence lives in `build/piano-extension/` (`storage-before.txt`, `storage-after.txt`, `rss-*.txt`, `import-check.json`, `web-package-check.json`, `prepared-check.log`, `web-build.log`).
