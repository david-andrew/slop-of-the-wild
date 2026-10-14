#!/usr/bin/env python3
"""Export actual production strike CSVs as readable timed scores and piano rolls."""
import argparse
import csv
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

NAMES=['C','C#','D','Eb','E','F','F#','G','G#','A','Bb','B']

def export(source, destination, seconds):
    rows=list(csv.DictReader(source.open()))
    rows=[r for r in rows if float(r['time']) <= seconds]
    destination.mkdir(parents=True,exist_ok=True)
    label=source.stem.removesuffix('-notes')
    lines=[f'{label}: actual production onsets; seconds, pitch, hand, velocity, gain, pan, fragment, instrument',
           'Rolls mark onsets/register with nominal 1.25 s widths (0.26 s combat); they do not truncate the audio decay.']
    image = Image.new('RGB', (1600,620), '#fbfaf7')
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=15)
    small = ImageFont.load_default(size=11)
    x = lambda t: 70 + t / seconds * 1500
    y = lambda midi: 555 - (midi - 18) / 96 * 490
    draw.text((70,15), label.replace('_',' '), fill='#26333b', font=font)
    draw.rectangle((70,y(72),1570,y(48)),fill='#eceeed')
    step = 5 if seconds <= 45 else 30
    for t in range(0, math.ceil(seconds)+1, step):
        draw.line((x(t),60,x(t),555),fill='#d9ddde')
        draw.text((x(t),568),str(t),fill='#4d5a63',font=small)
    for pitch in [24,36,48,60,72,84,96,108]:
        draw.line((70,y(pitch),1570,y(pitch)),fill='#d9ddde')
        draw.text((15,y(pitch)-8),f'C{pitch//12-1}',fill='#4d5a63',font=font)
    draw.text((680,595),'Production time (seconds)',fill='#26333b',font=font)
    for row in rows:
        t=float(row['time']); midi=int(row['midi']); hand=int(row['hand'])
        name=NAMES[midi%12]+str(midi//12-1)
        role={-1:'cue/combat',0:'high',1:'low',2:'glass/reverse',3:'glass-low',4:'glass-answer'}.get(hand,str(hand))
        lines.append(f"{t:8.3f}  {name:4} ({midi:3})  {role:12} v={float(row['velocity']):.3f} g={float(row['gain']):.3f} pan={float(row['pan']):+.3f} phrase={row['phrase']} {row['kind']}")
        colour={'piano':'#547b94','glass':'#b59769','reverse':'#926994'}[row['kind']]
        width = .26 if label.startswith(("combat", "low_health")) else 1.25
        draw.rectangle((x(t),y(midi)-3,x(min(seconds,t+width)),y(midi)+3),fill=colour)
        if seconds<=45:draw.text((x(t),y(midi)-17),name,fill='#344651',font=small)
    image.save(destination/(label+'.png'))
    (destination/(label+'.txt')).write_text('\n'.join(lines)+'\n')
    print(destination/(label+'.txt'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('sources',nargs='+',type=Path);p.add_argument('--out',type=Path,default=Path('build/listen-final/scores'));p.add_argument('--seconds',type=float,default=45)
    a=p.parse_args()
    for source in a.sources:export(source,a.out,a.seconds)
