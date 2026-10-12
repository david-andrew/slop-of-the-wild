#!/usr/bin/env python3
"""Refine the shipped fox silhouette without changing topology, rig or influences.

python3 tools/fox_shape_bake.py --source build/round68/before-fox.mdl
The source must be the original 4a1402e model (also shipped through 3ef63a7).
"""
import argparse
import hashlib
import math
from pathlib import Path
import struct
from enemy_model_check import read_model


def smooth(a, b, x):
    t=max(0.,min(1.,(x-a)/(b-a)))
    return t*t*(3-2*t)


def shape(p, joints, weights):
    x,y,z=p
    tail=sum(w for j,w in zip(joints,weights) if 33 <= int(j) <= 40)
    ears=sum(w for j,w in zip(joints,weights) if 11 <= int(j) <= 18)
    head=sum(w for j,w in zip(joints,weights) if int(j)==10)
    bush=tail*smooth(-.23,-.36,z)
    x*=1+.65*bush
    center=.47+(z+.21)*.42
    y+=(y-center)*.22*bush
    y+=.035*ears*smooth(.49,.61,y)
    # Flared cheeks behind the pointed muzzle. The snout tip retains its small nose.
    x*=1+.13*head*smooth(.24,.34,z)*(1-smooth(.43,.54,z))
    return x,y,z


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--output',type=Path,default=Path('assets/models/fox.mdl'))
    args=ap.parse_args()
    data=bytearray(args.source.read_bytes())
    assert hashlib.sha256(data).hexdigest()=='101bc73ab51886b6feaf3d5b0fff4cfe187579fd505087a6fe0243a689f45de5', 'expected original fox model; do not apply twice'
    before=read_model(args.source)
    offset=8
    def u32():
        nonlocal offset
        n,=struct.unpack_from('<I',data,offset);offset+=4;return n
    def skip_string():
        nonlocal offset
        size=u32();offset+=size
    skip_string();skip_string()
    for _ in range(u32()):
        skip_string();offset+=113
    offset+=4
    bounds=offset;offset+=24
    slots,variants=u32(),u32()
    for _ in range(slots*variants):
        w,h=u32(),u32();offset+=w*h*4
    positions=[]
    for _ in range(u32()):
        skip_string();offset+=5
        nv=u32()
        for i in range(nv):
            at=offset+i*80
            v=list(struct.unpack_from('<20f',data,at))
            p=shape(v[:3],v[12:16],v[16:20]); positions.append(p)
            if tuple(v[:3])==p: continue
            # Inverse-transpose of the local deformation preserves authored hard edges.
            eps=1e-5
            cols=[]
            for axis in range(3):
                lo=list(v[:3]);hi=list(v[:3]);lo[axis]-=eps;hi[axis]+=eps
                a,b=shape(lo,v[12:16],v[16:20]),shape(hi,v[12:16],v[16:20])
                cols.append([(b[k]-a[k])/(2*eps) for k in range(3)])
            def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
            cof=[cross(cols[1],cols[2]),cross(cols[2],cols[0]),cross(cols[0],cols[1])]
            n=[sum(cof[j][k]*v[3+j] for j in range(3)) for k in range(3)]
            length=math.sqrt(sum(c*c for c in n))
            struct.pack_into('<6f',data,at,*p,*(c/length for c in n))
        offset+=nv*80
        size=u32();offset+=size*4
    assert offset==len(data)
    struct.pack_into('<6f',data,bounds,*(min(p[k] for p in positions) for k in range(3)),*(max(p[k] for p in positions) for k in range(3)))
    args.output.write_bytes(data)
    after=read_model(args.output)
    assert before['rig']==after['rig'] and len(before['parts'])==len(after['parts'])
    for old,new in zip(before['parts'],after['parts']):
        assert old[:3]==new[:3] and old[4]==new[4]
        for a,b in zip(old[3],new[3]):
            assert a[6:]==b[6:], 'UV, colors or skin weights changed'
            if a[1]<.08: assert a==b, 'sole moved'
    print('PASS fox shape: one draw, 3752 vertices / 1848 triangles; rig, weights, materials and soles unchanged')

if __name__=='__main__':main()
