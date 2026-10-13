#!/usr/bin/env python3
"""Measure posed combat silhouettes on flat ground, a slope, a doorway and by a tree.

Self-locks each render. Requires numpy and a C compiler (use a build/ venv if needed).
Body and equipment have separate masks; target visibility uses all foreground depths.
The masks conservatively include all triangles, ignoring terrain occlusion/dissolve.
"""
from pathlib import Path
import argparse, ctypes, hashlib, json, os, re, struct, subprocess, sys
sys.dont_write_bytecode = True
import numpy as np
ROOT = Path(__file__).resolve().parents[1]

class Reader:
    def __init__(self, path): self.data, self.at = path.read_bytes(), 0
    def unpack(self, fmt):
        out = struct.unpack_from('<'+fmt, self.data, self.at)
        self.at += struct.calcsize('<'+fmt)
        return out
    def string(self):
        n, = self.unpack('I'); out = self.data[self.at:self.at+n].decode(); self.at += n; return out
    def array(self, n):
        out = np.frombuffer(self.data, '<f4', n, self.at).astype(float); self.at += n*4; return out
    def matrix(self): return self.array(16).reshape(4,4).T

def model(path):
    r = Reader(path)
    assert r.unpack('II') == (0x4C444D4A,1)
    r.string(); r.string()
    nb, = r.unpack('I')
    bones, bind = [], []
    for _ in range(nb):
        bones.append(r.string()); r.unpack('iiB'); r.array(10); bind.append(r.matrix())
    r.array(7); slots, variants = r.unpack('II')
    for _ in range(slots*variants):
        w,h = r.unpack('II'); r.at += w*h*4
    count, = r.unpack('I'); parts = []
    for _ in range(count):
        name = r.string(); r.unpack('IB'); nv, = r.unpack('I')
        vs = r.array(nv*20).reshape(nv,20); ni, = r.unpack('I')
        idx = np.array(r.unpack(f'{ni}I')).reshape(-1,3)
        if name not in ('club','bow','sword','shield','hood'): parts.append((name,vs,idx))
    return parts, bones, bind

def posed(parts, palette, world, vp):
    if not len(palette): return []  # First pre-camera frame has no drawn pose.
    mats = palette.reshape(-1,3,4)
    output=[]
    for name,vs,idx in parts:
        p = np.column_stack((vs[:,:3], np.ones(len(vs))))
        skin = (mats[vs[:,12:16].astype(int)] * vs[:,16:20,None,None]).sum(axis=1)
        p = np.einsum('nij,nj->ni',skin,p)
        p = np.column_stack((p,np.ones(len(p)))) @ world.T
        clip = p @ vp.T
        uv = clip[:,:2]/np.maximum(clip[:,3:4],0.001)
        uv = (uv*np.array([1,-1])+1)*np.array([160,90])
        output.append((p[:,:3],uv,clip[:,3],idx))
    return output

def head_projection(parts, bones, palette, world, vp):
    # Pose the actual head-weighted vertices, then project their bounds centre.
    # This also follows guard, recoil and crouched windups instead of root height.
    if not len(palette): return None
    head = next(i for i, name in enumerate(bones) if name.lower() == 'head')
    selected = []
    for name, vertices, indices in parts:
        weight = np.where(vertices[:,12:16].astype(int) == head, vertices[:,16:20], 0).sum(axis=1)
        mask = weight >= .5
        if mask.any():
            mesh = posed([(name,vertices[mask],np.empty((0,3),dtype=int))],palette,world,vp)
            selected.extend(p for p,_,_,_ in mesh)
    points = np.vstack(selected)
    centre = (points.min(axis=0)+points.max(axis=0))/2
    clip = vp @ np.r_[centre,1]
    projected = np.column_stack((points,np.ones(len(points)))) @ vp.T
    head_x = (projected[:,0]/np.maximum(projected[:,3],.001)+1)*640
    centre_px = (clip[:2]/max(clip[3],.001)*[1,-1]+1)*[640,360]
    return centre_px, float(np.ptp(head_x))

def head_centre(parts, bones, palette, world, vp):
    projected = head_projection(parts, bones, palette, world, vp)
    return projected[0] if projected is not None else None

def depth_mask(mesh, raster):
    depth=np.full((180,320),np.inf,dtype=np.float64)
    for _,uv,w,idx in mesh:
        points=np.ascontiguousarray(np.column_stack((uv,w)),dtype=np.float64)
        indices=np.ascontiguousarray(idx,dtype=np.int64)
        raster(points.ctypes.data, indices.ctypes.data, len(indices), depth.ctypes.data, 320,180)
    return depth

FIXTURE = '''
use '{game}/gfx.jo'
use '{game}/main.jo'
use '{game}/skel.jo'
use '{game}/chars.jo'
use '{game}/enemies.jo'
use '{game}/items.jo'
use '{game}/player.jo'
use '{game}/camera.jo'
use '{game}/combat.jo'
use '{game}/sheath.jo'
use '{game}/input.jo'
use '{game}/trees.jo'
use '{game}/vegetation.jo'
use '{game}/physics.jo'
use '{game}/structures.jo'
use '{game}/terrain.jo'
use '{game}/build.jo'
use '{game}/scene.jo'
use '{root}/tools/performance_output.jo'
framing_trace = BinW()
framing_ready = false
framing_contacts = 0
framing_lock_frames = 0
framing_scene = env("FRAMING_SCENE") ?? "flat"
framing_frames = to_int(env("FRAMING_FRAMES") ?? "960") ?? 960
framing_count = if framing_scene == "camp": 0 else: (if framing_scene == "flat": 5 else: (if framing_scene == "doorway": 1 else: 3))
framing_ids: int[]
framing_update = (dt: f64):
    if not framing_ready:
        if framing_scene == "slope":
            found = false
            loop dx in [-4..5):
                if found: break
                loop dz in [-4..5):
                    x = -1439.0 + f64(dx)*10.0
                    z = 1614.0 + f64(dz)*10.0
                    rise = abs(height_at(x,z-3.0)-height_at(x,z+3.0))
                    if rise < 1.0 or rise > 2.4: continue
                    pl.pos = v3(x,height_at(x,z),z)
                    print("framing slope: rise={rise:.3}m over 6m pos={pl.pos}")
                    found = true
                    break
            assert(found,"fixture must exercise an actual walkable terrain slope")
        else if framing_scene == "doorway":
            pl.pos = lp(TEMPLE,TEMPLE_ROT,0.0,0.0,40.0)
            cam.yaw = TEMPLE_ROT
            print("framing doorway: production Temple entry pos={pl.pos}")
        else if framing_scene == "tree":
            selected = -1
            nearest = 10000.0
            loop i in 0.. and p in places:
                if not tree_suitable(p) or p.col < 0 or p.height < 7.0: continue
                d = hypot(f64(p.pos.x)+1000.0,f64(p.pos.z)-1620.0)
                if d < nearest:
                    nearest = d
                    selected = i
            assert(selected >= 0,"fixture needs a real collidable forest tree")
            pl.pos = places[selected].pos - vec3(0,0,3)
            cam.yaw = 0.0
            print("framing tree: collider={places[selected].col} trunk={places[selected].pos} player={pl.pos}")
        if framing_scene != "flat" and framing_scene != "camp":
            pl.ground = ground_at(f64(pl.pos.x),f64(pl.pos.z),f64(pl.pos.y)+5.0,0.5,RADIUS)
            pl.pos.y = pl.ground.y
            pl.last_safe = pl.pos
            camera_snap()
            cam.pos = cam.target + transform_dir(rotation_y(cam.yaw),vec3(0,1.2,5.3))
            camera_update(0.0)
        if framing_scene != "camp":
            enemies.clear()
            # The course replaces world actors, so it must also replace their pose
            # histories. Animation LOD reads the previous render lens; seed the new
            # location before the first production tick after this fixture teleport.
            eanims.clear()
            sc.cam = view_pos()
            inv_add("travelers_sword")
            inv_add("travelers_shield")
            loop j in [0..framing_count):
                # The front club bearer is both the natural first lock target and
                # an engaging melee attacker; flankers still use production slots.
                d = (if framing_count == 5: [vec3(0,0,-3.8),vec3(3,0,-4),vec3(0,0,3),vec3(-4,0,1),vec3(4,0,1)] else: [vec3(0,0,-3.8),vec3(3,0,-4),vec3(-3,0,-4)])[j]
                if framing_scene == "doorway": d = [vec3(0,0,-2.8),vec3(1.25,0,-4.5)][j]
                p = pl.pos + transform_dir(rotation_y(cam.yaw),d)
                if framing_scene != "flat" and framing_scene != "camp":
                    g = ground_at(f64(p.x),f64(p.z),f64(pl.pos.y)+5.0,0.5,RADIUS)
                    p.y = g.y
                k = spawn_enemy(.blue_bokoblin, p, if j == 0: "boko_club" else: "boko_spear")
                enemies[k].state = .chase
                enemies[k].alert = 1.0
                enemies[k].hp = 10000.0
                enemies[k].hp_max = 10000.0
            pl.hp_max = 40
            pl.hp = 40
        else:
            inv_add("travelers_sword")
            inv_add("travelers_shield")
            loop i in 0.. and e in enemies:
                if enemy_melee_body(e) and e.state != .buried and e.state != .gone and length(e.pos-pl.pos) < 35.0: framing_ids.push(i)
            framing_count = framing_ids.len()
            assert(framing_count >= 3, "README camp keeps its actual three or more actors")
        if framing_scene != "camp": framing_ids = [loop i in [0..framing_count): i]
        framing_ready = true
    update(dt)
    if frame_number() % 60 == 0: print("framing camera: scene={framing_scene} frame={frame_number()} boom={length(view_pos()-view_target()):.3}m pos={view_pos()} player={pl.pos}")
    framing_lock_frames = if cam.locked: framing_lock_frames + 1 else: 0
    framing_contacts = enemy_contact_serial
    vp = perspective(view_fov()*PI/180.0, 16.0/9.0, 0.1, 1000.0) * look_at(view_pos(),view_target(),vec3(0,1,0))
    if frame_number() == 0:
        w_u32(framing_trace,0x46524D36)
        w_u32(framing_trace,framing_count)
    w_u32(framing_trace,frame_number())
    w_m4(framing_trace,vp)
    w_v3(framing_trace,pl.pos)
    w_m4(framing_trace,hero_world)
    w_u32(framing_trace,hero_skin.mats.len())
    w_raw(framing_trace,hero_skin.mats)
    w_f32(framing_trace,hitstop)
    w_f32(framing_trace,fight.t)
    w_u32(framing_trace,if fight.weapon_out or fight.act != .idle: 1 else: 0)
    damage = 0.0
    loop e in enemies: damage += e.hp_max-e.hp
    w_f32(framing_trace,f64(framing_contacts))
    selected = -1
    loop i in [0..framing_count):
        if framing_ids[i] == fight.target: selected = i
    w_u32(framing_trace, selected + 1)
    w_u32(framing_trace, framing_lock_frames)
    w_m4(framing_trace, hero_shield_matrix())
    sword = socket_world(hero_m, hero_world, hero_skin, if fight.weapon_out or fight.act != .idle: SOCKET_HAND_R else: SOCKET_BACK)
    if not fight.weapon_out and fight.act == .idle: sword = sword_back_transform(sword, .sword)
    w_m4(framing_trace, sword)
    loop fi in [0..framing_count):
        i = framing_ids[fi]
        e = enemies[i]
        w_u32(framing_trace, if e.state == .windup: 1 else: 0)
        w_u32(framing_trace, if len(e.weapon) > 0 and item(e.weapon).spear: 1 else: 0)
        w_u32(framing_trace, if e.state == .windup or e.state == .attack: 1 else: 0)
        waiting = e.state == .chase and not e.may_engage and not e.archer
        tp = pl.pos - e.pos
        bearing = yaw_of(vec3(tp.x,0,tp.z))
        error = abs(atan2(sin(e.face-bearing),cos(e.face-bearing)))
        w_f32(framing_trace, if waiting: error else: -1.0)
        w_u32(framing_trace, if waiting and e.speed <= 0.35: eanims[i].a.clip + 1 else: 0)
        drawn = e.state != .gone and e.state != .buried and eanims[i].skin.mats.len()>0
        w_u32(framing_trace, (if drawn: 1 else: 0) + (if drawn and e.state != .dead and len(e.weapon)>0: 2 else: 0) + (if enemy_alive(e): 4 else: 0))
        w_m4(framing_trace, boko_weapon_draw_transform(i))
        w_v3(framing_trace,e.pos)
        w_f32(framing_trace,enemy_attack_ring(e))
        w_m4(framing_trace,eanims[i].world)
        w_u32(framing_trace,eanims[i].skin.mats.len())
        w_raw(framing_trace,eanims[i].skin.mats)
    if frame_number() == framing_frames - 1:
        damage = 0.0
        loop e in enemies: damage += e.hp_max-e.hp
        print("framing production fight: damage={damage:.1} contacts={framing_contacts}")
        # Preserve the full pose evidence even if the encounter minimum fails.
        assert(write_bytes(env("FRAMING_TRACE") ?? "", framing_trace.b))
        assert(framing_scene == "tentfire" or framing_scene == "camp" or framing_contacts >= min(3,framing_count),"scripted encounter must land real weapon contacts for its actor count")
        assert(framing_scene == "tentfire" or damage > 0.0, "scripted fight must land real posed sword contacts")
framing_draw = ():
    draw()
    if framing_scene == "camp" and frame_number() == 300:
        flush()
        assert(save_png(screenshot(),env("FRAMING_CRITIC_PNG") ?? "build/combat-frame300.png"))
main = (): performance_output_run(framing_update,framing_draw)
'''

def equipment_geometry(game, out):
    source = (game/'items.jo').read_text()
    shape = source[source.index('__shape_mesh ='):source.index('shape_meshes:')]
    shape = shape.replace('__shape_mesh = (s: IShape) -> Mesh:', 'framing_shape = (s: IShape) -> MeshB:').replace('    mesh(b.vs, b.idx)', '    b')
    exporter = f"use '{game.resolve()}/gfx.jo'\nuse '{game.resolve()}/items.jo'\nfrom '{game.resolve()}/items.jo' import __mb_plate\nuse '{ROOT}/game/skel.jo'\n" + shape + "\nw = BinW()\nloop s in [IShape.shield, IShape.sword, IShape.club, IShape.spear]:\n    b = framing_shape(s)\n    w_u32(w,b.vs.len())\n    loop v in b.vs: w_v3(w,v.pos)\n    w_u32(w,b.idx.len())\n    loop i in b.idx: w_u32(w,int(i))\nassert(write_bytes(args()[1],w.b))\n"
    (out/'equipment.jo').write_text(exporter)
    subprocess.run(['sloppy/bin/sloppy','build',str(out/'equipment.jo'),'-o',str(out/'equipment')],check=True)
    subprocess.run([str(out/'equipment'),str(out/'equipment.bin')],check=True)
    reader = Reader(out/'equipment.bin'); meshes=[]
    for _ in range(4):
        n, = reader.unpack('I'); points = reader.array(n*3).reshape(-1,3)
        n, = reader.unpack('I'); idx = np.array(reader.unpack(f'{n}I')).reshape(-1,3)
        meshes.append((points,idx))
    return meshes

def rigid(mesh, world, vp):
    points,idx = mesh
    p = np.column_stack((points,np.ones(len(points)))) @ world.T
    clip = p @ vp.T
    uv = (clip[:,:2]/np.maximum(clip[:,3:4],.001)*np.array([1,-1])+1)*np.array([160,90])
    return [(p[:,:3],uv,clip[:,3],idx)]

def visible_fraction(subject, blockers):
    mask = np.isfinite(subject)
    return float((mask & (subject <= blockers+.001)).sum()/max(1,mask.sum()))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',type=Path,default=ROOT/'game')
    parser.add_argument('--output',type=Path,default=ROOT/'build/combat-framing')
    parser.add_argument('--locked', action='store_true', help='caller holds the render lock; never acquire a nested lock')
    parser.add_argument('--capture-only', action='store_true', help='capture now; run --analyze-only after releasing the lock')
    parser.add_argument('--baseline',action='store_true')
    parser.add_argument('--analyze-only',action='store_true')
    parser.add_argument('--scene', choices=['all','flat','slope','doorway','tree','tentfire','camp'], default='all')
    parser.add_argument('--frames', type=int, default=960, help='at least 720 (301 for the README camp); default continues four seconds after the orbit')
    args=parser.parse_args(); os.chdir(ROOT)
    assert (301 if args.scene == "camp" else 720) <= args.frames <= 3600
    out=args.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    assert out.is_relative_to(ROOT/'build'), 'evidence must stay under build/'
    if args.scene == 'all':
        results = {}
        for scene in ('flat','slope','doorway','tree','tentfire','camp'):
            command = [sys.executable, str(Path(__file__).resolve()), '--game', str(args.game.resolve()), '--output', str(out/scene), '--scene', scene, '--frames', str(args.frames)]
            if args.locked: command.append('--locked')
            if args.capture_only: command.append('--capture-only')
            if args.baseline: command.append('--baseline')
            if args.analyze_only: command.append('--analyze-only')
            status = subprocess.run(command).returncode
            results[scene] = {'passed': status == 0}
            measurements = out/scene/'measurements.json'
            if measurements.exists(): results[scene]['measurements'] = json.loads(measurements.read_text())
            (out/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
        assert all(r['passed'] for r in results.values()), 'combat scenario failed; see per-scene evidence'
        print(('PASS captures: ' if args.capture_only else 'PASS combat framing: ') + 'flat, slope, confined ruin doorway, tree-obstructed camera, converging tent-fire crowd, README placed camp (frame 300)')
        return
    render_status = 0
    if not args.analyze_only:
        (out/'frames').mkdir(exist_ok=True)
        (out/'framing.jo').write_text(FIXTURE.replace('{game}',str(args.game.resolve())).replace('{root}',str(ROOT)))
        subprocess.run(['sloppy/bin/sloppy','build',str(out/'framing.jo'),'-o',str(out/'framing')],check=True)
        sources = {str(p.relative_to(args.game.resolve())): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.game.resolve().glob('*.jo'))}
        (out/'sources.json').write_text(json.dumps(dict(game=sources,fixture_sha256=hashlib.sha256((out/'framing.jo').read_bytes()).hexdigest(),executable_sha256=hashlib.sha256((out/'framing').read_bytes()).hexdigest()),indent=2)+'\n')
        env={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_'))}
        # Allow the initial tell and subsequent recovery/windup to play. A
        # constant attack spam could keep the selected foe staggered throughout.
        attacks=','.join(f'{f}:j+,{f+1}:j-' for f in range(150,args.frames-10,90))
        # Start, turn away from lock, move laterally, and orbit both ways while
        # the course's durable foes retain their production AI and contacts.
        env.update(BOTW_SKIP='1',BOTW_AT='-1439,1614,0',BOTW_HOUR='10',BOTW_WEATHER='clear',BOTW_SCALE='1',BOTW_NOVSYNC='1',SLOPPY_PLATFORM='x11',SLOPPY_WINDOW='1280x720',SLOPPY_FRAMES='720',SLOPPY_SCREENSHOT=str(out/'fight720.png'),BOTW_CAPTURE_DIR=str(out/'frames'),BOTW_CAPTURE_EVERY='60',FRAMING_TRACE=str(out/'trace.bin'),FRAMING_SCENE=args.scene,SLOPPY_INPUT='1:k+,200:k-,205:d+,245:d-,260:left+,340:left-,400:right+,510:right-,540:k+,'+attacks)
        env.update(SLOPPY_FRAMES=str(args.frames),FRAMING_FRAMES=str(args.frames),SLOPPY_SCREENSHOT=str(out/f'fight{args.frames}.png'))
        if args.scene == 'camp':
            env.update(BOTW_LANE_TRACE='1', FRAMING_CRITIC_PNG=str(out/'frame300.png'), BOTW_AT='-1439,1606,0', BOTW_GIVE='travelers_sword,travelers_shield', SLOPPY_INPUT='1:k+,1:w+,150:j+,151:j-,165:j+,166:j-,195:j+,196:j-,200:w-,225:j+,226:j-,255:j+,256:j-')
        if args.scene == 'tentfire':
            env.update(BOTW_AT='-955,1964,0', BOTW_TENTFIRE='5', SLOPPY_INPUT='')
        if args.scene == 'doorway':
            # A short sidestep stays in the real portal's walking lane. The
            # outdoor course's forty-frame strafe walks behind its solid jamb.
            env['SLOPPY_INPUT'] = env['SLOPPY_INPUT'].replace('205:d+,245:d-','205:d+,217:d-')
            # The confined course pans across each jamb instead of making the
            # outdoor course's full circles through solid masonry behind Link.
            env['SLOPPY_INPUT'] = env['SLOPPY_INPUT'].replace('260:left+,340:left-','260:left+,280:left-').replace('400:right+,510:right-','400:right+,420:right-')
        command = ['python3','tools/performance_window.py','1280x720','timeout','180',str(out/'framing')]
        if not args.locked: command = ['flock','/tmp/botw-render.lock',*command]
        with (out/'render.log').open('w') as log:
            render_status = subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
        (out/'render-status.json').write_text(json.dumps({'status':render_status,'frames':args.frames})+'\n')
        assert (out/'trace.bin').is_file(), f'no complete trace; render status {render_status}: {out/"render.log"}'
    elif (out/'render-status.json').exists():
        recorded = json.loads((out/'render-status.json').read_text())
        render_status = recorded['status']
        args.frames = recorded['frames']
    if args.capture_only:
        assert render_status == 0, 'capture failed; render log and trace retained'
        print('PASS capture', args.scene, flush=True)
        return
    subprocess.run(['cc','-O2','-shared','-fPIC',str(ROOT/'tools/combat_framing_raster.c'),'-o',str(out/'raster.so'),'-lm'],check=True)
    raster=ctypes.CDLL(str(out/'raster.so')).framing_raster
    raster.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_int]
    raster.restype=None
    exact_gap=ctypes.CDLL(str(out/'raster.so')).framing_mesh_gap
    exact_gap.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int]
    exact_gap.restype=ctypes.c_double
    tri=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]])
    tri_indices=np.array([[0,1,2]],dtype=np.int64)
    shifted=tri+np.array([0.,0.,0.3])
    assert abs(exact_gap(tri.ctypes.data,tri_indices.ctypes.data,1,shifted.ctypes.data,tri_indices.ctypes.data,1)-0.3)<1e-10
    crossing=np.array([[0.2,0.2,-1.],[0.2,0.2,1.],[0.8,0.2,0.]])
    assert exact_gap(tri.ctypes.data,tri_indices.ctypes.data,1,crossing.ctypes.data,tri_indices.ctypes.data,1)<1e-10
    # Calibrate coverage and depth ordering with a 10x10 pixel square.
    square=np.array([[10.,10.,5.],[20.,10.,5.],[20.,20.,5.],[10.,20.,5.]])
    indices=np.array([[0,1,2],[0,2,3]],dtype=np.int64)
    calibrated=np.full((180,320),np.inf)
    raster(square.ctypes.data,indices.ctypes.data,2,calibrated.ctypes.data,320,180)
    assert np.isfinite(calibrated).sum()==100 and np.allclose(calibrated[10:20,10:20],5.,rtol=0,atol=1e-12)
    square[:,2]=3.
    raster(square.ctypes.data,indices.ctypes.data,2,calibrated.ctypes.data,320,180)
    assert np.allclose(calibrated[10:20,10:20],3.,rtol=0,atol=1e-12)
    # BOTW_SKIP equips Old Shirt; hero_draw uses hero.mdl with its hood hidden.
    hero,hero_bones,hero_bind=model(ROOT/'assets/models/hero.mdl')
    foe,foe_bones,foe_bind=model(ROOT/'assets/models/bokoblin.mdl')
    shield,sword,club,spear = equipment_geometry(args.game.resolve(),out)
    trace=Reader(out/'trace.bin'); magic, enemy_count = trace.unpack('II')
    assert magic in (0x46524D32,0x46524D33,0x46524D34,0x46524D35,0x46524D36) and 1 <= enemy_count <= 128
    hit_frames=[]; pause_rows=[]; blade_intersections=[]; body_intersections=[]; previous_damage=0.; visibility=[]; equipment_front=[]; waiting_equipment_front=[]; rows=[]; peak=0.; foreground=0; min_gap=100.; all_overlap=0; min_mesh_gap=100.; min_surface_gap=100.; min_crowd_gap=100.
    head_pairs = []
    waiting_rows = []
    while trace.at < len(trace.data):
        frame,=trace.unpack('I'); vp=trace.matrix(); hp=trace.array(3); hw=trace.matrix(); n,=trace.unpack('I'); hm=trace.array(n)
        hero_head=head_centre(hero,hero_bones,hm,hw,vp)
        hero_mesh=posed(hero,hm,hw,vp); hero_z=depth_mask(hero_mesh,raster); hero_mask=np.isfinite(hero_z)
        hero_points=np.ascontiguousarray(np.vstack([p for p,_,_,_ in hero_mesh]))
        offsets=np.cumsum([0]+[len(p) for p,_,_,_ in hero_mesh])
        hero_indices=np.ascontiguousarray(np.vstack([idx+offsets[k] for k,(_,_,_,idx) in enumerate(hero_mesh)]),dtype=np.int64)
        pause,phase = trace.unpack('ff'); active, = trace.unpack('I'); damage, = trace.unpack('f')
        if damage > previous_damage: hit_frames.append(frame)
        previous_damage=damage
        pause_rows.append(dict(frame=frame,pause=pause,phase=phase,damage=damage))
        target, = trace.unpack('I'); target -= 1
        lock_frames = trace.unpack('I')[0] if magic >= 0x46524D33 else (frame if frame < 200 else max(0,frame-540))
        shield_z = depth_mask(rigid(shield,trace.matrix(),vp),raster)
        sword_mesh = rigid(sword,trace.matrix(),vp)
        sword_z = depth_mask(sword_mesh,raster)
        blade_points = np.ascontiguousarray(sword_mesh[0][0])
        blade_indices = np.ascontiguousarray(sword[1][(sword[0][sword[1],1].min(axis=1) >= .11*.88-1e-5)],dtype=np.int64)
        committed_states=[]
        collidable=[]
        weapon_present=[]
        heads=[]; roots=[]; bodies=[]; weapons=[]; windups=[]; framed=[]; weapon_framed=[]; combined_fraction=[]
        for enemy in range(enemy_count):
            windup, = trace.unpack('I'); windups.append(windup)
            spear_weapon = trace.unpack('I')[0] if magic >= 0x46524D34 else enemy != 0
            committed = trace.unpack('I')[0] if magic >= 0x46524D34 else windup
            waiting_angle = trace.unpack('f')[0] if magic >= 0x46524D34 else -1.
            idle_clip = trace.unpack('I')[0] if magic >= 0x46524D34 else 0
            drawn = trace.unpack('I')[0] if magic >= 0x46524D35 else 3
            collidable.append(bool(drawn & 4) if magic >= 0x46524D36 else bool(drawn & 1))
            weapon_present.append(bool(drawn & 2))
            waiting_rows.append(dict(frame=frame,enemy=enemy,angle_rad=waiting_angle,clip=idle_clip))
            committed_states.append(committed)
            weapon_world = trace.matrix()
            weapon_mesh = rigid(spear if spear_weapon else club,weapon_world,vp) if drawn & 2 else []
            weapon_z = depth_mask(weapon_mesh,raster); weapons.append(weapon_z)
            weapon_uv = np.vstack([uv for _,uv,_,_ in weapon_mesh]) if weapon_mesh else np.array([[-1,-1]])
            weapon_framed.append(bool((weapon_uv.min(axis=0)>[4,4]).all() and (weapon_uv.max(axis=0)<[316,176]).all()))
            pos=trace.array(3); roots.append(pos); ring,=trace.unpack('f'); world=trace.matrix(); n,=trace.unpack('I'); palette=trace.array(n)
            head = head_projection(foe,foe_bones,palette,world,vp) if drawn & 1 else None
            enemy_head = head[0] if head is not None else None
            heads.append(head if float(np.linalg.norm(pos-hp)) < 14.0 else None)
            head_gap=float(np.linalg.norm(enemy_head-hero_head)) if enemy_head is not None and hero_head is not None else None
            mesh=posed(foe,palette,world,vp) if drawn & 1 else []; enemy_z=depth_mask(mesh,raster); body=np.isfinite(enemy_z)
            nearby = float(np.linalg.norm(pos-hp)) < 14.0
            bodies.append(enemy_z)
            combined_fraction.append(float(np.isfinite(np.minimum(enemy_z,weapon_z)).sum()/body.size))
            uv = np.vstack([uv for _,uv,_,_ in mesh]) if mesh else np.array([[-1,-1]])
            framed.append(bool((uv.min(axis=0)>[4,4]).all() and (uv.max(axis=0)<[316,176]).all()))
            fraction=float(body.sum()/body.size); overlap=int((body&hero_mask).sum())
            direction=(pos-hp)*np.array([1,0,1])
            direction/=max(float(np.linalg.norm(direction)),0.001)
            mesh_gap=100.0
            surface_gap=None
            blade_gap=None
            if mesh:
                enemy_points=np.vstack([p for p,_,_,_ in mesh])
                # A positive support-plane gap proves the complete posed
                # triangle sets cannot intersect, including arms and ears.
                mesh_gap=float((enemy_points*direction).sum(axis=1).min()-(hero_points*direction).sum(axis=1).max())
                min_mesh_gap=min(min_mesh_gap,mesh_gap)
                # The plane is a cheap lower bound. Where envelopes overlap,
                # use exact triangle/triangle separation rather than treating
                # arms at different heights as a body intersection.
                if mesh_gap < 0.025:
                    offsets=np.cumsum([0]+[len(p) for p,_,_,_ in mesh])
                    enemy_indices=np.ascontiguousarray(np.vstack([idx+offsets[k] for k,(_,_,_,idx) in enumerate(mesh)]),dtype=np.int64)
                    enemy_points=np.ascontiguousarray(enemy_points)
                    surface_gap=exact_gap(hero_points.ctypes.data,hero_indices.ctypes.data,len(hero_indices),enemy_points.ctypes.data,enemy_indices.ctypes.data,len(enemy_indices))
                    assert np.isfinite(surface_gap)
                    min_surface_gap=min(min_surface_gap,surface_gap)
                    if surface_gap<=.000001: body_intersections.append(dict(frame=frame,enemy=enemy))
                if active:
                    offsets=np.cumsum([0]+[len(p) for p,_,_,_ in mesh])
                    indices=np.ascontiguousarray(np.vstack([idx+offsets[k] for k,(_,_,_,idx) in enumerate(mesh)]),dtype=np.int64)
                    enemy_points=np.ascontiguousarray(enemy_points)
                    gap3=np.maximum(0,np.maximum(enemy_points.min(axis=0)-blade_points.max(axis=0),blade_points.min(axis=0)-enemy_points.max(axis=0)))
                    blade_gap=float(np.linalg.norm(gap3))
                    if blade_gap<=.025:
                        blade_gap=exact_gap(blade_points.ctypes.data,blade_indices.ctypes.data,len(blade_indices),enemy_points.ctypes.data,indices.ctypes.data,len(indices))
                    if blade_gap<=.000001: blade_intersections.append(dict(frame=frame,enemy=enemy))
            front=int((body & hero_mask & (enemy_z<hero_z-0.001)).sum())
            gap=float(np.linalg.norm((pos-hp)[[0,2]])-0.75)
            peak=max(peak,fraction);foreground=max(foreground,front);all_overlap=max(all_overlap,overlap);min_gap=min(min_gap,gap) if collidable[-1] else min_gap
            if args.scene == "camp" and not nearby: continue
            rows.append(dict(frame=frame,enemy=enemy,screen_fraction=fraction,projected_overlap_pixels=overlap,foreground_overlap_pixels=front,capsule_gap_m=gap,head_gap_px=head_gap,hero_head_px=hero_head.tolist() if hero_head is not None else None,enemy_head_px=enemy_head.tolist() if enemy_head is not None else None,selected=enemy==target,lock_frames=lock_frames,support_plane_gap_m=mesh_gap,exact_surface_gap_m=surface_gap,blade_surface_gap_m=blade_gap))
        for i, a in enumerate(heads):
            for j in range(i+1,len(heads)):
                b = heads[j]
                if a is None or b is None: continue
                # Compare horizontal separation independently of vertical gap:
                # vertically stacked heads still read as one two-headed body.
                if not (0 <= a[0][0] <= 1280 and 0 <= b[0][0] <= 1280 and 0 <= a[0][1] <= 720 and 0 <= b[0][1] <= 720): continue
                gap = abs(float(a[0][0]-b[0][0]))
                width = max(a[1],b[1])
                head_pairs.append(dict(frame=frame,a=i,b=j,both_committed=bool(committed_states[i] and committed_states[j]),horizontal_gap_px=gap,head_width_px=width,vertical_gap_px=abs(float(a[0][1]-b[0][1])),clearance_widths=gap/max(width,.001)))
        for i, a in enumerate(roots):
            for j, b in enumerate(roots[i+1:],i+1):
                if not collidable[i] or not collidable[j]: continue
                if np.linalg.norm(a-hp) < 14 and np.linalg.norm(b-hp) < 14 and abs(a[1]-b[1]) < 1.46:
                    min_crowd_gap=min(min_crowd_gap,float(np.linalg.norm((a-b)[[0,2]])-.8))
        scene = np.minimum.reduce([hero_z,shield_z,sword_z]+bodies+weapons)
        foreground_equipment = np.minimum.reduce(weapons)
        obscured = int((hero_mask & (foreground_equipment < hero_z-.001)).sum())
        equipment_front.append(obscured/max(1,int(hero_mask.sum())))
        waiting = [z for i,z in enumerate(weapons) if i != target]
        waiting_z = np.minimum.reduce(waiting) if waiting else np.full_like(hero_z,np.inf)
        waiting_obscured = int((hero_mask & (waiting_z < hero_z-.001)).sum())
        waiting_equipment_front.append(waiting_obscured/max(1,int(hero_mask.sum())))
        for enemy in range(enemy_count):
            blockers=np.minimum.reduce([hero_z,shield_z,sword_z]+[z for i,z in enumerate(bodies) if i!=enemy]+[z for i,z in enumerate(weapons) if i!=enemy])
            visibility.append(dict(frame=frame,enemy=enemy,selected=enemy==target,windup=bool(windups[enemy]),weapon_present=weapon_present[enemy],equipment_screen_fraction=combined_fraction[enemy],body_in_frame=framed[enemy],weapon_in_frame=weapon_framed[enemy],body_pixels=int(np.isfinite(bodies[enemy]).sum()),weapon_pixels=int(np.isfinite(weapons[enemy]).sum()),body_visible=visible_fraction(bodies[enemy],blockers),weapon_visible=visible_fraction(np.where(weapons[enemy]<=bodies[enemy]+.001,weapons[enemy],np.inf),blockers),weapon_self_visible=visible_fraction(weapons[enemy],bodies[enemy]),exposed_weapon_pixels=int((np.isfinite(weapons[enemy]) & (weapons[enemy]<=bodies[enemy]+.001)).sum()),shield_visible=visible_fraction(shield_z,np.minimum.reduce([hero_z,sword_z]+bodies+weapons)),foreground_weapon_hero_pixels=obscured,bystander_weapon_hero_pixels=waiting_obscured))
    paired = [r for r in rows if r['selected'] and r['lock_frames'] >= 60 and args.scene != 'tentfire']
    result=dict(paired_lock_samples=len(paired),paired_middle_third_failures=sum(not (1280/3 <= r['hero_head_px'][0] <= 1280*2/3 and 1280/3 <= r['enemy_head_px'][0] <= 1280*2/3) for r in paired),min_head_gap_px=min(r['head_gap_px'] for r in rows if r['head_gap_px'] is not None),frames=frame+1,samples=len(rows),mask_size=[320,180],max_screen_fraction=peak,max_foreground_overlap_pixels=foreground,max_projected_overlap_pixels=all_overlap,min_capsule_gap_m=min_gap,min_enemy_capsule_gap_m=min_crowd_gap,min_support_plane_gap_m=min_mesh_gap,min_posed_mesh_gap_m=min_surface_gap,method='CPU skinning of every body triangle; two-sided raster at pixel centres with perspective-correct per-pixel depth. No terrain occlusion or dissolve. Body masks separate from real procedural shield/sword/club/spear triangles transformed by production draw sockets; target visibility includes all bodies and equipment. No terrain/dissolve/contact effects.')
    result.update(enemy_head_pair_samples=len(head_pairs),min_enemy_head_horizontal_clearance_widths=min((r['clearance_widths'] for r in head_pairs),default=None),enemy_head_overlap_frames=len({r['frame'] for r in head_pairs if r['clearance_widths'] < 1.0}))
    (out/'head-pairs.json').write_text(json.dumps(head_pairs)+'\n')
    pauses=[]
    for frame in hit_frames:
        held=0
        start=pause_rows[frame]['phase']
        for r in pause_rows[frame:]:
            if r['pause']<=0 or abs(r['phase']-start)>.006: break
            held+=1
        pauses.append(dict(frame=frame,held_frames=held,pause_seconds=pause_rows[frame]['pause']))
    (out/'hit-pauses.json').write_text(json.dumps(pauses,indent=2)+'\n')
    result.update(enemy_count=enemy_count,weapon_contact_count=int(previous_damage),max_equipped_enemy_screen_fraction=max(r["equipment_screen_fraction"] for r in visibility),hit_count=len(hit_frames),min_hit_pause_frames=min((p['held_frames'] for p in pauses),default=0),blade_intersection_frames=len({r['frame'] for r in blade_intersections}),body_intersection_frames=len({r['frame'] for r in body_intersections}),blade_intersections=blade_intersections)
    selected=[r for r in visibility if r['selected'] and r['windup'] ]
    result.update(selected_windup_frames=len(selected),selected_windup_body_clipped_frames=sum(not r['body_in_frame'] for r in selected),selected_windup_weapon_clipped_frames=sum(r['weapon_present'] and not r['weapon_in_frame'] for r in selected),min_selected_windup_body_visible=min((r['body_visible'] for r in selected),default=0),min_selected_windup_weapon_visible=min((r['weapon_visible'] for r in selected if r['exposed_weapon_pixels']>=8),default=0),max_foreground_equipment_hero_fraction=max(equipment_front),max_bystander_equipment_hero_fraction=max(waiting_equipment_front),min_shield_visible=min(r['shield_visible'] for r in visibility if r['body_pixels']>0))
    waiting = [r for r in waiting_rows if r['angle_rad'] >= 0]
    longest = 0
    for enemy in range(enemy_count):
        previous, run = None, 0
        for r in [r for r in waiting_rows if r['enemy'] == enemy]:
            key = r['clip'] if r['angle_rad'] >= 0 and r['clip'] > 0 else None
            run = run + 1 if key is not None and key == previous else (1 if key is not None else 0)
            previous = key
            longest = max(longest, run)
    result.update(waiting_frames=len(waiting),max_waiting_facing_degrees=max((r['angle_rad']*180/np.pi for r in waiting),default=0),max_waiting_single_clip_frames=longest,both_committed_head_pairs=sum(r['both_committed'] for r in head_pairs))
    (out/'waiting.json').write_text(json.dumps(waiting_rows)+'\n')
    if args.scene == 'camp':
        critic = [r for r in head_pairs if r['frame'] == 300]
        result['critic_frame_300'] = critic
    (out/'visibility.json').write_text(json.dumps(visibility)+'\n')
    (out/'measurements.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'frames.json').write_text(json.dumps(rows)+'\n')
    print(json.dumps(result,indent=2),flush=True)
    if args.scene == 'camp':
        assert result['critic_frame_300'], 'README camp frame 300 must include posed nearby enemy heads'
    assert result['frames']==args.frames
    assert render_status == 0, f'production encounter minimum failed ({render_status}); all measurements retained'
    assert selected or args.scene == 'tentfire', 'fixture must capture selected enemy windups'
    if not args.baseline:
        assert result['max_waiting_facing_degrees'] <= 45.001, 'waiting enemy turns its back to Jo'
        assert longest <= 90, 'waiting pose persists longer than 1.5 seconds'
        if args.scene == 'camp':
            assert all(r['clearance_widths'] >= 1 for r in result['critic_frame_300']), 'README camp frame 300 overlaps enemy faces'
        landed=re.search(r'framing production fight: damage=([0-9.]+)',(out/'render.log').read_text())
        assert args.scene == 'tentfire' or (landed and float(landed[1])>0), 'trace must include real posed sword hits'
        assert result['max_equipped_enemy_screen_fraction']<=.06, 'body plus equipment fills more than 6% of screen'
        assert peak<=0.06, 'enemy body fills more than 6% of screen in a frame'
        assert not blade_intersections, 'blade intersects an enemy body'
        assert args.scene == 'tentfire' or result['min_hit_pause_frames']>=3, 'a hit lacks three readable pause frames'
        assert foreground==0, 'enemy body obscures Link'
        assert args.scene == 'tentfire' or len(paired) >= 100, 'fixture must retain steady locked framing samples'
        assert result['paired_middle_third_failures'] == 0, 'locked heads leave the middle third'
        assert result['enemy_head_overlap_frames'] == 0, 'enemy heads overlap horizontally within one posed head width'
        assert result['min_head_gap_px'] >= 40, 'enemy head is within 40 px of Link at 1280x720'
        assert min_crowd_gap >= -0.001, 'enemy capsules interpenetrate'
        assert min_gap>=0.44, 'enemy capsule loses its minimum body gap'
        assert result['selected_windup_body_clipped_frames'] == 0, 'selected windup body leaves viewport'
        assert result['selected_windup_weapon_clipped_frames'] == 0, 'selected windup weapon leaves viewport'
        assert args.scene == 'tentfire' or result['min_selected_windup_body_visible'] >= .80, 'selected windup body hidden by bodies or equipment'
        assert args.scene == 'tentfire' or result['min_selected_windup_weapon_visible'] >= .65, 'selected windup weapon hidden'
        assert result['max_bystander_equipment_hero_fraction'] <= .10, 'bystander weapons obscure Link'
        assert result['max_foreground_equipment_hero_fraction'] <= .20, 'contact weapons obscure more than 20% of Link'
        assert min_surface_gap>0.001, 'posed body meshes intersect'

if __name__=='__main__':main()
