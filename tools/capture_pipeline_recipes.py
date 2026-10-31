#!/usr/bin/env python3
"""Observe production warmup recipes in a private fixture. Owns one render lock.

Writes candidate Sloppy source under build/ for review and cold-cache validation;
never changes production recipes or the vendored runtime. Do not wrap in flock.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text, old, new):
    assert text.count(old) == 1, f'production anchor changed: {old}'
    return text.replace(old, new)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    os.chdir(ROOT)
    out = args.output.resolve()
    assert out.is_relative_to(ROOT/'build') and out != ROOT/'build'
    assert not out.exists(), 'use a fresh directory under build/'
    game = out/'game'
    game.mkdir(parents=True)
    scripts = out/'tools'
    scripts.mkdir()
    hashes = {}
    for path in sorted((ROOT/'game').glob('*.jo')):
        assert not path.is_symlink(), f'refuse a linked game input: {path}'
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copyfile(path, game/path.name)
    shutil.copyfile(ROOT/'tools/performance_output.jo', scripts/'performance_output.jo')
    path = game/'main.jo'
    path.write_text(replace_once(path.read_text(), 'main = (): game_run(update, draw)',
        "use '../tools/performance_output.jo'\nmain = (): performance_output_run(update, draw)"))
    path = game/'shader_load.jo'
    path.write_text(replace_once(path.read_text(), '        sh = make_shader(s)\n',
        '        sh = make_shader(s)\n        eprint("recipe shader: {sh.prog} {__str_hash(s.vs_spirv)}:{__str_hash(s.fs_spirv)}")\n'))
    path = game/'pipeline_warmup.jo'
    path.write_text(replace_once(path.read_text(), '        __game_pipeline_loading=false',
        '        loop i in 0.. and p in __vgp: eprint("recipe keys: {i} {p.pipelines.keys()}")\n        __game_pipeline_loading=false'))
    binary = out/'plateau'
    with (out/'build.log').open('w') as log:
        subprocess.run(['sloppy/bin/sloppy','build',str(game/'main.jo'),'-o',str(binary)],
                       stdout=log,stderr=subprocess.STDOUT,check=True)
    env = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_','CP_','PROBE_'))}
    env.update(SLOPPY_PLATFORM='x11',SLOPPY_VULKAN='1',SLOPPY_VSYNC='0',SLOPPY_WINDOW='2133x1200',
        SLOPPY_FRAMES='1',SLOPPY_SCREENSHOT=str(out/'frame.png'),BOTW_SKIP='1',BOTW_SCALE='1',
        BOTW_LOADTIME='1',BOTW_HOUR='11',BOTW_TIMESCALE='0',BOTW_WEATHER='clear')
    command = ['flock','/tmp/botw-render.lock',sys.executable,'tools/performance_window.py',
               '2133x1200','timeout','90',str(binary)]
    with (out/'run.log').open('w') as log:
        subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    text = (out/'run.log').read_text()
    shaders = {int(i):digest for i,digest in re.findall(r'^recipe shader: (\d+) ([\d:]+)$',text,re.M)}
    keys = {int(i):json.loads(values) for i,values in re.findall(r'^recipe keys: (\d+) (\[[\d, ]*\])$',text,re.M)}
    assert shaders and keys, 'missing shader or pipeline inventory'
    recipes = {}
    for program, digest in shaders.items():
        if keys.get(program): recipes[digest] = sorted(set(recipes.get(digest,[]) + keys[program]))
    assert all(hashlib.sha256((ROOT/'game'/name).read_bytes()).hexdigest()==value for name,value in hashes.items()), 'game inputs changed during capture'
    header = (ROOT/'game/pipeline_recipes.jo').read_text().split('game_pipeline_recipes:',1)[0]
    source = header + 'game_pipeline_recipes: {str: int[]} = {\n'
    source += ''.join(f'    "{digest}": {values},\n' for digest,values in recipes.items()) + '}\n'
    (out/'pipeline_recipes.jo').write_text(source)
    report = dict(game_sha256=hashes,command=command,
        environment={k:v for k,v in env.items() if k.startswith(('BOTW_','SLOPPY_'))},recipes=recipes,
        programs=len(recipes),variants=sum(map(len,recipes.values())),executable_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Observed {report["programs"]} canonical programs / {report["variants"]} variants: {out/"pipeline_recipes.jo"}')
    print('Review this candidate and validate fresh-cache startup/transition coverage before copying it into game/.')


if __name__ == '__main__':
    main()
