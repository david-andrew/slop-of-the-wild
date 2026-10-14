#!/usr/bin/env python3
"""Import the Iowa Steinway pp/mf/ff bank. Requires Python 3, numpy and ffmpeg.

Run from any directory: python3 tools/import_piano.py [--download]
Sources stay in assets/src/piano; only compact WAVs and provenance are committed.
No game process or language toolchain is needed for this offline step.
"""
import argparse
import hashlib
import json
import subprocess
import urllib.request
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/src/piano"
OUTPUT = ROOT / "assets/audio"
PAGE = "https://theremin.music.uiowa.edu/MISpiano.html"
PERMISSION = "https://theremin.music.uiowa.edu/MIS.html"
BASE = "https://theremin.music.uiowa.edu/sound%20files/MIS/Piano_Other/piano/"
RATE = 48000  # MIX_RATE in sloppy/lib/game/audio.jo
KEYS = range(21, 109, 3)  # PIANO_LO .. PIANO_HI, PIANO_STEP = 3


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url, path):
    if not path.exists():
        with urllib.request.urlopen(url, timeout=90) as response:
            contents = response.read()
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(contents)
        tmp.replace(path)


def decode(path, filters=None):
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-protocol_whitelist", "file,pipe", "-i", str(path)]
    if filters:
        cmd += ["-af", filters]
    cmd += ["-ar", str(RATE), "-ac", "1", "-f", "f32le", "-"]
    return np.frombuffer(subprocess.check_output(cmd), dtype="<f4").copy()


def attack(data, max_onset_ms=2000):
    # 1 ms RMS windows, sustained for 3 ms: rejects individual room-noise spikes.
    block = RATE // 1000
    rms = np.sqrt(np.mean(data[:len(data) // block * block].reshape(-1, block)**2, axis=1))
    noise = float(np.percentile(rms[:50], 90))
    peak = float(rms.max())
    threshold = max(peak * .08, min(noise * 6, peak * .25))
    above = np.convolve((rms > threshold).astype(int), np.ones(3, dtype=int), "valid")
    candidates = np.flatnonzero(above == 3)
    if not len(candidates):
        raise ValueError("No sustained piano attack")
    onset = int(candidates[0])
    if onset > max_onset_ms:
        raise ValueError(f"Unexpected attack at {onset} ms; inspect the source")
    # Find the quiet edge before the strike, preserving the hammer's softer start.
    edge = max(min(noise * 2.5, peak * .08), peak * .015)
    quiet = np.flatnonzero(rms[max(0, onset - 40):onset] < edge)
    start_ms = max(0, onset - 40) + int(quiet[-1]) + 1 if len(quiet) else onset
    return max(0, (max(start_ms, onset - 4) - 1) * block), noise


def pitch_cents(data, midi):
    # A harmonic-sum FFT check catches mislabeled / multi-note excerpts.
    segment = data[int(.08 * RATE):int(.58 * RATE)]
    spectrum = abs(np.fft.rfft(segment * np.hanning(len(segment)), n=131072))
    expected = 440 * 2 ** ((midi - 69) / 12)
    cents = np.arange(-100, 101)
    frequencies = expected * 2 ** (cents / 1200)
    score = np.zeros(len(cents))
    for harmonic in range(1, 7):
        indices = np.rint(frequencies * harmonic * 131072 / RATE).astype(int)
        score += spectrum[np.minimum(indices, len(spectrum) - 1)] / harmonic
    return int(cents[np.argmax(score)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="fetch missing AIFFs and credit pages")
    parser.add_argument("--only-missing", action="store_true",
                        help="preserve verified WAVs/provenance and import only new bank keys")
    args = parser.parse_args()
    # Worktrees sometimes symlink the source cache into the main checkout.
    if SOURCE.parent.is_symlink() or SOURCE.is_symlink():
        raise SystemExit("Use a local assets/src directory, not a symlink to another checkout")
    SOURCE.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.download:
        for url in [PAGE, PERMISSION]:
            fetch(url, SOURCE / url.rsplit("/", 1)[1])
    previous = {}
    if args.only_missing:
        report = json.loads((OUTPUT / "piano-import.json").read_text())
        previous = {(e["dynamic"], e["midi"]): e for e in report["samples"]}
    entries = []
    for dynamic in ["pp", "mf", "ff"]:
        for midi in KEYS:
            # Iowa lacks pp A0 and mf A0/Bb0. The lowest slot uses the
            # first available recording, with per-layer pitch correction in game.
            recording_midi = {"pp": 22, "mf": 23, "ff": 22}[dynamic] if midi == 21 else midi
            if dynamic == "pp" and midi == 24:
                recording_midi = 25  # Iowa's pp C1 file actually sounds near B0.
            note = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"][recording_midi % 12] + str(recording_midi // 12 - 1)
            if dynamic == "ff" and midi == 21:
                note = "A0"
            # mf A7/C8 are mislabeled by one semitone, with normal positive
            # treble stretch relative to Ab7/B7. Keep the actual source names.
            if dynamic == "mf" and midi in (105, 108):
                recording_midi = midi - 1
            target = OUTPUT / f"piano-{dynamic}-{midi}.wav"
            if (dynamic, midi) in previous:
                entry = previous[(dynamic, midi)]
                if sha(target) != entry["output_sha256"]:
                    raise ValueError(f"{target}: does not match existing provenance")
                entries.append(entry)
                continue
            path = SOURCE / f"Piano.{dynamic}.{note}.aiff"
            if args.download:
                fetch(BASE + path.name, path)
            if not path.exists():
                raise SystemExit(f"Missing {path}; run with --download")
            # Measure attacks after removing DC/rumble; raw-file RMS can trigger early.
            highpass = 15 if midi < 36 else 25
            raw = decode(path, f"highpass=f={highpass},lowpass=f=11000")
            start, noise = attack(raw, 8000 if midi < 36 else 2000)
            duration = min(8.0 - max(0, midi - 36) / 20, len(raw) / RATE - start / RATE)
            fade = .8 if midi < 72 else .5
            filters = (f"atrim=start={start / RATE:.6f}:duration={duration:.6f},"
                       f"asetpts=PTS-STARTPTS,highpass=f={highpass},lowpass=f=11000,"
                       f"afade=t=in:d=0.001,afade=t=out:st={duration - fade:.6f}:d={fade}")
            data = decode(path, filters)
            tuning = pitch_cents(data, recording_midi)
            # The Steinway's top octave has genuine stretched tuning.
            # A7/C8 exceed the middle-register 40-cent guard; still reject a
            # wrong key (>= one semitone) instead of hiding source mistakes.
            tuning_limit = 50 if recording_midi >= 99 else 40
            if abs(tuning) > tuning_limit:
                raise ValueError(f"{path.name}: pitch {tuning:+} cents; inspect the note")
            # Normalize the first half-second RMS, retaining pp's gentler strike.
            # A peak cap keeps sparse chords safely below full scale before reverb.
            target_rms = {"pp": .028, "mf": .050, "ff": .070}[dynamic] * 2 ** (-(midi - 60) * .12 / 12)
            peak_cap = {"pp": .12, "mf": .21, "ff": .29}[dynamic]
            rms = float(np.sqrt(np.mean(data[:RATE // 2] ** 2)))
            gain = min(target_rms / rms, peak_cap / float(abs(data).max()))
            data *= gain
            pcm = np.round(data * 32767).astype("<i2")
            nonzero = np.flatnonzero(pcm)
            audible = np.flatnonzero(abs(data) >= float(abs(data).max()) * .01)
            blocks = data[:len(data) // 48 * 48].reshape(-1, 48)
            envelope = np.sqrt(np.mean(blocks ** 2, axis=1))
            musical_onset_ms = int(np.flatnonzero(envelope > envelope.max() * .08)[0])
            if (not len(nonzero) or nonzero[0] > RATE * .003 or audible[0] > RATE * .010
                    or musical_onset_ms > 10):
                raise ValueError(f"{path.name}: leading silence after import")
            temporary = target.with_suffix(".wav.tmp")
            with wave.open(str(temporary), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(RATE)
                wav.writeframes(pcm.tobytes())
            temporary.replace(target)
            entries.append({"midi": midi, "recording_midi": recording_midi, "note": note, "dynamic": dynamic,
                            "source_url": BASE + path.name, "source_sha256": sha(path),
                            "source_duration_seconds": len(raw) / RATE,
                            "output": target.name, "output_sha256": sha(target),
                            "output_bytes": target.stat().st_size,
                            "start_seconds": start / RATE, "duration_seconds": len(data) / RATE,
                            "filters": filters, "gain": gain, "peak": float(abs(data).max()),
                            "attack_rms": float(np.sqrt(np.mean(data[:RATE // 2] ** 2))),
                            "source_noise_rms": noise, "pitch_offset_cents": tuning,
                            "first_nonzero_ms": nonzero[0] * 1000 / RATE,
                            "musical_onset_ms": musical_onset_ms,
                            "first_minus_40db_ms": audible[0] * 1000 / RATE})
            print(f"{target.name}: {len(data) / RATE:.3f}s, peak {abs(data).max():.3f}, "
                  f"pitch {tuning:+} cents, onset {audible[0] * 1000 / RATE:.2f}ms", flush=True)
    report = {"library": "University of Iowa MIS, Steinway & Sons model B (2001)",
              "source_page": PAGE, "permission_page": PERMISSION,
              "permission": "May be downloaded and used for any projects, without restrictions.",
              "format": "mono PCM16 WAV", "sample_rate": RATE,
              "bank": {"low_midi": 21, "high_midi": 108, "step_semitones": 3},
              "lowest_recordings": {"pp": "Bb0", "mf": "B0", "ff": "Bb0 (file named A0)"},
              "source_substitutions": {"ff_21": "A0 file sounds Bb0",
                                       "pp_24": "Db1; nominal C1 source sounds approximately B0",
                                       "mf_105": "A7 file sounds Ab7 with treble stretch",
                                       "mf_108": "C8 file sounds B7 with treble stretch"},
              "missing_source_notes": ["Piano.pp.A0.aiff", "Piano.mf.A0.aiff", "Piano.mf.Bb0.aiff"],
              "source_layout": "One note per AIFF; no octave-range slicing required.",
              "ffmpeg_version": subprocess.check_output(["ffmpeg", "-version"], text=True).splitlines()[0],
              "numpy_version": np.__version__,
              "versions_scope": "new imports; --only-missing preserves existing entries byte-for-byte",
              "credit_pages": [{"url": url, "sha256": sha(SOURCE / url.rsplit('/', 1)[1])}
                               for url in [PAGE, PERMISSION] if (SOURCE / url.rsplit('/', 1)[1]).exists()],
              "total_audio_bytes": sum(e["output_bytes"] for e in entries), "samples": entries}
    if args.only_missing:
        report["prior_credit_pages"] = json.loads((OUTPUT / "piano-import.json").read_text()).get("prior_credit_pages",
            json.loads((OUTPUT / "piano-import.json").read_text()).get("credit_pages", []))
    (OUTPUT / "piano-import.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"{len(entries)} samples: {report['total_audio_bytes']:,} bytes")


if __name__ == "__main__":
    main()
