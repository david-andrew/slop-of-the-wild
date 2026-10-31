#!/usr/bin/env python3
"""Matched hourly weather silhouettes and CPU tails. Self-locking, one weather per process.

Visible/background/mask passes share a simulation instant and normal shadows.
Default: 24 hours x four weathers at the meadow. Assert 1.5:1 linear
luminance contrast for the rainy-night regression; record every other sample.
The companion headless check requires zero added fill in dry weather/daylight.
Use --record for baseline evidence without rejecting the known regression.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
from PIL import Image, ImageChops, ImageFilter, ImageStat, ImageDraw
from critic_pack import ROOT, BASE, clean_env, percentiles
from weather_silhouette_check import body_mask, LINEAR, pixels

FIXTURE = '''
build:
    opt = release
use '../game/main.jo'
use '../game/env.jo'
use 'performance_output.jo'
from '../game/chars.jo' import __hero_capture
from '../game/shadows.jo' import shadow_frame
hours = [loop h in split(env("WX_HOURS")!,","): to_float(h)!]
wx_update = (dt: f64):
    index = clamp((frame_number()-121)/60,0,hours.len()-1)
    env.hour = hours[index]
    env.bolt_wait = 1e9
    env.lightning = 0
    update(dt)
wx_draw = ():
    if frame_number()<180 or (frame_number()-180)%60!=0:
        draw()
        return
    index = (frame_number()-180)/60
    prefix = "{env("WX_OUT")!}/{env("BOTW_WEATHER")!}-{index}"
    schedule = shadow_frame
    loop mode in ["visible","hidden","mask"]:
        shadow_frame = schedule
        __hero_capture = if mode=="visible": "" else: mode
        draw()
        assert(save_png(screenshot(),"{prefix}-{mode}.png"))
    __hero_capture = ""
main = ():
    weather_rng_restore(rng(31))
    performance_output_run(wx_update,wx_draw)
'''

def measure(visible, hidden, mask):
    # Crop rank filters to the silhouette; histogram sums retain native pixel
    # precision without repeatedly scanning the entire frame in Python.
    x0,y0,x1,y1=mask.getbbox()
    box=(max(0,x0-9),max(0,y0-9),min(mask.width,x1+9),min(mask.height,y1+9))
    part=mask.crop(box)
    core=part.filter(ImageFilter.MinFilter(3))
    ring=ImageChops.subtract(part.filter(ImageFilter.MaxFilter(17)),part.filter(ImageFilter.MaxFilter(7)))
    vis,hid=visible.crop(box),hidden.crop(box)
    def mean(image, selection):
        count=selection.histogram()[255]
        assert count>=50, 'insufficient silhouette pixels'
        return sum(weight*sum(n*v for n,v in zip(channel.histogram(selection),LINEAR))/count
                   for channel,weight in zip(image.split(),(.2126,.7152,.0722)))
    excluded=Image.new('L',mask.size,255)
    ImageDraw.Draw(excluded).rectangle((x0-32,y0-32,x1+32,y1+32),fill=0)
    drift=sum(ImageStat.Stat(ImageChops.difference(visible,hidden),excluded).mean)/3
    assert drift<1, f'unmatched background: {drift}'
    separations=[]
    for a,b,m in zip(pixels(vis),pixels(hid),pixels(core)):
        if not m: continue
        a=sum(LINEAR[c]*w for c,w in zip(a,(.2126,.7152,.0722)))
        b=sum(LINEAR[c]*w for c,w in zip(b,(.2126,.7152,.0722)))
        separations.append(abs(a-b)/max(a+b,1e-6))
    separation=sum(separations)/len(separations)
    return dict(inside_luminance=mean(vis,core),ring_luminance=mean(vis,ring),
                hidden_luminance=mean(hid,core),background_drift=drift,body_pixels=core.histogram()[255],
                paired_ratio=(1+separation)/max(1-separation,1e-6))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('output',type=Path)
    ap.add_argument('--hours',nargs='+',type=float,default=list(range(24)))
    ap.add_argument('--weathers',nargs='+',choices=['clear','cloudy','rain','storm'],default=['clear','cloudy','rain','storm'])
    ap.add_argument('--at',default='-1030,1805,1.57')
    ap.add_argument('--record',action='store_true')
    ap.add_argument('--verify',action='store_true',help='analyse existing matched captures without rendering')
    args=ap.parse_args()
    assert all(0<=hour<24 for hour in args.hours), 'hours must be in [0,24)'
    os.chdir(ROOT)
    out=args.output.resolve()
    assert out.is_relative_to(ROOT/'build') and (args.verify or not out.exists())
    print(f'Evidence: {out}',flush=True)
    if not args.verify:
        (out/'fixture/tools').mkdir(parents=True)
        shutil.copytree(ROOT/'game',out/'fixture/game')
        shutil.copyfile(ROOT/'tools/performance_output.jo',out/'fixture/tools/performance_output.jo')
        (out/'fixture/tools/capture.jo').write_text(FIXTURE)
        binary=out/'capture'
        with (out/'build.log').open('w') as log:
            subprocess.run(['sloppy/bin/sloppy','build',str(out/'fixture/tools/capture.jo'),'-o',str(binary)],stdout=log,stderr=subprocess.STDOUT,check=True)
    results={}; cpu={}; failures=[]
    for weather in args.weathers:
        if args.verify:
            saved=json.loads((out/f'{weather}-settings.json').read_text())
            assert [float(v) for v in saved['WX_HOURS'].split(',')]==args.hours, 'hours must match saved capture'
            assert saved['BOTW_AT']==args.at and saved['BOTW_WEATHER']==weather, 'fixture must match saved capture'
        if not args.verify:
            settings=clean_env()|BASE|dict(BOTW_SKIP='1',BOTW_AT=args.at,BOTW_WEATHER=weather,
                BOTW_FRAME_LOG='1',WX_HOURS=','.join(map(str,args.hours)),WX_OUT=str(out),
                SLOPPY_FRAMES=str(121+60*len(args.hours)),SLOPPY_SCREENSHOT=str(out/f'{weather}-final.png'))
            (out/f'{weather}-settings.json').write_text(json.dumps({k:v for k,v in settings.items() if k.startswith(('BOTW_','SLOPPY_','WX_'))},indent=2))
            with (out/f'{weather}.log').open('w') as log:
                subprocess.run(['flock','/tmp/botw-render.lock','python3','tools/performance_window.py','1280x720','timeout','150',str(binary)],env=settings,stdout=log,stderr=subprocess.STDOUT,check=True)
        rows=[[float(x) for x in line.split()[2:]] for line in (out/f'{weather}.log').read_text().splitlines() if line.startswith('frame sample:')]
        for i,hour in enumerate(args.hours):
            prefix=f'{weather}-{i}'
            vis,hid,debug=[Image.open(out/f'{prefix}-{m}.png').convert('RGB') for m in ['visible','hidden','mask']]
            mask=body_mask(debug,hid)
            data=measure(vis,hid,mask)
            a,b=data['inside_luminance'],data['ring_luminance']
            data['region_ratio']=max(a,b)/max(min(a,b),1e-8)
            data['ratio']=data['region_ratio']
            data['hero_to_background']=a/max(b,1e-8)
            if weather in ['rain','storm'] and (hour<6 or hour>19.2):
                data['ratio']=data['hero_to_background']
            data['hour']=hour
            results[prefix]=data
            data['requires_night_contrast']=weather in ['rain','storm'] and (hour<6.2 or hour>19.2)
            if data['requires_night_contrast'] and data['ratio']<1.5: failures.append(prefix)
            vis.resize((640,360),Image.Resampling.LANCZOS).save(out/f'{prefix}.jpg')
            samples=[r[4] for r in rows if 121+i*60<=r[0]<180+i*60]
            if samples: cpu[prefix]=percentiles(samples)
            print(f"{prefix} hour={hour}: contrast {data['ratio']:.3f}:1",flush=True)
        (out/'contrast.json').write_text(json.dumps(dict(results=results,failures=failures),indent=2)+'\n')
        (out/'cpu.json').write_text(json.dumps(cpu,indent=2)+'\n')
    assert args.record or not failures, f'contrast below 1.5:1: {failures}'
if __name__=='__main__': main()
