#!/usr/bin/env python3
"""Pack traced runtime inputs, patch boot, and emit a static Pages site."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--packs', default='water,farland,chime,textures')
args = parser.parse_args()
root = Path('.')
site = Path('build/site')
site.mkdir(parents=True, exist_ok=True)
for old in list(site.glob('assets-*.gz')) + list(site.glob('manifest-*.json')):
    old.unlink()
paths = sorted(set(json.loads(Path('build/web-evidence/reads.json').read_text())))
paths = [p for p in paths if not p.startswith('assets/prepared/')]
packs = [f'assets/prepared/{name}.bin' for name in args.packs.split(',') if name]
if 'assets/prepared/textures.bin' in packs:
    # The RGBA pack replaces all decoded startup images (including both UI atlases).
    paths = [p for p in paths if not p.endswith('.png')]
paths += packs
for path in paths:
    if not path.startswith('assets/') or '..' in Path(path).parts or not Path(path).is_file():
        raise SystemExit(f'Invalid or missing traced asset: {path}')
# Captured stamps preserve key validation without stat() in the in-memory filesystem.
stamp_paths = set(paths)
for directory in ('game', 'sloppy/lib'):
    stamp_paths.update(str(p) for p in Path(directory).rglob('*.jo'))
stamp_paths.update(str(p) for p in Path('assets/audio').glob('*.wav'))
stamp_paths.update(str(p) for p in Path('assets/src/nature/Textures').glob('*.png'))
stamp_paths.update(['assets/title.png', 'assets/names.png'])
stamps = {}
for path in sorted(stamp_paths):
    st = Path(path).stat()
    stamps[path] = f'{st.st_size}:{st.st_mtime_ns // 10**9}:{st.st_mtime_ns % 10**9}'
manifest = {'format': 1, 'packs': packs, 'stamps': stamps, 'archives': []}
# Bound compressed downloads with <=64 MiB of raw source per archive; an individual
# prepared record can be larger but must still compress below the Pages file limit.
groups, current, size = [], [], 0
for path in paths:
    n = Path(path).stat().st_size
    if current and size + n > 64 * 1024 * 1024:
        groups.append(current); current, size = [], 0
    current.append(path); size += n
if current:
    groups.append(current)
for i, group in enumerate(groups):
    output = site / f'assets-{i:02}.gz'
    files = []
    with output.open('wb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, compresslevel=6, mtime=0) as zipped:
            for path in group:
                data = Path(path).read_bytes()
                zipped.write(data)
                files.append({'path': path, 'bytes': len(data)})
    size = output.stat().st_size
    if size >= 100_000_000:
        raise SystemExit(f'Pages file limit exceeded: {output} ({size} bytes)')
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    hashed = output.with_name(f'assets-{i:02}-{digest[:16]}.gz')
    output.rename(hashed)
    manifest['archives'].append({'url': hashed.name, 'bytes': size,
        'sha256': digest, 'files': files})
manifest_text = json.dumps(manifest, separators=(',', ':'))
manifest_name = 'manifest-' + hashlib.sha256(manifest_text.encode()).hexdigest()[:16] + '.json'
(site / manifest_name).write_text(manifest_text)
html = Path('build/web/raw.html').read_text()
marker = '// start the program once all runtime modules are registered'
if html.count(marker) != 1 or html.count('try { sloppy.run(bin); }') != 1:
    raise SystemExit('Sloppy boot changed; update web postprocessor')
html = html.replace(marker, Path('tools/web_loader.js').read_text() + '\n' + marker)
html = html.replace('try { sloppy.run(bin); }', 'try { botwBoot(bin); }')
html = html.replace("fetch('manifest.json')", f"fetch('{manifest_name}')")
ui = '''<style>
#botw-loading {position:fixed;inset:0;z-index:10;background:#101411;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;font:16px system-ui}
#botw-loading[hidden],#botw-fullscreen[hidden]{display:none}
#botw-progress{width:240px;height:8px;margin-top:12px;accent-color:#ddd}
#botw-fullscreen{position:fixed;right:12px;top:12px;z-index:2;color:#fff;background:#18221ccc;border:1px solid #aaa;border-radius:4px;padding:6px 10px;cursor:pointer}
</style><div id="botw-loading" role="status"><span id="botw-status">Loading 0%</span><progress id="botw-progress" max="100" value="0"></progress></div>
<button id="botw-fullscreen" hidden onclick="document.getElementById('sloppy-canvas').requestFullscreen().catch(console.error)">Fullscreen</button>'''
html = html.replace('<body>', '<body>' + ui)
(site / 'index.html').write_text(html)
(site / 'manifest.json').write_text(manifest_text)
(site / '.nojekyll').touch()
size = sum(p.stat().st_size for p in site.iterdir() if p.is_file())
if size >= 1_000_000_000:
    raise SystemExit('Pages site size limit exceeded')
print(json.dumps({'siteBytes': size, 'downloadBytes': size,
    'assetBytes': sum(a['bytes'] for a in manifest['archives']), 'files': len(paths),
    'archives': len(groups), 'packs': packs}, indent=2))
