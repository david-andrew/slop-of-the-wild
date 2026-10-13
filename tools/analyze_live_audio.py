#!/usr/bin/env python3
"""Analyze live_audio_check captures with only Python's standard library."""
import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path
import wave
from array import array

def db(power):
    return 10 * math.log10(max(power, 1e-18))

def analyze(path, mode):
    layers = defaultdict(dict)
    with (path / f'{mode}-frames.csv').open() as f:
        for row in csv.DictReader(f):
            layers[row['layer']][round(float(row['time']) * 60)] = (
                float(row['energy']), float(row['peak']), int(row['above40']), int(row['samples']))
    results = {}
    for name, frames in layers.items():
        values = list(frames.values())
        total = sum(v[3] for v in values)
        # RMS occupancy counts 100 ms windows, independently of the instantaneous sample statistic.
        occupied = windows = 0
        for start in range(0, len(values) - 5, 6):
            occupied += sum(v[0] for v in values[start:start+6]) / sum(v[3] for v in values[start:start+6]) > 1e-4
            windows += 1
        results[name] = {'rms_dbfs': db(sum(v[0] for v in values) / total),
                         'peak_dbfs': db(max(v[1] for v in values) ** 2),
                         'above_minus40_samples_pct': 100 * sum(v[2] for v in values) / total,
                         'above_minus40_100ms_rms_pct': 100 * occupied / max(1, windows)}
    events = list(csv.DictReader((path / f'{mode}-events.csv').open()))
    ratios = []
    for event in events:
        kind = event['kind']
        if kind == 'cue_step' or not (kind.startswith('cue_') or kind == 'step'):
            continue
        start = round(float(event['time']) * 60)
        def power(names, offset=0):
            return sum(layers[n].get(i, (0, 0, 0, 1600))[0]
                       for n in names for i in range(start + offset, start + offset + 6)) / 9600
        signal = power(['footsteps' if kind == 'step' else 'cues'])
        # The score's legacy and game-owned gain attacks both last 20 ms.
        # Keep the raw onset metric, and check the settled 100 ms cue body.
        # Two 60 Hz rows (33.3 ms) conservatively clear that sample ramp.
        body_offset = 2 if kind.startswith('cue_') else 0
        body_signal = power(['footsteps' if kind == 'step' else 'cues'], body_offset)
        ratios.append({'time': float(event['time']), 'kind': kind,
                       'signal_dbfs': db(signal), 'music_dbfs': db(power(['music'])),
                       'cue_to_music_db': db(signal) - db(power(['music'])),
                       'to_rain_fire_db': db(signal) - db(power(['rain', 'fire'])),
                       'to_all_background_db': db(signal) - db(power(['music', 'wind', 'rain', 'fire', 'wildlife', 'other'])),
                       'body_start_ms': body_offset * 1000 / 60,
                       'body_cue_to_music_db': db(body_signal) - db(power(['music'], body_offset)),
                       'body_to_all_background_db': db(body_signal) - db(power(['music', 'wind', 'rain', 'fire', 'wildlife', 'other'], body_offset))})
    with (path / f'{mode}-onsets.csv').open('w') as f:
        if ratios:
            writer = csv.DictWriter(f, fieldnames=ratios[0].keys())
            writer.writeheader()
            writer.writerows(ratios)
    repetitions = {}
    for kind in ['step', 'bird', 'gust', 'phrase']:
        last = {}
        prior = None
        count = consecutive = within20 = within120 = 0
        mingap = math.inf
        gaps = []
        for e in events:
            if e['kind'] != kind:
                continue
            identity = e['sample']
            if kind == 'phrase' and not identity:
                continue  # a silent turn is not an emitted phrase
            count += 1
            if identity == prior: consecutive += 1
            prior = identity
            t = float(e['time'])
            if identity in last:
                gap = t - last[identity]
                mingap = min(mingap, gap)
                gaps.append(gap)
                within20 += gap < 20
                within120 += gap < 120
            last[identity] = t
        repetitions[kind] = {'events': count, 'identical_consecutive': consecutive,
                             'same_within20s': within20, 'same_within120s': within120,
                             'minimum_same_sample_gap_s': None if math.isinf(mingap) else mingap}
    preclip = sum(v[2] for v in layers['preclip'].values())
    with wave.open(str(path / f'{mode}.wav')) as wav:
        energy = peak = samples = rail = 0
        while block := wav.readframes(48000):
            vals = array('h'); vals.frombytes(block)
            energy += sum((v / 32767) ** 2 for v in vals)
            peak = max(peak, max(abs(v / 32767) for v in vals))
            rail += sum(abs(v) >= 32767 for v in vals)
            samples += len(vals)
    results['full_mix'] = {'rms_dbfs': db(energy / samples), 'peak_dbfs': db(peak ** 2),
                            'pre_limiter_overloads': preclip, 'pcm_clipped_samples': rail}
    phases = {}
    if mode == 'scenario':
        for name, start, end in [('rain_walk', 0, 30), ('rain_fire', 30, 60), ('wildlife', 60, 90),
                                  ('engaged', 90, 120), ('low_hp', 120, 150), ('shelter', 150, 180)]:
            phases[name] = {}
            for layer, frames in layers.items():
                if layer == 'preclip': continue
                values = [v for frame, v in frames.items() if start * 60 <= frame < end * 60]
                phases[name][layer] = {'rms_dbfs': db(sum(v[0] for v in values) / sum(v[3] for v in values)),
                                       'peak_dbfs': db(max(v[1] for v in values) ** 2)}
    return {'levels': results, 'phases': phases, 'repetition': repetitions, 'onsets': ratios}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--check', action='store_true', help='Require occupancy, audibility, repeat and headroom targets')
    args = parser.parse_args()
    data = {mode: analyze(args.path, mode) for mode in ['scenario', 'engaged', 'low_hp', 'field', 'biome']
            if (args.path / f'{mode}.wav').exists()}
    (args.path / 'metrics.json').write_text(json.dumps(data, indent=2) + '\n')
    if args.check:
        low = data['low_hp']; engaged = data['engaged']
        for measure in ['above_minus40_samples_pct', 'above_minus40_100ms_rms_pct']:
            assert low['levels']['music'][measure] < engaged['levels']['music'][measure], measure
        for mode in ['scenario', 'engaged', 'low_hp']:
            for onset in data[mode]['onsets']:
                if onset['kind'].startswith('cue_'):
                    assert onset['body_cue_to_music_db'] >= 6, (mode, onset)
                    assert onset['body_to_all_background_db'] >= 6, (mode, onset)
                elif mode == 'scenario':
                    assert onset['to_rain_fire_db'] >= 0, (mode, onset)
        field = data['field']['repetition']
        assert field['step']['identical_consecutive'] == 0
        assert field['bird']['same_within20s'] == 0
        assert field['bird']['identical_consecutive'] == 0
        assert field['gust']['same_within20s'] == 0
        assert field['phrase']['identical_consecutive'] == 0
        repeat = field['phrase']['minimum_same_sample_gap_s']
        assert repeat is None or repeat >= 180, field['phrase']
        for mode in data:
            assert data[mode]['levels']['full_mix']['pre_limiter_overloads'] == 0
            assert data[mode]['levels']['full_mix']['pcm_clipped_samples'] == 0
        print('PASS live audio: low-health occupancy, settled cue body audibility after 20 ms attack, rain/fire footstep masking, repetitions and pre-clip headroom')
    for mode, metrics in data.items():
        print(mode, json.dumps({'levels': metrics['levels'], 'repetition': metrics['repetition']}))
        for kind in sorted({r['kind'] for r in metrics['onsets']}):
            rows = [r for r in metrics['onsets'] if r['kind'] == kind]
            print(kind, 'minimum cue/music', min(r['cue_to_music_db'] for r in rows),
                  'minimum rain/fire', min(r['to_rain_fire_db'] for r in rows),
                  'minimum settled cue/music', min(r['body_cue_to_music_db'] for r in rows))

if __name__ == '__main__':
    main()
