#!/usr/bin/env python3
"""Profile terrain distance bands without editing the working game's source.

Builds disposable copies under build/; all GPU runs hold the shared render lock.
Outside the selected band the probe draws constant colour (never visual evidence).
Subtracting the flat probe estimates each band's fragment cost. The bands do not
sum exactly because SIMD occupancy and early depth rejection change with branches.
"""
import argparse
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

from terrain_bench import CASES, read_log

BANDS = {'flat': None, 'near': (0, 30), 'middle': (30, 90), 'far': (90, 100000)}


def noise_inventory(root):
    functions = {}
    for filename in ['terrain.jo', 'shade.jo']:
        text = (root / filename).read_text()
        for match in re.finditer(r'^(\w+) = \([^\n]*\)(?: -> [^:\n]+)?:\n', text, re.M):
            start = match.end()
            stop = re.search(r'^\S', text[start:], re.M)
            body = text[start:start + stop.start()] if stop else text[start:]
            body = '\n'.join(line.split('#')[0] for line in body.splitlines())
            functions[match[1]] = body
    def counts(name, stack=()):
        if name == 'vnoise': return {'vnoise': 1, 'fbm3': 0, 'hash12': 4}
        if name == 'hash12': return {'vnoise': 0, 'fbm3': 0, 'hash12': 1}
        result = {'vnoise': 0, 'fbm3': int(name == 'fbm3'), 'hash12': 0}
        if name in stack: return result
        for callee in re.findall(r'\b(\w+)\(', functions.get(name, '')):
            if callee in functions:
                for key, value in counts(callee, stack+(name,)).items(): result[key] += value
        return result
    names = ['cold_uv', 'meadow_color', 'rock_color', 'terrain_albedo', 'snow_amount',
             'snow_color', 'rock_normal', 'face_normal', '__face_h', 'snow_normal', 'terrain_fs']
    return {name: counts(name) for name in names}



def count_variant(source, original):
    """Shader counters are for counts only; never use their timings as performance."""
    terrain = source / 'game/terrain.jo'
    begin = original.index('terrain_fs =')
    end = original.index('\nterrain_depth_fs =', begin)
    body = original[begin:end].replace('    vec4(c, 1)\n', '    terrain_count_color(c, length(w - u.cam))\n')
    body = body.replace('glsl_lod(u.canopy,', 'terrain_count_canopy(u.canopy,')
    body = body.replace('sample(u.mats,', 'terrain_count_mats(u.mats,')
    body = body.replace('glsl_lod(u.mats,', 'terrain_count_mats_lod(u.mats,')
    helper = r'''
terrain_count_color = (c: vec3, d: f32) -> vec4: vec4(c, d)
terrain_count_canopy = (t: Texture, uv: vec2, lod: f32) -> vec4: glsl_lod(t, uv, lod)
terrain_count_mats = (t: Texture, uv: vec2) -> vec4: sample(t, uv)
terrain_count_mats_lod = (t: Texture, uv: vec2, lod: f32) -> vec4: glsl_lod(t, uv, lod)
terrain_count_shader = (src: ShaderSource) -> ShaderSource:
    s = src
    counters = ["vnoise", "fbm3", "rock_color", "rock_normal", "face_normal", "snow_color", "snow_amount", "snow_normal", "cold_uv", "meadow_color", "terrain_count_canopy", "terrain_count_mats", "terrain_count_mats_lod"]
    declarations = ""
    loop name in counters: declarations = declarations + "float tc_{name} = 0.0;\n"
    s.fs = replace(s.fs, "precision highp int;", "precision highp int;\n" + declarations)
    loop name in counters:
        at = find(s.fs, "float f_{name}_")
        if at < 0: at = find(s.fs, "vec3 f_{name}_")
        if at < 0: at = find(s.fs, "vec2 f_{name}_")
        if at < 0: at = find(s.fs, "vec4 f_{name}_")
        assert(at >= 0)
        op = find(s.fs, "{{", at)
        s.fs = s.fs[..op + 1) + "\n    tc_{name} += 1.0;\n" + s.fs[op + 1..]
    at = find(s.fs, "vec4 f_terrain_count_color_")
    lp = find(s.fs, "(", at)
    rp = find(s.fs, ")", lp)
    params = split(s.fs[lp + 1..rp), ",")
    words_ = words(params[1])
    d = words_[words_.len() - 1]
    op = find(s.fs, "{{", rp)
    cl = find(s.fs, "\n}", op)
    # Integer packing stays below 2^24; RGBA32F preserves each counter exactly.
    a = "tc_fbm3 + tc_vnoise * 64.0 + tc_rock_color * 16384.0 + tc_rock_normal * 32768.0 + tc_face_normal * 65536.0 + tc_snow_color * 131072.0 + tc_snow_amount * 524288.0 + tc_snow_normal * 1048576.0"
    b = "tc_cold_uv + tc_meadow_color * 2.0 + tc_terrain_count_canopy * 4.0 + (tc_terrain_count_mats + tc_terrain_count_mats_lod) * 32.0"
    s.fs = s.fs[..op + 1) + "\n    return vec4({a}, {b}, {d}, 1.0);" + s.fs[cl..]
    s
'''
    patched = original[:begin] + body + original[end:] + helper
    if 'make_sh(terrain_noise_shader(shader(terrain_vs, terrain_fs)))' in patched:
        patched = patched.replace('make_sh(terrain_noise_shader(shader(terrain_vs, terrain_fs)))',
                                  'make_sh(terrain_count_shader(terrain_noise_shader(shader(terrain_vs, terrain_fs))))')
    else:
        patched = patched.replace('make_sh(shader(terrain_vs, terrain_fs))',
                                  'make_sh(terrain_count_shader(shader(terrain_vs, terrain_fs)))')
    terrain.write_text(patched)
    gfx = source / 'game/gfx.jo'
    gfx.write_text(gfx.read_text().replace('const GL_RGBA16F_ = 0x881A', 'const GL_RGBA16F_ = 0x8814')
                   .replace('GL_RGBA16F_, GL_RGBA, GL_HALF_FLOAT', 'GL_RGBA16F_, GL_RGBA, GL_FLOAT'))
    render = source / 'game/render.jo'
    text = render.read_text().replace('    gpu_mark("terrain")',
                                     '    glClearColor(0, 0, 0, 0)\n    glClear(GL_COLOR_BUFFER_BIT)\n    gpu_mark("terrain")')
    capture = r'''
        if frame_number() == 300:
            assert(glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE)
            px = fill(f32(1), target_rt.w * target_rt.h * 4)
            game_read_pixels_f32(0, 0, target_rt.w, target_rt.h, data(px) as *u8)
            counts = fill(0, 3)
            noise_sum = fill(0.0, 3)
            fbm_sum = fill(0.0, 3)
            noise_max = fill(0.0, 3)
            component_sum = fill(0.0, 3 * 13)
            loop k in [0..target_rt.w * target_rt.h):
                if px[k * 4 + 3] < 0.5: continue
                d = px[k * 4 + 2]
                band = if d < 30.0: 0 else: (if d < 90.0: 1 else: 2)
                counts[band] += 1
                a = int(px[k * 4])
                b = int(px[k * 4 + 1])
                values = [a & 63, (a >> 6) & 255, (a >> 14) & 1, (a >> 15) & 1, (a >> 16) & 1, (a >> 17) & 3, (a >> 19) & 1, (a >> 20) & 1, b & 1, (b >> 1) & 1, (b >> 2) & 7, (b >> 5) & 7, 1]
                assert(values[6] == 1)  # every covered fragment invoked snow_amount once
                fbm_sum[band] += f64(values[0])
                noise_sum[band] += f64(values[1])
                noise_max[band] = max(noise_max[band], f64(values[1]))
                loop j in [0..13): component_sum[band * 13 + j] += f64(values[j])
            loop band in [0..3):
                n = max(counts[band], 1)
                eprint("terrain counts: {band} pixels {counts[band]} fbm {fbm_sum[band] / f64(n):.3} vnoise {noise_sum[band] / f64(n):.3} max {noise_max[band]:.0}")
                labels = ["fbm3", "vnoise", "rock_color", "rock_normal", "face_normal", "snow_color", "snow_amount", "snow_normal", "cold_uv", "meadow_color", "canopy_reads", "material_reads", "fragments"]
                line = "terrain components: {band}"
                loop j in [0..13): line = line + " {labels[j]} {component_sum[band * 13 + j] / f64(n):.3}"
                eprint(line)
'''
    text = text.replace('        glDepthMask(1)\n    gpu_mark("chars")',
                        '        glDepthMask(1)\n'+capture+'    gpu_mark("chars")')
    render.write_text(text)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default='fac814a')
    parser.add_argument('--views', nargs='+', choices=['snow', 'fire', 'camp'], default=['snow'])
    parser.add_argument('--output', type=Path, default=Path('build/terrain-profile'))
    parser.add_argument('--counts-only', action='store_true', help='Measure actual shader call counts per visible fragment/band')
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
    report = {'band_limits_m': BANDS, 'baseline': args.baseline, 'runs': {}, 'noise_inventory': {}}
    for phase in ['before', 'after']:
        source = root / phase / 'source'
        source.mkdir(parents=True, exist_ok=True)
        if phase == 'before':
            archive = subprocess.check_output(['git', 'archive', args.baseline, 'game'])
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                tar.extractall(source, filter='data')
        else:
            shutil.copytree('game', source/'game', dirs_exist_ok=True)
        terrain = source / 'game/terrain.jo'
        original = terrain.read_text()
        report['noise_inventory'][phase] = noise_inventory(source/'game')
        report['runs'][phase] = {}
        variants = {'counts': None} if args.counts_only else BANDS
        for band, limits in variants.items():
            begin = original.index('terrain_fs =')
            body = original.index('\n', begin)+1
            if band == 'counts':
                count_variant(source, original)
                modified = terrain.read_text()
            elif limits is None:
                end = original.index('\nterrain_depth_fs =', body)
                modified = original[:body] + '    vec4(0, 0, 0, 1)\n' + original[end:]
            else:
                lo, hi = limits
                modified = original[:body] + (
                    f'    probe_distance = length(i.world - u.cam)\n'
                    f'    if probe_distance < {lo}.0 or probe_distance >= {hi}.0: return vec4(0, 0, 0, 1)\n'
                ) + original[body:]
            terrain.write_text(modified)
            executable = root / phase / ('game-'+band)
            subprocess.run(['sloppy/bin/sloppy', 'build', str(source/'game/main.jo'),
                            '-o', str(executable)], check=True)
            report['runs'][phase][band] = {}
            for view in args.views:
                prefix = root / phase / f'{view}-{band}'
                env = dict(clean, BOTW_SKIP='1', BOTW_SCALE='0.8', BOTW_GPU='1',
                           BOTW_NOVSYNC='1', SLOPPY_PLATFORM='x11', SLOPPY_WINDOW='2133x1200',
                           SLOPPY_FRAMES='360', SLOPPY_FRAME_STATS='1', BOTW_FRAME_LOG='1',
                           SLOPPY_SCREENSHOT=str(prefix.with_suffix('.png')), **CASES[view])
                print(phase, view, band, flush=True)
                with prefix.with_suffix('.log').open('w') as log:
                    subprocess.run(['flock', '/tmp/botw-render.lock', 'timeout', '300', str(executable)],
                                   env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
                report['runs'][phase][band][view] = read_log(prefix.with_suffix('.log'))
                if band == 'counts':
                    report['runs'][phase][band][view]['counts'] = re.findall(r'^terrain counts:.*$', prefix.with_suffix('.log').read_text(), re.M)
                    report['runs'][phase][band][view]['components'] = re.findall(r'^terrain components:.*$', prefix.with_suffix('.log').read_text(), re.M)
        terrain.write_text(original)
    (root/'profile.json').write_text(json.dumps(report, indent=2)+'\n')
    for view in args.views:
        for band in (['counts'] if args.counts_only else BANDS):
            if band == 'counts':
                for phase in ['before','after']:
                    print(phase, view, report['runs'][phase][band][view]['counts'])
                    print(phase, view, report['runs'][phase][band][view]['components'])
                continue
            values = [report['runs'][phase][band][view]['gpu_median']['terrain']
                      for phase in ['before','after']]
            print(f'{view} {band}: {values[0]:.2f} -> {values[1]:.2f} ms')


if __name__ == '__main__':
    main()
