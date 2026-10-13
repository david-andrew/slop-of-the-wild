#!/usr/bin/env python3
"""Collect existing Round 67 evidence; does not render or acquire a lock."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/round67'


def read(path):
    return json.loads(path.read_text())


def main():
    matrix = {}
    for name in ['baseline', 'fixed-scale', 'mailbox60', 'fifo60', 'final-default']:
        report = read(OUT / name / 'soak.json')
        run = next(iter(report['runs'].values()))
        matrix[name] = {k: run[k] for k in ['frames', 'elapsed_s', 'timing_ms', 'window_count',
                     'windows_over_20ms', 'windows_over_17_5ms', 'scene_scales', 'flags', 'log_sha256']}
        matrix[name]['executable_sha256'] = report['executable_sha256']
        matrix[name]['game_sources'] = report['sources']
    native = {}
    for name in ['trace-attribution', 'image-attribution']:
        data = json.loads(gzip.decompress((OUT / (name + '.json.gz')).read_bytes()))
        r = next(iter(data['runs'].values()))
        tails = r['all_intervals_over_20ms']
        native[name] = {k: r[k] for k in ['native_calls_in_play', 'attribution_counts', 'stage_coverage']}
        worst = max(tails, key=lambda t: t['interval_ms'])
        native[name]['worst'] = {k: worst[k] for k in ['frame', 'elapsed_s', 'interval_ms', 'present_ms',
                         'callback_wall_ms', 'callback_thread_ms', 'attribution', 'native_calls']}
    cadence = {}
    for name, row in matrix.items():
        mode = 'default' if name == 'fifo60' else 'mailbox'
        text = (OUT / name / ('soak-' + mode + '.log')).read_text()
        origin = float(re.search(r'probe monotonic start: ([\d.]+)', text)[1])
        rows = [[float(v) for v in line.split()[2:]] for line in text.splitlines()
                if line.startswith('present return:')]
        periodic = [r for r in rows if r[3] > 25 and abs((origin + r[1]) % 10 - 8) < .15]
        cadence[name] = {'count': len(periodic), 'median_absolute_end_phase_s':
            statistics.median((origin+r[1]) % 10 for r in periodic) if periodic else None,
            'events': [dict(frame=int(r[0]),elapsed_s=r[1],present_ms=r[3],absolute_end_s=origin+r[1]) for r in periodic]}
    sources = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted((ROOT / 'game').glob('*.jo'))}
    result = {'base_revision': '500126f', 'selected_default': 'Vulkan mailbox, dynamic scale, BOTW_FPS=0',
              'limitations': ['producer/present-return timestamps, not scanout', 'shared desktop',
                 'initial two rows predate audio/combat changes; capped rows share an executable',
                 'periodic acquire stall persists', 'historical 231 ms CPU stage lacks its raw trace'],
              'pacing': matrix, 'native': native, 'cadence': cadence,
              'piano_sample_bytes': 106525404, 'loudness': read(OUT / 'live-audio/loudness.json'),
              'final_game_sources': sources}
    framing = OUT / 'final5/framing/summary.json'
    result['framing'] = read(framing)
    assert all(row['passed'] for row in result['framing'].values()), 'final framing must pass'
    for scene in result['framing']:
        captured = read(framing.parent / scene / 'sources.json')['game']
        assert captured == {Path(name).name: value for name, value in sources.items()}, 'framing source mismatch'
    (OUT / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    compact = {k: v for k, v in result.items() if k not in ['cadence', 'final_game_sources']}
    for row in compact['pacing'].values(): row.pop('game_sources', None)
    compact['final_game_source_digest'] = hashlib.sha256(json.dumps(sources,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    (ROOT / 'docs/performance-round67.json').write_text(json.dumps(compact, indent=2) + '\n')
    print('Saved Round 67 summary and source digest')


if __name__ == '__main__':
    main()
