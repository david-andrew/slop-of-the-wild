#!/usr/bin/env python3
"""Render/meter final cues and refresh the self-contained local music audition.

Run listen.py --out build/listen-final first. This tool owns one lock for its sequential extra-clip
batch; never wrap it in flock. Existing embedded baseline clips survive
without reading another checkout. Python dependencies match music_score_export.
"""
import argparse
import base64
import html
import json
from pathlib import Path
import re
import subprocess

from listen import measure
from music_score_export import export

ROOT = Path(__file__).resolve().parents[1]
EXTRAS = ['wake', 'tower', 'tower_night', 'item', 'discovery', 'orb', 'orb_night',
          'secret', 'alert', 'victory', 'theme_2', 'theme_4', 'theme_8', 'theme_16',
          'title_music', 'field_240']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default='build/listen-final')
    parser.add_argument('--render-extras', action='store_true')
    args = parser.parse_args()
    out = (ROOT / args.out).resolve()
    assert out.is_relative_to(ROOT), 'keep audition artifacts in this checkout'
    baseline = {}
    destination = out / 'audition.html'
    if destination.exists():
        pairs = re.findall(r'<span>([^<]+)</span>[\s\S]*?<audio[^>]+src="([^"]+)"', destination.read_text())
        baseline = {label: source for label, source in pairs if label.endswith(' · old')}
    if args.render_extras:
        print('Rendering extra cues sequentially under /tmp/botw-render.lock', flush=True)
        with (out / 'extra-render.log').open('w') as log:
            subprocess.run(['flock', '/tmp/botw-render.lock', 'timeout', '300',
                            str(out / 'listen-render'), str(out), 'batch', *EXTRAS],
                           cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    levels = {name: measure(out / f'{name}.wav', 240 if name == 'field_240' else 45) for name in EXTRAS}
    assert all(r['true_peak_dbtp'] is None or r['true_peak_dbtp'] <= -1 for r in levels.values()), levels
    (out / 'extra-levels.json').write_text(json.dumps(levels, indent=2) + '\n')
    assert (out / 'levels.json').stat().st_mtime_ns >= (out / 'listen-render').stat().st_mtime_ns, 'finish listen.py before finalizing the audition'
    context = json.loads((out / 'levels.json').read_text())['clips']
    for source in sorted(out.glob('*-notes.csv')):
        if source.stem.removesuffix('-notes') in {'shrine_hum', 'shrine_room', 'shrine_steps', 'shrine_bed', 'night_insects'}:
            continue
        seconds = 240 if '1200' in source.name or '240' in source.name else (120 if 'combat_120' in source.name else 45)
        export(source, out / 'scores', seconds)
    rows = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width,initial-scale=1">',
            '<title>Slop of the Wild: extended piano audition</title>',
            '<style>body{font:16px system-ui;color:#e8eee8;background:#13201a;max-width:960px;margin:32px auto;padding:0 16px}h1{font-weight:600}p,small{color:#b6c8bc}small{display:block;font-size:.8em}.row{display:grid;grid-template-columns:220px 1fr;gap:16px;align-items:center;margin:16px 0}audio{width:100%;min-width:0}section{margin:32px 0}@media(max-width:600px){.row{grid-template-columns:1fr;gap:6px}body{margin:20px auto}}</style></head><body>',
            '<h1>Music audition</h1><p>Extended Iowa piano recordings · original gameplay gains · production mixer, wind and footsteps. No clip normalization.</p>']
    count = 0

    def player(label, name=None, source=None):
        nonlocal count
        if source is None:
            audio = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(out / f'{name}.wav'),
                                             '-c:a', 'libopus', '-b:a', '96k', '-f', 'ogg', '-'])
            assert audio.startswith(b'OggS') and b'OpusHead' in audio[:256]
            source = 'data:audio/ogg;base64,' + base64.b64encode(audio).decode()
        assert source.startswith('data:audio/ogg;base64,')
        encoded = base64.b64decode(source.split(',', 1)[1], validate=True)
        assert encoded.startswith(b'OggS') and b'OpusHead' in encoded[:256]
        reading = (levels.get(name) or context.get(name)) if name else None
        meter = f"<small>{reading['lufs_i']:.1f} LUFS-I · {reading['true_peak_dbtp']:.1f} dBTP</small>" if reading else ''
        rows.append(f'<div class="row"><div><span>{html.escape(label)}</span>{meter}</div><audio controls preload="none" src="{source}"></audio></div>')
        count += 1

    rows.append('<section><h2>Title and exploration</h2>')
    for name in ['title', 'field_day', 'cave_exit']:
        label = name.replace('_', ' ')
        if label + ' · old' in baseline:
            player(label + ' · old', source=baseline[label + ' · old'])
        player(label + ' · extended bank', name=name)
    rows.append('</section><section><h2>Field and chamber</h2>')
    for name in ['field_night', 'rain', 'field_240', 'shrine', 'combat_engaged', 'low_health']:
        player(name.replace('_', ' '), name=name)
    rows.append('</section><section><h2>Cues and motif family</h2>')
    for name in EXTRAS:
        if name != 'field_240': player(name.replace('_', ' '), name=name)
    rows.append('</section></body></html>')
    destination.write_text(''.join(rows))
    print(f'PASS {count} self-contained Opus players; all {len(EXTRAS)} extra exports <= -1 dBTP; {destination}')


if __name__ == '__main__':
    main()
