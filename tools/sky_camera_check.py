#!/usr/bin/env python3
"""Painted-sky evidence and matched storm grading through both update paths.

Owns one render lock per process. --source selects a copied game directory;
--capture-only records night/cloudy/storm baselines without regression assertions.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from PIL import Image, ImageStat

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, default=Path('build/sky-camera-check'))
parser.add_argument('--source', type=Path, default=Path('game'))
parser.add_argument('--capture-only', action='store_true')
a = parser.parse_args()
root = Path.cwd()
source = a.source.resolve()
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=True)
text = (source / 'main.jo').read_text()
text = re.sub(r"(?m)^(use|from) '([^']+)'", lambda m: f"{m[1]} '{source / m[2]}'", text)
# Keep the update path different but make both render the identical sky projection.
old = '    if free_cam:\n        f = v3(sin(fc_yaw) * cos(fc_pitch), sin(fc_pitch), -cos(fc_yaw) * cos(fc_pitch))\n        render_world(fc_pos, fc_pos + f, 50.0)'
assert text.count(old) == 1
text = text.replace(old, old.replace('if free_cam:', 'if free_cam or env("ROUND75_FIXED_VIEW") != none:'))
text = text.replace('    gpu_queue_wait()\n', '''    gpu_queue_wait()
    if frame_number() == 300:
        eprint("sky grade: sat={post.sat:.6} moon={post_moon:.6} golden={post_golden:.6} flash={env.lightning:.6} dark={env.dark:.6}")
''', 1)
text += '\nweather_rng_restore(rng(31))\nif env("ROUND75_GAMEPLAY") != none: free_cam = false\n'
(out / 'fixture.jo').write_text(text)
binary = out / 'game'
subprocess.run(['sloppy/bin/sloppy', 'build', str(out / 'fixture.jo'), '-o', str(binary)], check=True)
views = {'night': ('clear', '23', False), 'cloudy': ('cloudy', '11', False),
         'storm-free': ('storm', '11', False)}
if not a.capture_only:
    views.update({'clear-free': ('clear', '11', False), 'storm-play': ('storm', '11', True)})
clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'ROUND75_'))}
profiles = {}
for name, (weather, hour, gameplay) in views.items():
    settings = dict(clean, BOTW_SKIP='1', BOTW_CAM='-1030,260,1805,0.5,0',
        BOTW_HOUR=hour, BOTW_TIMESCALE='0', BOTW_WEATHER=weather,
        BOTW_NOVSYNC='1', SLOPPY_VSYNC='0', BOTW_SCALE='1', ROUND75_FIXED_VIEW='1',
        SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='1280x720', SLOPPY_FRAMES='300',
        SLOPPY_INPUT='', SLOPPY_SCREENSHOT=str(out / f'{name}.png'))
    if gameplay:
        settings['ROUND75_GAMEPLAY'] = '1'
    log_path = out / f'{name}.log'
    with log_path.open('w') as log:
        subprocess.run(['flock', '/tmp/botw-render.lock', 'python3', 'tools/performance_window.py',
                        '1280x720', 'timeout', '300', str(binary)], env=settings,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    observations = [dict((k, float(v)) for k, v in re.findall(r'(\w+)=([\d.]+)', line))
                    for line in log_path.read_text().splitlines() if line.startswith('sky grade:')]
    assert observations, f'missing production profile: {name}'
    profiles[name] = observations[-1]
    print('captured sky', name, profiles[name], flush=True)
(out / 'profiles.json').write_text(json.dumps(profiles, indent=2) + '\n')
if not a.capture_only:
    free, play = [profiles[k] for k in ('storm-free', 'storm-play')]
    for key in ('sat', 'moon', 'golden', 'dark', 'flash'):
        assert abs(free[key] - play[key]) < 0.00001, f'camera-dependent {key}: {free}/{play}'
    assert free['flash'] == 0.0, 'storm comparison must be outside a lightning flash'
    assert free['dark'] > 0.75 and profiles['night']['moon'] > 0.99
    # Central upper quarter is pure sky, above distant castle/volcano silhouettes.
    def sky(name):
        return Image.open(out / f'{name}.png').convert('RGB').crop((320, 0, 832, 135))
    import PIL.ImageChops
    difference = ImageStat.Stat(PIL.ImageChops.difference(sky('storm-free'), sky('storm-play'))).mean
    assert max(difference) < 0.75, f'camera-dependent painted sky: {difference}'
    storm = ImageStat.Stat(sky('storm-free').convert('L')).mean[0]
    clear = ImageStat.Stat(sky('clear-free').convert('L')).mean[0]
    assert storm < clear * 0.80, f'storm must darken the sky: {storm}/{clear}'
    print(f'PASS sky camera: identical grades; sky RGB drift {max(difference):.4f}, '
          f'storm/clear brightness {storm:.1f}/{clear:.1f}; moonlit night and cloudy layers captured')
