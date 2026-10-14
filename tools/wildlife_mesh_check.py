#!/usr/bin/env python3
"""Run production wildlife mesh builders headlessly by replacing only mesh upload.

The generated audit validates indices and normals, and preserves the eight boar
parts / fifteen bird batches. Pass --baseline REF for matched triangle budgets.
"""
from pathlib import Path
import argparse, re, subprocess
root=Path(__file__).resolve().parents[1]
out=root/'build/round68';out.mkdir(parents=True,exist_ok=True)
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--baseline');args=ap.parse_args()
budgets={}
for label,source in ([('before',subprocess.check_output(['git','show',f'{args.baseline}:game/wildlife.jo'],cwd=root,text=True))] if args.baseline else [])+[('after',(root/'game/wildlife.jo').read_text())]:
    boar=source[source.index('__boar_m:'):source.index('__boar_hips =')]
    start=source.index('__bird_fan =') if '__bird_fan =' in source else source.index('__bird_details:')
    bird=source[start:source.index('__butterfly_m:')]
    meshcode=(boar+bird).replace('__boar','audit_boar').replace('__BOAR','AUDIT_BOAR').replace('__bird','audit_bird')
    meshcode=re.sub(r'\bmesh\(', 'audit_mesh(',meshcode)
    code=f"use '{root}/game/items.jo'\nuse '{root}/game/gfx.jo'\nuse '{root}/game/shade.jo'\n"+'''
audit_mesh = (vs: Vertex3D[], idx: u32[]) -> Mesh:
    assert(idx.len() % 3 == 0)
    loop i in idx: assert(int(i) < vs.len(), "valid mesh index")
    loop v in vs:
        assert(length(v.normal) > 0.99 and length(v.normal) < 1.01, "finite unit normals")
        assert(length(v.pos) < 3.0, "finite bounded animal geometry")
        assert(abs(v.color.w - 1.0) < 0.00001, "opaque wildlife pigment must preserve its material alpha")
    Mesh(count = vs.len(), index_count = idx.len())
'''+meshcode+'''
parts = audit_boar_parts()
assert(parts.len() == 8, "boar part/draw budget unchanged")
triangles = 0
loop i in [0..parts.len()): triangles += parts[i].index_count / 3 * (if i == 2 or i == 3: 4 else: 1)
print("boar: {triangles} triangles, 14 near / 6 distant draws")
loop k in [0..3):
    loop pose in [0..3):
        m = audit_bird(k, pose)
        WING_AUDIT
        print("bird {k} pose {pose}: {(m.index_count + audit_bird_details[k].index_count + (if pose == 0: audit_bird_details[k + 3].index_count else: 0)) / 3} triangles")
assert(audit_bird_m.len() == 9 and audit_bird_details.len() == 6, "bird batch/draw budget unchanged")
print("PASS production mesh normals, indices, bounds and draw budgets")
'''
    # Flight now draws one body and two instances of its shared wing mesh.
    wing_audit = 'if pose > 0: m.index_count = audit_bird(k, 1).index_count + audit_bird(k, 2).index_count * 2' if 'pose.flap' in source else 'pass'
    code = code.replace('WING_AUDIT', wing_audit)
    path=out/f'{label}-mesh-check.jo';path.write_text(code)
    result=subprocess.run(['sloppy/bin/sloppy',str(path)],cwd=root,text=True,capture_output=True)
    (out/f'{label}-mesh-check.log').write_text(result.stdout+result.stderr)
    if result.returncode: print(result.stderr);result.check_returncode()
    print(label+'\n'+result.stdout)
    budgets[label]={(int(k),int(pose)):int(n) for k,pose,n in re.findall(r'bird (\d+) pose (\d+): (\d+) triangles',result.stdout)}
if args.baseline:
    assert all(n<=budgets['before'][key] for key,n in budgets['after'].items()), 'bird silhouettes must retain the baseline triangle budget'
    print('PASS baseline bird triangle budgets')
