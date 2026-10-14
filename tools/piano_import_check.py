#!/usr/bin/env python3
"""Verify committed PCM16 recordings and production note-to-recording coverage.

Build and run a private headless storage fixture for the runtime-selected slots.
Raw AIFFs are never opened here; tools/import_piano.py alone decodes sources.
"""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import wave

ROOT = Path(__file__).resolve().parents[1]
report = json.loads((ROOT / 'assets/audio/piano-import.json').read_text())
bank = report['bank']
keys = range(bank['low_midi'], bank['high_midi'] + 1, bank['step_semitones'])
entries = {(e['dynamic'], e['midi']): e for e in report['samples']}
assert set(entries) == {(dynamic, midi) for dynamic in ('pp', 'mf', 'ff') for midi in keys}
for entry in entries.values():
    path = ROOT / 'assets/audio' / entry['output']
    assert path.parent == ROOT / 'assets/audio'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['output_sha256'], path
    assert path.stat().st_size == entry['output_bytes'], path
    with wave.open(str(path)) as wav:
        assert (wav.getframerate(), wav.getsampwidth(), wav.getnchannels()) == (48000, 2, 1), path
        assert abs(wav.getnframes() / 48000 - entry['duration_seconds']) < 1 / 48000, path
    assert entry['first_nonzero_ms'] <= 3 and entry['musical_onset_ms'] <= 10, path
    assert 0 < entry['peak'] <= .30, path
# Never consume another check's CSV, even if one already exists: parallel and
# standalone runs must validate mappings generated from the current sources.
scratch = ROOT / 'build/piano-import-check'
scratch.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(dir=scratch) as directory:
    out = Path(directory)
    binary = out / 'storage-check'
    subprocess.run([sys.executable, str(ROOT / 'tools/headless_build.py'),
                    str(ROOT / 'tools/piano_storage_check.jo'), '-o', str(binary)],
                   cwd=ROOT, check=True)
    subprocess.run([str(binary), str(out)], cwd=ROOT, check=True)
    with (out / 'coverage.csv').open() as stream:
        rows = list(csv.DictReader(stream))
assert {(int(r['midi']), r['dynamic']) for r in rows} == {
    (midi, dynamic) for midi in range(24, 109) for dynamic in ('pp', 'mf', 'ff')}
worst = 0
for row in rows:
    entry = entries[(row['dynamic'], int(row['slot']))]
    recorded = entry.get('recording_midi', entry['midi'])
    assert recorded == int(row['recording_midi']), row
    distance = abs(int(row['midi']) - (recorded + entry['pitch_offset_cents'] / 100))
    assert distance <= 1.5, (row, distance)
    worst = max(worst, distance)
print(f'PASS {len(entries)} hashed mono PCM16 recordings; C1-C8 production mappings '
      f'within {worst:.2f} semitones including measured source tuning')
