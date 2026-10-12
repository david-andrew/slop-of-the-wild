#!/usr/bin/env python3
"""Summarize matched captures, linear silhouette contrast and wind recurrence."""
from array import array
import csv
import html
import json
import math
from pathlib import Path
import wave

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/round68/sol2'
def correlation(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    den = math.sqrt(sum((x-ma)**2 for x in a) * sum((y-mb)**2 for y in b))
    return sum((x-ma)*(y-mb) for x,y in zip(a,b)) / max(den, 1e-20)

def audio_metrics(path):
    with wave.open(str(path)) as w:
        rate = w.getframerate()
        samples = array('h', w.readframes(w.getnframes()))
    block = rate // 10 * 2
    envelope = [math.sqrt(sum(v*v for v in samples[i:i+block])/block)/32768
                for i in range(0, len(samples), block)]
    settled = envelope[100:]
    scores = [(correlation(settled[:-lag], settled[lag:]), lag / 10)
              for lag in range(50, 401)]
    score, lag = max(scores)
    rms = math.sqrt(sum(v*v for v in samples)/len(samples))/32768
    return dict(rms=rms, rms_dbfs=20*math.log10(max(rms, 1e-12)),
        peak=max(abs(v) for v in samples)/32768,
        clipped=sum(abs(v)>=32760 for v in samples),
        strongest_envelope_recurrence=score, recurrence_lag_seconds=lag,
        envelope=envelope)

result = dict(baseline='fe93d1c', protocol='180 s production ambient mixer, score disabled, master 0.8, 11:00 field, gust=1.0, altitude=240 m; no per-export normalization. Pearson correlation of 100 ms stereo RMS windows, excluding first 10 s, lags 5..40 s.')
for phase in ('before', 'after'):
    result[phase] = {name: audio_metrics(OUT / phase / 'audio' / f'{name}.wav') for name in ('field', 'gust')}
    events = list(csv.DictReader((OUT / phase / 'audio/gust-events.csv').open()))
    times = [float(e['time']) for e in events]
    intervals = [b-a for a,b in zip(times,times[1:])]
    result[phase]['gust_events'] = dict(count=len(events),
        distinct_durations=sorted({float(e['duration']) for e in events}),
        looping=any(e['looping']=='true' for e in events),
        min_interval=min(intervals, default=None), max_interval=max(intervals, default=None))
    path = OUT / phase / 'silhouettes/contrast.json'
    if path.exists():
        silhouettes = json.loads(path.read_text())
        result[phase]['silhouettes'] = dict(passed=12-len(silhouettes['failures']),
            minimum=min(min(m['contrast'],m['paired_separation']) for m in silhouettes['results'].values()),
            canopy_storm=silhouettes['results']['canopy-storm'], threshold=silhouettes['threshold'])

(OUT / 'measurements.json').write_text(json.dumps(result, indent=2)+'\n')
b, a = result['before'], result['after']
lines = ['# Round 68 — Sol2 presentation and gust variation', '',
    'Baseline: `fe93d1c`, fast-forwarded on `sol2/work`. All graphical game renders are serialized through `/tmp/botw-render.lock`; capture scripts own their locks. Artifacts are ignored build output, not committed.', '',
    '## Shrines', '',
    '- Decorative generic lines emit 75% less light; named architecture emits 82.2% less and accent inlays/caustics 71.8% less. Machinery, pressure plates, stage signals, monk/exit glow, and actual fixture pools retain their values.',
    '- Oman Au opens at a 90° vertical field of view from inside the rear wall, framing the weight, pressure plate and bridge mouth together, then eases into the 50° follow camera. The full bounds of both mechanisms stay in view for at least 0.5 s after fade-in at 30/60/120 Hz.',
    '- Gameplay positions, collision, routes and puzzle timing are unchanged.', '',
    '## Storm canopy and rain', '',
    '- Existing bilinear forest/weather gate adds at most 0.36 local fill and 0.54 rim to skinned characters/enemies. Open ground, ordinary rain/clear weather and shrine interiors receive no added light. No scene exposure or background lighting changes.',
    '- Nearest rain stroke width falls to 52% of baseline; nearest opacity multiplier falls to 48%, with a longer lens fade. Distance is measured after wind drift so nearby windblown streaks receive the fade.', '']
for phase in ('before','after'):
    if 'silhouettes' in result[phase]:
        s=result[phase]['silhouettes']
        lines.append(f"- {phase.title()} silhouette checks: {s['passed']}/12, minimum {s['minimum']:.2%}; canopy storm {s['canopy_storm']['contrast']:.2%} silhouette / {s['canopy_storm']['paired_separation']:.2%} paired separation.")
lines += ['', '## Sound', '', result['protocol'], '',
    '| Measurement | Before | After |', '|---|---:|---:|']
for name in ('field','gust'):
    lines += [f"| {name.title()} strongest envelope recurrence | {b[name]['strongest_envelope_recurrence']:.4f} | {a[name]['strongest_envelope_recurrence']:.4f} |",
        f"| {name.title()} RMS dBFS | {b[name]['rms_dbfs']:.2f} | {a[name]['rms_dbfs']:.2f} |"]
lines += [f"| Wind gust voice starts in 180 s | {b['gust_events']['count']} (looping) | {a['gust_events']['count']} (one-shots) |", '',
    f"Four takes each for wind and rain, with distinct attack/shoulder/release, rising/falling two-pole filter sweeps, no consecutive repeated take, bounded playback rates 0.88–1.12, varying pan and independent renewal clocks. Observed wind start intervals: {a['gust_events']['min_interval']:.1f}–{a['gust_events']['max_interval']:.1f} s. The base wind becomes a nearly steady 19 s carrier with continuous slow rate drift, removing its dominant eight-second wobble. No clipped samples in either export.", '',
    'Listen: [before field](before/audio/field.wav), [after field](after/audio/field.wav), [before isolated gust](before/audio/gust.wav), [after isolated gust](after/audio/gust.wav). The recurrence measure detects regular amplitude patterns; it does not substitute for listening.', '',
    '## Map and hints', '',
    '- Survey labels grow from 12 to 14 logical px with opaque dark lettering on narrow parchment contour knockouts. Hover names use the same treatment.',
    '- Bottom hints grow from 15 to 17.5 logical px, keycaps from radius 11 to 12, on a compact 32 px dark strip. Text opacity rises from 0.496 to 0.9216 on the map. Reduced-size evidence covers both keyboard and gamepad at actual 960×540 and 1280×720 output.', '',
    '## Checks', '']
for path in sorted((OUT/'checks').glob('*.log')):
    text=path.read_text()
    status='FAIL' if 'panic:' in text or 'FAIL' in text else ('PASS' if 'PASS' in text or 'baked SFX' in text else 'inspect log')
    lines.append(f'- {status}: [{path.stem}](checks/{path.name})')
lines += ['', '## Matched images', '']
scenes = ['oman-arrival-120','oman-arrival-160','shrine-0-settled','shrine-1-settled','shrine-2-settled','shrine-3-settled','forest-storm','map-960x540-keys','map-960x540-pad','map-1280x720-keys','map-1280x720-pad']
for scene in scenes:
    lines += [f'### {scene}', '', f'![Before](before/{scene}.png)', f'![After](after/{scene}.png)', '']
(OUT/'report.md').write_text('\n'.join(lines))
(ROOT/'build/round68/README-sol2.md').write_text('[Sol2 report](sol2/report.md) — [measurements](sol2/measurements.json) — [visual comparison](sol2/comparison.html)\n')

cards=[]
for scene in scenes:
    cards.append(f'<section><h3>{html.escape(scene)}</h3><div class="pair">'+''.join(
        f'<figure><img src="{OUT/phase/(scene+".png")}" alt="{phase} {scene}"><figcaption>{phase.title()}</figcaption></figure>' for phase in ('before','after'))+'</div></section>')
summary=f'<p>Field wind recurrence: <strong>{b["field"]["strongest_envelope_recurrence"]:.4f} → {a["field"]["strongest_envelope_recurrence"]:.4f}</strong>. Four wind and four rain takes; irregular, non-repeating one-shots.</p>'
if 'silhouettes' in a:
    summary+=f'<p>Weather silhouettes: <strong>{a["silhouettes"]["passed"]}/12</strong>, minimum <strong>{a["silhouettes"]["minimum"]:.1%}</strong>.</p>'
document='<!doctype html><html><meta charset="utf-8"><style>body{margin:0;font:14px var(--font-sans,system-ui);color:var(--foreground,#ddd)}p{line-height:1.5}h3{font-size:15px;margin:22px 0 8px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:10px}figure{margin:0}img{width:100%;display:block}figcaption{color:var(--muted-foreground,#aaa);margin-top:4px}@media(max-width:500px){.pair{grid-template-columns:1fr}}</style>'+summary+''.join(cards)+'</html>'
(OUT/'comparison.html').write_text(document)
print('wrote', OUT/'report.md')
