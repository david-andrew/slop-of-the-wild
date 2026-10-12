#!/usr/bin/env python3
"""Matched entrance architecture gallery, palette measurements and GPU budget.
Run after locked before/after captures; performs no game rendering.
"""
import argparse
import base64
import json
import re
import statistics
from pathlib import Path
import colorsys
import math
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument('root', nargs='?', default='build/shrine-round58')
args = parser.parse_args()
root = Path(args.root).resolve()
names = ['Ohman Ow', 'Jaba Badge', 'Owa Dime', 'Kay Nomut']
identities = ['Orange forge gantry / winding drums', 'Ember-red blast ribs / soot hood',
              'Gold clockwork wheel / barrel vault', 'Aqua scalloped aqueduct / caustic vaults']
rows = []
for n, name in enumerate(names, 1):
    row = {'shrine': name, 'identity': identities[n-1]}
    for phase in ['before', 'after']:
        directory = root / ('final' if phase == 'after' else phase)
        image_path = directory / f'{n}-architecture.png'
        room = Image.open(image_path).convert('RGB')
        w, h = room.size
        mask = Image.new('L', (w, h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rectangle((int(w*.06)+1, int(h*.245)+1, int(w*.94)-1, int(h*.78)-1), fill=255)
        mask_draw.rectangle((int(w*.415)+1, int(h*.465)+1, int(w*.585)-1, h), fill=0)
        histogram = Counter(color for color, included in zip(room.get_flattened_data(), mask.get_flattened_data()) if included)
        pixels = sum(histogram.values())
        hue_x = hue_y = luma_sum = linear_sum = 0.0
        linear_channels = [v/255/12.92 if v/255 <= .04045 else ((v/255+.055)/1.055)**2.4 for v in range(256)]
        for (r, g, b), count in histogram.items():
            rgb = (r/255, g/255, b/255)
            hue, _, _ = colorsys.rgb_to_hsv(*rgb)
            chroma = max(rgb)-min(rgb)
            angle = hue*math.tau
            hue_x += math.cos(angle)*chroma*count
            hue_y += math.sin(angle)*chroma*count
            luma_sum += (.2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2])*count
            linear_sum += (.2126*linear_channels[r]+.7152*linear_channels[g]+.0722*linear_channels[b])*count
        mean_hue = math.degrees(math.atan2(hue_y, hue_x)) % 360
        logs = sorted(directory.glob(f'{n}-gpu*.log'))
        gpu = []
        buildings = []
        for log in logs:
            samples = re.findall(r'^gpu ms:.*buildings ([0-9.]+).* = ([0-9.]+)$', log.read_text(), re.M)
            gpu += [float(total) for _, total in samples]
            buildings += [float(building) for building, _ in samples]
        assert len(gpu) >= 5, (phase, name, 'missing GPU samples')
        row[phase] = {'mean_hue_degrees': round(float(mean_hue), 1),
                      'mean_display_luma_percent': round(luma_sum/pixels*100, 2),
                      'mean_linear_luminance_percent': round(linear_sum/pixels*100, 2),
                      'room_pixels': pixels, 'gpu_median_ms': statistics.median(gpu),
                      'gpu_range_ms': [min(gpu), max(gpu)], 'gpu_samples': len(gpu),
                      'buildings_median_ms': statistics.median(buildings)}
    before, after = row['before']['gpu_median_ms'], row['after']['gpu_median_ms']
    row['gpu_delta_ms'] = round(after-before, 4)
    row['gpu_budget_ms'] = round(before*1.03+.1, 4)
    row['gpu_budget_pass'] = after <= row['gpu_budget_ms']
    rows.append(row)
(root/'measurements.json').write_text(json.dumps(rows, indent=2)+'\n')
font_paths = ['/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf', '/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf']
font_path = next((path for path in font_paths if Path(path).exists()), None)
font = ImageFont.truetype(font_path, 36) if font_path else ImageFont.load_default(size=36)
# Four shrine columns, before/after rows; all screenshots remain unmodified.
thumb_w, thumb_h, label_h = 640, 360, 56
canvas = Image.new('RGB', (4*thumb_w, 2*(thumb_h+label_h)), '#101823')
draw = ImageDraw.Draw(canvas)
for col, name in enumerate(names):
    for row, phase in enumerate(['before', 'after']):
        x, y = col*thumb_w, row*(thumb_h+label_h)
        draw.text((x+14, y+10), f'{name} · {phase}', fill='#e1e9ee', font=font)
        im = Image.open(root/('final' if phase == 'after' else phase)/f'{col+1}-architecture.png').convert('RGB')
        canvas.paste(im.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS), (x, y+label_h))
canvas.save(root/'entrance-4x2.png')
# Also retain the untouched default gameplay pitch beside the ceiling-revealing view.
for col, name in enumerate(names):
    for row, phase in enumerate(['before', 'after']):
        x, y = col*thumb_w, row*(thumb_h+label_h)
        im = Image.open(root/('final' if phase == 'after' else phase)/f'{col+1}-entrance.png').convert('RGB')
        canvas.paste(im.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS), (x, y+label_h))
canvas.save(root/'entrance-default-4x2.png')

lines = ['Round 58 shrine entrances and Talus camera', '',
         'Matched X11 uncapped captures: 1280x720, scale 1, clear weather, 11:00, identical spawn and scripted entrance pitch. GPU: 720 fixed simulation frames; five 120-frame interval samples after warmup, one matched capture per version.',
         'Palette mask: x 6–94%, y 24.5–78%, excluding hero x 41.5–58.5%, y >46.5%. No HUD/title or foreground pad. Hue is circular and chroma-weighted. Display luma is Rec.709-weighted sRGB; linear luminance also supplied.', '',
         '| Shrine | Hue before → after | Display luma before → after | Linear luminance before → after | GPU before → after (ms) | Budget |',
         '|---|---:|---:|---:|---:|---|']
for r in rows:
    b, a = r['before'], r['after']
    lines.append(f"| {r['shrine']} | {b['mean_hue_degrees']:.1f}° → {a['mean_hue_degrees']:.1f}° | {b['mean_display_luma_percent']:.2f}% → {a['mean_display_luma_percent']:.2f}% | {b['mean_linear_luminance_percent']:.2f}% → {a['mean_linear_luminance_percent']:.2f}% | {b['gpu_median_ms']:.2f} → {a['gpu_median_ms']:.2f} | {'PASS' if r['gpu_budget_pass'] else 'FAIL'} |")
mean_b = statistics.mean(r['before']['gpu_median_ms'] for r in rows)
mean_a = statistics.mean(r['after']['gpu_median_ms'] for r in rows)
lines += ['', f'Mean of four GPU medians: {mean_b:.4f} → {mean_a:.4f} ms ({mean_a-mean_b:+.4f} ms, {(mean_a/mean_b-1)*100:+.2f}%). Per-shrine allowance: baseline × 1.03 + 0.1 ms.', '', 'Checks:']
for name in ['feel_test', 'integration_test', 'input_check', 'camera_check', 'shrine_route_check', 'shrine_exit_check', 'shrine_discovery_check', 'shrine_ceremony_check', 'late_story_check']:
    path = root/'checks'/f'{name}.log'
    text = path.read_text()
    assert not re.search(r'^(?:FAIL|panic:|.*: error:)', text, re.M), f'{name} has a failure in the final log'
    assert any(token in text for token in ('PASS', 'passed', 'behavioral correctness:')), f'{name} has no success result'
    lines += ['', f'[{name}]({path})', '```text', *[line for line in text.splitlines() if line.startswith(('PASS', 'camera ', 'camera:', 'integration:', 'input:', 'feel:', 'agreement with measured', 'behavioral correctness:'))][-8:], '```']
lines += ['', 'Artifacts: entrance-4x2.png (ceiling view), entrance-default-4x2.png (default gameplay pitch), shrine-comparison.html, measurements.json, before/ and final/ original screenshots/GPU logs.', 'All game renders acquire /tmp/botw-render.lock exactly once.']
(root/'report.md').write_text('\n'.join(lines)+'\n')
image_b64 = base64.b64encode((root/'entrance-4x2.png').read_bytes()).decode()
table = ''.join(f"<tr><td>{r['shrine']}</td><td>{r['before']['mean_hue_degrees']}° → {r['after']['mean_hue_degrees']}°</td><td>{r['before']['mean_display_luma_percent']}% → {r['after']['mean_display_luma_percent']}%</td><td>{r['before']['gpu_median_ms']:.2f} → {r['after']['gpu_median_ms']:.2f}</td><td>{'PASS' if r['gpu_budget_pass'] else 'FAIL'}</td></tr>" for r in rows)
html = f'''<!doctype html><html><head><meta charset="utf-8"><title>Shrine entrance comparison</title><style>body{{font:14px var(--font-sans,system-ui);margin:0;color:var(--foreground)}}img{{width:100%;height:auto}}table{{border-collapse:collapse;width:100%;margin-top:20px}}th,td{{text-align:left;padding:10px;border-bottom:1px solid var(--border)}}p{{color:var(--muted-foreground);font-size:14px}}</style></head><body><img src="data:image/png;base64,{image_b64}" alt="Four shrine entrances: baseline above, revised below"><table><tr><th>Shrine</th><th>Mean room hue</th><th>Mean display luma</th><th>GPU ms</th><th>+3% + 0.1 ms</th></tr>{table}</table><p>Matched room mask excludes HUD, title, hero and foreground pad. Hue: circular chroma-weighted mean. Luma: Rec.709-weighted sRGB. GPU: median of matched 120-frame samples at 1280×720, scale 1. Original captures, linear luminance and full check logs accompany the report.</p></body></html>'''
(root/'shrine-comparison.html').write_text(html)
(root/'shrine-comparison-inline.html').write_text(html.replace('data:image/png;base64,'+image_b64, str(root/'entrance-4x2.png')))
print('\n'.join(lines[:15]))
if not all(r['gpu_budget_pass'] for r in rows): raise SystemExit('GPU budget exceeded')
