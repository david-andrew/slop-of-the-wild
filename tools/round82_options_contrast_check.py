#!/usr/bin/env python3
"""Check actual secondary-label pixels against Options' local panel in three captures."""
from collections import Counter
import argparse, json
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/round82'
def luminance(rgb):
 c=[v/255 for v in rgb]
 c=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c]
 return sum(v*w for v,w in zip(c,[.2126,.7152,.0722]))
regions={'heading':(310,174,520,192),'restore-controls':(525,498,661,517),
         'navigation':(310,590,665,609),'scroll-hint':(720,590,1010,609)}
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--label',default='after')
phase=parser.parse_args().label
reports={}
for scene in ['options-snow','options-grass','options-interior']:
 picture=Image.open(OUT/scene/f'{phase}.png').convert('RGB')
 assert picture.size==(1280,720)
 background=picture.getpixel((300,166))
 assert all(picture.getpixel(p)==background for p in [(300,166),(300,640),(1030,640)])
 labels={}
 for label,box in regions.items():
  colors=Counter(p for p in picture.crop(box).getdata() if luminance(p)>luminance(background)+.20)
  assert colors, f'{scene}/{label}: missing secondary label'
  ink=colors.most_common(1)[0][0]
  contrast=(luminance(ink)+.05)/(luminance(background)+.05)
  assert contrast>=7, f'{scene}/{label}: contrast {contrast:.2f}'
  labels[label]=dict(ink=ink,contrast=contrast)
 reports[scene]=dict(background=background,labels=labels)
 assert background==reports['options-snow']['background'],'landscape changes panel background'
 print(scene,'PASS',background,'minimum contrast',round(min(r['contrast'] for r in labels.values()),2))
(OUT/('options-contrast.json' if phase=='after' else f'options-contrast-{phase}.json')).write_text(json.dumps(reports,indent=2)+'\n')
