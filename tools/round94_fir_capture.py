#!/usr/bin/env python3
"""Matched fir evidence; the reused capture runner owns one flock per render."""
import argparse, sys
sys.dont_write_bytecode = True
from pathlib import Path
import round82_critic_capture as capture
from PIL import Image, ImageDraw
capture.OUT = capture.ROOT / 'build/round94'
capture.SCENES['forest-firs'] = (150, dict(BOTW_SKIP='1', BOTW_CAM='-880,206,2273,2.60,-0.16'))
SCENES = ['snow', 'camp', 'forest', 'forest-firs', 'overlook']

def triptychs():
    for name in SCENES:
        folder = capture.OUT / name
        sheet = Image.new('RGB', (3840, 752), (24, 27, 30))
        labels = ['before', 'current', 'after']
        d = ImageDraw.Draw(sheet)
        for k, label in enumerate(labels):
            sheet.paste(Image.open(folder / f'{label}.png'), (k * 1280, 32))
            d.text((k * 1280 + 12, 10), label, fill='white')
        sheet.save(folder / 'triptych.png')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['prepare','capture','performance','triptychs'])
    p.add_argument('label', nargs='?', default='after')
    p.add_argument('scenes', nargs='*')
    p.add_argument('--baseline', default='current')
    a = p.parse_args()
    if a.mode == 'prepare':
        source = capture.OUT / a.label / 'game'
        capture.prepare(a.label, source if source.exists() else None)
    elif a.mode == 'capture': capture.capture(a.label, a.scenes or SCENES, a.baseline)
    elif a.mode == 'performance': capture.performance(a.label, a.scenes or SCENES, a.baseline, 2880, 720)
    else: triptychs()
