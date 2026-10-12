#!/usr/bin/env python3
"""Round 72 matched character/material evidence. Captures own flock; do not wrap.

prepare before|after; capture before|after [views]; variants-batch before|after
[--remaining]. The batch owns one flock; children never reacquire it. All assets and source baseline
come from bcccdbb. Variant overrides exercise identical camp/combat poses without
changing enemy AI or production variant selection.
"""
import sys
import subprocess
import round71_character_check as prior
base = prior.base
base.OUT = base.ROOT / 'build/round72'
base.BASELINE = 'bcccdbb'
base.VIEWS = {k:v for k,v in base.VIEWS.items() if k != 'night'}

def prepare(phase):
    base.prepare(phase)
    game = base.game_dir(phase)
    source = (game/'main.jo').read_text()
    import re
    source = re.sub(r"(?m)^(use|from) '([^']+)'",lambda m:f"{m[1]} '{game/m[2]}'",source)
    # Override only the texture selector in a private copy of chars.jo. The
    # simulation, cameras, meshes, enemy type and all other draws stay identical.
    chars = (game/'chars.jo').read_text()
    chars = re.sub(r"(?m)^(use|from) '([^']+)'",lambda m:f"{m[1]} '{game/m[2]}'",chars)
    chars = chars.replace('p.variant = 1', 'p.variant = 1\n                if let forced = env("ROUND72_VARIANT"): p.variant = to_int(forced) ?? p.variant')
    out = base.OUT/phase
    (out/'chars.jo').write_text(chars)
    source = source.replace(str(game/'chars.jo'),str(out/'chars.jo'))
    (out/'variant.jo').write_text(source)
    base.build(out/'variant.jo',out/'variant-game')

def capture(phase,names):
    for name in names or base.VIEWS:
        flags,frame = base.VIEWS[name]
        base.render(phase,name,base.OUT/phase/'game-bin',dict(BOTW_HOUR='11',BOTW_WEATHER='clear',SLOPPY_FRAMES=str(frame),**flags),True)

def variants(phase,names):
    for view in names or ('blue-camp','combat'):
        flags,frame = base.VIEWS[view]
        for variant,name in enumerate(('red','blue','black','green')):
            if '--remaining' in sys.argv and (base.OUT/phase/f'{view}-{name}.png').exists(): continue
            base.render(phase,f'{view}-{name}',base.OUT/phase/'variant-game',dict(BOTW_HOUR='11',BOTW_WEATHER='clear',SLOPPY_FRAMES=str(frame),ROUND72_VARIANT=str(variant),**flags),True)

if __name__ == '__main__':
    mode,phase = sys.argv[1:3]
    if mode == 'prepare': prepare(phase)
    elif mode == 'capture': capture(phase,sys.argv[3:])
    elif mode == 'variants': variants(phase,sys.argv[3:])
    elif mode == 'variants-batch':
        if '--locked' not in sys.argv:
            subprocess.run(['flock','/tmp/botw-render.lock',sys.executable,__file__,*sys.argv[1:],'--locked'],check=True)
        else:
            base.LOCKED = True
            variants(phase,[a for a in sys.argv[3:] if not a.startswith('--')])
