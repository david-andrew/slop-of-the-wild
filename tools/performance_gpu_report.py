#!/usr/bin/env python3
"""Summarize fixed-output GPU work and paired captures without discarding outliers.

Usage: performance_gpu_report.py build/gpu63 build/perf-evidence/docs/performance-round63
Each phase has source.json and steady/, motion/, motion08/ captures from
performance_bench.py. Isolated experiments and rejected probes remain auditable.
"""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import re
from PIL import Image, ImageChops, ImageStat
from performance_bench import percentile, read_run, pool_runs
from performance_tail_report import analyze


def image_difference(before, after, crop_path=None):
    a = Image.open(before).convert('RGB')
    b = Image.open(after).convert('RGB')
    assert a.size == b.size == (2133, 1200), (a.size, b.size)
    diff = ImageChops.difference(a, b)
    stat = ImageStat.Stat(diff)
    result = {'mean_absolute_difference_255': statistics.mean(stat.mean),
              'max_channel_difference_255': max(v[1] for v in stat.extrema),
              'png_bytes_equal': before.read_bytes() == after.read_bytes(),
              'before_png_sha256': hashlib.sha256(before.read_bytes()).hexdigest(),
              'after_png_sha256': hashlib.sha256(after.read_bytes()).hexdigest()}
    histogram = diff.histogram()
    result['changed_rgb_channels'] = sum(sum(histogram[n + 1:n + 256]) for n in [0, 256, 512])
    # Two native-pixel crops retain canopy/shadow edges and nearby grass/figures.
    if crop_path:
        boxes = [(650, 220, 1162, 540), (850, 730, 1362, 1050)]
        result['crop_mean_absolute_differences_255'] = [statistics.mean(ImageStat.Stat(diff.crop(box)).mean) for box in boxes]
        sheet = Image.new('RGB', (1024, 640))
        for row, box in enumerate(boxes):
            sheet.paste(a.crop(box), (0, row * 320))
            sheet.paste(b.crop(box), (512, row * 320))
        sheet.save(crop_path)
        result['side_by_side_crops'] = str(crop_path)
        result['crop_png_sha256'] = hashlib.sha256(crop_path.read_bytes()).hexdigest()
    return result


def summarize(directory, raw, prefix):
    runs = {}
    for p in sorted(directory.glob('*-gpu-*.log')):
        if not p.with_name(p.stem + '.environment.json').exists():
            continue
        run = read_run(p)
        tail, samples = analyze(p.read_text(), allow_trace_gaps=True)
        # The frozen baseline has one bookkeeping gap beyond the 2 ms trace
        # guard. Retain the row and reject any additional, unexplained gap.
        expected_gaps = {'before/motion/forest-sprint-gpu-1-3': [2059]}
        assert tail['untraced_tail_frames'] == expected_gaps.get(prefix + '/' + p.stem, []), (p, tail['untraced_tail_frames'])
        assert len(samples['samples']) == int(run['metadata']['flags']['SLOPPY_FRAMES'])
        for field in ['cpu_spikes', 'cpu_wall_thread_spikes']:
            run.pop(field, None)
        run['tail_analysis'] = tail
        assert run['output'] == '2133x1200'
        flags = run['metadata']['flags']
        assert all(flags.get(k) == v for k, v in {'BOTW_GPU': '1', 'BOTW_NOVSYNC': '1', 'SLOPPY_PLATFORM': 'x11', 'BOTW_CPU': '1', 'BOTW_GPU_FRAME_LOG': '1'}.items())
        if prefix != 'queue-invalid':
            assert run['game_wall']['p50'] > 0 and run['game_thread']['p50'] > 0
            if int(flags['SLOPPY_FRAMES']) >= 2400 and p.name.startswith(('forest-sprint-', 'talus-')):
                fields = dict(re.findall(r'(distance|sprint|swing|talus_active|talus_strike|hp) ([\d.]+)', run['motion_samples'][-1]))
                assert float(fields['hp']) > 0
                if p.name.startswith('talus-'):
                    assert all(int(fields[k]) >= v for k, v in [('swing', 100), ('talus_active', 500), ('talus_strike', 60)])
                else:
                    assert float(fields['distance']) > 80 and int(fields['sprint']) > 300
        run['noise_cache_events'] = [line for line in p.read_text().splitlines() if line.startswith('post grain cache:')]
        run['queue_batches'] = [line for line in p.read_text().splitlines() if line.startswith('gpu queue:')]
        passes = defaultdict(list)
        frames = [(n, v) for n, v in samples['gpu_frames'].items() if n >= 240]
        names = set().union(*(v['passes'].keys() for _, v in frames))
        for name in names:
            # Missing alternating cascades cost zero in that delivered frame.
            passes[name] = [v['passes'].get(name, 0) for _, v in frames]
        run['ranked_gpu_passes'] = [{'pass': k, 'mean_ms': statistics.mean(v),
                                    'p99_ms': percentile(v, .99)}
                                   for k, v in sorted(passes.items(), key=lambda x: -statistics.mean(x[1]))]
        raw[prefix + '/' + p.stem] = samples
        runs[p.stem] = run
    assert runs, directory
    pooled = pool_runs(directory, runs)
    for group in pooled.values():
        gpu = [v for name in group['runs']
               for n, v in raw[prefix + '/' + name]['gpu_frames'].items() if n >= 240]
        values = [v['total'] for v in gpu]
        producer_thread = [row[4] + row[13] for name in group['runs']
                           for row in raw[prefix + '/' + name]['samples'] if row[0] >= 241]
        group['producer_thread_total'] = {'mean': statistics.mean(producer_thread), 'p50': percentile(producer_thread, .5),
                                          'p99': percentile(producer_thread, .99), 'worst': max(producer_thread)}
        group['gpu_total'] = {'mean': statistics.mean(values), 'p50': percentile(values, .5),
                              'p99': percentile(values, .99), 'worst': max(values), 'samples': len(values)}
        names = set().union(*(v['passes'].keys() for v in gpu))
        group['ranked_gpu_passes'] = sorted(
            [{'pass': name, 'mean_ms': statistics.mean(v['passes'].get(name, 0) for v in gpu)} for name in names],
            key=lambda v: -v['mean_ms'])
    return {'runs': runs, 'pooled': pooled}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    a = parser.parse_args()
    raw = {}
    report = {'protocol': 'round63-gpu-shaders-v1',
              'hardware': 'i7-6700 / GTX 1070 / Linux X11 / NVIDIA 580.178.04',
              'sampling': 'nearest-rank pooled producer intervals; discard only startup frames 1–240; retain every repeat and outlier',
              'gpu_alignment': 'sample n describes game frame n−1; timer queries are asynchronous; final three GPU draws may be unread',
              'trace_gap_note': 'One frozen baseline frame (forest-sprint repeat 3, game frame 2059) has CPU wall/thread 12.504/5.318 ms and six involuntary switches without a stage trace. Stage timing uses a 10 ms threshold with a 2 ms bookkeeping guard; this guard did not cover the entire raw CPU frame. The row is retained and stage attribution is unavailable. Every other CPU frame >12 ms is traced.',
              'phases': {}}
    for phase in ['before', 'after']:
        base = a.root / phase
        source = json.loads((base / 'source.json').read_text())
        groups = {d.name: summarize(d, raw, phase + '/' + d.name)
                  for d in sorted(base.iterdir()) if d.is_dir()}
        assert set(groups) == {'steady', 'motion', 'motion08'}
        assert all(len(g['runs']) == (9 if name == 'steady' else 6)
                   for name, g in groups.items())
        assert all(r['metadata']['executable_sha256'] == source['executable_sha256']
                   for g in groups.values() for r in g['runs'].values())
        report['phases'][phase] = {'source': source, 'groups': groups}
    for name, digest in report['phases']['after']['source']['sources'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, 'final sources changed: ' + name
    assert report['phases']['before']['source']['compiler_sha256'] == report['phases']['after']['source']['compiler_sha256']
    before_sources = report['phases']['before']['source']['sources']
    after_sources = report['phases']['after']['source']['sources']
    report['changed_game_sources'] = [name for name in sorted(before_sources.keys() | after_sources.keys())
                                      if before_sources.get(name) != after_sources.get(name)]
    crops = a.output.parent / (a.output.name + '-crops')
    crops.mkdir(exist_ok=True)
    report['paired_captures'] = {}
    for group, before in report['phases']['before']['groups'].items():
        after = report['phases']['after']['groups'][group]
        assert before['runs'].keys() == after['runs'].keys()
        for name, b in before['runs'].items():
            c = after['runs'][name]
            flags = lambda r: {k: v for k, v in r['metadata']['flags'].items() if k != 'SLOPPY_SCREENSHOT'}
            assert flags(b) == flags(c), (group, name)
            report['paired_captures'][group + '/' + name] = image_difference(
                a.root / 'before' / group / (name + '.png'),
                a.root / 'after' / group / (name + '.png'), crops / (group + '-' + name + '.png'))
            assert report['paired_captures'][group + '/' + name]['max_channel_difference_255'] <= 1, 'visible capture drift: ' + name
    if (a.root / 'profile-before').exists():
        report['profile_before'] = summarize(a.root / 'profile-before', raw, 'profile-before')
    report['isolated_changes'] = {}
    for name, previous in [('grass', 'profile-before'), ('grass-post', 'grass'), ('paper', 'grass-post'), ('grass-bound', 'paper')]:
        directory = a.root / name
        if not directory.exists():
            continue
        group = summarize(directory, raw, name)
        group['retained'] = name in {'grass-post', 'paper'}
        group['interpretation'] = ('No consistent isolated GPU gain; grass edits reverted.' if name.startswith('grass') and name != 'grass-post' else
                                   'Tap reuse is pixel-exact; isolated timing gain is inconclusive.' if name == 'grass-post' else
                                   'Static pigment cache reduces the post pass; max RGB error one byte.')
        group['paired_captures'] = {n: image_difference(
            a.root / previous / (n + '.png'), directory / (n + '.png'), crops / (name + '-' + n + '.png'))
            for n in group['runs']}
        report['isolated_changes'][name] = group
    report['queue_probe'] = {}
    for phase in ['queue-control', 'queue-valid', 'queue-yield']:
        directory = a.root / phase
        if directory.exists():
            report['queue_probe'][phase] = summarize(directory, raw, phase)
    if report['queue_probe']:
        for group in report['queue_probe'].values():
            assert all(run['game_wall']['p50'] > 0 and run['game_thread']['p50'] > 0
                       for run in group['runs'].values()), 'invalid queue CPU samples'
        report['queue_probe']['paired_captures'] = {n: image_difference(
            a.root / 'queue-control' / (n + '.png'),
            a.root / 'queue-valid' / (n + '.png'), crops / ('queue-' + n + '.png'))
            for n in report['queue_probe']['queue-valid']['runs']}
        assert all(r['png_bytes_equal'] for r in report['queue_probe']['paired_captures'].values())
        report['queue_probe']['yielding_paired_captures'] = {n: image_difference(
            a.root / 'queue-control' / (n + '.png'), a.root / 'queue-yield' / (n + '.png'),
            crops / ('queue-yield-' + n + '.png')) for n in report['queue_probe']['queue-yield']['runs']}
        assert all(r['png_bytes_equal'] for r in report['queue_probe']['yielding_paired_captures'].values())
        assert all(r['metadata']['executable_sha256'] == report['phases']['after']['source']['executable_sha256']
                   for r in report['queue_probe']['queue-yield']['runs'].values())
    report['unfenced_pilot'] = summarize(a.root / 'grass-post-motion', raw, 'unfenced-pilot')
    report['rejected_queue_probe'] = {'reason': 'build/ wrapper imported main through a different lexical path, creating a second game; scenes differ and CPU frame fields are zero; excluded as a protocol error',
                                      'data': summarize(a.root / 'queue-motion', raw, 'queue-invalid')}
    report['check_drivers'] = {p.name: p.read_text() for p in [a.root / 'check-headless.py', a.root / 'render-checks.py']}
    report['checks'] = {}
    for p in (a.root / 'checks').glob('*.json'):
        report['checks'].update(json.loads(p.read_text()))
    required = {'feel_test', 'fauna_test', 'element_test', 'element_check', 'save_test',
                'integration_test', 'input_check', 'combat_check', 'camera_check',
                'title_handoff_check', 'journey_controller_check', 'prepared_assets_check',
                'shrine_route_check', 'late_story_check', 'traversal_check', 'slot_check',
                'shrine_exit_check', 'passage_check', 'opening_check', 'occluder_check',
                'weather_silhouette_check', 'daylight_check', 'talus_checks', 'talus_test',
                'talus_mesh_check', 'talus_skin_check', 'talus_visual_check'}
    assert required <= report['checks'].keys(), 'missing checks: ' + str(required - report['checks'].keys())
    assert all(r['exit_code'] == 0 for r in report['checks'].values()), 'failed check'
    for check in report['checks'].values():
        log = Path(check['log'])
        check['log_text'] = log.read_text()
        check['log_sha256'] = hashlib.sha256(log.read_bytes()).hexdigest()
    report['source_counts'] = json.loads((a.root / 'loc.json').read_text()) if (a.root / 'loc.json').exists() else None
    report['compilation'] = json.loads((a.root / 'compilation.json').read_text()) if (a.root / 'compilation.json').exists() else None
    report['sample_counts'] = {'runs': len(raw), 'raw': sum(len(r['samples']) for r in raw.values()),
                               'gpu': sum(len(r['gpu_frames']) for r in raw.values())}
    a.output.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    with gzip.open(str(a.output) + '-samples.json.gz', 'wt') as f:
        json.dump(raw, f, separators=(',', ':'))
    print(report['sample_counts'])
    for phase, data in report['phases'].items():
        for name, group in data['groups'].items():
            for view, result in group['pooled'].items():
                print(phase, name, view, 'interval', result['interval']['p99'], result['interval']['worst'])
    print('largest paired MAD:', max(r['mean_absolute_difference_255'] for r in report['paired_captures'].values()))


if __name__ == '__main__':
    main()
