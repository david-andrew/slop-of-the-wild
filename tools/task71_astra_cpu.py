#!/usr/bin/env python3
"""Round 71 adjacent AB/BA CPU comparison. Owns a bounded flock per pair."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
import task68_astra_evidence as evidence
from task71_astra_capture import capture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--before', type=Path)
    parser.add_argument('--after', type=Path)
    parser.add_argument('--scenes', nargs='+', choices=capture.SCENES,
                        default=['golden', 'storm', 'storm-morning', 'snow'])
    parser.add_argument('--cpu', type=int, default=min(os.sched_getaffinity(0)))
    parser.add_argument('--locked', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--round', type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    out = args.output.resolve()
    assert out.is_relative_to(evidence.ROOT/'build')
    out.mkdir(parents=True, exist_ok=True)
    evidence.OUT = out
    evidence.SCENES = {name: ([(300, name)], dict(BOTW_SKIP='1') | flags, name)
                       for name, flags in capture.SCENES.items()}
    os.environ['TASK68_CPU_SET'] = str(args.cpu)
    if args.locked:
        assert len(args.scenes) == 1
        scene = args.scenes[0]
        for phase in (['before', 'after'] if args.round == 0 else ['after', 'before']):
            evidence.run(phase, scene, out/f'{scene}-{phase}-{args.round}', performance=True, locked=True)
        return
    assert args.before and args.after
    for phase, source in [('before', args.before), ('after', args.after)]:
        source = source.resolve()
        assert source.is_relative_to(evidence.ROOT/'build') and source.is_file()
        (out/phase).mkdir()
        shutil.copyfile(source, out/phase/'capture')
        (out/phase/'capture').chmod(0o755)
    for round in range(2):
        for scene in args.scenes:
            subprocess.run(['flock', '/tmp/botw-render.lock', 'timeout', '175', sys.executable,
                            __file__, str(out), '--locked', '--round', str(round),
                            '--cpu', str(args.cpu), '--scenes', scene], check=True)
    report = dict(protocol='Adjacent AB/BA, one bounded flock per pair; 1440 fixed frames, first 360 excluded; managed 1920x1080 Vulkan; main-thread affinity applied after frame 60; all 1080 steady samples retained per run',
                  cpu=args.cpu, scenes={})
    for scene in args.scenes:
        row = {}
        for phase in ['before', 'after']:
            pooled = []
            runs = []
            for round in range(2):
                text = (out/f'{scene}-{phase}-{round}'/'run.log').read_text()
                values = [float(line.split()[6]) for line in text.splitlines()
                          if line.startswith('frame sample:') and int(line.split()[2]) > 360]
                assert len(values) == 1080
                runs.append(evidence.pack.percentiles(values))
                pooled.extend(values)
            row[phase] = dict(pooled=evidence.pack.percentiles(pooled), runs=runs)
        row['delta_p99_ms'] = row['after']['pooled']['p99'] - row['before']['pooled']['p99']
        report['scenes'][scene] = row
    (out/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
