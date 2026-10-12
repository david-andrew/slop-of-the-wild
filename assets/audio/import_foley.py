#!/usr/bin/env python3
"""Rebuild compact Kenney CC0 foley: python3 assets/audio/import_foley.py --download.

Requires ffmpeg, otherwise Python standard library only. Source archives/evidence
are cached in /tmp/sol3/sfx (override --source); only adaptations and provenance ship.
"""
import argparse
import array
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import subprocess
import urllib.request
import wave
import zipfile

OUT = Path(__file__).resolve().parent
RATE = 48000
PACKS = {
    "impact-sounds": "https://kenney.nl/media/pages/assets/impact-sounds/87b4ddecda-1677589768/kenney_impact-sounds.zip",
    "rpg-audio": "https://kenney.nl/media/pages/assets/rpg-audio/8e99002d76-1677590336/kenney_rpg-audio.zip",
}
FILES = []
for surface, source in [("grass", "grass"), ("stone", "concrete"), ("snow", "snow"), ("wood", "wood")]:
    FILES.extend(("impact-sounds", f"footstep_{source}_{k:03}.ogg", f"step-{surface}-{k}", .10, .42) for k in range(5))
for kind, source in [("hit", "impactPunch_medium"), ("hit-big", "impactPunch_heavy"), ("block", "impactMetal_medium"), ("hit-wood", "impactWood_medium")]:
    FILES.extend(("impact-sounds", f"{source}_{k:03}.ogg", f"{kind}-{k}", .12, .48) for k in range(3))
FILES.extend(("rpg-audio", file, f"swing-{k}", .09, .40) for k, file in enumerate(["knifeSlice.ogg", "knifeSlice2.ogg", "drawKnife1.ogg"]))
FILES.extend(("rpg-audio", f"creak{k+1}.ogg", f"bow-draw-{k}", .055, .25) for k in range(3))
FILES.extend(("rpg-audio", f"cloth{k+1}.ogg", f"cloth-{k}", .065, .32) for k in range(3))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--source", type=Path, default=Path("/tmp/sol3/sfx"))
    args = parser.parse_args()
    args.source.mkdir(parents=True, exist_ok=True)
    archives = {}
    provenance = {"creator": "Kenney / Kenney Vleugels", "license": "CC0-1.0", "license_url": "https://creativecommons.org/publicdomain/zero/1.0/", "accessed": "2026-10-09", "sample_rate": RATE, "format": "mono PCM16", "packs": {}, "files": []}
    for name, url in PACKS.items():
        page_url = "https://kenney.nl/assets/" + name
        for remote, local in [(url, args.source / (name + ".zip")), (page_url, args.source / (name + ".html"))]:
            if args.download and not local.exists():
                local.write_bytes(urllib.request.urlopen(remote, timeout=60).read())
        raw = (args.source / (name + ".zip")).read_bytes()
        archive = zipfile.ZipFile(io.BytesIO(raw))
        archives[name] = archive
        license_data = archive.read("License.txt")
        if "CC0" not in license_data.decode():
            raise ValueError("Archive does not explicitly grant CC0: " + name)
        license_path = OUT / ("kenney-" + name + "-LICENSE.txt")
        license_path.write_bytes(license_data)
        page = (args.source / (name + ".html")).read_bytes()
        provenance["packs"][name] = {"url": page_url, "page_sha256": sha(page), "archive_url": url, "archive_sha256": sha(raw), "license_file": license_path.name, "license_sha256": sha(license_data)}
    for pack, source, target, target_rms, peak_limit in FILES:
        raw = archives[pack].read("Audio/" + source)
        decoded = subprocess.check_output(["ffmpeg", "-v", "error", "-i", "pipe:0", "-af", "highpass=f=35,lowpass=f=9500", "-ar", str(RATE), "-ac", "1", "-f", "f32le", "pipe:1"], input=raw)
        x = array.array("f", decoded)
        pk = max(map(abs, x))
        active = [i for i, v in enumerate(x) if abs(v) > pk * .008]
        start = max(0, active[0] - 192)
        end = min(len(x), active[-1] + 960)
        x = x[start:end]
        rms = math.sqrt(sum(v * v for v in x) / len(x))
        gain = min(target_rms / rms, peak_limit / max(map(abs, x)))
        for i in range(len(x)):
            x[i] *= gain * min(1., i / 96., (len(x) - 1 - i) / 480.)
        path = OUT / ("foley-" + target + ".wav")
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(RATE)
            wav.writeframes(b"".join(struct.pack("<h", round(max(-1., min(1., v)) * 32767)) for v in x))
        provenance["files"].append({"file": path.name, "pack": pack, "archive_member": "Audio/" + source, "source_sha256": sha(raw), "output_sha256": sha(path.read_bytes()), "processing": {"highpass_hz": 35, "lowpass_hz": 9500, "trim_start_frame": start, "trim_end_frame": end, "attack_fade_ms": 2, "release_fade_ms": 10, "target_rms": target_rms, "peak_limit": peak_limit, "gain": gain}, "seconds": len(x) / RATE, "peak": max(map(abs, x)), "rms": math.sqrt(sum(v * v for v in x) / len(x))})
    provenance["total_wav_bytes"] = sum((OUT / f["file"]).stat().st_size for f in provenance["files"])
    (OUT / "foley-import.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(f"Imported {len(FILES)} CC0 adaptations; {provenance['total_wav_bytes']} WAV bytes")


if __name__ == "__main__":
    main()
