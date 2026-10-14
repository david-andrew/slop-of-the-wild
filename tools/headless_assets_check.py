#!/usr/bin/env python3
"""Run all asset bakers with graphics/window dlopen forbidden and no display.

Copy current tracked inputs (including working edits) into a temporary checkout
so no existing packs or build products can mask a failure or be overwritten.
An empty LD_LIBRARY_PATH alone would still allow installed system GL libraries.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def graphics_guard(directory):
    directory = Path(directory).resolve()
    guard = directory / 'no-graphics.so'
    subprocess.run(['cc', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror',
                    str(ROOT / 'tools/no_graphics.c'), '-o', str(guard), '-ldl'], check=True)
    empty = directory / 'empty-libs'
    empty.mkdir()
    env = {k: v for k, v in os.environ.items()
           if k not in ('DISPLAY', 'WAYLAND_DISPLAY', 'LD_PRELOAD')
           and not k.startswith(('BOTW_', 'SLOPPY_'))}
    env.update(LD_PRELOAD=str(guard), LD_LIBRARY_PATH=str(empty))
    # Positive controls: the guard must reject both the reported GLES dependency
    # and a window library, even if neither is installed on the test host.
    for library in ('libGLESv2.so.2', 'libX11.so.6'):
        probe = subprocess.run([sys.executable, '-c',
                                'import ctypes; ctypes.CDLL(' + repr(library) + ')'],
                               env=env, capture_output=True, text=True)
        assert probe.returncode == 86 and library in probe.stderr, probe
    return env


def main():
    scratch = ROOT / 'build/headless-assets-check'
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as directory:
        temporary = Path(directory)
        checkout = temporary / 'checkout'
        paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
        for name in filter(None, paths):
            if not name.startswith(('tools/', 'game/', 'sloppy/', 'assets/')):
                continue
            target = checkout / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        env = graphics_guard(temporary)
        subprocess.run(['tools/prepare_assets.sh'], cwd=checkout, env=env, check=True)
        for pack in ('world', 'terrain', 'water', 'farland', 'structures', 'sfx',
                     'piano-compact', 'chime', 'textures', 'enemy-contacts', 'blade-hero', 'blade-hero_bare'):
            assert (checkout / f'assets/prepared/{pack}.bin').stat().st_size > 0, pack
    print('PASS headless asset preparation: fresh packs, no GL/Vulkan/window libraries or display')


if __name__ == '__main__':
    main()
