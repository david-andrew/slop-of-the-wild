#!/usr/bin/env python3
"""Downscaled side-by-side review of every final critic shot against master."""
import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from PIL import Image, ImageChops, ImageDraw, ImageStat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pack', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--master', type=Path, default=Path('/tmp/crit71pack'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.output.resolve()
    assert out.is_relative_to(root/'build')
    out.mkdir(parents=True, exist_ok=True)
    shots = json.loads((args.pack/'pack.json').read_text())['shots']
    stats = {}
    sheets = []
    for start in range(0, len(shots), 3):
        batch = shots[start:start+3]
        sheet = Image.new('RGB', (1280, len(batch)*384), '#161c22')
        draw = ImageDraw.Draw(sheet)
        for row, shot in enumerate(batch):
            images = [Image.open(base/shot['png']).convert('RGB') for base in [args.master, args.pack]]
            assert images[0].size == images[1].size
            delta = ImageChops.difference(*images)
            extrema = delta.getextrema()
            red, green, blue = delta.split()
            mask = ImageChops.lighter(ImageChops.lighter(red, green), blue)
            count = mask.width*mask.height-mask.histogram()[0]
            stats[shot['name']] = dict(changed_pixels=count, max_channel_difference=max(v[1] for v in extrema),
                                      mean_rgb_difference=ImageStat.Stat(delta).mean, bounds=delta.getbbox())
            for col, (image, label) in enumerate(zip(images, ['master', 'final'])):
                sheet.paste(image.resize((640,360), Image.Resampling.LANCZOS), (col*640,row*384+24))
                draw.text((col*640+6,row*384+5), shot['name']+' / '+label, fill='white')
        path = out/f'comparison-{start//3+1:02}.jpg'
        sheet.save(path, quality=94)
        sheets.append(str(path))
    (out/'differences.json').write_text(json.dumps(stats,indent=2)+'\n')
    (out/'sheets.json').write_text(json.dumps(sheets,indent=2)+'\n')
    print(f'{len(shots)} shots, {len(sheets)} comparison sheets; {sum(s["changed_pixels"]==0 for s in stats.values())} pixel-identical')


if __name__ == '__main__':
    main()
