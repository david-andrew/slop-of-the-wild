#!/usr/bin/env python3
"""Matched 0.6 Vulkan/OpenGL and master captures; one render lock per launch.

Baseline must be an archived master copy under build/ with its own executable
and complete terrain/nature inputs. Images/metrics remain under build/.
"""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
import math
ROOT = Path(__file__).resolve().parents[1]
VIEWS = {
    'opening': {'SLOPPY_FRAMES': '600'},
    'overlook': {'BOTW_SKIP': '1', 'BOTW_AT': '-1050,1828,-2.36'},
    'forest': {'BOTW_SKIP': '1', 'BOTW_AT': '-1000,1620,3.14'},
    'fire': {'BOTW_SKIP': '1', 'BOTW_FIRE': '1', 'SLOPPY_FRAMES': '120'},
    'pond': {'BOTW_SKIP': '1', 'BOTW_AT': '-1190,1665,-0.9'},
    'camp': {'BOTW_SKIP': '1', 'BOTW_AT': '-1439,1606,0'},
    'snow': {'BOTW_SKIP': '1', 'BOTW_AT': '-1060,2230,2.0'},
    'storm': {'BOTW_SKIP': '1', 'BOTW_AT': '-1000,1620,3.14', 'BOTW_WEATHER': 'storm'},
    'shrine': {'BOTW_SKIP': '1', 'BOTW_TOWER': '1', 'BOTW_SHRINE': '1'},
    'title': {'BOTW_TITLE': '1', 'BOTW_AT': '-1024,1799,0', 'SLOPPY_FRAMES': '180'},
}
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline', type=Path, required=True)
    ap.add_argument('--output', type=Path, default=Path('build/renderer-compare'))
    ap.add_argument('--views', nargs='+', choices=VIEWS, default=list(VIEWS))
    ap.add_argument('--resume', action='store_true')
    a = ap.parse_args(); os.chdir(ROOT)
    baseline = a.baseline.resolve(); out = a.output.resolve()
    assert baseline.is_relative_to(ROOT/'build') and out.is_relative_to(ROOT/'build')
    out.mkdir(parents=True, exist_ok=True)
    exe = out/'game'
    subprocess.run(['sloppy/bin/sloppy', 'build', 'game/main.jo', '-o', str(exe)], check=True)
    before = baseline/'build/game'; assert before.is_file()
    summary = {'protocol': 'same 1280x720 pixels, scene scale 1, fixed simulation frames, hour 11, clear unless storm; raw RGB pixel differences, no normalization',
               'baseline_revision': (baseline/'build/revision').read_text().strip(), 'executables': {'current': digest(exe), 'master': digest(before)},
               'sources': {str(p): digest(p) for p in sorted(Path('game').glob('*.jo'))}, 'views': {}}
    clean = {k:v for k,v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
    for view in a.views:
        for mode in ('vulkan', 'opengl', 'master'):
            prefix = out/f'{view}-{mode}'
            env = {**clean, 'BOTW_HOUR':'11', 'BOTW_WEATHER':'clear', 'BOTW_SCALE':'1', 'BOTW_LOADTIME':'1',
                   'SLOPPY_PLATFORM':'x11', 'SLOPPY_WINDOW':'1280x720', 'SLOPPY_FRAMES':'1', 'SLOPPY_VSYNC':'0',
                   **VIEWS[view], 'SLOPPY_SCREENSHOT':str(prefix.with_suffix('.png'))}
            if mode != 'vulkan': env['SLOPPY_VULKAN'] = '0'
            cwd = baseline if mode == 'master' else ROOT
            binary = before if mode == 'master' else exe
            meta = {'binary_sha256': digest(binary), 'cwd': str(cwd), 'flags': {k:v for k,v in env.items() if k.startswith(('BOTW_', 'SLOPPY_'))}}
            stamp = prefix.with_suffix('.json')
            if not (a.resume and stamp.is_file() and json.loads(stamp.read_text()) == meta and prefix.with_suffix('.png').is_file()):
                print('capture', view, mode, flush=True)
                stamp.write_text(json.dumps(meta, indent=2)+'\n')
                with prefix.with_suffix('.log').open('w') as log:
                    subprocess.run(['flock', '/tmp/botw-render.lock', 'python3', str(ROOT/'tools/performance_window.py'), '1280x720',
                                    'timeout', '180', str(binary)], cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            assert Image.open(prefix.with_suffix('.png')).size == (1280,720)
        arrays = {m: Image.open(out/f'{view}-{m}.png').convert('RGB') for m in ('vulkan','opengl','master')}
        results = {}
        for left,right in [('vulkan','opengl'),('opengl','master'),('vulkan','master')]:
            delta = ImageChops.difference(arrays[left], arrays[right])
            channels = delta.split(); peak = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
            hist = delta.histogram(); combined = [sum(hist[k+256*c] for c in range(3)) for k in range(256)]
            target = math.ceil(1280*720*3*.99); count = 0; p99 = 0
            for k,n in enumerate(combined):
                count += n
                if count >= target: p99 = k; break
            results[f'{left}_vs_{right}'] = {'mean_absolute_rgb_counts': sum(ImageStat.Stat(delta).mean)/3, 'p99_absolute_rgb_counts': p99,
                'pixels_over_10_counts_pct': sum(peak.histogram()[11:])*100/(1280*720), 'maximum_rgb_counts': peak.getextrema()[1]}
            delta.point(lambda v:min(v*4,255)).save(out/f'{view}-{left}-vs-{right}-delta.png')
        summary['views'][view] = results
        (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        print(view, json.dumps(results), flush=True)
if __name__ == '__main__': main()
