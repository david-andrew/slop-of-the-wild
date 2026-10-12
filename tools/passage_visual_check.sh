#!/bin/bash
# Full native passage replay, retaining every frame of the mouth reveal (600-900).
# Test-only capture gating avoids hundreds of PNG readbacks before the review interval.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ${1:-} != --locked ]]; then
    exec flock /tmp/botw-render.lock "$PWD/tools/passage_visual_check.sh" --locked "$@"
fi
shift
out=${1:-build/passage-visual}
mkdir -p "$out"
python3 - "$out" <<'PY'
from pathlib import Path
import sys
out=Path(sys.argv[1]).resolve()
game=Path('game').resolve()
s=(game/'main.jo').read_text()
for p in game.glob('*.jo'):
    s=s.replace(f"'{p.name}'",f"'{p}'")
anchor='if __capture_dir != none and __capture_every > 0 and frame_number() > 0'
assert s.count(anchor)==1
s=s.replace(anchor,'if __capture_dir != none and __capture_every > 0 and frame_number() >= 600')
(out/'capture.jo').write_text(s)
for p in out.glob('frame-*.png'): p.unlink()
PY
sloppy/bin/sloppy build "$out/capture.jo" -o "$out/game"
env BOTW_PASSAGE=1 BOTW_NOVSYNC=1 SLOPPY_VSYNC=0 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=960x540 \
    SLOPPY_INPUT=20:w+ BOTW_CAPTURE_DIR="$out" BOTW_CAPTURE_EVERY=1 \
    SLOPPY_SCREENSHOT="$out/final.png" SLOPPY_FRAMES=900 "$out/game" > "$out/run.log" 2>&1
python3 - "$out" <<'PY'
from pathlib import Path
import sys
out=Path(sys.argv[1])
frames=sorted(int(p.stem.split('-')[1]) for p in out.glob('frame-*.png'))
assert frames==list(range(600,901)),frames
print(f'PASS: all 301 passage frames 600-900 captured in {out}')
PY
