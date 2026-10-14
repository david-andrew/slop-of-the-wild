#!/usr/bin/env python3
"""Check authored field activity from actual production strike logs, not RNG plans.

Silence means no notated gesture (first strike through last strike + 1.25 s
pedal allowance). Decaying room tails are deliberately not counted as attacks.
This is a composition metric, not digital/audio silence or a hearing verdict.
"""
import argparse
import csv
import json
from pathlib import Path
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CONTEXTS = ['field_day', 'field_night', 'rain', 'golden', 'forest', 'snow', 'ruins']


def check(path, seconds=1200):
    notes = list(csv.DictReader(path.open()))
    groups = {}
    reverse = []
    for n in notes:
        n.update(t=float(n['time']), pitch=int(n['midi']), voice=int(n['hand']))
        if n['kind'] == 'reverse':
            reverse.append(n['t'])
        else:
            assert n['kind'] == 'piano', 'field must contain only piano samples'
            groups.setdefault((n['voice'], n['phrase']), []).append(n)
    high = sorted((v for (h, _), v in groups.items() if h == 0), key=lambda v:v[0]['t'])
    low = sorted((v for (h, _), v in groups.items() if h == 1), key=lambda v:v[0]['t'])
    assert len(high) >= 24 and len(low) >= 6, (path, 'non-vacuous two-hand coverage')
    intervals = []
    previous = {}
    repeats = []
    roots = set()
    b7 = False
    for voice, phrases in [(0, high), (1, low)]:
        for phrase in phrases:
            first, last = phrase[0]['t'], phrase[-1]['t']
            assert all(21 <= n['pitch'] <= 108 for n in phrase), (path, '88-key piano range', phrase)
            assert 2 <= len(phrase) <= 7, (path, phrase)
            assert 1.4 <= last - first <= 6.0, (path, phrase)
            intervals.append((first, min(seconds, last+1.25)))
            key = (voice, tuple(n['pitch'] for n in phrase))
            if key in previous: repeats.append(first - previous[key])
            previous[key] = first
            root = int(phrase[0]['root'])
            roots.add(root)
            classes = [(n['pitch'] - root) % 12 for n in phrase]
            b7 |= 10 in classes
            assert 4 not in classes and 3 not in classes, (path, 'third withheld', phrase)
            # A strict no-tonic-ending rule rules out a melodic V-I cadence,
            # and no field event carries a chordal third that could make a PAC.
            assert classes[-1] != 0, (path, 'tonic cadence', phrase)
            assert abs(float(phrase[0]['pan'])) <= .300001
    for t in reverse: intervals.append((t, min(seconds, t+3.0)))
    occupied = 0.0
    start = end = 0.0
    for a,b in sorted(intervals):
        if a > end:
            occupied += end-start
            start,end = a,b
        else: end = max(end,b)
    occupied += end-start
    silence = 1.0 - occupied/seconds
    middle = sum(48 <= n['pitch'] <= 72 for n in notes) / len(notes)
    gain_spread = {}
    for voice, phrases in [('high', high), ('low', low)]:
        gains = [float(v[0]['gain']) for v in phrases]
        spread = max(gains) / min(gains)
        assert 1.2 <= spread <= 2.0001, (path, voice, 'bounded +/-3dB fragment variation', spread)
        assert statistics.pstdev([float(v[0]['pan']) for v in phrases]) > .08, (path, voice, 'pan variation')
        gain_spread[voice] = round(spread, 3)
    hi_starts = [v[0]['t'] for v in high]
    lo_starts = [v[0]['t'] for v in low]
    phase = [min(abs(t-h) for h in hi_starts) for t in lo_starts]
    assert .60 <= silence <= .92, (path, silence)
    assert middle <= .02 and all(n['pitch'] > 72 for v in high for n in v), (path, middle)
    assert b7 and len(roots) == 1, (path, 'modal mixture/tonic')
    assert not repeats or min(repeats) >= 179.98, (path, min(repeats))
    assert 3 <= len(reverse) <= 12, (path, 'rare reverse coverage')
    assert statistics.pstdev(phase) > 1.0 and sum(p < .1 for p in phase)/len(phase) < .20, (path, phase)
    # Fixed opening, independent of the random pool selection.
    root = int(high[0][0]['root'])
    assert [(n['pitch'] - root) % 12 for n in high[0]][:2] == ([1,1] if path.stem.startswith('ruins') else [2,2])
    return dict(high_phrases=len(high), low_phrases=len(low), notes=len(notes),
                notated_silence_fraction=round(silence,4), middle_register_share=round(middle,4),
                minimum_repeat_seconds=round(min(repeats),3) if repeats else None,
                low_to_high_phase_std_seconds=round(statistics.pstdev(phase),3),
                coincident_hand_fraction=round(sum(p < .1 for p in phase)/len(phase),4),
                reverse_events=len(reverse), fragment_gain_max_min=gain_spread, third_notes=0, tonic_endings=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',default='build/music-style-check')
    parser.add_argument('--measure-only',action='store_true')
    args=parser.parse_args()
    out=ROOT/args.out; out.mkdir(parents=True, exist_ok=True)
    if not args.measure_only:
        binary=out/'trace'
        subprocess.run(['sloppy/bin/sloppy','build','tools/music_style_trace.jo','-o',str(binary)],cwd=ROOT,check=True)
        for name in CONTEXTS:
            # One clip per lock, never wrap this checker in an outer flock.
            subprocess.run(['flock','/tmp/botw-render.lock','timeout','300',str(binary),str(out/f'{name}.csv'),name],cwd=ROOT,check=True)
    data={name:check(out/f'{name}.csv') for name in CONTEXTS}
    (out/'metrics.json').write_text(json.dumps(data,indent=2)+'\n')
    for name, result in data.items(): print('PASS',name,json.dumps(result))

if __name__=='__main__':main()
