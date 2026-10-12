#!/usr/bin/env python3
"""Assemble matched Round 64 screenshots without rendering or acquiring the GPU lock."""
from pathlib import Path
from PIL import Image, ImageDraw

root=Path('build/round64')
for name in ['forest','boars','golden','overview','snow','hylia-pass','talus']:
    images=[Image.open(root/phase/f'{name}.png').convert('RGB') for phase in ['before','after']]
    assert images[0].size==images[1].size
    width,height=images[0].size
    sheet=Image.new('RGB',(width*2,height+38),(21,25,24))
    draw=ImageDraw.Draw(sheet)
    for index,(phase,im) in enumerate(zip(['before: 0d1b209','after: sol3/work'],images)):
        sheet.paste(im,(width*index,38))
        draw.text((width*index+12,12),f'{name} / {phase}',fill=(230,234,226))
    sheet.save(root/f'{name}-comparison.png')
# Continuous production Talus camera at exact frames; no actor/camera fixture changes.
for phase in ['before','after']:
    frames=[100,200,300,400,500,600]
    images=[Image.open(root/phase/'talus'/f'frame-{f}.png').convert('RGB') for f in frames]
    width,height=images[0].size
    sheet=Image.new('RGB',(width*3,(height+32)*2),(21,25,24))
    draw=ImageDraw.Draw(sheet)
    for index,(f,im) in enumerate(zip(frames,images)):
        x,y=(index%3)*width,(index//3)*(height+32)
        sheet.paste(im,(x,y+32));draw.text((x+10,y+10),f'{phase}: frame {f}',fill=(230,234,226))
    sheet.save(root/f'talus-{phase}-sequence.png')
print('Round 64 matched comparisons and continuous Talus sequences assembled')

# A faster documentary loop makes the small post-rise mass motion visible.
# Keep the matched PNGs above at full resolution; this GIF is 3.33x time lapse.
motion=[]
for f in range(200,601,50):
    sheet=Image.new('RGB',(1280,392),(21,25,24))
    draw=ImageDraw.Draw(sheet)
    for index,phase in enumerate(['before','after']):
        im=Image.open(root/phase/'talus'/f'frame-{f}.png').convert('RGB')
        im.thumbnail((640,360))
        sheet.paste(im,(640*index,32))
        draw.text((640*index+10,10),f'{phase}: frame {f} / 3.33x time lapse',fill=(230,234,226))
    motion.append(sheet)
motion[0].save(root/'talus-motion-comparison.gif',save_all=True,append_images=motion[1:],duration=250,loop=0)
