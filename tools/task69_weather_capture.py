#!/usr/bin/env python3
"""Matched weather/wing/collapse evidence; owns one bounded render lock per scene."""
import argparse
import json
import hashlib
import os
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode=True
from PIL import Image
from critic_pack import BASE, ROOT, clean_env, command_run, capture_source, percentiles

SCENES=[
    ('storm',[299,300],dict(BOTW_AT='-1000,1620,3.14',BOTW_WEATHER='storm',BOTW_BOLT='300')),
    ('snow',[150],dict(BOTW_AT='-1060,2230,2.0')),
    ('temple',[300],dict(BOTW_CAM='-802,237,1900,-2.967,-0.14')),
    ('tent-fire',[900],dict(BOTW_TENTFIRE='5',BOTW_AT='-955,1964,0')),
    ('forest-rain',[300],dict(BOTW_AT='-1000,1620,3.14',BOTW_WEATHER='rain')),
    ('pond-rain',[300],dict(BOTW_AT='-1190,1665,-0.9',BOTW_WEATHER='rain')),
    ('bird-flight',[120],dict(BOTW_CAM='-818,195,1950,0,0')),
    ('bird-cycle',[120,122,124,126,128,130],dict(BOTW_CAM='-818,195,1950,0,0')),
    ('cloud-shadow',[120,720,1320],dict(BOTW_CAM='-700,330,2150,-0.8,-0.35')),
    ('overcast',[119,420,720,1320],dict(BOTW_CAM='-700,330,2150,-0.8,-0.35')),
    ('death',[45,90,115,150,180],dict(BOTW_AT='-1030,1805,1.57')),
]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('output',type=Path)
    ap.add_argument('--resume',action='store_true',help='reuse completed captures from the same frozen source')
    ap.add_argument('--source',type=Path,help='frozen critic fixture/game for the baseline')
    ap.add_argument('--scenes',nargs='+',choices=[s[0] for s in SCENES])
    args=ap.parse_args();os.chdir(ROOT)
    out=args.output.resolve();assert out.is_relative_to(ROOT/'build')
    out.mkdir(parents=True,exist_ok=True)
    source_dir=args.source or ROOT/'game'
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source_dir.glob('*.jo'))}
    record=out/'sources.json'
    if args.resume and record.exists():assert json.loads(record.read_text())==hashes,'source changed; use a new output directory'
    record.write_text(json.dumps(hashes,indent=2))
    game=out/'fixture/game';game.mkdir(parents=True,exist_ok=True)
    scripts=out/'fixture/tools';scripts.mkdir(exist_ok=True)
    for p in (args.source or ROOT/'game').glob('*.jo'):shutil.copyfile(p,game/p.name)
    shutil.copyfile(ROOT/'tools/performance_output.jo',scripts/'performance_output.jo')
    source=(args.source/'main.jo').read_text() if args.source else capture_source()
    source=source.replace('    production_update(dt)\n','''    if cp_scene=="overcast" and frame_number()==120: env.weather=.cloudy
    if cp_scene=="overcast" or cp_scene=="cloud-shadow": env.weather_t=1e9
    if cp_scene=="death" and frame_number()==30: damage_player(pl.hp,pl.pos)
    production_update(dt)
''')
    source=source.replace('if cp_scene=="bird-flight":','if cp_scene=="bird-flight" or cp_scene=="bird-cycle":')
    source=source.replace('        animal.idle=1.8','        animal.idle=1.8+(if cp_scene=="bird-cycle":f64(frame_number()-120)/60.0 else:0.0)')
    source = source.replace('draw = ():\n    production_draw()\n', '''from 'fx.jo' import __pinst_alpha
draw = ():
    production_draw()
    if cp_frames.contains(frame_number()) and env.rain > 0.1:
        near_strokes=0
        far_strokes=0
        impacts=0
        loop item in __pinst_alpha:
            if item.data.y==4 and item.data.w>0:
                if length(item.pos.xyz-sc.cam)<6: near_strokes+=1
                else: far_strokes+=1
            if item.data.y==8 or item.data.y==20: impacts+=1
        eprint("rain evidence: frame {frame_number()} rain {env.rain:.3} near {near_strokes} far {far_strokes} impacts {impacts}")
''')
    (game/'main.jo').write_text(source)
    binary=out/'fixture/capture'
    command_run(['sloppy/bin/sloppy','build',str(game/'main.jo'),'-o',str(binary)],out/'build.log')
    result={}
    for name,frames,flags in SCENES:
        if args.scenes and name not in args.scenes:continue
        folder=out/name;folder.mkdir(exist_ok=True)
        env=clean_env()|BASE|dict(BOTW_SKIP='1',BOTW_FRAME_LOG='1',CP_SCENE=name,CP_FRAMES=','.join(map(str,frames)),CP_OUT=str(folder),SLOPPY_FRAMES=str(max(901,max(frames)+1)),SLOPPY_SCREENSHOT=str(folder/'final.png'))|flags
        (folder/'settings.json').write_text(json.dumps({k:v for k,v in env.items() if k.startswith(("BOTW_","SLOPPY_","CP_"))},indent=2))
        if not (args.resume and (folder/'final.png').exists() and all((folder/f'frame-{f}.png').exists() for f in frames)):
            command_run(['flock','/tmp/botw-render.lock','python3','tools/performance_window.py','1280x720','timeout','90',str(binary)],folder/'run.log',env)
        for frame in frames:
            with Image.open(folder/f'frame-{frame}.png') as im:im.convert('RGB').resize((640,360),Image.Resampling.LANCZOS).save(folder/f'frame-{frame}.jpg')
        rows=[[float(v) for v in line.split()[2:]] for line in (folder/'run.log').read_text().splitlines() if line.startswith('frame sample:')]
        steady=[r for r in rows if r[0]>(30 if name=="death" else 120) and int(r[0]) not in frames]
        result[name]={key:percentiles([r[col] for r in steady]) for key,col in [('callback_wall',2),('callback_thread',4)]}
        (out/'cpu.json').write_text(json.dumps(result,indent=2))
        print('PASS',name,result[name]['callback_thread'],flush=True)
if __name__=='__main__':main()
