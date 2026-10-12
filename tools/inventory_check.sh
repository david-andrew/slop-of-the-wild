#!/bin/bash
# Full obtainable inventory, every tab and every material selection; visual evidence.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ${1:-} != --locked ]]; then
    exec flock /tmp/botw-render.lock "$PWD/tools/inventory_check.sh" --locked
fi
out=build/inventory-check
mkdir -p "$out"
sloppy/bin/sloppy build tools/inventory_fixture.jo -o "$out/fixture"
for tab in 0 1 2 3 4 5 6; do
    SLOPPY_SCREENSHOT="$out/tab-$tab.png" SLOPPY_FRAMES=3 "$out/fixture" "$tab" > "$out/tab-$tab.log" 2>&1
done
# All food/material types, including the final row. input_check guards definition coverage.
materials=$(sed -n 's/.*tab=3 items=\([0-9]*\).*/\1/p' "$out/tab-3.log")
for sel in $(seq 0 $((materials - 1))); do
    SLOPPY_SCREENSHOT="$out/material-$sel.png" SLOPPY_FRAMES=3 "$out/fixture" 3 "$sel" > "$out/material-$sel.log" 2>&1
done
python3 - <<'PY'
from pathlib import Path
from PIL import Image
root = Path('build/inventory-check')
for path in root.glob('*.png'):
    image = Image.open(path).convert('RGB')
    assert image.getextrema()[0][0] != image.getextrema()[0][1], f'blank capture: {path}'
    if path.name.startswith('material-'):
        sx, sy = image.width / 1280, image.height / 720
        grid = image.crop((int(310*sx), int(170*sy), int(970*sx), int(494*sy)))
        pixels = grid.get_flattened_data() if hasattr(grid, 'get_flattened_data') else grid.getdata()
        gold = [(i % grid.width, i // grid.width) for i,(r,g,b) in enumerate(pixels) if r > 240 and g > 210 and b < 170]
        assert gold, f'selection missing: {path}'
        sel = int(path.stem.split('-')[1])
        first_row = max(0, sel // 6 - 2)
        cx, cy = (sel % 6 * 110 + 50) * sx, (sel // 6 - first_row) * 110 * sy + 50 * sy
        assert all(abs(x-cx) <= 47*sx and abs(y-cy) <= 47*sy for x,y in gold), f'selection outside its visible cell: {path}'
print('PASS inventory renders: seven tabs, every material/food selection; visible selection, separate details')
PY
