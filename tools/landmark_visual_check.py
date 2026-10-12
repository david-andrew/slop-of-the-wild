#!/usr/bin/env python3
"""Locked, fixed-camera distant-landmark captures and paired uncapped GPU checks.

Build immutable baseline/current executables, then run before/after with --binary.
Run paired --binary CURRENT --baseline BEFORE for three interleaved comparisons.
Use paired --verify-gpu with the same --output to recheck retained GPU logs.
"""
import argparse
import json
import os
from pathlib import Path
import re
import statistics
import subprocess

SCENES = {
    "overlook-clear": {"BOTW_SKIP": "1", "BOTW_AT": "-1030,1805,1.57", "BOTW_HOUR": "11"},
    "overlook-golden": {"BOTW_SKIP": "1", "BOTW_AT": "-1030,1805,1.57", "BOTW_HOUR": "6.4"},
    "overlook-dusk": {"BOTW_SKIP": "1", "BOTW_AT": "-1030,1805,1.57", "BOTW_HOUR": "18.4"},
    "title-850": {"BOTW_TITLE": "1", "SLOPPY_INPUT": "10:w+,300:w-"},
}

def capture(binary, root, name, flags, frames, window="1280x720", locked=False):
    root.mkdir(parents=True, exist_ok=True)
    # A closed test window must not pass by inheriting a previous screenshot.
    (root / f"{name}.png").unlink(missing_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("BOTW_", "SLOPPY_"))}
    env.update(BOTW_WEATHER="clear", BOTW_SCALE="0.8", BOTW_NOVSYNC="1",
               SLOPPY_PLATFORM="x11", SLOPPY_WINDOW=window,
               SLOPPY_FRAMES=str(frames), SLOPPY_SCREENSHOT=str((root / f"{name}.png").resolve()))
    env.update(flags)
    command = ["timeout", "300", str(binary.resolve())]
    if not locked:
        command = ["flock", "/tmp/botw-render.lock", *command]
    with (root / f"{name}.log").open("w") as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    assert (root / f"{name}.png").is_file()
    print(root / f"{name}.png", flush=True)


def gpu_summary(root, name):
    text = (root / f"{name}.log").read_text()
    batches = []
    for passes, total in re.findall(r"^gpu ms:(.*?)= ([\d.]+)$", text, re.M):
        batch = {k: float(v) for k, v in re.findall(r"(\S+) ([\d.]+)", passes)}
        batch["total"] = float(total)
        batches.append(batch)
    # Production gpu_vsync_check reports any failed eglSwapInterval(0). The optional
    # runtime backend banner is absent unless SLOPPY_FRAME_STATS was enabled.
    assert "BOTW_NOVSYNC:" not in text, "X11 uncapped swap interval failed"
    steady = batches[2:]
    assert len(steady) >= 3, "incomplete steady GPU samples"
    dimensions = re.findall(r"; (\d+x\d+) scale ([\d.]+)", text)
    assert dimensions and len(set(dimensions[2:])) == 1
    assert dimensions[-1][1] == "0.80"
    frames = [int(f) for f in re.findall(r"^frame sample: (\d+) ", text, re.M)]
    assert len([f for f in frames if f >= 241]) == 720, "incomplete steady frame samples"
    return {"dimensions": dimensions[-1], "batches": steady,
            "median": {k: statistics.median(b[k] for b in steady) for k in steady[0]}}


def report_gpu(root):
    summary = {}
    for phase in ["before", "after"]:
        summary[phase] = {f"{scene}-{n}": gpu_summary(root / phase, f"gpu-{scene}-{n}")
                          for scene in ["overlook-clear", "title-850"] for n in range(1, 4)}
    dimensions = {tuple(run["dimensions"]) for phase in summary.values() for run in phase.values()}
    assert len(dimensions) == 1, "baseline/current GPU dimensions must match"
    (root / "gpu-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    for scene in ["overlook-clear", "title-850"]:
        medians = {}
        for phase in ["before", "after"]:
            runs = [summary[phase][f"{scene}-{n}"]["median"] for n in range(1, 4)]
            medians[phase] = {key: statistics.median(r[key] for r in runs)
                              for key in ["total", "farland", "far-trees"]}
            print(f"{scene} {phase}: total {medians[phase]['total']:.3f} ms; "
                  f"farland {medians[phase]['farland']:.3f} ms; "
                  f"far trees {medians[phase]['far-trees']:.3f} ms")
        # Fixed mesh and pass counts should preserve GPU cost within measurement noise.
        assert medians["after"]["farland"] <= medians["before"]["farland"] + 0.10
        assert medians["after"]["total"] <= medians["before"]["total"] * 1.03 + 0.10
    print(f"PASS matched GPU cost: {next(iter(dimensions))}, three interleaved runs/view")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase", choices=["before", "after", "paired"])
    p.add_argument("--binary", type=Path, required=True)
    p.add_argument("--baseline", type=Path)
    p.add_argument("--output", type=Path, default=Path("build/landmark-retune"))
    p.add_argument("--locked-pair", type=int)
    p.add_argument("--verify-gpu", action="store_true")
    a = p.parse_args()
    if a.verify_gpu:
        report_gpu(a.output)
        return
    if a.phase != "paired":
        for name, flags in SCENES.items():
            capture(a.binary, a.output / a.phase, name, flags, 850 if name == "title-850" else 300)
        return
    assert a.baseline
    if not a.locked_pair:
        for repeat in range(1, 4):
            subprocess.run(["flock", "/tmp/botw-render.lock", "python3", __file__, "paired",
                            "--binary", str(a.binary), "--baseline", str(a.baseline),
                            "--output", str(a.output), "--locked-pair", str(repeat)], check=True)
        report_gpu(a.output)
        return
    # The parent holds one lock for the pair. Children must not reacquire it.
    for scene in ["overlook-clear", "title-850"]:
        for phase, binary in [("before", a.baseline), ("after", a.binary)]:
            flags = {**SCENES[scene], "BOTW_GPU": "1", "BOTW_FRAME_LOG": "1"}
            capture(binary, a.output / phase, f"gpu-{scene}-{a.locked_pair}", flags,
                    960, window="2133x1200", locked=True)


if __name__ == "__main__":
    main()
