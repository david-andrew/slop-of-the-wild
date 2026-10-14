#!/usr/bin/env python3
# Run: python3 tools/mix_loudness_check.py [build/live-audio] --check (first run python3 tools/live_audio_check.py).
"""Measure production live_audio_check WAVs using FFmpeg's BS.1770/EBU R128 meter.

Reads existing captures only (no render or lock). --check enforces the final
exploration/combat ranges, contrast, true-peak ceiling and unclipped float mix.
"""
import argparse
import csv
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def measure(path, start=None, seconds=None):
    command = ['ffmpeg', '-hide_banner', '-nostats']
    if start is not None:
        command += ['-ss', str(start), '-t', str(seconds)]
    command += ['-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-']
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    summary = result.stderr[result.stderr.rfind('Summary:'):]
    return {
        'integrated_lufs': float(re.search(r'I:\s+([\d.-]+) LUFS', summary)[1]),
        'true_peak_dbtp': float(re.search(r'Peak:\s+([\d.-]+) dBFS', summary)[1]),
        'loudness_range_lu': float(re.search(r'LRA:\s+([\d.-]+) LU', summary)[1]),
    }, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture_dir', nargs='?', default=ROOT / 'build/live-audio', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    modes = ['scenario', 'field', 'engaged', 'low_hp']
    required = modes if args.check else [mode for mode in modes if (args.capture_dir / f'{mode}.wav').exists()]
    if not required:
        parser.error(f'no captures in {args.capture_dir}; run python3 tools/live_audio_check.py first')
    missing = [str(args.capture_dir / f'{mode}{suffix}') for mode in required
               for suffix in ['.wav', '-frames.csv'] if not (args.capture_dir / f'{mode}{suffix}').is_file()]
    if missing:
        parser.error(f'missing captures: {", ".join(missing)}; run python3 tools/live_audio_check.py first')
    readings, logs = {}, []
    for mode in modes:
        path = args.capture_dir / f'{mode}.wav'
        if not path.exists():
            continue
        readings[mode], summary = measure(path)
        logs.append(f'{mode}\n{summary}')
        with (args.capture_dir / f'{mode}-frames.csv').open() as stream:
            preclip = [row for row in csv.DictReader(stream) if row['layer'] == 'preclip']
        readings[mode]['pre_limiter_overloads'] = sum(int(row['above40']) for row in preclip)
    for phase, start, duration in [('rain_walk', 0, 30), ('rain_fire', 30, 30),
                                   ('wildlife', 60, 30), ('engaged', 90, 30),
                                   ('low_hp', 120, 30), ('shelter', 150, 30)]:
        if 'scenario' not in readings:
            break
        key = f'scenario_{phase}'
        readings[key], summary = measure(args.capture_dir / 'scenario.wav', start, duration)
        logs.append(f'{key}\n{summary}')
    (args.capture_dir / 'loudness.json').write_text(json.dumps(readings, indent=2) + '\n')
    (args.capture_dir / 'loudness.log').write_text('\n'.join(logs))
    for mode, reading in readings.items():
        print(mode, json.dumps(reading))
    if args.check:
        # Sparse extreme-register pp now leaves the world in front; match
        # listen.py's documented exploration target, without master gain.
        assert -43 <= readings['field']['integrated_lufs'] <= -30, readings['field']
        for mode in ['engaged', 'low_hp']:
            assert -22.5 <= readings[mode]['integrated_lufs'] <= -20.0, (mode, readings[mode])
            assert readings[mode]['integrated_lufs'] > readings['field']['integrated_lufs'], (mode, readings[mode])
        assert abs(readings['engaged']['integrated_lufs'] - readings['low_hp']['integrated_lufs']) <= 2.5, 'last-heart/combat level proximity'
        for mode, reading in readings.items():
            assert reading['true_peak_dbtp'] <= -1, (mode, reading)
            assert reading.get('pre_limiter_overloads', 0) == 0, (mode, reading)
        print('PASS full-mix loudness: exploration -43 to -30 LUFS, combat -22.5 to -20 LUFS, close last-heart level, peaks <= -1 dBTP, no pre-limiter overloads')


if __name__ == '__main__':
    main()
