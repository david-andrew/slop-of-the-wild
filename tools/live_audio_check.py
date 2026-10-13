#!/usr/bin/env python3
# Run: python3 tools/live_audio_check.py (defaults to build/live-audio; owns the render lock, do not wrap).
"""Capture deterministic production audio. Owns /tmp/botw-render.lock; do not wrap.

Copies the current game's complete play_events dispatcher (including effects) into a
headless fixture, so future gain/event changes cannot drift from these captures.
Scripted state/events exercise audio integration, not physical traversal/AI validation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import wave
from array import array

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', nargs='?', default=ROOT / 'build/live-audio', type=Path)
    parser.add_argument('--modes', nargs='+', default=['scenario', 'engaged', 'low_hp', 'field', 'biome'])
    parser.add_argument('--seconds', type=float)
    parser.add_argument('--game-dir', type=Path, default=ROOT / 'game', help='Source snapshot for baseline comparisons')
    parser.add_argument('--skip-build', action='store_true', help='Reuse the pinned capture binary')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    game_dir = args.game_dir.resolve()
    game_prefix = os.path.relpath(game_dir, out) + '/'
    source = (game_dir / 'main.jo').read_text()
    imports = '\n'.join(line.replace("use '", "use '" + game_prefix).replace("from '", "from '" + game_prefix)
                        for line in source.splitlines() if line.startswith(('use ', 'from ')))
    dispatcher = source[source.index('cam_right ='):source.index('# eat or use what is bound')]
    fixture = out / 'capture.jo'
    if not args.skip_build:
        template = (ROOT / 'tools/live_audio_scenario.jo').read_text().replace('../../game/', game_prefix)
        audio_source = (ROOT / 'sloppy/lib/game/audio.jo').read_text()
        linear_mixer = audio_source[audio_source.index('__mix ='):audio_source.index('    # soft clip')].replace('__mix =', 'capture_linear_mix =', 1)
        fixture.write_text('build:\n    opt = release\n' + imports + '\nhitstop = 0.0\n' + dispatcher + linear_mixer + '\n' + template)
        paths = ['game/main.jo', 'game/music.jo', 'game/sfx.jo', 'game/elements.jo', 'sloppy/lib/game/audio.jo', 'tools/live_audio_scenario.jo']
        provenance = {path: hashlib.sha256(((game_dir / Path(path).name) if path.startswith('game/') else ROOT / path).read_bytes()).hexdigest() for path in paths}
        (out / 'sources.json').write_text(json.dumps(provenance, indent=2) + '\n')
    binary = out / 'capture'
    if not args.skip_build:
        subprocess.run([str(ROOT / 'sloppy/bin/sloppy'), 'build', str(fixture), '-o', str(binary)], cwd=ROOT, check=True)
    for mode in args.modes:
        seconds = args.seconds or {'scenario': 180, 'engaged': 40, 'low_hp': 40, 'field': 600, 'biome': 120}[mode]
        print(f'Rendering {mode}: {seconds:g}s under /tmp/botw-render.lock', flush=True)
        # Release between captures; compilation and PCM conversion need no lock.
        subprocess.run(['flock', '/tmp/botw-render.lock', 'timeout', '180', str(binary), str(out), mode, str(seconds)], cwd=ROOT,
                       env={**os.environ, 'BOTW_NO_PREPARED_ASSETS': '1'} if game_dir != ROOT / 'game' else None, check=True)
        raw = out / f'{mode}.f32'
        with raw.open('rb') as pcm, wave.open(str(out / f'{mode}.wav'), 'wb') as wav:
            wav.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
            while chunk := pcm.read(96000 * 4):
                samples = array('f')
                samples.frombytes(chunk)
                wav.writeframes(array('h', (int(max(-1, min(1, v)) * 32767) for v in samples)).tobytes())
        raw.unlink()
        print(f"Wrote {out / (mode + '.wav')}", flush=True)

if __name__ == '__main__':
    main()
