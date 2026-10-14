#!/usr/bin/env python3
"""Cold/warm/rebuilt startup in one bounded, self-locking short batch."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def measure(binary, out, rebuilt, locked=False):
    out = out.resolve()
    assert out.is_relative_to(ROOT/'build') and not out.is_symlink()
    out.mkdir(parents=True, exist_ok=True)
    if not locked:
        with (out/'batch.log').open('w') as log:
            subprocess.run(['flock','/tmp/botw-render.lock','timeout','150',sys.executable,
                str(ROOT/'tools/round67_startup.py'),'--locked','--rebuilt',str(rebuilt),str(binary),str(out)],
                cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        return json.loads((out/'summary.json').read_text())
    cache = out/'cache'
    cache.mkdir(exist_ok=True)
    (cache/'nvidia').mkdir(exist_ok=True)
    rows = []
    stages = [('cold', binary), *[(f'warm-{i}', binary) for i in range(1, 4)], ('new-build', rebuilt)]
    for name, exe in stages:
        settings = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_','CP_'))}
        settings.update(XDG_CACHE_HOME=str(cache), __GL_SHADER_DISK_CACHE_PATH=str(cache/'nvidia'),
            SLOPPY_PLATFORM='x11', SLOPPY_VULKAN='1', SLOPPY_VSYNC='0', SLOPPY_WINDOW='1280x720',
            SLOPPY_FRAMES='1', SLOPPY_SCREENSHOT=str(out/f'{name}.png'), BOTW_LOADTIME='1',
            BOTW_SKIP='1', BOTW_HOUR='11', BOTW_TIMESCALE='0', BOTW_WEATHER='clear', BOTW_SCALE='1',
            BOTW_SHADER_DIGESTS='1')
        if name == 'cold':
            assert not list(cache.glob('sloppy/*.vkpipelines')), 'use a fresh startup directory'
        with (out/f'{name}.log').open('w') as log:
            subprocess.run([sys.executable,'tools/performance_window.py','1280x720',
                sys.executable,'tools/startup_measure.py','timeout','120',str(exe)],cwd=ROOT,env=settings,stdout=log,stderr=subprocess.STDOUT,check=True)
        text = (out/f'{name}.log').read_text()
        assert all(f'prepared {p}: hit' in text for p in ['terrain','water','farland','structures','textures'])
        rows.append(dict(name=name,load_s=float(re.search(r'loaded in ([\d.]+)s',text)[1]),
            warmup_s=float(re.search(r'render_warmup ([\d.]+)s',text)[1]),
            process_s=float(re.search(r'startup_elapsed_s=([\d.]+)',text)[1]),
            cache_hit='game pipeline cache: hit' in text,
            shader_digests=re.findall(r'^shader digest:.*$',text,re.M),
            loadavg=Path('/proc/loadavg').read_text().strip(), executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
            log=str(out/f'{name}.log')))
        print('startup',name,rows[-1]['load_s'],rows[-1]['warmup_s'],flush=True)
    assert rows[0]['executable_sha256'] != rows[-1]['executable_sha256'], 'rebuild probe must change executable bytes'
    assert rows[0]['shader_digests'] == rows[-1]['shader_digests'], 'unrelated rebuild changed shader bytes'
    assert rows[-1]['cache_hit'], 'new executable did not reuse shared cache'
    result=dict(protocol='1280x720 X11 Vulkan, full scale, prepared assets; fresh local Vulkan/NVIDIA cache directory for cold run; same directory for warm and changed executable; no kernel/system cache flush; render-lock wait excluded',
        runs=rows, warm_median_s=statistics.median(r['load_s'] for r in rows if r['name'].startswith('warm-')),
        cold_s=rows[0]['load_s'], new_build_s=rows[-1]['load_s'])
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def rebuilt_fixture(binary, out):
    """An entry-point-only edit changes the binary without changing shaders."""
    game = out/'fixture/game'
    game.mkdir(parents=True, exist_ok=True)
    scripts = out/'fixture/tools'
    scripts.mkdir(exist_ok=True)
    for p in (ROOT/'game').glob('*.jo'): shutil.copyfile(p,game/p.name)
    shutil.copyfile(ROOT/'tools/performance_output.jo',scripts/'performance_output.jo')
    source = (ROOT/'game/main.jo').read_text().replace('main = (): game_run(update, draw)',
        'main = ():\n    eprint("startup rebuild probe")\n    performance_output_run(update, draw)')
    source += "\nuse '../tools/performance_output.jo'\n"
    (game/'main.jo').write_text(source)
    exe=out/'rebuilt-plateau'
    subprocess.run(['sloppy/bin/sloppy','build',str(game/'main.jo'),'-o',str(exe)],cwd=ROOT,check=True)
    return exe


if __name__ == '__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--locked',action='store_true',help=argparse.SUPPRESS)
    ap.add_argument('--rebuilt',type=Path,help=argparse.SUPPRESS)
    ap.add_argument('binary',type=Path)
    ap.add_argument('output',type=Path)
    a=ap.parse_args()
    os.chdir(ROOT)
    a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    rebuilt = a.rebuilt.resolve() if a.rebuilt else rebuilt_fixture(a.binary,a.output)
    print(json.dumps(measure(a.binary.resolve(),a.output,rebuilt,locked=a.locked),indent=2))
