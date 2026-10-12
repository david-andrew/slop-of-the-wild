#!/usr/bin/env python3
"""Report nearest-rank percentiles from game-side wall-clock samples, never fixed dt."""
import json, math, pathlib, re, statistics, sys

def percentile(values, p):
    values = sorted(values)
    return values[max(0, math.ceil(len(values) * p) - 1)]

def read_run(path, frames, scale="0.80", end=None):
    end = end or frames
    text = path.read_text()
    samples = [[float(x) for x in line.split()[2:]] for line in text.splitlines() if line.startswith('frame sample:')]
    early = [s for s in samples if s[0] <= 120]
    first_interval = samples[0] if samples else []
    samples = [s for s in samples if 241 <= s[0] <= end]
    if len(samples) != end - 240:
        raise ValueError(f'{path}: expected {end - 240} samples, got {len(samples)}')
    ft = [s[1] for s in samples]
    resolution = re.findall(r'; (\d+x\d+) scale ([\d.]+)', text)
    if not resolution or any(s != scale for _, s in resolution[2:]):
        raise ValueError(f'{path}: missing/variable render scale')
    gpu_lines = re.findall(r'^gpu ms:(.*?)= ([\d.]+)$', text, re.M)
    gpu = {}
    if path.stem.endswith(('-gpu','-cpu')) and ('BOTW_NOVSYNC:' in text or 'egl window surface' not in text):
        raise ValueError(f'{path}: uncapped X11 presentation was not confirmed')
    # Last complete query batch (120 frames), after startup; GPU runs explicitly uncapped X11.
    if gpu_lines:
        gpu = dict((k, float(v)) for k, v in re.findall(r'(\S+) ([\d.]+)', gpu_lines[-1][0]))
        gpu['total'] = float(gpu_lines[-1][1])
    gpu_batches = []
    for passes,total in gpu_lines[2:]:
        batch = dict((k,float(v)) for k,v in re.findall(r'(\S+) ([\d.]+)',passes))
        batch['total'] = float(total)
        gpu_batches.append(batch)
    load_start = path.with_suffix('.load-start').read_text().strip()
    load_end = path.with_suffix('.load-end').read_text().strip()
    switch_samples=[s for s in samples if len(s)>=9]
    usage_samples=[s for s in samples if len(s)>=11]
    usage=dict(sampled_frames=len(usage_samples))
    if usage_samples:
        for key,index in [('user_ms',9),('system_ms',10)]:
            values=[s[index] for s in usage_samples]
            usage[key]=dict(mean=statistics.mean(values), p99=percentile(values,.99))
    presentation = {}
    if samples and len(samples[0]) >= 14:
        for key,index in [('present_ms',11),('outside_present_ms',12),('runtime_thread_ms',13)]:
            values=[s[index] for s in samples]
            presentation[key]=dict(mean=statistics.mean(values), p95=percentile(values,.95), p99=percentile(values,.99))
    return dict(gpu_batches=gpu_batches, gpu_peak=max((b["total"] for b in gpu_batches),default=None), presentation=presentation, measured_frames=f'241-{end}', slow_intervals=sorted(samples,key=lambda s:-s[1])[:5], slow_cpu_frames=sorted(samples,key=lambda s:-s[2])[:5], thread_user_system=usage, context_switches=dict(voluntary=sum(s[7] for s in switch_samples), involuntary=sum(s[8] for s in switch_samples), sampled_frames=len(switch_samples)), first_interval=first_interval, startup_120=dict(p50=percentile([s[1] for s in early],.5), p95=percentile([s[1] for s in early],.95), p99=percentile([s[1] for s in early],.99), worst_sample=max(early,key=lambda s:s[1])),
                p50=percentile(ft,.5), p95=percentile(ft,.95), p99=percentile(ft,.99), worst=max(ft),
                mean=statistics.mean(ft), cpu=statistics.mean(s[2] for s in samples), thread=statistics.mean(s[4] for s in samples),
                cpu_p99=percentile([s[2] for s in samples],.99), thread_p99=percentile([s[4] for s in samples],.99), gap_p99=percentile([s[3] for s in samples],.99),
                gap=statistics.mean(s[3] for s in samples), long=sum(t > percentile(ft,.5)*1.5+1 for t in ft),
                uploads=statistics.mean(s[5] for s in samples), upload_bytes=statistics.mean(s[6] for s in samples),
                resolution=resolution[-1][0], scale=resolution[-1][1], gpu=gpu,
                cpu_profiles=re.findall(r'^cpu avg ms:.*$',text,re.M),
                fx_counts=re.findall(r'^fx particles:.*$',text,re.M),
                load_start=load_start, load_end=load_end, concurrent_processes=path.with_suffix('.processes').read_text().splitlines(),
                atlas_loads=re.findall(r'^  (?:names_atlas|title_atlas) .*$',text,re.M),
                warmup=re.findall(r'^  render_warmup .*$',text,re.M), skipped_gpu_frames=re.findall(r'^gpu skipped:.*$',text,re.M),
                first_frame=re.findall(r'^first frame:.*$', text,re.M), load=re.findall(r'^loaded in .*$',text,re.M),
                backend=re.findall(r'^frame cpu:.*$',text,re.M), samples=len(ft))

def main():
    root, repeats, frames, json_path = pathlib.Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    names=['open ground','Forest of Sprites','Hopper Pond','camp (fight)','grass fire','snow','storm in the forest','a shrine','sprinting through the forest','sprinting across the open']
    cases = [(i,name) for i,name in enumerate(names)]
    if (root/'cases.tsv').exists():
        cases = [(int(i),name) for i,name in (line.split('\t',1) for line in (root/'cases.tsv').read_text().splitlines())]
    modes = (root/'modes').read_text().split() if (root/'modes').exists() else ['paced','gpu']
    runs = {name:{mode:[read_run(root/f'{r}-{i}-{mode}.log',frames,
            scale='0.72' if name=='burning tent' else '0.80', end=900 if name=='burning tent' else frames)
            for r in range(1,repeats+1)] for mode in modes} for i,name in cases}
    result=dict(sample_columns=['interval_number','interval_ms','game_cpu_wall_ms','gap_ms','main_thread_cpu_ms','instance_uploads','instance_bytes','voluntary_switches (newer logs)','involuntary_switches (newer logs)','user_cpu_ms (latest logs)','system_cpu_ms (latest logs)','runtime_present_ms','gap_minus_present_ms','runtime_gap_thread_cpu_ms'],date=(root/'date').read_text().strip(),gpu=(root/'gpu').read_text().strip(),requested_window='default paced; 2133x1200 X11',logs=str(root),frames=f'241-{frames}',repeats=repeats,runs=runs)
    pathlib.Path(json_path).write_text(json.dumps(result,indent=2)+'\n')
    loads=[float(run[key].split()[0]) for modes in runs.values() for rs in modes.values() for run in rs for key in ['load_start','load_end']]
    print('# Performance\n')
    print(f"Generated by `tools/bench.sh` on {result['date']} ({result['gpu']}; {repeats} repeats per view/backend).")
    dims={mode:sorted({r['resolution'] for runs_by_mode in runs.values() for r in runs_by_mode[mode]}) for mode in modes}
    burn_note = '; burning tent: intervals 241–900, 660 samples at 72% scale' if 'burning tent' in runs else ''
    print(f"Measured real frame intervals {result['frames']}{burn_note}; nearest-rank percentiles. Actual output: {'; '.join(mode+' '+', '.join(dims[mode]) for mode in modes)}. Other scenes fixed at 80% of each output; three 2048² shadow maps. Paced runs use Wayland; GPU runs use uncapped X11 (`BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11`). Window-manager sizing is read from the game, not inferred from the requested window.")
    print(f"\n8 logical CPUs; concurrent one-minute load averages {min(loads):.2f}–{max(loads):.2f}. The render lock covers the whole suite; other agents' compilation and desktop/browser work can still run. Per-run load, CPU/thread time, resolution and first-frame measurements: [{pathlib.Path(json_path).name}]({pathlib.Path(json_path).name}). Raw logs: `{root}`.")
    print('\nEach cell gives the median across runs and, in parentheses, the min–max spread. GPU totals measure actual headroom, excluding presentation. CPU is game update + draw, excluding runtime final submit/audio; frame intervals include all of those and presentation. New raw samples separately record runtime presentation and remaining gap/thread work in the JSON.\n')
    print('| place | frame p50 ms | p95 ms | p99 ms | worst ms | CPU ms | long / run | GPU ms (top passes) |')
    print('|---|---|---|---|---|---|---|---|')
    def span(rs,key):
        vs=[r[key] for r in rs]
        return f'{statistics.median(vs):.2f} ({min(vs):.2f}–{max(vs):.2f})'
    for name,modes in runs.items():
        rs=modes.get('paced',next(iter(modes.values()))); gr=modes.get('gpu',[])
        totals=[r['gpu']['total'] for r in gr if r['gpu']]
        if not totals:
            print('| '+name+' | '+' | '.join(span(rs,k) for k in ['p50','p95','p99','worst','cpu','long'])+' | not measured |')
            continue
        passes={p:statistics.median(r['gpu'].get(p,0) for r in gr) for p in gr[0]['gpu'] if p!='total'}
        top=sorted(passes,key=passes.get,reverse=True)[:4]
        gt=f'{statistics.median(totals):.2f} ({min(totals):.2f}–{max(totals):.2f}); '+', '.join(f'{p} {passes[p]:.2f}' for p in top)
        if name == 'burning tent':
            gt += '; peak batch '+span(gr,'gpu_peak')
        print('| '+name+' | '+' | '.join(span(rs,k) for k in ['p50','p95','p99','worst','cpu','long'])+' | '+gt+' |')
    if any(r.get('presentation') for ms in runs.values() for rs in ms.values() for r in rs):
        print('\nPresentation is measured directly around the runtime platform present call. The residual gap includes submission, audio/polling, diagnostics and scheduling outside game callbacks. Thread time here is CPU used between game draw completion and the next update.\n')
        print('| place / mode | present p95 ms | residual gap p95 ms | runtime thread mean ms |')
        print('|---|---|---|---|')
        for name,ms in runs.items():
            for mode,rs in ms.items():
                if not all(r.get('presentation') for r in rs): continue
                vals=[statistics.median(r['presentation'][key][stat] for r in rs)
                      for key,stat in [('present_ms','p95'),('outside_present_ms','p95'),('runtime_thread_ms','mean')]]
                print(f'| {name} / {mode} | '+' | '.join(f'{v:.3f}' for v in vals)+' |')
    print('\nLong frames exceed 1.5× that run’s median + 1 ms. Startup and transition hitches are measured separately in [PERFORMANCE_FINDINGS.md](PERFORMANCE_FINDINGS.md). Do not interpret compositor-bound 16.7 ms GPU totals from older tables as uncapped GPU cost.')

if __name__ == '__main__':
    main()
