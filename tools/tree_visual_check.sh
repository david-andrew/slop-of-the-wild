#!/bin/bash
# Caller owns flock /tmp/botw-render.lock; never acquire a nested lock.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-build/tree-visuals}
mkdir -p "$out"
python3 - "$out" <<'PY'
from pathlib import Path
import sys
out=Path(sys.argv[1]).resolve()
game=Path('game').resolve()
s=(game/'main.jo').read_text()
for p in game.glob('*.jo'): s=s.replace(f"'{p.name}'",f"'{p}'")
s=s.replace('update = (dt0: f64):','production_update = (dt0: f64):')
s+=f"\nuse '{game/'trees.jo'}'\nuse '{game/'matter.jo'}'\n"
s+='''
visual_case=env("TREE_VISUAL") ?? "chop"
visual_ready=false
visual_tree=-1
visual_root=vec3(0,0,0)
visual_water=vec3(0,0,0)
visual_moved=false
visual_target=vec3(0,0,0)
visual_camera=vec3(0,0,0)
update = (dt: f64):
    if not visual_ready:
        best=1e9
        loop i in 0.. and p in places:
            if not tree_suitable(p) or p.height>11.0 or p.height<5.0: continue
            d=f64(length(p.pos.xz-vec2(-784,2255)))
            if d<best:
                best=d
                visual_tree=i
        assert(visual_tree>=0,"existing cabin-area trunk")
        visual_root=places[visual_tree].pos
        visual_target=visual_root+vec3(0,2.6,0)
        visual_camera=visual_root+vec3(7,5,9)
        pl=Player(pos=visual_root+vec3(0,0,0.95),face=0.0,hp=40,hp_max=40)
        pl.pos.y=f32(height_at(f64(pl.pos.x),f64(pl.pos.z)))
        inv_add("axe")
        inv_add("old_shirt")
        fight.weapon_out=true
        loop mut e in enemies: e.state=.gone
        if visual_case!="chop":
            tree_fell(tree_record(visual_tree),pl.pos)
            pl.pos=visual_root+vec3(3,0,3)
        visual_ready=true
        print("TREE selected pos={visual_root} model={vmodels[places[visual_tree].model].name} height={places[visual_tree].height}")
    production_update(dt)
    if tree_states.len()>0:
        t=tree_states[0]
        if visual_case=="water" and t.phase==2 and not visual_moved:
            deepest=0.0
            loop z in [-10..10]:
                loop x in [-10..10]:
                    wx=-1201.7+f64(x)
                    wz=1655.7+f64(z)
                    depth=water_depth(wx,wz)
                    if depth>deepest and depth<4.0:
                        if let wl=water_level(wx,wz):
                            deepest=depth
                            visual_water=v3(wx,wl+0.1,wz)
            assert(deepest>1.0,"Hopper Pond has water for the production log")
            tree_states[0].pos=visual_water
            tree_states[0].vel=vec3(0,0,0)
            tree_states[0].yaw=0.55
            tree_states[0].pitch=0.0
            pl.pos=visual_water+vec3(4,1.5,5)
            visual_target=visual_water
            visual_camera=visual_water+vec3(7,4,9)
            visual_moved=true
        if visual_case=="burning" and t.phase==2 and not visual_moved:
            bonfires.push(Bonfire(t.pos+vec3(1,0,0)))
            visual_target=t.pos+vec3(0,0.7,0)
            visual_camera=t.pos+vec3(6,3,7)
            visual_moved=true
        if visual_case=="burning" and t.phase==2 and visual_moved:
            visual_target=t.pos+vec3(0,0.5,0)
            visual_camera=t.pos+vec3(4.5,2.6,5.5)
        if frame_number()%10==0:
            print("TREE frame={frame_number()} phase={t.phase} hits={t.hits} age={t.age:.3} pos={t.pos} burn={t.el.burning:.3}")
    cam.override=true
    cam.blend=1.0
    cam.o_pos=visual_camera
    cam.o_target=visual_target
    cam.o_fov=43.0
    cam.yaw=0.0
    cam_yaw_global=0.0
    if frame_number()==(if visual_case=="chop":360 else:300):
        assert(tree_states.len()>0 and tree_states[0].phase==2,"production tree becomes physical log")
        if visual_case=="water": assert(abs(f64(tree_states[0].pos.y-visual_water.y))<0.3,"production log floats")
        if visual_case=="burning": assert(burning(tree_states[0].el),"bonfire ignites log")
        print("TREE visual passed")
'''
(out/'tree-visual.jo').write_text(s)
PY
sloppy/bin/sloppy build "$out/tree-visual.jo" -o "$out/tree-visual"
if [[ ${VISUAL_PREPARE:-0} == 1 ]]; then exit 0; fi
for scene in ${TREE_SCENES:-chop water burning}; do
 mkdir -p "$out/$scene"
 frames=300
 input=""
 if [[ $scene == chop ]]; then
  frames=360
  input="20:j+,22:j-,100:j+,102:j-,180:j+,182:j-,260:j+,262:j-"
 fi
 env BOTW_SKIP=1 BOTW_HOUR=10 BOTW_WEATHER=clear BOTW_SCALE=1 BOTW_NOVSYNC=1 \
  TREE_VISUAL="$scene" BOTW_CAPTURE_DIR="$out/$scene" BOTW_CAPTURE_EVERY=10 \
  SLOPPY_INPUT="$input" SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=1280x720 \
  SLOPPY_FRAMES="$frames" SLOPPY_SCREENSHOT="$out/$scene-final.png" \
  timeout 240 "$out/tree-visual" > "$out/$scene.log" 2>&1
 grep -E 'TREE selected|TREE visual passed|panic:|FAIL' "$out/$scene.log"
 if ! grep -Eq 'TREE visual passed' "$out/$scene.log"; then tail -20 "$out/$scene.log"; exit 1; fi
done
python3 - "$out" <<'PY'
from PIL import Image
from pathlib import Path
import re,sys
out=Path(sys.argv[1])
frames=[]
for line in (out/'chop.log').read_text().splitlines():
 m=re.search(r'TREE frame=(\d+) phase=(\d+) hits=(\d+) age=([\d.]+)',line)
 if m: frames.append(tuple(map(float,m.groups())))
fall=[int(f) for f,p,h,a in frames if p==1]
chop=[30,50,110,130]
for name,scene,nums in [('chop','chop',chop),('fall','chop',[fall[i] for i in [0,len(fall)//3,2*len(fall)//3,-1]]),('water','water',[100,150,200,280]),('burning','burning',[150,200,250,280])]:
 imgs=[Image.open(out/scene/f'frame-{n}.png').convert('RGB') for n in nums]
 # Unlabelled 2x2 contact strips: no added on-screen text.
 strip=Image.new('RGB',(imgs[0].width*2,imgs[0].height*2))
 for k,img in enumerate(imgs): strip.paste(img,((k%2)*img.width,(k//2)*img.height))
 strip.save(out/f'{name}-strip.png')
 print(name,'frames',nums,'->',out/f'{name}-strip.png')
PY
