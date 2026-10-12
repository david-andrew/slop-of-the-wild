#!/usr/bin/env python3
"""Independently recompute response measurements from feel_test --csv output (CPU only)."""
import argparse
import csv
import math
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    root = parser.parse_args().directory
    rows = list(csv.DictReader((root / 'measurements.tsv').open(), delimiter='\t'))
    metrics = {r['measure']: r for r in rows}
    checks = 0

    def check(ok, message):
        nonlocal checks
        if not ok:
            raise AssertionError(message)
        checks += 1

    def measured(name, expected, tolerance=2e-5):
        check(abs(float(metrics[name]['ours']) - expected) <= tolerance,
              f'{name}: TSV={metrics[name]["ours"]}, trace={expected}')

    def trace(name):
        data = list(csv.DictReader((root / f'{name}.csv').open()))
        check(float(data[0]['t']) == 0, f'{name}: missing initial row')
        check(all(abs(float(r['t']) - i / 60) < 1e-6 for i, r in enumerate(data)),
              f'{name}: timestamps must be fixed 60 Hz')
        check(all(float(r['look_x']) == float(r['look_y']) == 0 for r in data),
              f'{name}: right stick must be neutral')
        return data

    def distance(a, b):
        return math.hypot(float(a['x']) - float(b['x']), float(a['z']) - float(b['z']))

    def angle_error(a, b):
        return abs(math.atan2(math.sin(a - b), math.cos(a - b)))

    for r in rows:
        if r['evidence'] == 'gap':
            check(r['BotW reference'] == r['tolerance'] == '' and r['verdict'] == 'GAP',
                  f'{r["measure"]}: missing evidence must not become a scored baseline')
        check(math.isfinite(float(r['ours'])), f'{r["measure"]}: invalid value')

    for name, prefix, top, release_frame in [('run_curve', 'run', 5.556, None),
                                             ('sprint_start_stop', 'sprint', 8.1, 90)]:
        data = trace(name)
        for frame in [6, 12, 30, 60]:
            measured(f'{prefix} startup displacement at {frame}/60 s', distance(data[0], data[frame]))
        first = next(r for r in data[1:] if float(r['speed']) >= 0.9 * top)
        metric = 'time to 90% run' if prefix == 'run' else 'time to 90% sprint from rest'
        measured(metric, float(first['t']))
        if release_frame:
            release = data[release_frame]
            stopped = next(r for r in data[release_frame + 1:] if float(r['speed']) < 0.05)
            measured('sprint release stop time (<0.05 m/s)', float(stopped['t']) - float(release['t']))
            measured('sprint release stop distance', distance(release, data[-1]))
            check(all(r['sprint'] == 'true' for r in data[1:91]), 'sprint startup input')
            check(all(float(r['move_y']) == 0 for r in data[91:]), 'sprint release input')

    data = trace('run_stop')
    release = data[180]
    stopped = next(r for r in data[181:] if float(r['speed']) < 0.05)
    measured('run release stop time (<0.05 m/s)', float(stopped['t']) - float(release['t']))
    measured('run release stop distance', distance(release, data[-1]))

    for degrees in [90, 180]:
        data = trace(f'velocity_turn_{degrees}_world')
        heading = math.radians(degrees)
        check(all(angle_error(math.atan2(float(r['wish_x']), -float(r['wish_z'])), heading) < 2e-6
                  for r in data[1:]), f'{degrees}: world command drifted with camera')
        first = next(r for r in data[1:] if float(r['speed']) > 0.05 and
                     angle_error(math.atan2(float(r['vx']), -float(r['vz'])), heading) <= math.radians(5))
        measured(f'{degrees} run velocity heading response (<5 deg)', float(first['t']))
        measured(f'{degrees} run minimum speed during turn', min(float(r['speed']) for r in data[1:]))

    data = trace('jump_side_world')
    landed = next(r for r in data[1:] if r['state'] == 'ground')
    measured('jump 90 steer lateral displacement', abs(float(landed['x']) - float(data[0]['x'])))
    measured('jump 90 steer forward displacement', float(data[0]['z']) - float(landed['z']))
    measured('jump 90 steer airtime', float(landed['t']))
    check(float(data[1]['wish_z']) == -1 and data[1]['jump'] == 'true', 'jump launches forward')
    check(all(float(r['wish_x']) > .999999 for r in data[2:int(round(float(landed['t']) * 60)) + 1]),
          'air steering holds world east until landing')

    data = trace('glide_forward_world')
    check(all(r['state'] == 'glide' for r in data), 'steady glide entered another mode')
    horizontal = distance(data[0], data[-1])
    measured('steady forward displacement over 2 s', horizontal)
    measured('steady forward speed (2 s window)', horizontal / 2)
    measured('steady forward sink (2 s window)', (float(data[0]['y']) - float(data[-1]['y'])) / 2)
    check(all(float(r['wish_z']) == -1 for r in data[1:]), 'steady glide command')

    data = trace('glide_turn_90_world')
    check(all(r['state'] == 'glide' for r in data), 'glide turn entered another mode')
    check(all(float(r['wish_x']) > .999999 for r in data[1:]), 'glide turn command')
    heading = math.pi / 2
    body = next(r for r in data[1:] if angle_error(float(r['face']), heading) <= math.radians(5))
    velocity = next(r for r in data[1:] if angle_error(math.atan2(float(r['vx']), -float(r['vz'])), heading) <= math.radians(5))
    measured('90 glide heading response (<5 deg)', float(body['t']))
    measured('90 glide velocity response (<5 deg)', float(velocity['t']))
    peak = max(angle_error(float(a['face']), float(b['face'])) * 60 * 180 / math.pi
               for a, b in zip(data, data[1:]))
    measured('90 glide peak heading rate', peak, .007)  # CSV angles rounded to 1e-6 rad

    data = trace('camera_world_turn')
    initial = data[0]
    measured('steady run look-point lag', -(float(initial['z']) - float(initial['target_z'])))
    first = next(r for r in data[1:] if float(r['cam_yaw']) >= math.pi / 4)
    measured('90 world turn camera reaches 45 deg', float(first['t']))
    last_out = max(float(r['t']) for r in data[1:] if angle_error(float(r['cam_yaw']), math.pi / 2) > math.radians(5))
    measured('90 world turn settles within 5 deg', last_out + 1 / 60)
    peak = max(angle_error(float(a['cam_yaw']), float(b['cam_yaw'])) * 60 * 180 / math.pi
               for a, b in zip(data, data[1:]))
    measured('90 world turn peak yaw rate', peak, .007)
    print(f'PASS {checks} response trace/evidence checks; no BotW reference manufactured')


if __name__ == '__main__':
    main()
