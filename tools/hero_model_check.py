#!/usr/bin/env python3
"""Validate baked hero geometry; optionally compare contacts with a prior model directory.

python3 tools/hero_model_check.py --baseline build/round58/before/assets/models
No window or GPU context. Reads the production MDL v1 layout in game/skel.jo.
"""
from collections import Counter, defaultdict
import argparse
import math
from pathlib import Path
import struct


class Model:
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        self.pos = 0
        assert (self.u32(), self.u32()) == (0x4C444D4A, 1), path
        self.name, self.skeleton = self.string(), self.string()
        self.bone_count = self.u32()
        start = self.pos
        self.bone_names, self.parents, self.bind = [], [], []
        for _ in range(self.bone_count):
            self.bone_names.append(self.string())
            self.parents.append(struct.unpack_from('<i', self.data, self.pos)[0])
            self.pos += 8 + 1 + 40
            matrix = struct.unpack_from('<16f', self.data, self.pos)
            self.pos += 64
            # Rigid inverse-bind: recover the unchanged joint origin.
            self.bind.append(tuple(-sum(matrix[c*4+r]*matrix[12+r] for r in range(3))
                                   for c in range(3)))
        self.bones = self.data[start:self.pos]
        self.pos += 4 + 24  # translation scale and bounds
        slots, variants = self.u32(), self.u32()
        for _ in range(slots * variants):
            width, height = self.u32(), self.u32()
            self.pos += width * height * 4
        self.parts = []
        self.indices = []
        for _ in range(self.u32()):
            name = self.string()
            self.pos += 5  # texture slot and sidedness
            count = self.u32()
            vertices = list(struct.iter_unpack('<20f', self.data[self.pos:self.pos + count * 80]))
            self.pos += count * 80
            count = self.u32()
            indices = struct.unpack_from(f'<{count}I', self.data, self.pos)
            assert all(i < len(vertices) for i in indices), 'invalid triangle index'
            self.pos += count * 4
            self.parts.append((name, vertices))
            self.indices.append(indices)
        assert self.pos == len(self.data), 'truncated or trailing model data'

    def u32(self):
        value = struct.unpack_from('<I', self.data, self.pos)[0]
        self.pos += 4
        return value

    def string(self):
        size = self.u32()
        value = self.data[self.pos:self.pos + size].decode()
        self.pos += size
        return value


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline', type=Path)
parser.add_argument('--models', type=Path, default=Path('assets/models'))
args = parser.parse_args()
for name in ('hero', 'hero_bare'):
    model = Model(args.models / f'{name}.mdl')
    count = 0
    for part, vertices in model.parts:
        for v in vertices:
            assert all(map(math.isfinite, v)), 'non-finite vertex'
            assert abs(math.sqrt(sum(n * n for n in v[3:6])) - 1) < 1e-4, 'invalid normal'
            assert min(v[16:20]) >= 0 and abs(sum(v[16:20]) - 1) < 1e-5, 'invalid skin weights'
            assert all(0 <= j < model.bone_count for j in v[12:16]), 'invalid joint'
        count += len(vertices)
    # Welded leg surfaces must retain matching influences through all poses.
    # UV duplication is allowed; the bare skin also needs continuous normals
    # and a closed surface. Dressed leather keeps its intentional hard edges.
    seams = defaultdict(list)
    edges = Counter()
    for (_, vertices), indices in zip(model.parts, model.indices):
        keys = [tuple(round(c, 5) for c in v[:3]) for v in vertices]
        for v, key in zip(vertices, keys):
            if 0.08 < v[1] < 0.80:
                seams[key].append(v)
        if name == 'hero_bare':
            for a, b, c in zip(indices[::3], indices[1::3], indices[2::3]):
                for i, j in ((a, b), (b, c), (c, a)):
                    if max(vertices[i][1], vertices[j][1]) < 0.80:
                        edges[tuple(sorted((keys[i], keys[j])))]+=1
    for group in seams.values():
        def weights(v):
            result = defaultdict(float)
            for joint, weight in zip(v[12:16], v[16:20]):
                if weight: result[int(joint)] += weight
            return dict(result)
        first = weights(group[0])
        for v in group[1:]:
            other = weights(v)
            assert all(abs(first.get(j, 0)-other.get(j, 0)) < 1e-5
                       for j in first.keys() | other.keys()), 'leg seam weights split'
            if name == 'hero_bare':
                assert math.dist(v[3:6], group[0][3:6]) < 0.001, 'bare leg normals split'
    if name == 'hero_bare':
        assert edges and all(n == 2 for n in edges.values()), 'open/nonmanifold bare leg seam'
    seam_count = sum(len(group)>1 for group in seams.values())
    print(f'PASS {name} leg seams: {seam_count} coincident groups, matching skin weights'
          + ('; closed surface and unified normals' if name == 'hero_bare' else '; leather creases retained'))
    if name == 'hero_bare':
        # The round-63 radial shaping inflated the upper-arm cap into a second
        # mass behind the raised arm. Keep both caps inside the slim envelope
        # around this model's unchanged bind-space humerus axis (metres).
        for side in (-1, 1):
            cap = [v for _, vertices in model.parts for v in vertices
                   if 0.205 < side * v[0] < 0.275 and 1.20 < v[1] < 1.39]
            assert len(cap) > 100, 'missing deltoid surface'
            radius = max(math.hypot(v[1] - 1.295849, v[2] + 0.060) for v in cap)
            assert radius < 0.045, f'inflated deltoid cap: {radius:.6f} m'
            # Radius alone permits a round upper arc that still hangs behind
            # the armpit. The distal cap must taper onto the upper arm.
            upper_arc = max(v[1] - 1.295849 for v in cap if side * v[0] > 0.225)
            assert upper_arc < 0.025, f'rounded posterior deltoid belly: {upper_arc:.6f} m'
    hair = [v for _, vertices in model.parts for v in vertices if v[11] < .1]
    assert len(hair) > 100, 'missing baked hair material mask'
    assert all(v[11] > .999 for part, vertices in model.parts for v in vertices
               if part != 'tail' and v[1] < 1.10), 'hair mask leaked into body/cloth'
    detail = ''
    if args.baseline:
        before = Model(args.baseline / f'{name}.mdl')
        assert before.bones == model.bones, 'skeleton/socket transforms changed'
        assert len(before.parts) == len(model.parts), 'draw count changed'
        worst = 0.0
        finger_before = finger_after = 0.0
        palm_contacts = 0
        for (part, vertices), (old_part, old_vertices) in zip(model.parts, before.parts):
            assert part == old_part
            if part == 'tail':
                continue  # new hair geometry shares the existing draw
            assert len(vertices) >= len(old_vertices), 'original vertex order must be retained'
            for a, b in zip(vertices, old_vertices):
                shoulder = name == 'hero_bare' and 0.96 < b[1] < 1.43 and abs(b[0]) < 0.44
                if not shoulder:
                    assert a[12:20] == b[12:20], 'influences changed outside shoulder girdle'
                delta = math.dist(a[:3], b[:3])
                worst = max(worst, delta)
                if b[1] < 0.08:
                    assert delta == 0, 'sole vertices moved'
                if abs(b[0]) > 0.64:
                    assert delta < 0.014, 'hand shaping exceeds 14 mm envelope'
                    assert a[12:20] == b[12:20], 'hand influences changed'
                    joint = int(b[12])
                    joint_name = model.bone_names[joint]
                    origin = model.bind[joint]
                    if any(finger in joint_name for finger in ('index', 'middle', 'ring', 'pinky', 'thumb')):
                        children = [j for j, parent in enumerate(model.parents) if parent == joint]
                        end = model.bind[children[0]] if children else model.bind[model.parents[joint]]
                        axis = tuple(t-o for t, o in zip(end, origin))
                        size = math.sqrt(sum(v*v for v in axis))
                        axis = tuple(v/size for v in axis)
                        def radius(vertex):
                            d = tuple(v-o for v, o in zip(vertex[:3], origin))
                            along = sum(v*n for v, n in zip(d, axis))
                            return math.sqrt(sum((v-along*n)**2 for v, n in zip(d, axis)))
                        finger_before += radius(b)
                        finger_after += radius(a)
                    elif joint_name.startswith('hand_') and b[16] > .999 and b[1] <= origin[1]-.010:
                        assert delta < .001, 'supporting palm surface moved over 1 mm'
                        palm_contacts += 1
            for a in vertices[len(old_vertices):]:
                assert name == 'hero_bare' and 0.93 < a[1] < 1.45 and abs(a[0]) < 0.48, 'new body loops outside shoulder girdle'
        assert finger_before > 0 and finger_after <= finger_before*1.001, 'finger sections became heavier'
        if name == 'hero_bare':
            assert palm_contacts > 0, 'missing supporting palm surface'
        print(f'PASS {name} hands: finger radius {finger_after/finger_before:.1%} of baseline; '
              f'{palm_contacts} bare supporting palm vertices within 1 mm')
        detail = f'; unchanged skeleton/socket transforms, soles and non-shoulder influences; hand shaping <14 mm; max adjustment {worst:.6f} m'
    print(f'PASS {name}: {count} vertices, finite unit normals and valid skin weights{detail}')
