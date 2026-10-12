#!/usr/bin/env python3
# Run: python3 tools/enemy_model_check.py (uses the committed pre-round-77 Bokoblin baseline).
"""Check the baked Bonkoblin's mesh and contact contract against a prior asset.

Override: python3 tools/enemy_model_check.py --baseline path/to/prior-bokoblin.mdl
No rendering or GPU context. Rig, body topology, influences, soles and grips are fixed; the head is authored.
"""
import argparse
import hashlib
import math
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
# Parent of the authored head: pin the actual historical asset, never compare
# against the current model itself or an untracked build-directory snapshot.
BASELINE_REV = '9bea708c681e50be1c11aaf278c9f1866e0853a6'


def read_model(path, data=None):
    if data is None:
        data = Path(path).read_bytes()
    offset = 0

    def unpack(fmt):
        nonlocal offset
        value = struct.unpack_from(fmt, data, offset)
        offset += struct.calcsize(fmt)
        return value

    def string():
        nonlocal offset
        size, = unpack('<I')
        value = data[offset:offset + size].decode()
        offset += size
        return value

    assert unpack('<II') == (0x4C444D4A, 1)
    name, skeleton = string(), string()
    bones, = unpack('<I')
    start = offset
    bone_names = []
    for _ in range(bones):
        bone_names.append(string())
        offset += 8 + 1 + 40 + 64
    offset += 4  # translation scale is part of the rig contract
    rig = data[start:offset]
    offset += 24
    slots, variants = unpack('<II')
    textures = []
    for _ in range(slots * variants):
        w, h = unpack('<II')
        textures.append((w, h, hashlib.sha256(data[offset:offset+w*h*4]).digest()))
        offset += w * h * 4
    count, = unpack('<I')
    parts = []
    for _ in range(count):
        part = string()
        slot, sided = unpack('<IB')
        nv, = unpack('<I')
        verts = list(struct.iter_unpack('<20f', data[offset:offset + nv * 80]))
        offset += nv * 80
        ni, = unpack('<I')
        idx = unpack(f'<{ni}I')
        assert ni % 3 == 0, 'incomplete triangle'
        assert ni > 0 and nv > 0, 'empty draw part'
        assert all(i < nv for i in idx), 'invalid triangle index'
        for v in verts:
            assert all(map(math.isfinite, v)), 'nonfinite vertex'
            assert abs(math.sqrt(sum(x*x for x in v[3:6])) - 1) < 2e-4, 'invalid normal'
            assert abs(sum(v[16:20]) - 1) < 1e-5, 'invalid weights'
            assert all(0 <= j < bones for j in v[12:16]), 'invalid joint'
        parts.append((part, slot, sided, verts, idx))
    assert offset == len(data)
    return dict(name=name, skeleton=skeleton, rig=rig, bones=bone_names,
                slots=slots, variants=variants, textures=textures, parts=parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, help=f'Prior model file (default: committed asset at {BASELINE_REV})')
    parser.add_argument('--model', default=ROOT / 'assets/models/bokoblin.mdl', type=Path)
    args = parser.parse_args()
    if args.baseline is None:
        result = subprocess.run(['git', 'show', f'{BASELINE_REV}:assets/models/bokoblin.mdl'],
                                cwd=ROOT, capture_output=True)
        if result.returncode:
            parser.error('committed baseline unavailable; use --baseline path/to/prior-bokoblin.mdl')
        before = read_model(None, result.stdout)
    else:
        if not args.baseline.is_file():
            parser.error(f'baseline not found: {args.baseline}')
        before = read_model(args.baseline)
    after = read_model(args.model)
    for field in ('name', 'skeleton', 'rig', 'bones', 'slots', 'variants'):
        assert before[field] == after[field], f'{field} changed'
    assert len(before['parts']) == len(after['parts']), 'draw count changed'
    assert before['textures'][::before['slots']] == after['textures'][::after['slots']], 'source body variant textures changed'
    contacts = 0
    head = after['bones'].index('Head')
    old_body, new_body = before['parts'][0], after['parts'][0]
    assert old_body[:3] == new_body[:3], 'body material/draw changed'
    def is_head(v):
        return int(v[12]) == head and v[16] >= .5
    def triangles(part):
        return [tuple(part[3][i] for i in part[4][t:t+3]) for t in range(0,len(part[4]),3)]
    expected = [t for t in triangles(old_body) if not all(is_head(v) for v in t)]
    assert triangles(new_body) == expected, 'body/neck topology or attributes changed'
    assert before['parts'][1] == after['parts'][1], 'baked club changed'
    old_extra, new_extra = before['parts'][2], after['parts'][2]
    assert old_extra[:3] == new_extra[:3], 'extras material/draw changed'
    # Original horn, belt and cloth precede the 90 old pupil vertices.
    assert old_extra[3][:-90] == new_extra[3][:len(old_extra[3])-90], 'horn/cloth changed'
    assert old_extra[4][:-384] == new_extra[4][:len(old_extra[4])-384], 'horn/cloth topology changed'
    for v in new_extra[3][len(old_extra[3])-90:]:
        assert v[12:20] == (float(head),0.,0.,0.,1.,0.,0.,0.), 'authored head rig changed'
    for part in after['parts']:
        for v in part[3]:
            if part[0] == 'club' or abs(v[0]) > .72 or v[1] < .14:
                contacts += 1
    for t in triangles(new_extra)[(len(old_extra[4])-384)//3:]:
        a,b,c = t
        u = [b[i]-a[i] for i in range(3)]
        v = [c[i]-a[i] for i in range(3)]
        n = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
        assert sum(x*x for x in n) > 1e-18, 'collapsed authored head triangle'
        assert sum(n[i]*(a[3+i]+b[3+i]+c[3+i]) for i in range(3)) > 0, 'inverted authored head triangle'
    assert sum(len(p[4])//3 for p in after['parts']) <= 8000, 'Bonkoblin triangle budget exceeded'
    verts = sum(len(p[3]) for p in after['parts'])
    tris = sum(len(p[4]) // 3 for p in after['parts'])
    print(f'PASS Bonkoblin: {verts} vertices, {tris} triangles, {len(after["parts"])} parts; unchanged rig/body/club/horn/cloth; {contacts} protected contact vertices')


if __name__ == '__main__':
    main()
