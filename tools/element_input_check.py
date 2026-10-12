#!/usr/bin/env python3
"""Bounded production-input fire/save/rain/reuse course and ordinary tell captures.

Owns one render flock per process. All generated sources, saves and images stay
under build/. Run --tells for the natural storm warning and snow-entry evidence.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('build/element-input-check'))
    parser.add_argument('--tells', action='store_true')
    parser.add_argument('--only', choices=['storm', 'cold', 'write', 'read'])
    parser.add_argument('--record', action='store_true', help='retain ordinary-play clips at 15 fps')
    parser.add_argument('--continuous', action='store_true', help='capture ignition, propagation, rain and exact-copy reuse in one uninterrupted session')
    args = parser.parse_args()
    if args.continuous and (args.tells or args.only):
        parser.error('--continuous uses the complete interaction chain')
    if args.only and ((args.only in ("storm", "cold")) != args.tells):
        parser.error("--only storm/cold requires --tells; write/read uses the default course")
    os.chdir(ROOT)
    out = args.output.resolve()
    assert out.is_relative_to(ROOT / 'build'), 'evidence must stay under build/'
    out.mkdir(parents=True, exist_ok=True)
    source = Path('game/main.jo').read_text()
    source = re.sub(r"(?m)^(use|from) '([^']+)'", lambda m: f"{m[1]} '{(ROOT / 'game' / m[2]).resolve()}'", source)
    source = source.replace('update = (dt0: f64):', 'element_input_update = (dt0: f64):')
    source = source.replace('\ndraw = ():', '\nelement_input_draw = ():')
    assert source.count('    play_events()') == 1
    source = source.replace('    play_events()', '    element_input_observe()\n    play_events()')
    assert source.count('    player_torch_update(wdt, torch_lit)') == 1
    source = source.replace('    player_torch_update(wdt, torch_lit)', '    player_torch_update(wdt, torch_lit)\n    element_input_carried_observe()')
    fixture = Path('tools/element_input.fixture.jo').read_text()
    fixture = re.sub(r"(?m)^(use|from) '([^']+)'", lambda m: f"{m[1]} '{(ROOT / 'tools' / m[2]).resolve()}'", fixture)
    source += '\n' + fixture
    (out / 'fixture.jo').write_text(source)
    binary = out / 'game'
    subprocess.run(['sloppy/bin/sloppy', 'build', str(out / 'fixture.jo'), '-o', str(binary)], check=True)
    clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_', 'ELEMENT_INPUT_'))}

    def run(mode, frames, **settings):
        if args.only and args.only != mode:
            return
        directory = out / mode
        directory.mkdir(exist_ok=True)
        for old in directory.glob('*.png'):
            old.unlink()
        clip = directory / 'clip'
        clip.mkdir(exist_ok=True)
        for old in clip.glob('*.png'):
            old.unlink()
        env = {**clean, 'BOTW_SKIP': '1', 'BOTW_HOUR': '12',
               'BOTW_NOVSYNC': '1', 'SLOPPY_PLATFORM': 'x11', 'SLOPPY_WINDOW': '1280x720',
               'SLOPPY_FRAMES': str(frames), 'SLOPPY_SCREENSHOT': str(directory / 'final.png'),
               'ELEMENT_INPUT_MODE': mode, 'ELEMENT_INPUT_OUT': str(directory),
               'ELEMENT_INPUT_SAVE': str(out / 'mid-burn.save'), **settings}
        if args.record:
            env['ELEMENT_INPUT_RECORD'] = '1'
        (directory / 'settings.json').write_text(json.dumps({k: v for k, v in env.items() if k.startswith(('BOTW_', 'SLOPPY_', 'ELEMENT_INPUT_'))}, indent=2) + '\n')
        with (directory / 'run.log').open('w') as log:
            status = subprocess.run(['flock', '/tmp/botw-render.lock', 'timeout', ('900' if mode == 'chain' and args.record else '300'), str(binary)],
                                    env=env, stdout=log, stderr=subprocess.STDOUT).returncode
        log = (directory / 'run.log').read_text()
        for line in log.splitlines():
            if line.startswith(('PASS element', 'TRACE element')) or 'panic:' in line:
                print(line, flush=True)
        assert status == 0 and not re.search(r'panic:|error:|\bFAIL\b', log), f'{mode}: see {directory / "run.log"}'
        assert f'PASS element {mode}' in log, f'{mode}: incomplete course'
        if args.record:
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-framerate', '15',
                            '-pattern_type', 'glob', '-i', str(clip / '*.png'), '-c:v', 'libx264',
                            '-pix_fmt', 'yuv420p', '-crf', '20', str(directory / 'play.mp4')], check=True)

    if args.continuous:
        run('chain', 1620, BOTW_AT='-943,1881.6,0', BOTW_GIVE='old_shirt,torch,travelers_sword',
            BOTW_WEATHER_SEQ='430:rain',
            SLOPPY_INPUT='10:tab+,11:tab-,20:n1+,21:n1-,30:tab+,31:tab-,40:j+,41:j-,120:s+,235:s-,250:j+,251:j-,310:j+,311:j-,1420:tab+,1421:tab-,1430:right+,1431:right-,1440:e+,1441:e-,1450:tab+,1451:tab-,1520:n1+,1521:n1-,1540:j+,1541:j-')
        # The strip is an index into the complete 15 fps capture, with original
        # frame numbers retained. No restart or hidden simulation jump occurs.
        from PIL import Image, ImageDraw
        frames = [110, 250, 419, 1400, 1500, 1555, 1619]
        labels = ['Carried ignition', 'Carry from fire', 'Grass propagation', 'Rain extinguishes', 'Alternate equipment', 'Exact-copy reuse', 'Doused swing']
        strip = Image.new('RGB', (480 * len(frames), 302), '#111827')
        draw = ImageDraw.Draw(strip)
        for i, (frame, label) in enumerate(zip(frames, labels)):
            path = out / 'chain' / f'frame-{frame}.png'
            strip.paste(Image.open(path).convert('RGB').resize((480, 270)), (480*i, 32))
            draw.text((480*i+8, 7), f'{label} | frame {frame} ({frame/60:.2f}s)', fill='white')
        strip.save(out / 'chain' / 'interaction-strip.jpg')
        (out / 'chain' / 'strip.json').write_text(json.dumps(dict(frames=frames, labels=labels, continuous=True, simulation_fps=60), indent=2)+'\n')
    elif args.tells:
        # Initial loadout/weather/location only. No forced bolt, warning or cold state.
        # Storm has no SLOPPY_INPUT at all; snow uses only movement and camera keys.
        run('storm', 7200, BOTW_AT='-1030,1805,0', BOTW_WEATHER='storm', BOTW_GIVE='old_shirt,travelers_sword')
        run('cold', 300, BOTW_AT='-1150,1838,3.14159265', BOTW_GIVE='old_shirt',
            SLOPPY_INPUT='10:w+,90:w-,100:right+,130:right-')
    else:
        run('write', 420, BOTW_AT='-943,1881.6,0', BOTW_GIVE='old_shirt,torch,travelers_sword',
            SLOPPY_INPUT='10:tab+,11:tab-,20:n1+,21:n1-,30:tab+,31:tab-,40:j+,41:j-,120:s+,235:s-,250:j+,251:j-,310:j+,311:j-')
        # Weather changes through the production transition, not a wetness fixture.
        run('read', 1200, BOTW_WEATHER_SEQ='10:rain',
            SLOPPY_INPUT='1000:tab+,1001:tab-,1010:right+,1011:right-,1020:e+,1021:e-,1030:tab+,1031:tab-,1100:n1+,1101:n1-,1120:j+,1121:j-')
    print(f'Evidence: {out}')


if __name__ == '__main__':
    main()
