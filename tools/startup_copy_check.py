#!/usr/bin/env python3
"""Reproduce prepared startup from cp -r of a clean revision, retaining evidence in build/."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import tempfile
import shutil


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ref', default='master')
    ap.add_argument('--repeats', type=int, default=18)
    ap.add_argument('--binary-repeats', type=int, default=6)
    ap.add_argument('--resident-repeats', type=int, default=0, help='optional diagnostic runs of the identical copied binary with the original working directory')
    ap.add_argument('--max-median-load', type=float, default=3.5, help='fail if either prepared median exceeds this documented budget')
    ap.add_argument('--output', type=Path, default=Path('build/startup-copy-check'))
    ap.add_argument('--worktree', action='store_true', help='snapshot current tracked worktree contents instead of --ref (for pre-commit measurements)')
    ap.add_argument('--prepared-copy', type=Path, help='reuse a fresh copy already prepared by warm_assets.sh')
    a = ap.parse_args()
    assert not (a.prepared_copy and a.worktree), '--prepared-copy and --worktree are exclusive'
    assert a.repeats > 0 and a.binary_repeats > 0 and a.resident_repeats >= 0
    root = Path(__file__).resolve().parent.parent
    out = (root / a.output).resolve()
    assert out.is_relative_to(root / 'build'), 'raw evidence must stay under build/'
    out.mkdir(parents=True, exist_ok=True)
    revision = subprocess.check_output(['git', 'rev-parse', a.ref], cwd=root, text=True).strip()
    mesh_packs = subprocess.run(['git', 'cat-file', '-e', revision + ':game/architecture_assets.jo'],
                                cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
    # No cache flush, driver setting changes, or modifications to another worktree.
    with tempfile.TemporaryDirectory(prefix='botw-startup-copy-', dir=out) as temp:
        if a.prepared_copy:
            copy = a.prepared_copy.resolve()
            expected = subprocess.check_output(['git', 'show', revision + ':game/main.jo'], cwd=root)
            assert (copy / 'game/main.jo').read_bytes() == expected, 'prepared copy does not match requested revision'
            required = ('world', 'terrain', 'water', 'farland', 'structures', 'sfx', 'piano', 'chime') if mesh_packs else ('world',)
            assert all((copy / 'assets/prepared' / (name + '.bin')).is_file() for name in required), 'run warm_assets.sh in the fresh copy first'
        else:
            with tempfile.TemporaryDirectory(prefix='snapshot-', dir=out) as snapshot:
                archive = subprocess.run(['git', 'archive', revision], cwd=root, check=True, stdout=subprocess.PIPE).stdout
                subprocess.run(['tar', '-x', '-C', snapshot], input=archive, check=True)
                if a.worktree:
                    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
                    for relative in filter(None, tracked):
                        source = root / relative
                        target = Path(snapshot) / relative
                        if source.is_file(): shutil.copy2(source, target)
                    # Include newly added modules without copying build/ or prepared caches.
                    for folder in ('game', 'tools'):
                        for source in (root / folder).glob('*'):
                            if source.is_file(): shutil.copy2(source, Path(snapshot) / folder / source.name)
                # Terrain inputs are generated and ignored, but required for a full
                # Plateau. Preserve the source tree's cp -r symlinks/read-only inputs.
                for name in ['height.f32', 'water.f32', 'edge.f32', 'area.u8']:
                    subprocess.run(['cp', '-r', str(root / 'assets' / name), str(Path(snapshot) / 'assets' / name)], check=True)
                textures = root / 'assets/src/nature/Textures'
                assert textures.is_dir() and len(list(textures.glob('*.png'))) >= 20, 'missing nature source PNGs; incomplete snapshots invalidate startup timings'
                shutil.copytree(textures, Path(snapshot) / 'assets/src/nature/Textures')
                copy = Path(temp) / 'game'
                subprocess.run(['cp', '-r', snapshot, str(copy)], check=True)
            with (out / 'warm-assets.log').open('w') as log:
                # This script acquires its own render lock exactly once.
                subprocess.run(['tools/warm_assets.sh'], cwd=copy, env=clean, stdout=log, stderr=subprocess.STDOUT, check=True)
        copied_textures = copy / 'assets/src/nature/Textures'
        assert copied_textures.is_dir() and len(list(copied_textures.glob('*.png'))) >= 20, 'prepared copy lacks complete nature PNG inputs'
        if a.resident_repeats:
            with (out / 'resident-warm.log').open('w') as log:
                subprocess.run(['tools/warm_assets.sh'], cwd=root, env=clean,
                               stdout=log, stderr=subprocess.STDOUT, check=True)
            for pack in (copy / 'assets/prepared').glob('*.bin'):
                # Dependency stamps change on copy; payloads must still be identical.
                frozen = pack.read_bytes()
                resident = (root / 'assets/prepared' / pack.name).read_bytes()
                assert resident[:8] + resident[16:] == frozen[:8] + frozen[16:], 'resident pack payload differs'
        flags = dict(BOTW_LOADTIME='1', BOTW_NOVSYNC='1', SLOPPY_VSYNC='0', BOTW_SCALE='1',
                     BOTW_FRAME_LOG='1', SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='1280x720', SLOPPY_FRAMES='1', SLOPPY_FRAME_STATS='1')
        summary = {'revision': revision, 'worktree_snapshot': a.worktree, 'copy': str(copy), 'flags': flags, 'mesh_packs': mesh_packs,
                   'protocol': 'git archive plus ignored terrain inputs to clean snapshot; cp -r under build/; warm_assets.sh; complete ignored nature PNG inputs; fresh one-frame X11 processes, one flock per launch; time excludes lock wait',
                   'cache': 'warm after preparation; no page/shader cache deletion',
                   'driver_env': {k: v for k, v in clean.items() if k.startswith('__GL_')}, 'runs': []}
        summary['input_pngs'] = {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted((copy / 'assets/src/nature/Textures').glob('*.png'))}
        summary['compile_runs_s'] = []
        for repeat in range(a.binary_repeats):
            prefix = out / f'compile-{repeat + 1:02}.log'
            with prefix.open('w') as log:
                subprocess.run(['/usr/bin/time', '-f', 'compile_elapsed_s=%e', 'sloppy/bin/sloppy', 'build', 'game/main.jo', '-o', 'build/startup-compile'], cwd=copy, env=clean, stdout=log, stderr=subprocess.STDOUT, check=True)
            summary['compile_runs_s'].append(float(re.search(r'compile_elapsed_s=([0-9.]+)', prefix.read_text())[1]))
        summary['compile_median_s'] = statistics.median(summary['compile_runs_s'])
        modes = [('source', a.repeats), ('binary', a.binary_repeats), ('resident-binary', a.resident_repeats)]
        for mode, count in modes:
            for repeat in range(1, count + 1):
                prefix = out / f'{mode}-{repeat:02}'
                env = {**clean, **flags, 'SLOPPY_SCREENSHOT': str(prefix.with_suffix('.png'))}
                launch = ['sloppy/bin/sloppy', 'game/main.jo'] if mode == 'source' else [str(copy / 'build/asset-warmup/game')]
                cmd = ['python3', 'tools/performance_window.py', '1280x720',
                       'python3', str(root / 'tools/startup_measure.py'), *launch]
                loadavg = Path('/proc/loadavg').read_text().strip()
                with prefix.with_suffix('.log').open('w') as log:
                    subprocess.run(['flock', '/tmp/botw-render.lock', *cmd], cwd=(root if mode == 'resident-binary' else copy), env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
                loadavg_after = Path('/proc/loadavg').read_text().strip()
                text = prefix.with_suffix('.log').read_text()
                assert not re.search(r'panic:|error:|FAIL', text), text[-2000:]
                # Missing ignored terrain creates an empty scene and invalid timing.
                monsters = re.search(r'^enemies: (\d+),', text, re.M)
                assert monsters and int(monsters[1]) > 0, 'startup probe did not load Plateau encounters'
                if mesh_packs:
                    assert all(f'prepared {name}: hit' in text for name in ('terrain', 'water', 'farland', 'structures')), 'prepared mesh pack miss; warm_assets.sh must bake every static payload'
                if (copy / 'game/texture_assets.jo').is_file():
                    assert 'prepared textures: hit' in text and 'PNG decodes 0' in text, 'prepared texture pack miss'
                    assert 'startup textures: PNG decodes' not in text, 'unexpected startup PNG decode'
                first = re.search(r'first frame: cpu ([0-9.]+) thread ([0-9.]+) ms', text)
                assert first, 'first-frame callback timing missing'
                assert '1280x720 pixels' in text, 'invalid output size'
                load = float(re.search(r'loaded in ([0-9.]+)s', text)[1])
                elapsed = float(re.search(r'startup_elapsed_s=([0-9.]+)', text)[1])
                stages = {m[1]: float(m[2]) for m in re.finditer(r'^  ([A-Za-z_]+) ([0-9.]+)s$', text, re.M)}
                summary['runs'].append({'mode': mode, 'repeat': repeat, 'loaded_s': load,
                                        'process_elapsed_s': elapsed,
                                        'first_callback_end_s': float(re.search(r'startup_first_callback_end_s=([0-9.]+)', text)[1]),
                                        'first_capture_s': float(re.search(r'startup_first_capture_s=([0-9.]+)', text)[1]),
                                        'first_frame_cpu_ms': float(first[1]), 'first_frame_thread_ms': float(first[2]), 'stages_s': stages,
                                        'shader_hits': text.count('shader cache hit'), 'loadavg_before_lock': loadavg, 'loadavg_after': loadavg_after, 'log': str(prefix.with_suffix('.log'))})
                (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
                print(mode, repeat, f'loaded={load:.2f}s process={elapsed:.2f}s', flush=True)
        for mode, count in modes:
            if not count: continue
            runs = [r for r in summary['runs'] if r['mode'] == mode]
            summary[mode] = {field: {'median': statistics.median(r[field] for r in runs),
                                    'min': min(r[field] for r in runs), 'max': max(r[field] for r in runs)}
                             for field in ('loaded_s', 'process_elapsed_s', 'first_callback_end_s', 'first_capture_s', 'first_frame_cpu_ms', 'first_frame_thread_ms')}
            print(mode, json.dumps(summary[mode]), flush=True)
        measured = ['game/main.jo', 'sloppy/bin/sloppy', 'build/asset-warmup/game']
        measured += [str(p.relative_to(copy)) for p in sorted((copy / 'game').glob('*.jo'))]
        for relative in measured:
            summary.setdefault('sha256', {})[relative] = hashlib.sha256((copy / relative).read_bytes()).hexdigest()
        summary['max_median_load_s'] = a.max_median_load
        summary['budget_pass'] = all(summary[mode]['loaded_s']['median'] <= a.max_median_load for mode in ('source', 'binary'))
        (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        assert summary['budget_pass'], f'prepared median startup exceeded {a.max_median_load:.2f}s; inspect retained per-stage logs'


if __name__ == '__main__':
    main()
