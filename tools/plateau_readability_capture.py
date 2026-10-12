#!/usr/bin/env python3
"""Repeatable entry/map evidence; each render owns the shared GPU lock once."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument("phase", choices=["before", "after"])
p.add_argument("--binary", required=True)
p.add_argument("--gpu", action="store_true")
p.add_argument("--gpu-only", action="store_true")
p.add_argument("--extra", action="store_true")
p.add_argument("--repeat", type=int, default=1)
p.add_argument("--reuse-gpu", action="store_true")
p.add_argument("--baseline")
p.add_argument("--locked-pair", type=int)
p.add_argument("--shrine", type=int, action="append")
a = p.parse_args()
root = Path("build/round55") / a.phase
root.mkdir(parents=True, exist_ok=True)
clean = {k: v for k, v in os.environ.items() if not k.startswith(("BOTW_", "SLOPPY_"))}
if a.baseline:
    ids = [a.locked_pair] if a.locked_pair else [1, 2, 3, 4]
    for n in ids:
        if not a.locked_pair:
            subprocess.run(["flock", "/tmp/botw-render.lock", sys.executable, __file__,
                            "after", "--binary", a.binary, "--baseline", a.baseline,
                            "--locked-pair", str(n)], check=True)
            continue
        # The parent owns the GPU lock once across this pair; neither child nests it.
        for phase, binary in [("before", a.baseline), ("after", a.binary)]:
            out = Path("build/round55") / phase
            name = f"gpu-shrine{n}-paired"
            env = {**clean, "BOTW_SKIP": "1", "BOTW_TOWER": "1", "BOTW_SHRINE": str(n),
                   "BOTW_GPU": "1", "BOTW_NOVSYNC": "1", "BOTW_FRAME_LOG": "1",
                   "SLOPPY_PLATFORM": "x11", "SLOPPY_WINDOW": "1280x720",
                   "SLOPPY_FRAMES": "960", "SLOPPY_SCREENSHOT": str(out / f"{name}.png")}
            with (out / f"{name}.log").open("w") as log:
                subprocess.run(["timeout", "300", binary], env=env,
                               stdout=log, stderr=subprocess.STDOUT, check=True)
            print(f"paired measurement {phase} shrine {n}", flush=True)
    sys.exit(0)
scenes = [(f"shrine{n}", {"BOTW_SHRINE": str(n)}) for n in (a.shrine or range(1, 5))]
if not a.shrine: scenes += [("map", {"SLOPPY_INPUT": "10:m+,12:m-"})]
if a.gpu_only: scenes = []
for name, settings in scenes:
    env = {**clean, "BOTW_SKIP": "1", "BOTW_TOWER": "1",
           "SLOPPY_PLATFORM": "x11", "SLOPPY_WINDOW": "1280x720",
           "SLOPPY_FRAMES": "300", "SLOPPY_SCREENSHOT": str(root / f"{name}.png"),
           **settings}
    with (root / f"{name}.log").open("w") as log:
        subprocess.run(["flock", "/tmp/botw-render.lock", "timeout", "300", a.binary],
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    print(f"captured {root / f'{name}.png'}", flush=True)
if a.gpu or a.gpu_only:
    for n in range(1, 5):
        for repeat in range(1, a.repeat + 1):
            name = f"gpu-shrine{n}-{repeat}"
            if a.reuse_gpu and (root / f"{name}.png").exists(): continue
            env = {**clean, "BOTW_SKIP": "1", "BOTW_TOWER": "1", "BOTW_SHRINE": str(n),
                   "BOTW_GPU": "1", "BOTW_NOVSYNC": "1", "BOTW_FRAME_LOG": "1",
                   "SLOPPY_PLATFORM": "x11", "SLOPPY_WINDOW": "1280x720",
                   "SLOPPY_FRAMES": "960", "SLOPPY_SCREENSHOT": str(root / f"{name}.png")}
            with (root / f"{name}.log").open("w") as log:
                subprocess.run(["flock", "/tmp/botw-render.lock", "timeout", "300", a.binary],
                               env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            print(f"measured {name}", flush=True)

if a.extra:
    extra = [("tower-ping", a.binary, {"BOTW_RISE": "1"}, "700"),
             ("map-pins", "build/round55/map-view", {}, "3"),
             ("map-zoom", "build/round55/map-view", {"MAP_VIEW_ZOOM": "2.744"}, "3")]
    for name, binary, settings, frames in extra:
        env = {**clean, "BOTW_SKIP": "1", "BOTW_TOWER": "1",
               "SLOPPY_PLATFORM": "x11", "SLOPPY_WINDOW": "1280x720",
               "SLOPPY_FRAMES": frames, "SLOPPY_SCREENSHOT": str(root / f"{name}.png"),
               **settings}
        if name == "tower-ping": env.pop("BOTW_TOWER")
        with (root / f"{name}.log").open("w") as log:
            subprocess.run(["flock", "/tmp/botw-render.lock", "timeout", "300", binary],
                           env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        print(f"captured {root / f'{name}.png'}", flush=True)
