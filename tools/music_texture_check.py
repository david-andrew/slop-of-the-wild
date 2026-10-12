#!/usr/bin/env python3
"""Audit rendered combat variation, insect steadiness and field phrase recurrence.

Uses FFmpeg and Python's standard library; no plotting/NumPy dependency. Spectra
are 4096-point Hann FFTs of 12 kHz mono PCM, one per 250 ms. Pitch/attack traces
come from the same production sequencer run that writes the twenty-minute WAVs.
"""
import argparse
from array import array
import cmath
import csv
import json
import math
from pathlib import Path
import subprocess
import wave

N = 4096
RATE = 12000
HOP = RATE // 4
ORDER = [int(f'{i:012b}'[::-1], 2) for i in range(N)]
ROOTS = {width: [cmath.exp(-2j * math.pi * k / width) for k in range(width // 2)]
         for width in [2**j for j in range(1, 13)]}
WINDOW = [0.5 - 0.5 * math.cos(2 * math.pi * i / (HOP - 1)) for i in range(HOP)]


def pcm(path, seconds):
    with wave.open(str(path)) as wav:
        assert wav.getnframes() / wav.getframerate() == seconds, (path, 'capture duration')
    data = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path),
                                    '-ac', '1', '-ar', str(RATE), '-f', 'f32le', '-'])
    result = array('f')
    result.frombytes(data)
    assert len(result) == RATE * seconds
    return result


def spectrum(samples):
    padded = [samples[i] * WINDOW[i] for i in range(len(samples))] + [0.] * (N - len(samples))
    out = [complex(padded[i]) for i in ORDER]
    for width, roots in ROOTS.items():
        half = width // 2
        for start in range(0, N, width):
            for k, root in enumerate(roots):
                even = out[start + k]
                odd = root * out[start + k + half]
                out[start + k], out[start + k + half] = even + odd, even - odd
    return [v.real**2 + v.imag**2 for v in out[:N // 2 + 1]]


def insect_metrics(path):
    samples = pcm(path, 45)
    spectra = []
    silent = 0
    persistent = [0] * (N // 2 + 1)
    low, high = int(2700 * N / RATE), int(5500 * N / RATE)
    for start in range(0, len(samples), HOP):
        chunk = samples[start:start + HOP]
        energy = sum(v*v for v in chunk) / HOP
        if energy < 10**(-75 / 10):
            silent += 1
            continue
        power = spectrum(chunk)[low:high]
        total = sum(power)
        normalized = [v / max(total, 1e-30) for v in power]
        spectra.append(normalized)
        # A 20 Hz neighbourhood containing >=20% of band power counts as a
        # dominant line. Denominator includes the gaps, not just active calls.
        radius = round(10 * N / RATE)
        for i in range(radius, len(power) - radius):
            if sum(normalized[i-radius:i+radius+1]) >= .20:
                persistent[low+i] += 1
    assert len(spectra) >= 10, 'missing insect calls cannot pass as silence'
    mean = [sum(column) / len(spectra) for column in zip(*spectra)]
    variance = sum(sum((v-m)**2 for v, m in zip(row, mean)) for row in spectra) / len(spectra)
    variance /= sum(m*m for m in mean)
    blocks = len(samples) // HOP
    result = {'spectral_relative_variance': round(variance, 4),
              'max_dominant_line_occupancy': round(max(persistent) / blocks, 4),
              'silent_250ms_fraction': round(silent / blocks, 4),
              'active_windows': len(spectra), 'windows': blocks,
              'thresholds': {'variance_min': .35, 'line_occupancy_max': .35, 'silence_min': .25}}
    assert variance >= .35 and max(persistent) / blocks <= .35 and silent / blocks >= .25, result
    return result


def combat_metrics(path):
    samples = pcm(path, 120)
    with path.with_name('combat_120-bars.csv').open() as file:
        starts = [float(row['time']) for row in csv.DictReader(file)]
    assert len(starts) >= 33
    # Use actual production 60 Hz bar boundaries. Exclude the first/last
    # 0.35 seconds of each bar's spectrum to keep damped tails at the edges.
    bars = []
    for bar in range(32):
        a, b = round(starts[bar] * RATE), round(starts[bar+1] * RATE)
        rms = math.sqrt(sum(v*v for v in samples[a:b]) / (b-a))
        power = [0.] * (N // 2 + 1)
        for at in range(a + round(.35 * RATE), b - round(.35 * RATE) - HOP, HOP):
            block = spectrum(samples[at:at+HOP])
            power = [x+y for x, y in zip(power, block)]
        norm = math.sqrt(sum(v*v for v in power))
        bars.append((rms, [v / max(norm, 1e-30) for v in power]))
    changed, details = [], []
    for bar in range(8):
        r0, p0 = bars[bar]
        r1, p1 = bars[bar+8]
        delta = abs(20 * math.log10(max(r1, 1e-12) / max(r0, 1e-12)))
        distance = 1 - sum(a*b for a,b in zip(p0,p1))
        altered = bar != 0 and (delta >= .75 or distance >= .10)  # exclude the entry fade/accent
        if altered: changed.append(bar)
        details.append({'bar': bar, 'rms_change_db': round(delta, 3),
                        'spectral_cosine_distance': round(distance, 4), 'changed': altered})
    # Middle of fourth-round bar 3 must be digitally silent, allowing the
    # previous damped note to finish before the gap begins.
    rest_start = starts[27] + .5
    gap = samples[round(rest_start*RATE):round((rest_start+2)*RATE)]
    gap_peak = max(abs(v) for v in gap)
    result = {'changed_bars_between_first_two_rounds': len(changed),
              'bars_compared': 8, 'bar_comparisons': details,
              'whole_bar_rest_middle_peak': gap_peak,
              'thresholds': {'changed_bars_min': 7, 'rms_change_db': .75,
                             'spectral_cosine_distance': .10, 'rest_peak_max': 1e-5}}
    assert len(changed) >= 7 and gap_peak <= 1e-5, result
    return result


def phrase_metrics(directory, context):
    name = context + '_1200'
    with wave.open(str(directory / (name + '.wav'))) as wav:
        assert wav.getnframes() / wav.getframerate() == 1200
    previous, repeats, phrases, notes = {}, [], 0, 0
    colours, bass_phrases, spans = set(), 0, []
    with (directory / (name + '-phrases.csv')).open() as file:
        for row in csv.DictReader(file):
            # Explicit melody role: added bass/glass cannot disguise repeats.
            key = row['pitches']
            assert key, 'empty phrase must not count toward coverage'
            t = float(row['time'])
            phrases += 1
            notes += len(key.rstrip(':').split(':'))
            onsets = [float(v) for v in row['onsets'].rstrip(':').split(':')]
            assert all(b > a for a, b in zip(onsets, onsets[1:])), row
            spans.append(max(onsets))
            if int(row['colour']) >= 0:
                colours.add(int(row['colour']))
                bass_phrases += 1
            if key in previous: repeats.append(t - previous[key])
            previous[key] = t
    minimum = min(repeats) if repeats else None
    result = {'seconds': 1200, 'nonempty_phrases': phrases, 'melody_notes': notes,
              'repeated_phrases': len(repeats), 'minimum_repeat_interval_s': minimum,
              'repeat_intervals_s': repeats, 'bass_phrases': bass_phrases,
              'bass_colours': sorted(colours), 'phrase_span_max_s': max(spans),
              'identity': 'ordered MIDI melody pitches including handoffs, partial/single-note phrases; excludes accompaniment; ignores timing and velocity',
              'thresholds': {'repeat_interval_min_s': 180, 'phrases_min': 24, 'melody_notes_min': 80,
                             'phrase_span_max_s': 18, 'field_bass_fraction_max': .65}}
    assert phrases >= 24 and notes >= 80, result
    assert minimum is None or minimum >= 180, result
    assert max(spans) <= 18, result
    if context == 'field':
        assert len(colours) >= 3 and 4 <= bass_phrases <= phrases * .65, result
    return result


def creature_metrics(directory, enforce=True):
    result = {}
    for creature in ['boar', 'fox', 'crow', 'bokoblin']:
        name = 'creature_' + creature
        samples = pcm(directory / (name + '.wav'), 45)
        with (directory / (name + '-calls.csv')).open() as file:
            calls = list(csv.DictReader(file))
        takes = [int(c['take']) for c in calls]
        pitches = [float(c['pitch']) for c in calls]
        durations = [float(c['source_seconds']) for c in calls]
        powers, centroids = [], []
        for call in calls:
            start = round(float(call['time']) * RATE)
            # Early attack/body, fixed window independent of take length.
            power = spectrum(samples[start:start + HOP])
            total = max(sum(power), 1e-30)
            centroids.append(sum(i * RATE / N * p for i, p in enumerate(power)) / total)
            norm = math.sqrt(sum(p*p for p in power))
            powers.append([p / max(norm, 1e-30) for p in power])
        distances = [1 - sum(a*b for a, b in zip(left, right))
                     for left, right in zip(powers, powers[1:])]
        reading = {'calls': len(calls), 'distinct_samples': len(set(takes)),
                   'adjacent_sample_repeats': sum(a == b for a,b in zip(takes,takes[1:])),
                   'pitch_span': round(max(pitches)-min(pitches), 6),
                   'source_duration_span_s': round(max(durations)-min(durations), 6),
                   'centroid_hz_min_max': [round(min(centroids), 1), round(max(centroids), 1)],
                   'adjacent_spectral_distance_min_mean': [round(min(distances), 4), round(sum(distances)/len(distances), 4)],
                   'scope': '12 close repeated encounters, same individual/source, frozen gameplay RNG; arrivals scripted; internal timing measured from source samples'}
        if enforce:
            assert len(calls) == 12 and len(set(takes)) >= 3 and reading['adjacent_sample_repeats'] == 0, reading
            assert reading['pitch_span'] > .015 and reading['source_duration_span_s'] > .015, reading
            assert sum(distances)/len(distances) >= .025, reading
        # A broad species check catches a wrong handle or silent call, not realism.
        lo, hi = {'boar': (40, 600), 'fox': (500, 2500), 'crow': (500, 3500), 'bokoblin': (150, 2000)}[creature]
        assert lo < sum(centroids)/len(centroids) < hi, reading
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(directory / (name + '.wav')),
                        '-lavfi', 'showspectrumpic=s=1200x500:legend=1:scale=log:fscale=log',
                        '-frames:v', '1', str(directory / (name + '-spectrum.png'))], check=True)
        result[creature] = reading
    return result


def check_textures(directory):
    result = {'night': insect_metrics(directory / 'night_insects.wav'),
              'combat': combat_metrics(directory / 'combat_120.wav'),
              'field': phrase_metrics(directory, 'field'),
              'shrine': phrase_metrics(directory, 'shrine'),
              'creatures': creature_metrics(directory)}
    for name in ['field_day', 'shrine', 'field_1200', 'shrine_1200']:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(directory / (name + '.wav')),
                        '-lavfi', 'showspectrumpic=s=1400x600:legend=1:scale=log:fscale=log',
                        '-frames:v', '1', str(directory / (name + '-spectrum.png'))], check=True)
    (directory / 'textures.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS music textures:', json.dumps(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, nargs='?', default=Path('build/listen'))
    check_textures(parser.parse_args().directory)
