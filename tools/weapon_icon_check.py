#!/usr/bin/env python3
"""Check the rendered inventory blade silhouettes and rust/steel material cues."""
from collections import Counter
from pathlib import Path
import sys

from PIL import Image

path = Path(sys.argv[1] if len(sys.argv) > 1 else "build/inventory-check/tab-0.png")
image = Image.open(path).convert("RGB")
sx, sy = image.width / 1280, image.height / 720


def icon(index):
    # Weapon tabs use the four-column, 92 px grid (material tabs remain six columns).
    cx, cy = 354 + index % 4 * 92, 214 + index // 4 * 92
    crop = image.crop((round((cx - 40) * sx), round((cy - 40) * sy),
                       round((cx + 40) * sx), round((cy + 40) * sy))).resize((80, 80))
    pixels = {(x, y): crop.getpixel((x, y)) for y in range(80) for x in range(80)
              if (x - 40) ** 2 + (y - 40) ** 2 < 38 ** 2}
    background = Counter(pixels.values()).most_common(1)[0][0]
    mask = {p for p, rgb in pixels.items() if max(abs(a - b) for a, b in zip(rgb, background)) > 35}
    assert len(mask) > 80, f"missing blade icon {index}"
    return pixels, mask


blades = {name: icon(index) for name, index in
          [("sword", 6), ("rusty", 7), ("soldier", 8), ("claymore", 9)]}
for left, right in [("sword", "soldier"), ("sword", "claymore"), ("soldier", "claymore")]:
    difference = len(blades[left][1] ^ blades[right][1])
    assert difference > 70, f"interchangeable silhouettes: {left}/{right}: {difference} pixels"
    print(f"PASS {left}/{right} silhouette difference: {difference} pixels")

rust, steel = blades["rusty"], blades["soldier"]
common = rust[1] & steel[1]
material = sum(max(abs(a - b) for a, b in zip(rust[0][p], steel[0][p])) > 35 for p in common)
assert material > 100, f"rust/steel cues are indistinct: {material} pixels"
# Isolate the blade's right-edge notch. Whole-icon XOR also counts handles and
# material antialiasing, and cannot establish that a chip is actually present.
notch = {(x, y) for y in range(30, 47) for x in range(43, 57)}
chipped = len((steel[1] - rust[1]) & notch)
assert chipped >= 12, f"rust notch is absent or subpixel: {chipped} missing edge pixels"
print(f"PASS rust/steel material difference: {material} pixels; notch {chipped} pixels; {path}")
