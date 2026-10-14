#!/usr/bin/env python3
"""Build a CPU fixture with software buffers and no display/device/window.

The original test body, main and save/environment semantics are retained. Only
runtime graphics initialization is primed before the body: meshes/textures stay
in CPU memory when model inspection lazily reaches the graphics API. All generated
source stays beside the requested executable under this checkout's build/.
"""
import argparse
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def build(source, output):
    source, output = source.resolve(), output.resolve()
    assert source.is_relative_to(ROOT) and output.is_relative_to(ROOT/'build')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Keep relative import spelling and module names intact. Mixing absolute
    # direct imports with relative helper imports creates separate mutable
    # module instances in the release compiler (e.g. two item/terrain states).
    mirror = output.with_name(output.name+'-headless-src')
    copied = set()
    def copy(path):
        path = path.resolve()
        if path in copied: return
        copied.add(path)
        assert path.is_relative_to(ROOT), 'fixture dependency outside checkout'
        text = path.read_text()
        target = mirror/path.relative_to(ROOT)
        assert target.resolve().is_relative_to(ROOT/'build'), 'refuse to write through a fixture symlink'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(text)
        for match in re.finditer(r"(?m)^\s*(?:use|from|import) '([^']+)'",text):
            dependency = path.parent/match[1]
            if dependency.is_file(): copy(dependency)
    copy(source)
    text = source.read_text()
    header = re.match(r'(?:#[^\n]*\n|\n)*build:\n(?:[ \t]+[^\n]*\n|\n)*', text)
    offset = header.end() if header else 0
    preamble = '# CPU inspection only: do not lazily open a graphics window.\n__win_open = true\n__soft = true\nassert(not __vk)\n'
    fixture = mirror/source.relative_to(ROOT)
    fixture.write_text(text[:offset]+preamble+text[offset:])
    subprocess.run([str(ROOT/'sloppy/bin/sloppy'),'build',str(fixture),'-o',str(output)],cwd=ROOT,check=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('-o','--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.source,args.output)
