#!/usr/bin/env python3
"""Verify a fresh Linux package with existing empty HOME directories, no XDG_CACHE_HOME.

Owns one render flock per launch; never wrap. Extracts, HOME caches, logs, images
and summaries remain under build/. Cold means new application/driver HOME and
new local shader cache, not eviction of system page caches.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--backend', choices=['vulkan', 'opengl', 'both'], default='both')
    a = p.parse_args()
    archive = a.archive.resolve()
    out = a.output.resolve()
    assert archive.is_relative_to(ROOT/'build') and out.is_relative_to(ROOT/'build') and out != ROOT/'build'
    out.mkdir(parents=True, exist_ok=True)
    result = {'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
              'protocol': 'fresh extract per backend; existing empty HOME before cold launch, same HOME for warm launch; XDG_CACHE_HOME absent; Wayland 2133x1200 forest, production dynamic scale, one fixed-frame screenshot; system page caches not flushed', 'runs': []}
    for backend in (['vulkan', 'opengl'] if a.backend == 'both' else [a.backend]):
        case = out/backend
        extract = case/'extract'
        home = case/'home'
        extract.mkdir(parents=True)  # refuse reuse: this must be a fresh extract
        home.mkdir()
        assert not list(home.iterdir())
        subprocess.run(['tar', '-xzf', str(archive), '-C', str(extract)], check=True)
        app = extract/'slop-of-the-wild'
        result[backend+'_executable_sha256'] = hashlib.sha256((app/'slop-of-the-wild').read_bytes()).hexdigest()
        clean = {k: v for k, v in os.environ.items()
                 if not k.startswith(('BOTW_', 'SLOPPY_', 'PROBE_')) and k != 'XDG_CACHE_HOME'}
        for phase in ['cold', 'warm']:
            png = case/(phase+'.png')
            env = {**clean, 'HOME': str(home), 'BOTW_SKIP': '1', 'BOTW_AT': '-1000,1620,3.14',
                   'BOTW_HOUR': '11', 'BOTW_WEATHER': 'clear', 'BOTW_LOADTIME': '1',
                   'SLOPPY_PLATFORM': 'wayland', 'SLOPPY_WINDOW': '1280x720',
                   'SLOPPY_FRAMES': '1', 'SLOPPY_FRAME_STATS': '1', 'SLOPPY_SCREENSHOT': str(png)}
            # Vulkan deliberately exercises the packaged default, including VSYNC.
            if backend == 'opengl': env['SLOPPY_VULKAN'] = '0'
            assert 'XDG_CACHE_HOME' not in env and home.is_dir()
            if phase == 'cold': assert not list(home.iterdir())
            log_path = case/(phase+'.log')
            print('package', backend, phase, flush=True)
            with log_path.open('w') as log:
                subprocess.run(['flock', '/tmp/botw-render.lock', '/usr/bin/time',
                                '-f', 'package_elapsed_s=%e', 'timeout', '-k', '5', '180', './play.sh'],
                               cwd=app, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            text = log_path.read_text()
            assert all(f'prepared {name}: hit' in text for name in ['terrain', 'water', 'farland', 'structures', 'textures'])
            assert 'PNG decodes 0' in text and 'vegetation: 18587 placed' in text
            assert Image.open(png).size == (2133, 1200)
            if backend == 'vulkan':
                cache = home/'.cache/sloppy/slop-of-the-wild.vkpipelines'
                assert cache.is_file() and cache.read_bytes()[:4] == b'SLPC', 'HOME pipeline cache was not saved'
                assert 'vulkan (' in text
            else:
                assert 'dma-buf' in text and 'vulkan (' not in text
            row = {'backend': backend, 'phase': phase,
                   'flags': {k: v for k, v in env.items() if k.startswith(('BOTW_', 'SLOPPY_')) or k == 'HOME'},
                   'xdg_cache_home_present': False,
                   'load_s': float(re.search(r'loaded in ([\d.]+)s', text)[1]),
                   'warmup_s': float(re.search(r'render_warmup ([\d.]+)s', text)[1]),
                   'elapsed_s': float(re.search(r'package_elapsed_s=([\d.]+)', text)[1]),
                   'log_sha256': hashlib.sha256(log_path.read_bytes()).hexdigest(),
                   'home_cache_files': sorted(str(f.relative_to(home)) for f in home.rglob('*') if f.is_file())}
            result['runs'].append(row)
            (out/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
            print(backend, phase, row['load_s'], row['elapsed_s'], flush=True)
    print('PASS fresh package, empty real HOME caches, zero PNG decodes, all prepared packs, 2133x1200')


if __name__ == '__main__': main()
