#!/usr/bin/env python3
"""Build a capture-only game that keeps shrine state active in free-camera mode.

Usage: python3 tools/round87_shrine_inspector.py GAME_DIR OUTPUT_BINARY
The ordinary game's free camera skips gameplay updates, including shrine
visibility. Preserve its renderer and camera but run the real shrine update
when inspecting upward. No production source is modified; no render is started.
"""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
game = Path(sys.argv[1]).resolve()
binary = Path(sys.argv[2]).resolve()
binary.parent.mkdir(parents=True, exist_ok=True)
source = (game / 'main.jo').read_text()
for path in game.glob('*.jo'):
    source = source.replace(f"'{path.name}'", f"'{path}'")
assert 'update = (dt0: f64):' in source
source = source.replace('update = (dt0: f64):', 'production_update = (dt0: f64):')
source += '''
# Capture-only: free camera otherwise returns before the real shrine update.
update = (dt: f64):
    production_update(dt)
    if free_cam: shrines_update(1.0 / 60.0)
'''
wrapper = binary.with_suffix('.jo')
wrapper.write_text(source)
subprocess.run([str(root/'sloppy/bin/sloppy'), 'build', str(wrapper), '-o', str(binary)], cwd=root, check=True)
