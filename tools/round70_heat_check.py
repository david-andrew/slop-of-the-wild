#!/usr/bin/env python3
"""Headless differential of every production heat query, including item ignition chains."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];os.chdir(ROOT)
out=ROOT/'build/round70/heat-verified';game=out/'game'
out.mkdir(parents=True,exist_ok=True)
shutil.copytree(ROOT/'game',game,dirs_exist_ok=True)
(out/'sources.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in game.glob('*.jo')},indent=2)+'\n')
old=subprocess.check_output(['git','show','645907d:game/elements.jo'],text=True)
legacy=old[old.index('heat_at = ('):old.index('# Sample exposure along',old.index('heat_at = ('))].replace('heat_at = (','legacy_heat = (',1)
p=game/'elements.jo';s=p.read_text();needle='    h\n\n# Sample exposure along'
assert s.count(needle)==1
s=s.replace(needle,'    assert(h==legacy_heat(p,target_col), "source-list heat differs from full live scan")\n    __heat_verified += 1\n    h\n\n# Sample exposure along')
s+='\n__heat_verified=0\n'+legacy;p.write_text(s)
t=Path('tools/tree_checks.jo').read_text().replace('../game/',str(game)+'/')
(out/'tree_checks.jo').write_text(t)
imports=s.split('# The chemistry:')[0]
imports=re.sub(r"'([^']+\.jo)'",lambda m:repr(str(game/m[1])),imports)
source=f'''build:
    opt = release
{imports}
use '{game}/elements.jo'
use '{out}/tree_checks.jo'
from '{out}/tree_checks.jo' import __tree_course
from '{game}/elements.jo' import __heat_items_scope, __heat_verified
__audio_state=2
items_init()
__tree_course()
add_box(vec3(1.5,0,0.5),vec3(0.1,3,4))
loop i in [0..165):
    k=spawn_enemy(.bokoblin,vec3(f32(i%16)-8,0,f32(i/16)-5))
    if i%37==0:enemies[k].burning=3.0
loop i in [0..96):
    id=if i%11==0:"firewood" else:(if i%7==0:"apple" else:"branch")
    witems.push(WItem(id,vec3(f32(i%16)-8,0.5,f32(i/16)-3),alive=i%13!=0,hang=i%7==0,el=Elem(burning=(if i%19==0:-1.0 else:0.0))))
assert(ignite_at(vec3(0.5,0.1,0.5)))
loop frame in [0..240):
    elements_update(1.0/120.0,pl.pos)
    assert(not __heat_items_scope,"source list never escapes loose-item stage")
    if frame==120:
        loop mut e in enemies:e.state=.gone
        env.rain=0.8
        water_grid_set(fill(f32(1),4096),64,-32.0,-32.0,1.0)
loop i in [0..1000):
    heat_at(vec3(f32(i%15)-7.5,0.5,f32(i%13)-6.5))
print("heat source differential PASS: {{__heat_verified}} exact queries; ignition chains, firewood, cooking, hanging fruit, gone enemies, rain and water")
'''
(out/'check.jo').write_text(source)
subprocess.run(['sloppy/bin/sloppy','build',str(out/'check.jo'),'-o',str(out/'check')],check=True)
subprocess.run([str(out/'check')],check=True)
