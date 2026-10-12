#!/usr/bin/env python3
"""Pulls actor placements out of the map-section dumps (docs/mapref/map/*.json) into
assets/actors.tsv: name, x, y, z, rot_y (radians), scale. Only the plateau and its surroundings."""
import json, math, os, sys

here = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(here, '..', 'docs', 'mapref', 'map')
out = os.path.join(here, '..', 'assets', 'actors.tsv')
rows = []
for sec in ['D-6', 'D-7', 'E-6', 'E-7']:
    for kind in ['Static', 'Dynamic']:
        d = json.load(open(os.path.join(src, f'{sec}_{kind}.json')))
        for o in d.get('Objs', []):
            name = o['UnitConfigName']
            prm = o.get('!Parameters', {})
            # Master Mode and DLC trial actors are not part of the base game
            if prm.get('IsHardModeActor') or 'HardMode' in str(prm.get('SaveFlag', '')) or 'DLC' in name or 'AoC' in name:
                continue
            if name.startswith('LinkTag') or name in ('Area', 'EventTag', 'SwitchTimeLag'):
                continue
            x, y, z = o['Translate']
            if not (-2300 < x < 300 and 900 < z < 3200):
                continue
            r = o.get('Rotate', 0.0)
            if isinstance(r, list):
                r = r[1]
            s = o.get('Scale', 1.0)
            if isinstance(s, list):
                s = s[1] if len(s) > 1 else s[0]
            rows.append((name, x, y, z, r, s))
rows.sort()
with open(out, 'w') as f:
    for r in rows:
        f.write('%s\t%.2f\t%.2f\t%.2f\t%.4f\t%.3f\n' % r)
print(len(rows), 'actors ->', out)
