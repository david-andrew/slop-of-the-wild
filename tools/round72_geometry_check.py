#!/usr/bin/env python3
"""Compare exact procedural geometry/rig/index streams. Owns each render's flock."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
from round72_character_check import base


def prepare():
    for phase in ('before','after'):
        out = base.OUT/phase/'geometry'
        game = out/'game'
        game.mkdir(parents=True,exist_ok=True)
        for source in base.game_dir(phase).glob('*.jo'):
            shutil.copyfile(source,game/source.name)
        monk = game/'shrine_monk.jo'
        s = monk.read_text()
        needle = '    m = Model(name = "ascetic"'
        pos = s.index(needle)
        s = s[:pos]+'''    evidence=BinW()
    loop v in vs:
        q=v
        q.col=vec4(0,0,0,0)
        w_raw(evidence,[q])
    w_raw(evidence,b.idx)
    assert(write_bytes(env("ROUND72_GEOMETRY")!+"/monk.bin",evidence.b))
    print("monk geometry: {vs.len()} vertices {b.idx.len()/3} triangles 1 part")
'''+s[pos:]
        monk.write_text(s)
        path = game/'structures.jo'
        s = path.read_text()
        needle = '        __bchunks[key]=b\n'
        assert s.count(needle)==1
        s = s.replace(needle,needle+'''        evidence=BinW()
        w_u32(evidence,first)
        w_u32(evidence,b.verts.len()-first)
        loop j in [first..b.verts.len()):
            v=b.verts[j]
            w_v3(evidence,v.pos)
            w_v3(evidence,v.normal)
            w_v4(evidence,v.mat)
            w_v3(evidence,v.light)
        w_raw(evidence,b.idx)
        assert(write_bytes(env("ROUND72_GEOMETRY")!+"/husk-{key}.bin",evidence.b))
        print("husk geometry: {key} {b.verts.len()-first} vertices, chunk indices {b.idx.len()}")
''')
        s="use 'skel.jo'\n"+s
        path.write_text(s)
        fixture=out/'probe.jo'
        fixture.write_text(f"build:\n    opt = release\nuse '{game/'main.jo'}'\nuse '{game/'shrine_monk.jo'}'\nmain = ():\n    shrine_monk_model()\n    print(\"geometry capture complete\")\n")
        base.build(fixture,out/'probe')


def run():
    for phase in ('before','after'):
        out=base.OUT/phase/'geometry'
        env={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_'))}
        env.update(BOTW_SKIP='1',BOTW_NO_PREPARED_ASSETS='1',SLOPPY_PLATFORM='x11',ROUND72_GEOMETRY=str(out))
        with (out/'run.log').open('w') as log:
            subprocess.run(['flock','/tmp/botw-render.lock','timeout','120',str(out/'probe')],env=env,cwd=base.OUT/'before' if phase=='before' else base.ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    before=base.OUT/'before/geometry';after=base.OUT/'after/geometry'
    names={p.name for p in before.glob('*.bin')}
    assert len(names)>1 and 'monk.bin' in names
    assert names=={p.name for p in after.glob('*.bin')}
    for name in sorted(names):
        assert (before/name).read_bytes()==(after/name).read_bytes(),name
    print(f'PASS: monk and {len(names)-1} husk chunks preserve positions, normals, UVs, rigs, weights, indices and material/draw grouping')

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':run()
