#!/usr/bin/env python3
"""Native half-second opening review with deterministic production audio.

Every game invocation owns /tmp/botw-render.lock here; do not wrap this tool.
Only the generated capture fixture adds telemetry/readbacks/software audio mixing.
"""
import argparse
from array import array
import json
import math
import os
from pathlib import Path
import re
import subprocess
import wave

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/round67'


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    source = (ROOT / 'game/main.jo').read_text()
    for path in (ROOT / 'game').glob('*.jo'):
        source = source.replace(repr(path.name), repr(str(path)))
    source = source.replace('sfx_init()\n', '__audio_state = 2\nsfx_init()\n', 1)
    imports = f"from '{ROOT}/sloppy/lib/game/audio.jo' import __mix as review_mix, __mix_buf as review_samples\n"
    source = source.replace('# ---------------- loading ----------------', imports + '''
review_audio = syscall(2, data(__zstr(env("BOTW_CAPTURE_DIR")! + "/audio.f32")), 0x241, 0x1A4)
assert(review_audio >= 0)
# ---------------- loading ----------------''', 1)
    source = source.replace('frame_number() > 0 and frame_number() % __capture_every',
                            'frame_number() >= 570 and frame_number() % __capture_every')
    marker = '    cpu_mark("shrines_light")'
    assert source.count(marker) == 1
    source = source.replace(marker, '''    review_wind = 0.0
    review_gust = 0.0
    loop voice in __voices:
        if voice.id == amb.wind: review_wind = f64(voice.volume)
        if voice.id == amb.wind_gust: review_gust = f64(voice.volume)
    eprint("review f={frame_number()} beat={story.beat} t={story.t:.5} pl={pl.pos} state={pl.state} cam={view_pos()} target={view_target()} fov={view_fov():.5} hud={not ui.hide} white={post.white:.5} indoor={env.indoor:.5} mood={seq.mood} alpha={story.title_alpha:.5} wind={review_wind:.5} gust={review_gust:.5} queued={laters.len()} done={story.title_done}")
    review_mix(800)
    __write_fd(review_audio, data(review_samples), review_samples.len()*4)
''' + marker)
    fixture = OUT / 'capture-after.jo'
    fixture.write_text(source)
    for source_path, binary in [(fixture, OUT / 'capture-after'), (ROOT / 'game/main.jo', OUT / 'game-after')]:
        temporary = binary.with_name(binary.name + '-new')
        subprocess.run([str(ROOT / 'sloppy/bin/sloppy'), 'build', str(source_path), '-o', str(temporary)], cwd=ROOT, check=True)
        temporary.replace(binary)


def run(binary, target, frames, flags):
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    settings = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
    settings.update(BOTW_NOVSYNC='1', BOTW_SCALE='1', SLOPPY_PLATFORM='x11',
                    SLOPPY_WINDOW='960x540', SLOPPY_FRAMES=str(frames), SLOPPY_SCREENSHOT=str(target))
    settings.update(flags)
    with target.with_suffix('.log').open('w') as log:
        subprocess.run(['flock', '/tmp/botw-render.lock', 'timeout', '600', str(binary)],
                       cwd=ROOT, env=settings, stdout=log, stderr=subprocess.STDOUT, check=True)
    assert target.is_file()


def passage():
    folder = OUT / 'after/passage'
    folder.mkdir(parents=True, exist_ok=True)
    run(OUT / 'capture-after', folder / 'final.png', 2880,
        {'BOTW_PASSAGE': '1', 'SLOPPY_INPUT': '20:w+',
         'BOTW_CAPTURE_DIR': str(folder), 'BOTW_CAPTURE_EVERY': '30'})
    with wave.open(str(folder / 'audio.wav'), 'wb') as wav:
        wav.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
        pcm = array('f')
        pcm.frombytes((folder / 'audio.f32').read_bytes())
        wav.writeframes(array('h', (int(max(-1, min(1, s))*32767) for s in pcm)).tobytes())
    (folder / 'audio.f32').unlink()
    verify()


def entries():
    for shrine in range(1, 5):
        run(OUT / 'game-after', OUT / f'after/shrines/{shrine}-entry.png', 720,
            {'BOTW_SKIP': '1', 'BOTW_TOWER': '1', 'BOTW_SHRINE': str(shrine),
             'BOTW_HOUR': '11', 'BOTW_WEATHER': 'clear', 'SLOPPY_WINDOW': '1280x720'})


def detail():
    run(OUT / 'game-after', OUT / 'after/shrines/3-wall-drive.png', 120,
        {'BOTW_SKIP': '1', 'BOTW_TOWER': '1', 'BOTW_SHRINE': '3',
         'BOTW_SHRINE_AT': '7,0,-3,0.6', 'BOTW_HOUR': '11',
         'BOTW_WEATHER': 'clear', 'SLOPPY_WINDOW': '1280x720'})


def verify():
    folder = OUT / 'after/passage'
    rows = []
    for line in (folder / 'final.log').read_text().splitlines():
        if not line.startswith('review '): continue
        rows.append(dict(re.findall(r'(\w+)=(vec3\([^)]*\)|\S+)', line)))
    assert len(rows) == 2881 and int(rows[0]['f']) == 0 and int(rows[-1]['f']) == 2880, len(rows)
    title = [r for r in rows if r['beat'] == 'title']
    assert title, 'straight passage approach must reach the title'
    assert any(float(r['alpha']) > .99 for r in title)
    assert any(r['done'] == 'true' for r in rows)
    assert all(r['hud'] == 'false' for r in rows if r['done'] == 'false')
    assert all(float(r['white']) == 0 for r in title), 'adaptation must clear before the card'
    cue = next(r for r in title if int(r['queued']) > 0)
    assert abs(float(cue['t']) - 1.2) < .017, cue
    for frame in range(570, 2881, 30): assert (folder / f'frame-{frame}.png').is_file()
    def vector(row, key): return tuple(float(n) for n in row[key][5:-1].split(','))
    control = next(r for r in rows if r['done'] == 'true')
    crane_rows = [r for r in rows if int(title[0]['f']) <= int(r['f']) <= int(control['f']) + 120]
    camera_step = max(math.dist(vector(a, 'cam'), vector(b, 'cam')) for a, b in zip(crane_rows, crane_rows[1:]))
    def gaze(row):
        delta = [b-a for a,b in zip(vector(row, 'cam'), vector(row, 'target'))]
        length = math.sqrt(sum(n*n for n in delta))
        return [n/length for n in delta]
    turn = max(math.degrees(math.acos(max(-1, min(1, sum(x*y for x,y in zip(gaze(a), gaze(b)))))))
               for a,b in zip(crane_rows, crane_rows[1:]))
    mouth = [r for r in rows if 570 <= int(r['f']) <= int(title[0]['f'])]
    wind_step = max(abs(float(a['wind'])-float(b['wind'])) for a,b in zip(mouth, mouth[1:]))
    assert camera_step < .5 and turn < 4, (camera_step, turn)
    assert wind_step < .03, wind_step
    footfalls = [r for r in mouth if int(r['f']) >= 1000]
    assert max(abs(float(a['wind'])-float(b['wind'])) for a,b in zip(footfalls, footfalls[1:])) < .005
    for row in title:
        if float(row['t']) <= 1.2: continue
        eye = vector(row, 'cam')
        point = list(vector(row, 'pl'))
        point[1] += 1.0
        delta = [b-a for a,b in zip(eye, point)]
        fwd = gaze(row)
        right = [-fwd[2], 0.0, fwd[0]]
        length = math.hypot(right[0], right[2])
        right = [n/length for n in right]
        up = [right[1]*fwd[2]-right[2]*fwd[1], right[2]*fwd[0]-right[0]*fwd[2], right[0]*fwd[1]-right[1]*fwd[0]]
        depth = sum(a*b for a,b in zip(delta, fwd))
        half = math.tan(float(row['fov'])*math.pi/360)
        assert depth > 0 and abs(sum(a*b for a,b in zip(delta, right))) < depth*half*16/9, row
        assert abs(sum(a*b for a,b in zip(delta, up))) < depth*half*.8, row
    stats = {'frames': len(rows), 'half_second_images': len(list(folder.glob('frame-*.png'))),
             'title_frame': int(title[0]['f']), 'title_cue_frame': int(cue['f']),
             'title_full_frame': int(next(r['f'] for r in title if float(r['alpha']) >= .99)),
             'control_frame': int(control['f']),
             'hud_hidden_until_control': True, 'white_clear_through_title': True,
             'hero_inside_crane_letterbox': True,
             'crane_max_camera_step_m': round(camera_step, 5), 'crane_max_turn_degrees': round(turn, 4),
             'mouth_max_wind_gain_step': round(wind_step, 5)}
    (OUT / 'opening-results.json').write_text(json.dumps(stats, indent=2) + '\n')
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'passage', 'entries', 'detail', 'verify'])
    args = parser.parse_args()
    globals()[args.command]()
