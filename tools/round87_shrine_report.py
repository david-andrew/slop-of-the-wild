#!/usr/bin/env python3
"""Inspect locked round87 captures. Requires Pillow, numpy and scipy.

Measures near-black connected regions in the upper third, not overall exposure.
Also writes review sheets for overlapping full-turn and raised camera sweeps.
Intentional transition fade frames are excluded; descent samples start at 180.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import label

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'build/round87')
partial = '--partial' in sys.argv
sheet_dir = root / 'sheets'
sheet_dir.mkdir(exist_ok=True)
rows = []
missing = []
failures = []
pans = []

def metric(path):
    with Image.open(path) as im:
        assert im.size == (1280, 720), (path, im.size)
        a = np.asarray(im.convert('RGB'))[:240]
    mask = a.max(axis=2) < 30
    regions, _ = label(mask)
    largest = int(np.bincount(regions.ravel())[1:].max(initial=0))
    return {'near_black_pixels': int(mask.sum()), 'largest_region': largest,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

def sheet(paths, destination):
    result = Image.new('RGB', (1280, ((len(paths)+3)//4)*202), '#18212b')
    draw = ImageDraw.Draw(result)
    for i, p in enumerate(paths):
        x, y = (i%4)*320, (i//4)*202
        with Image.open(p) as im:
            result.paste(im.convert('RGB').resize((320,180)), (x,y+22))
        draw.text((x+6,y+5), f'{p.parent.name}/{p.name}', fill='white')
    result.save(destination)

for shrine in range(1,5):
    for view in ['arrival','puzzle','up','pan','up-pan','descent'] + (['down-pan','eave-high'] if shrine == 2 else []):
        relative = [f'{shrine}-{view}.png']
        if view in ['pan','up-pan','down-pan','eave-high']:
            relative += [f'{shrine}-{view}/frame-{frame}.png' for frame in range(180,341,10)]
        elif view == 'descent':
            relative += [f'{shrine}-{view}/frame-{frame}.png' for frame in [180,240,300]]
        for name in relative:
            paths = [root/side/name for side in ['before','after']]
            if not all(p.exists() for p in paths):
                missing.extend(str(p) for p in paths if not p.exists())
                continue
            before, after = [metric(p) for p in paths]
            rows.append({'view': name, 'before': before, 'after': after})
            # Engravings and deep joints may remain dark; an unbroken void cannot.
            if after['largest_region'] >= 2500:
                failures.append(f'{name}: {after["largest_region"]} px near-black upper region')
            if before['largest_region'] >= 5000 and after['largest_region'] >= before['largest_region']*0.2:
                failures.append(f'{name}: void region did not shrink by at least 80%')
        for side in ['before','after']:
            log = root/side/f'{shrine}-{view}.log'
            if view in ['pan','up-pan','down-pan','eave-high'] and (root/side/relative[0]).exists():
                samples = []
                for line in log.read_text().splitlines():
                    match = re.search(r'cam (\d+).*?pitch=([-0-9.]+).*?view=vec3\(([^)]+)\) look=vec3\(([^)]+)\)',line)
                    if match and 360 <= int(match[1]) <= 720:
                        eye, target = [np.array([float(x) for x in match[j].split(',')]) for j in [3,4]]
                        direction = target-eye
                        samples.append((np.arctan2(direction[0],-direction[2]),float(match[2])))
                if len(samples) < 30:
                    failures.append(f'{side}/{view}: incomplete camera trace')
                else:
                    turn = float(abs(np.unwrap([v[0] for v in samples])[-1]-samples[0][0]))
                    pans.append({'view':f'{side}/{shrine}-{view}', 'degrees':float(np.degrees(turn)), 'pitch':samples[-1][1]})
                    if turn < 2*np.pi:
                        failures.append(f'{side}/{shrine}-{view}: camera turned only {np.degrees(turn):.2f} degrees')
            paths = [root/side/p for p in relative[1:] if (root/side/p).exists()]
            if paths:
                sheet(paths, sheet_dir/f'{side}-{shrine}-{view}.jpg')
    for side in ['before','after']:
        paths = [root/side/f'{shrine}-{v}.png' for v in ['arrival','puzzle','up','descent'] if (root/side/f'{shrine}-{v}.png').exists()]
        if paths:
            sheet(paths, sheet_dir/f'{side}-{shrine}-overview.jpg')

report = {'baseline_ref': 'ead9c13', 'threshold': 'max(R,G,B) < 30 in top 240 rows',
          'max_allowed_component': 2499, 'camera_pans': pans, 'views': rows, 'missing': missing, 'failures': failures}
(root/'image-report.json').write_text(json.dumps(report, indent=2)+'\n')
for r in rows:
    if '/' not in r['view']:
        print(f'{r["view"]}: largest near-black upper region {r["before"]["largest_region"]} -> {r["after"]["largest_region"]}')
print(f'{len(rows)} matched views; {len(missing)} missing captures; {len(failures)} rejected views')
for failure in failures: print('REJECT', failure)
if failures or (missing and not partial): sys.exit(1)
