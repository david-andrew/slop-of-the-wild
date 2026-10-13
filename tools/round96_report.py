#!/usr/bin/env python3
"""Analyze saved round-96 frames; no render or render lock required."""
import json, re, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops, ImageEnhance, ImageStat
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/round96'
STAGES=['Terrain','+ vegetation','+ mapped shadows','+ canopy shade','+ cloud shadow','+ wet darkening','+ puddles','+ storm lighting','+ storm grade','+ water','+ props / actors','+ effects']
for scene in ['layers','layers-default']:
    for label in ['before','after']:
        folder=OUT/scene/label
        if not (folder/'layer-0.png').exists(): continue
        sheet=Image.new('RGB',(1920,4*388),(24,27,30))
        for i,name in enumerate(STAGES):
            im=Image.open(folder/f'layer-{i}.png').convert('RGB')
            x,y=(i%3)*640,(i//3)*388
            sheet.paste(im.resize((640,360)),(x,y+28))
            ImageDraw.Draw(sheet).text((x+8,y+8),f'{i}: {name}',fill='white')
            if i:
                prev=Image.open(folder/f'layer-{i-1}.png').convert('RGB')
                diff=ImageEnhance.Contrast(ImageChops.difference(im,prev)).enhance(3)
                diff.save(folder/f'delta-{i}.png')
        sheet.save(folder/'contact-sheet.png')
ABLATIONS={20:'No wet darkening',21:'No puddle mask',22:'No canopy shade',23:'No shadow map',24:'No cloud shadow',25:'No water',26:'No effects',27:'No vegetation',28:'No root soil',29:'No forest pigment',30:'No burn mask',31:'No contact pools',32:'No puddle cards',40:'Root-soil mask',41:'Canopy mask',42:'Puddle mask',43:'Burn channels'}
for scene in ['layers','layers-default']:
    for label in ['before','after']:
        folder=OUT/scene/label
        if not (folder/'ablate-20.png').exists():continue
        original=Image.open(folder/'frame-300.png').convert('RGB')
        sheet=Image.new('RGB',(1920,6*388),(24,27,30))
        measurements={}
        for k,(stage,name) in enumerate(ABLATIONS.items()):
            im=Image.open(folder/f'ablate-{stage}.png').convert('RGB')
            x,y=k%3*640,k//3*388
            sheet.paste(im.resize((640,360)),(x,y+28))
            ImageDraw.Draw(sheet).text((x+8,y+8),f'{stage}: {name}',fill='white')
            diff=ImageChops.difference(original,im)
            diff.save(folder/f'ablation-diff-{stage}.png')
            measurements[name]=dict(floor_left=ImageStat.Stat(diff.crop((200,400,550,680))).mean,
                floor_right=ImageStat.Stat(diff.crop((720,500,1050,690))).mean)
        sheet.save(folder/'ablation-sheet.png')
        (folder/'ablation-diffs.json').write_text(json.dumps(measurements,indent=2)+'\n')
for label in ['before','after','candidate']:
    storm=OUT/'storm'/label/'frame-300.png'
    clear=OUT/'clear'/label/'frame-300.png'
    if storm.exists() and clear.exists():
        ImageEnhance.Contrast(ImageChops.difference(Image.open(storm),Image.open(clear))).enhance(3).save(OUT/'storm'/label/'clear-diff.png')
    folder=OUT/'minute'/label
    log=folder/'run.log'
    if not log.exists():continue
    lines=log.read_text().splitlines()
    strikes=[dict(frame=int(m[1]),distance=float(m[2])) for line in lines if (m:=re.search(r'bolt frame=(\d+).*distance=([\d.]+)m',line))]
    samples=[]
    for line in lines:
        if not line.startswith('minute '):continue
        row={k:float(v) for k,v in re.findall(r'(\w+)=([\d.]+)',line)}
        f=int(row['f'])
        path=folder/f'frame-{f}.png'
        if f%60==0 and path.exists():
            im=Image.open(path).convert('L')
            row['image_Y']=ImageStat.Stat(im.crop((40,100,1200,600))).mean[0]
            samples.append(row)
    if len(samples)<60:continue
    quiet=[s for s in samples if s['flash']==0]
    gaps=[(b['frame']-a['frame'])/60 for a,b in zip([{'frame':0}]+strikes,strikes)]
    report=dict(strikes=strikes,interval_seconds=gaps,samples=samples,
        quiet_sky_min=min(s['sky'] for s in quiet),quiet_sky_max=max(s['sky'] for s in quiet),
        quiet_image_Y_min=min(s['image_Y'] for s in quiet),quiet_image_Y_max=max(s['image_Y'] for s in quiet))
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(label, json.dumps({k:v for k,v in report.items() if k!='samples'}))
    if label=='after':
        assert 3<=len(strikes)<=6
        assert all(9.98<=g<=20.02 for g in gaps)
        assert all(18<=s['distance']<48 for s in strikes)
        assert report['quiet_sky_max']/report['quiet_sky_min']>1.2
        assert report['quiet_image_Y_max']-report['quiet_image_Y_min']>3
    selected=[min(quiet,key=lambda s:s['image_Y'])['f'],max(quiet,key=lambda s:s['image_Y'])['f']]+[s['frame'] for s in strikes]
    sheet=Image.new('RGB',(1280,388*((len(selected)+1)//2)),(24,27,30))
    for k,f in enumerate(selected):
        p=folder/f'frame-{int(f)}.png'
        if not p.exists():continue
        x,y=k%2*640,k//2*388
        sheet.paste(Image.open(p).resize((640,360)),(x,y+28))
        ImageDraw.Draw(sheet).text((x+8,y+8),f'{label} {f/60:.2f}s',fill='white')
    sheet.save(folder/'contact-sheet.png')

# Matched-frame acceptance: preserve clear noon and visibly increase the
# bright precipitation/effect footprint without changing the seed budget.
if (OUT/'layers/after/layer-11.png').exists():
    quality={}
    for label in ['before','after']:
        folder=OUT/'layers'/label
        base=Image.open(folder/'layer-10.png').convert('RGB')
        effects=Image.open(folder/'layer-11.png').convert('RGB')
        pixels=lambda im: im.get_flattened_data() if hasattr(im,'get_flattened_data') else im.getdata()
        count=sum(max(q[i]-p[i] for i in range(3))>16 for p,q in zip(pixels(base),pixels(effects)))
        sun=Image.open(OUT/'dawn'/label/'frame-300.png').convert('RGB')
        disk=[(x,y,sun.getpixel((x,y))) for y in range(300,382) for x in range(600,720) if sun.getpixel((x,y))[0]>245]
        assert disk
        quality[label]=dict(bright_effect_pixels=count,sun_center_y=sum(y for x,y,c in disk)/len(disk),
            sun_rgb=[sum(c[i] for x,y,c in disk)/len(disk) for i in range(3)])
    clear=ImageChops.difference(Image.open(OUT/'clear/before/frame-300.png'),Image.open(OUT/'clear/after/frame-300.png'))
    quality['clear_noon_identical']=clear.getbbox() is None
    assert quality['clear_noon_identical']
    assert quality['after']['bright_effect_pixels']>quality['before']['bright_effect_pixels']*1.6
    assert quality['after']['sun_center_y']>quality['before']['sun_center_y']+15
    assert quality['after']['sun_rgb'][2]<quality['before']['sun_rgb'][2]-20
    (OUT/'quality.json').write_text(json.dumps(quality,indent=2)+'\n')
    print('PASS matched image checks',quality)

# Keep the exact simulation timestamps, including the brief multi-stroke flashes.
folder=OUT/'minute/after'
if (folder/'frame-3600.png').exists():
    paths=sorted(folder.glob('frame-*.png'),key=lambda p:int(p.stem.split('-')[1]))
    entries=[]
    for i,path in enumerate(paths):
        f=int(path.stem.split('-')[1])
        next_f=int(paths[i+1].stem.split('-')[1]) if i+1<len(paths) else 3601
        entries += [f"file '{path.name}'",f'duration {(next_f-f)/60:.9f}']
    entries += [f"file '{paths[-1].name}'"]
    (folder/'frames.txt').write_text('\n'.join(entries)+'\n')
    subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i','frames.txt','-vf','fps=30','-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart','storm-minute.mp4'],cwd=folder,check=True)
