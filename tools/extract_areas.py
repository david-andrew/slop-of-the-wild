#!/usr/bin/env python3
"""Rasterizes the original's climate areas (FieldMapArea.beco: 1 m cells, x from -5000, z from
-4000) onto the game's 2 m grid: assets/area.u8 (2048 x 2048, area number per cell).
On the plateau: 46 temperate, 47 snow, 50 around the Shrine of Resurrection."""
import os, struct
here = os.path.dirname(os.path.abspath(__file__))
b = open(os.path.join(here, '..', 'docs', 'mapref', 'FieldMapArea.beco'), 'rb').read()
magic, rows, div, pad = struct.unpack('<IIII', b[:16])
offs = struct.unpack('<%dI' % rows, b[16:16 + 4 * rows])
base = 16 + 4 * rows
def row(i):
    o = base + offs[i] * 2
    end = base + offs[i + 1] * 2 if i + 1 < rows else len(b)
    out = bytearray()
    while o < end:
        v, l = struct.unpack('<HH', b[o:o + 4])
        out += bytes([min(v, 255)]) * l
        o += 4
    return out
N, CELL, X0, Z0 = 2048, 2.0, -3018.0, -133.0
grid = bytearray(N * N)
cache = {}
for gz in range(N):
    z = Z0 + gz * CELL
    r = int(z + 4000)
    if r < 0 or r >= rows:
        continue
    rw = row(r)
    for gx in range(N):
        c = int(X0 + gx * CELL + 5000)
        if 0 <= c < len(rw):
            grid[gz * N + gx] = rw[c]
open(os.path.join(here, '..', 'assets', 'area.u8'), 'wb').write(grid)
from collections import Counter
print(Counter(grid).most_common(12))
