#!/usr/bin/env python3
"""Matched meadow/canopy/Hopper Pond at 11:00 in all four weathers.

Each capture draws visible, hidden-body background and magenta body mask
passes at the identical simulation instant in one production frame. Normal hero shadows remain in all
three passes. Measure display-referred sRGB decoded to linear Rec.709 luminance,
using an eroded visible-body interior and a 3..8 pixel exterior ring. No exposure
normalization. --verify uses saved captures. Each game process owns one flock;
the lock is released between captures. The fixture fixes weather RNG seed 31 (also used by weather_transition_check) before the first simulation frame.
"""
import argparse
from collections import deque
import json
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageChops, ImageFilter

VIEWS = {"meadow": "-1030,1805,1.57", "canopy": "-1000,1620,3.14",
         "hopper-pond": "-1190,1665,-0.9"}
WEATHERS = ("clear", "cloudy", "rain", "storm")
# Regression floor: twelve percent linear-luminance Michelson separation.
MIN_CONTRAST = .12
LINEAR = [(v / 255 / 12.92 if v / 255 <= .04045 else
           ((v / 255 + .055) / 1.055) ** 2.4) for v in range(256)]


def pixels(image):
    # Pillow >=14 uses flattened_data; retain support for older project setups.
    return image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()


def body_mask(mask_image, hidden):
    """Largest changed magenta component; rejects UI, rain and foliage pixels."""
    assert mask_image.size == hidden.size
    w, h = hidden.size
    a, b = list(pixels(mask_image)), list(pixels(hidden))
    candidates = {i for i, (p, q) in enumerate(zip(a, b))
                  if p[0] - p[1] > 35 and p[2] - p[1] > 25
                  and max(abs(x - y) for x, y in zip(p, q)) > 20}
    largest = set()
    while candidates:
        first = candidates.pop()
        group = {first}
        queue = deque([first])
        while queue:
            i = queue.popleft()
            x, y = i % w, i // w
            for n in (i - 1 if x else -1, i + 1 if x + 1 < w else -1,
                      i - w if y else -1, i + w if y + 1 < h else -1):
                if n in candidates:
                    candidates.remove(n)
                    group.add(n)
                    queue.append(n)
        if len(group) > len(largest):
            largest = group
    assert len(largest) >= 100, f"missing/occluded Link body: {len(largest)} pixels"
    result = Image.new("L", (w, h))
    result.putdata([255 if i in largest else 0 for i in range(w * h)])
    return result


def luminance(p):
    return sum(LINEAR[c] * k for c, k in zip(p, (.2126, .7152, .0722)))


def measure(visible, hidden, mask):
    assert visible.size == hidden.size == mask.size
    core = mask.filter(ImageFilter.MinFilter(3))
    ring = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(17)),
                               mask.filter(ImageFilter.MaxFilter(7)))
    rgb = list(pixels(visible))
    inside = [luminance(p) for p, m in zip(rgb, pixels(core)) if m]
    outside = [luminance(p) for p, m in zip(rgb, pixels(ring)) if m]
    assert len(inside) >= 50 and len(outside) >= 100, "insufficient silhouette samples"
    li, lo = sum(inside) / len(inside), sum(outside) / len(outside)
    contrast = abs(li - lo) / max(li + lo, 1e-6)
    background = [luminance(p) for p, m in zip(pixels(hidden), pixels(core)) if m]
    # Paired same-pixel separation also detects contrast lost against the surface
    # directly behind Link, independent of a bright patch in the exterior ring.
    separation = sum(abs(a - b) / max(a + b, 1e-6)
                     for a, b in zip(inside, background)) / len(inside)
    excluded = mask.filter(ImageFilter.MaxFilter(65))
    differences = [sum(abs(a - b) for a, b in zip(p, q)) / 3
                   for p, q, m in zip(rgb, pixels(hidden), pixels(excluded)) if not m]
    background_drift = sum(differences) / max(len(differences), 1)
    assert background_drift < 1.0, f"unmatched background/time/camera: {background_drift:.2f} RGB levels"
    return dict(contrast=contrast, paired_separation=separation, background_drift=background_drift,
                inside_luminance=li, ring_luminance=lo,
                body_pixels=len(inside), ring_pixels=len(outside))


def verify(root):
    results, failures = {}, []
    for view in VIEWS:
        for weather in WEATHERS:
            key = f"{view}-{weather}"
            visible, hidden, debug = [Image.open(root / f"{key}-{mode}.png").convert("RGB")
                                      for mode in ("visible", "hidden", "mask")]
            mask = body_mask(debug, hidden)
            mask.save(root / f"{key}-silhouette.png")
            metrics = measure(visible, hidden, mask)
            results[key] = metrics
            ok = metrics["contrast"] >= MIN_CONTRAST and metrics["paired_separation"] >= MIN_CONTRAST
            if not ok:
                failures.append(key)
            print(f"{'PASS' if ok else 'FAIL'} {key}: silhouette {metrics['contrast']:.3f}, "
                  f"paired {metrics['paired_separation']:.3f}; linear Y "
                  f"{metrics['inside_luminance']:.4f}/{metrics['ring_luminance']:.4f}, "
                  f"{metrics['body_pixels']} body pixels; minimum {MIN_CONTRAST:.2f}", flush=True)
    (root / "contrast.json").write_text(json.dumps(dict(hour=11, frame=300, window="960x540", weather_seed=31,
        threshold=MIN_CONTRAST, results=results, failures=failures), indent=2) + "\n")
    assert not failures, f"unreadable silhouettes: {', '.join(failures)}"


def capture_view(binary, output, view, locked=False):
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("BOTW_", "SLOPPY_"))}
    at = VIEWS[view]
    for weather in WEATHERS:
        name = f"{view}-{weather}"
        prefix = (output / name).resolve()
        for mode in ("visible", "hidden", "mask"):
            Path(f"{prefix}-{mode}.png").unlink(missing_ok=True)
        final = output / f"{name}-final.png"
        final.unlink(missing_ok=True)
        settings = dict(clean, BOTW_SKIP="1", BOTW_AT=at, BOTW_HOUR="11",
            BOTW_WEATHER=weather, BOTW_NOVSYNC="1", SLOPPY_VSYNC="0", BOTW_SCALE="0.8",
            BOTW_SILHOUETTE_PREFIX=str(prefix), SLOPPY_PLATFORM="x11",
            SLOPPY_WINDOW="960x540", SLOPPY_FRAMES="300",
            SLOPPY_SCREENSHOT=str(final.resolve()))
        with (output / f"{name}.log").open("w") as log:
            lock_prefix = [] if locked else ["flock", "/tmp/botw-render.lock"]
            subprocess.run(lock_prefix + ["timeout", "300",
                            str(binary.resolve())], env=settings, stdout=log,
                            stderr=subprocess.STDOUT, check=True)
        assert all(Path(f"{prefix}-{mode}.png").is_file()
                   for mode in ("visible", "hidden", "mask")), f"capture missing: {prefix}"
        print(f"captured {name}: visible/hidden/mask at frame 300", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("build/weather-silhouette"))
    parser.add_argument("--binary", type=Path, help="immutable prebuilt capture executable; otherwise rebuild current sources")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--locked", action="store_true", help="caller owns the render flock for the batch; never nest")
    a = parser.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    if not a.verify:
        binary = a.binary or a.output / "game"
        if a.binary is None:
            binary.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["sloppy/bin/sloppy", "build", "tools/weather_silhouette_capture.jo", "-o", str(binary)], check=True)
        assert binary.is_file(), f"game binary missing: {binary}"
        for view in VIEWS:
            capture_view(binary, a.output, view, a.locked)
    verify(a.output)


if __name__ == "__main__":
    main()
