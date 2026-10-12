#!/usr/bin/env python3
"""Count physical source lines by primary system (includes comments and blank lines).

Run from any directory. --files shows the whole-file assignments; --json is machine-readable.
Mixed modules belong to one system, so each game/*.jo file is counted exactly once.
The pinned compiler/library, generated files, assets and prose documentation are excluded.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYSTEMS = {
    'Rendering/shaders': 'asset_stream charshade cputime dome frametime gfx gputime gpuqueue mesh_assets post render scene shade shader_load shadows sky water_render',
    'Terrain/world': 'architecture_assets trees build env farland grass interiors physics structures terrain terrain_assets vegetation water worldgen',
    'Player/camera/animation': 'camera chars clips gltf hero_motion player skel trail weapon_tracks',
    'Combat/enemies': 'talus combat enemies enemy_camp enemy_contacts enemy_footing enemy_weapon_pose',
    'Wildlife': 'wildlife',
    'Elements': 'cooking element_puzzles elements fx matter',
    'Story/shrines': 'interact shrine_monk shrines story',
    'Audio/music': 'audio_assets audio_cache music sfx',
    'UI/input/save': 'input inventory items main options save slate_map ui',
}


def line_count(path):
    # Like wc -l, with a final unterminated source line counted as well.
    data = path.read_bytes()
    return data.count(b'\n') + int(bool(data) and not data.endswith(b'\n'))


def report():
    game = set(ROOT.glob('game/*.jo'))
    assigned = set()
    rows = []
    for name, stems in SYSTEMS.items():
        paths = [ROOT / 'game' / f'{stem}.jo' for stem in stems.split()]
        for path in paths:
            if path not in game or path in assigned:
                raise SystemExit(f'Missing or duplicate assignment: {path.relative_to(ROOT)}')
            assigned.add(path)
        rows.append({'system': name, 'files': {str(p.relative_to(ROOT)): line_count(p) for p in paths}})
    if game != assigned:
        raise SystemExit('Assign new game modules in SYSTEMS: ' + ', '.join(str(p.relative_to(ROOT)) for p in sorted(game - assigned)))
    # Includes .jo.in harness templates and the extensionless Python traversal driver.
    paths = sorted(p for p in (ROOT / 'tools').rglob('*') if p.is_file() and
                   (p.suffix in ('.jo', '.py', '.sh') or p.name.endswith('.jo.in') or
                    (not p.suffix and p.read_bytes().startswith(b'#!'))))
    rows.append({'system': 'Tools/tests', 'files': {str(p.relative_to(ROOT)): line_count(p) for p in paths}})
    for row in rows:
        row['lines'] = sum(row['files'].values())
        row['file_count'] = len(row['files'])
    return {'method': 'physical lines including comments/blanks; whole files by primary system',
            'systems': rows, 'game_lines': sum(r['lines'] for r in rows[:-1]),
            'tools_lines': rows[-1]['lines']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--files', action='store_true', help='list each source file and line count')
    parser.add_argument('--json', action='store_true', help='emit the full report as JSON')
    args = parser.parse_args()
    data = report()
    if args.json:
        print(json.dumps(data, indent=2))
        return
    print('| System | Files | Lines |')
    print('|---|---:|---:|')
    for row in data['systems']:
        print(f"| {row['system']} | {row['file_count']} | {row['lines']:,} |")
    print(f"| **Game total** | {sum(r['file_count'] for r in data['systems'][:-1])} | **{data['game_lines']:,}** |")
    if args.files:
        for row in data['systems']:
            print(f"\n{row['system']}:")
            for path, lines in row['files'].items():
                print(f'  {lines:6}  {path}')


if __name__ == '__main__':
    main()
