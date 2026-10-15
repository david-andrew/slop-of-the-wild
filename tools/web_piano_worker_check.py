#!/usr/bin/env python3
"""CPU-only production worker/native equivalence; independent of site/prepared builds."""
from pathlib import Path
import os,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(tempfile.mkdtemp(prefix='web-piano-',dir=ROOT/'build'))
(ROOT/'build/web').mkdir(parents=True,exist_ok=True)
subprocess.run(['sloppy/bin/sloppy','build','tools/web_piano_worker.jo','--target','wasm','-o','build/web/piano-worker.html'],cwd=ROOT,check=True)
# Reuse the exact production serializer, changing only its output path. Fresh
# native generation keeps this standalone check safe alongside asset preparation.
source=(ROOT/'game/music.jo').read_text().split('piano_asset_write = () -> bool:',1)[1]
source=source.replace('    path = "assets/prepared/piano-compact.bin"',f'    path = "{OUT}/native.bin"',1)
fixture=OUT/'reference.jo'
fixture.write_text(f"build:\n    opt = release\nuse '{ROOT}/game/music.jo'\nuse '{ROOT}/game/asset_stream.jo'\nuse '{ROOT}/game/audio_assets.jo'\n__audio_state=2\npiano_init()\nreference_write = () -> bool:"+source+'\nassert(reference_write())\n')
subprocess.run(['python3','tools/headless_build.py',str(fixture),'-o',str(OUT/'reference')],cwd=ROOT,check=True)
subprocess.run([str(OUT/'reference')],cwd=ROOT,env=os.environ|{'BOTW_BAKE_ASSETS':'1'},check=True)
subprocess.run(['node','tools/web_piano_worker_check.cjs',str(OUT/'native.bin')],cwd=ROOT,check=True)
