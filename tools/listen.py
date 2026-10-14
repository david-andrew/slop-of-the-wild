#!/usr/bin/env python3
"""Render fixed 45s gameplay listening clips; measure BS.1770 integrated LUFS."""
import argparse
import array
import json
import html
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import wave

sys.dont_write_bytecode = True
from music_texture_check import check_textures

ROOT = Path(__file__).resolve().parents[1]
CLIPS = ['field_day', 'field_night', 'rain', 'combat_engaged', 'low_health', 'shrine', 'title', 'cave_exit']
AUDITS = ['night_insects', 'combat_120', 'field_1200', 'shrine_1200',
          'creature_boar', 'creature_fox', 'creature_crow', 'creature_bokoblin']
STEMS = ['shrine_hum', 'shrine_room', 'shrine_steps', 'shrine_music']
BEDS = ['shrine_bed']


def note_fixture(out):
    """Observe piano dispatch in a private copy; leave production sources intact."""
    fixture = out / 'fixture'
    game = fixture / 'game'
    scripts = fixture / 'tools'
    game.mkdir(parents=True, exist_ok=True)
    scripts.mkdir(exist_ok=True)
    for source in (ROOT / 'game').glob('*.jo'):
        shutil.copyfile(source, game / source.name)
    for name in ['listen_render.jo', 'music_event_paths.jo', 'creature_audio.jo']:
        shutil.copyfile(ROOT / 'tools' / name, scripts / name)
    music = game / 'music.jo'
    source = music.read_text()
    anchor = '    music_note_count += 1'
    assert source.count(anchor) == 1, 'piano note dispatch anchor changed'
    source = 'listen_note_t = 0.0\nlisten_notes = "onset_s,midi\\n"\n' + source
    source = source.replace(anchor, anchor + '\n    listen_notes += "{listen_note_t:.6},{midi}\\n"')
    music.write_text(source)
    render = scripts / 'listen_render.jo'
    source = render.read_text()
    source = source.replace('render = (name: str):\n    reset()', 'render = (name: str):\n    listen_notes = "onset_s,midi\\n"\n    reset()')
    source = source.replace('        t = f64(frame) / 60.0', '        t = f64(frame) / 60.0\n        listen_note_t = t')
    source = source.replace('    wav(name, mixb)', '    wav(name, mixb)\n    assert(write_file("{out_dir}/{name}-notes.csv", listen_notes))')
    render.write_text(source)
    return render


def measure(path, expected_seconds=45):
    result = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path),
                             '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                            capture_output=True, text=True, check=True)
    summary = result.stderr[result.stderr.rfind('Summary:'):]
    true_peak = float(re.search(r'Peak:\s+(-?inf|[\d.-]+) dBFS', summary)[1])
    integrated = re.findall(r'I:\s+(-?[\d.]+) LUFS', result.stderr)[-1]
    with wave.open(str(path)) as wav:
        assert wav.getnchannels() == 2 and wav.getsampwidth() == 2
        rate = wav.getframerate()
        values = array.array('h', wav.readframes(wav.getnframes()))
        seconds = len(values) / (2 * rate)
    def db(value):
        return round(20 * math.log10(value), 2) if value > 0 else None
    rms = math.sqrt(sum(v * v for v in values) / len(values)) / 32768
    # Walking intervals match the fixture; peak identifies transient masking.
    walking = values[:12 * rate * 2] + values[21 * rate * 2:33 * rate * 2]
    walk_rms = math.sqrt(sum(v * v for v in walking) / len(walking)) / 32768
    blocks = [math.sqrt(sum(v*v for v in values[i:i + rate*2]) / (rate*2)) / 32768
              for i in range(0, len(values), rate*2)]
    peak = max(abs(v) for v in values) / 32768
    assert seconds == expected_seconds and peak < 0.98, f'{path}: length/headroom regression'
    return {'seconds': seconds, 'lufs_i': float(integrated) if peak else None,
            'rms_dbfs': db(rms), 'walking_rms_dbfs': db(walk_rms),
            'loudest_second_rms_dbfs': db(max(blocks)), 'peak_dbfs': db(peak),
            'true_peak_dbtp': true_peak if peak else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render-clips', nargs=2, metavar=('BINARY', 'OUTPUT'), help=argparse.SUPPRESS)
    parser.add_argument('--individual-clips', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--clips-only', action='store_true', help='45-second listening clips and shrine stems only; skip long audits')
    parser.add_argument('--notes', action='store_true', help='write onset/MIDI CSVs from an instrumented private fixture copy')
    parser.add_argument('--out', default='build/listen')
    parser.add_argument('--binary', help='Use an already compiled fixture (baseline comparisons).')
    parser.add_argument('--measure-only', action='store_true')
    args = parser.parse_args()
    if args.render_clips:
        binary, destination = args.render_clips
        timings = []
        with (Path(destination) / 'render.log').open('w') as log:
            names = ['clips'] if args.clips_only else (CLIPS + STEMS if args.individual_clips else ['all'])
            for name in names:
                print(f'Rendering {name} under /tmp/botw-render.lock', flush=True)
                started = time.monotonic()
                marker = 'import os,sys,time; print("listen lock acquired:",time.monotonic(),flush=True); os.execvp(sys.argv[1],sys.argv[1:])'
                subprocess.run(['flock', '/tmp/botw-render.lock', sys.executable, '-c', marker, 'timeout', '180' if args.clips_only else '300', binary, destination, name], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
                acquired = float(re.findall(r'^listen lock acquired: ([\d.]+)$', (Path(destination) / 'render.log').read_text(), re.M)[-1])
                timings.append(dict(clip=name, lock_wait_s=max(0,acquired-started), process_wall_s=time.monotonic()-acquired))
                (Path(destination) / 'render-timing.json').write_text(json.dumps(timings,indent=2)+'\n')
        return
    out = (ROOT / args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not args.measure_only:
        binary = (ROOT / args.binary).resolve() if args.binary else out / 'listen-render'
        if not args.binary:
            source = note_fixture(out) if args.notes else ROOT / 'tools/listen_render.jo'
            with (out / 'build.log').open('w') as log:
                subprocess.run([str(ROOT / 'sloppy/bin/sloppy'), 'build', str(source), '-o', str(binary)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        # One bounded game process resets all seeded timelines; no nested locks.
        # Older baseline binaries retain the individual-clip protocol.
        subprocess.run([sys.executable, str(Path(__file__).resolve()),
                        '--render-clips', str(binary), str(out), *(['--individual-clips'] if args.binary else []),
                        *(['--clips-only'] if args.clips_only else [])], cwd=ROOT, check=True)
    textures = check_textures(out) if not args.binary and not args.clips_only else None
    levels = {name: measure(out / f'{name}.wav') for name in CLIPS + STEMS + ([] if args.binary else BEDS)}
    audit_levels = {name: measure(out / f'{name}.wav', {'combat_120': 120, 'field_1200': 1200, 'shrine_1200': 1200}.get(name, 45))
                    for name in AUDITS} if not args.binary and not args.clips_only else {}
    if not args.binary:
        for name, reading in {**levels, **audit_levels}.items():
            assert reading['true_peak_dbtp'] is None or reading['true_peak_dbtp'] <= -1.0, (name, reading)
        for name in ['field_day', 'field_night', 'rain']:
            # Extreme-register pp fragments, independent low answers and
            # ~75% notated silence intentionally replace the old middle-
            # register foreground score. Keep world/steps audible instead
            # of boosting piano to recover the old foreground-score LUFS.
            assert -43.0 <= levels[name]['lufs_i'] <= -30.0, (name, levels[name])
        engaged = levels['combat_engaged']['lufs_i']
        low = levels['low_health']['lufs_i']
        assert -22.5 <= engaged <= -20.0, levels['combat_engaged']
        assert -23.5 <= low <= engaged and engaged - low <= 2.5, levels['low_health']
        assert all(engaged > levels[name]['lufs_i'] for name in ['field_day', 'field_night', 'rain'])
        # The old 'louder than combat' target forced the reveal into a
        # fanfare. This original piano cue grows by register and motive,
        # keeping its breath and wind audible; reserve a pp/mp story range.
        for name in ['title', 'cave_exit']:
            assert -28.5 <= levels[name]['lufs_i'] <= -22.0, (name, 'restrained reveal', levels[name])
    hum, room, steps, music = (levels[k] for k in STEMS)
    relations = {}
    for name, bed in [('hum', hum), ('room', room)]:
        for reference, value, column in [('walking_steps', steps, 'walking_rms_dbfs'),
                                         ('music', music, 'rms_dbfs')]:
            relations[f'{name}_minus_{reference}_rms_db'] = (
                round(bed[column] - value[column], 2) if bed[column] is not None else None)
    if not args.binary:
        assert -30 <= hum['lufs_i'] <= -28, 'shrine hum participates in the mix'
        assert -30 <= levels['shrine_bed']['lufs_i'] <= -28, 'combined shrine bed target'
        # The finite glass/drone chamber has a different environmental bed
        # from the open field. Preserve a quiet chamber ceiling relative to
        # combat rather than boosting the field to exceed its drone.
        assert levels['shrine']['lufs_i'] < engaged - 3.0, 'shrine stays quieter than combat'
        assert 2 < relations['hum_minus_music_rms_db'] < 7, 'average bed/score energy balance'
        assert -24 < relations['room_minus_music_rms_db'] < -14, 'shrine room/music balance'
        assert -25 < room['rms_dbfs'] - hum['rms_dbfs'] < -17, 'room tone below hum'
        assert hum['peak_dbfs'] < steps['peak_dbfs'] - 1, 'footstep transients above hum'
        assert room['peak_dbfs'] < steps['peak_dbfs'] - 12, 'footstep transients above room'
    # The isolated stems must reproduce the full shrine mix to PCM rounding.
    def pcm(name):
        with wave.open(str(out / f'{name}.wav')) as wav:
            return array.array('h', wav.readframes(wav.getnframes()))
    full = pcm('shrine')
    stems = [pcm(name) for name in STEMS]
    error = max(abs(v - sum(parts)) for v, *parts in zip(full, *stems))
    assert error <= 4, f'stem timeline/gain drift: {error} PCM counts'
    relations['full_mix_minus_summed_stems_peak_pcm_counts'] = error
    if not args.binary:
        bed_error = max(abs(v - h - r) for v, h, r in zip(pcm('shrine_bed'), stems[0], stems[1]))
        assert bed_error <= 2, f'bed stem drift: {bed_error} PCM counts'
        relations['bed_minus_hum_and_room_peak_pcm_counts'] = bed_error
    data = {'protocol': ('45s listening clips only; long audits omitted. ' if args.clips_only else '45s listening clips; 45s insect and creature/120s combat/1200s field and shrine audits. ') + 'Seed 70070, production mixer/sequencer/player dispatch; master 0.8, music 1.0, export 1.0; no normalization. BS.1770 gated integrated LUFS and oversampled true peak via FFmpeg ebur128=peak=true; silence is null.',
            'textures': textures, 'audit_levels': audit_levels, 'clips': levels, 'shrine_balance': relations}
    (out / 'levels.json').write_text(json.dumps(data, indent=2) + '\n')
    table = ['| Clip | Seconds | LUFS-I | RMS dBFS | Peak dBFS | True peak dBTP |', '|---|---:|---:|---:|---:|---:|']
    for name in levels:
        row = levels[name]
        fmt = lambda key: 'silent' if row[key] is None else f'{row[key]:.2f}'
        table.append(f'| [{name}]({name}.wav) | 45 | {fmt("lufs_i")} | {fmt("rms_dbfs")} | {fmt("peak_dbfs")} | {fmt("true_peak_dbtp")} |')
    (out / 'LEVELS.md').write_text(data['protocol'] + '\n\n' + '\n'.join(table) + '\n\n' + '\n'.join(f'{k}: {v}' for k, v in relations.items()) + '\n')
    def loudness(name):
        value = {**levels, **audit_levels}[name]['lufs_i']
        return 'silent' if value is None else f'{value:.1f} LUFS-I'
    def spectrum_image(name):
        path = out / (name + '-spectrum.png')
        return f'<a href="{path.name}"><img alt="{html.escape(name)} log-frequency spectrogram" src="{path.name}"></a>' if path.exists() else ''
    players = ''.join(f'<section><label>{html.escape(name.replace("_", " "))} · {loudness(name)}</label><audio controls preload="none" src="{name}.wav"></audio>{spectrum_image(name)}</section>' for name in list(levels) + list(audit_levels))
    (out / 'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Listening clips</title><style>body{font:16px system-ui;margin:24px;max-width:900px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}label{display:block;margin-bottom:6px}audio,img{width:100%}</style><p>' + html.escape(data['protocol']) + '</p><main>' + players + '</main></html>')
    print(out / 'LEVELS.md')
    print(json.dumps(relations, indent=2))


if __name__ == '__main__':
    main()
