#!/usr/bin/env python3
"""Check burning/wet badge shape and greyscale contrast on every equipment icon at 720p.

Each process owns one render flock. Evidence stays under build/round80 by default.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=ROOT/'build/round80/inventory')
    a = ap.parse_args()
    os.chdir(ROOT)
    out = a.output.resolve()
    assert out.is_relative_to(ROOT/'build')
    out.mkdir(parents=True, exist_ok=True)
    source = (ROOT/'tools/inventory_fixture.jo').read_text()
    source = re.sub(r"(?m)^(use|from) '([^']+)'", lambda m: f"{m[1]} '{(ROOT/'tools'/m[2]).resolve()}'", source)
    source += f"\nuse '{ROOT}/game/matter.jo'\n"
    source = source.replace('setup()\n','inv.arrows = 0\nsetup()\n')
    source = source.replace('setup()\n', '''setup()
gear_elements_sync()
status = env("BADGE_STATE") ?? "wet"
loop mut el in inv.weapon_effects: el = Elem(wet = if status == "wet": 1.0 else: 0.0, burning = if status == "burn": 2.0 else: 0.0)
loop mut el in inv.shield_effects: el = Elem(wet = if status == "wet": 1.0 else: 0.0, burning = if status == "burn": 2.0 else: 0.0)
loop mut el in inv.bow_effects: el = Elem(wet = if status == "wet": 1.0 else: 0.0, burning = if status == "burn": 2.0 else: 0.0)
held_index = -1
shield_el.index = -1
bow_el.index = -1
''')
    source = source.replace('window("Full inventory",', 'window("The Legend of Jo: Slop of the Wild",')
    source += f"\nuse '{ROOT}/tools/performance_output.jo'\nmain = (): performance_output_run(update,draw)\n"
    # A negative held index is resynchronized when IDs match; clear cached IDs too.
    source = source.replace('held_index = -1', 'held_id = ""\nheld_index = -1').replace('shield_el.index = -1','shield_el.id = ""\nshield_el.index = -1').replace('bow_el.index = -1','bow_el.id = ""\nbow_el.index = -1')
    (out/'fixture.jo').write_text(source)
    subprocess.run(['sloppy/bin/sloppy','build',str(out/'fixture.jo'),'-o',str(out/'fixture')],check=True)
    clean={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_','BADGE_'))}
    results=[]
    for tab in range(3):
        # All equipment definitions fit the 4x3 grid; weapons need a second page.
        for selection in [0]:
            masks={}
            for state in ('burn','wet'):
                name=f'{tab}-{selection}-{state}'
                env={**clean,'SLOPPY_PLATFORM':'x11','SLOPPY_WINDOW':'1280x720','SLOPPY_FRAMES':'3','SLOPPY_SCREENSHOT':str(out/f'{name}.png'),'BADGE_STATE':state}
                with (out/f'{name}.log').open('w') as log:
                    subprocess.run(['flock','/tmp/botw-render.lock','timeout','120',str(out/'fixture'),str(tab),str(selection)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
                im=Image.open(out/f'{name}.png').convert('RGB'); assert im.size==(1280,720)
                n=int(re.search(r'items=(\d+)',(out/f'{name}.log').read_text())[1])
                first=max(0,selection//4-2)
                for i in range(first*4,min(n,(first+3)*4)):
                    x,y=354+i%4*92+29,214+(i//4-first)*92+27
                    badge=im.crop((x-12,y-12,x+12,y+12))
                    grey=badge.convert('L'); pixels=list(grey.get_flattened_data() if hasattr(grey,"get_flattened_data") else grey.getdata())
                    dark=sum(v<25 for v in pixels); light=sum(v>180 for v in pixels)
                    assert dark>=140 and light>=45, (name,i,dark,light)
                    assert max(pixels)-min(pixels)>=180, (name,i,'greyscale contrast')
                    masks[(state,i)]=grey
                    results.append(dict(tab=tab,icon=i,state=state,dark_pixels=dark,light_pixels=light,greyscale_range=max(pixels)-min(pixels)))
            for i in range(first*4,min(n,(first+3)*4)):
                difference=ImageChops.difference(masks[('burn',i)],masks[('wet',i)])
                diff=list(difference.get_flattened_data() if hasattr(difference,"get_flattened_data") else difference.getdata())
                assert sum(v>30 for v in diff)>=28, (tab,i,'burn/wet shapes indistinguishable without colour')
    (out/'measurements.json').write_text(json.dumps(results,indent=2)+'\n')
    print(f'PASS {len(results)} equipment badge/icon pairs: dark backing, pale rim, distinct greyscale shapes at exact 720p')


if __name__=='__main__': main()
