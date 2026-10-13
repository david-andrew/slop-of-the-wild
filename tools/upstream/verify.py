#!/usr/bin/env python3
"""Verify expected upstream failures and OpenGL controls; owns all render locks."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/upstream"
OUT.mkdir(parents=True, exist_ok=True)
BASE = {k: v for k, v in os.environ.items() if not k.startswith("SLOPPY_")}
BASE.update(SLOPPY_NO_AUDIO="1", SLOPPY_PLATFORM="x11", SLOPPY_VSYNC="0")
# One flock covers the whole short batch, so other queued captures cannot split
# the backend controls. Children below never acquire a nested lock.
if "--lock-held" not in sys.argv:
    raise SystemExit(subprocess.run([
        "flock", "/tmp/botw-render.lock", sys.executable, str(Path(__file__).resolve()),
        "--lock-held",
    ], cwd=ROOT).returncode)
results = []


def probe(name, code, evidence, *, backend=None, extra=None, label=None):
    env = {**BASE, **(extra or {})}
    if backend is not None:
        env["SLOPPY_VULKAN"] = backend
    cmd = ["sloppy/bin/sloppy", f"tools/upstream/{name}.jo"]
    cmd = ["timeout", "45", *cmd]  # The outer flock already owns the lock.
    run = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True)
    output = run.stdout + run.stderr
    label = label or f"{name}-{backend or 'cpu'}"
    (OUT / f"{label}.log").write_text(output)
    ok = run.returncode == code and all(text in output for text in evidence)
    results.append({"probe": label, "exit": run.returncode, "verified": ok, "output": output})
    print(f"{'VERIFIED' if ok else 'FAILED'} {label}", flush=True)
    if not ok:
        print(output, flush=True)


for name, evidence in [
    ("readback", ["crop guard byte: 64", "last alpha: -1.0"]),
    ("hash_seam_repro", ["continuous noise must agree"]),
    ("mipmap", ["LOD 2 red: 255"]),
    ("r32f_upload", ["R32F texel red: 0"]),
    ("snapshots", ["snapshot red: 0"]),
]:
    probe(name, 101, evidence, backend="1")
    probe(name, 0, [], backend="0")

for name, symbol in [
    ("signed_derivatives", "dFdx"),
    ("shadow_bias", "glPolygonOffset"),
    ("gpu_timestamps", "vkCmdWriteTimestamp"),
]:
    probe(name, 1, [f"unknown function '{symbol}'"])

probe("gain_ramp", 101, ["gain-change boundary: 0.5 -> 0.0"])
with tempfile.TemporaryDirectory(prefix="cache-probe-", dir=OUT) as directory:
    missing = Path(directory) / "cache"
    probe("pipeline_cache_path", 101, ["pipeline cache path: ''"],
          extra={"XDG_CACHE_HOME": str(missing)}, label="cache-parent-absent")
    missing.mkdir()
    probe("pipeline_cache_path", 0, [".vkpipelines"],
          extra={"XDG_CACHE_HOME": str(missing)}, label="cache-parent-created")

probe("anisotropy", 101, ["supported: 1; requested by runtime: 0"], backend="1")
cache = OUT / "prewarm-cache"
cache.mkdir(exist_ok=True)
for attempt in [1, 2]:
    probe("pipeline_prewarm", 0, ["pipelines after make_shader: 0", "pipelines 1", "pipelines 2"],
          backend="1", extra={"XDG_CACHE_HOME": str(cache), "SLOPPY_PLATFORM": "wayland"},
          label=f"prewarm-launch-{attempt}")
for backend, vsync in [("1", "0"), ("1", "1"), ("0", "0")]:
    probe("presentation", 0, ["interval p50/p99/worst ms:", "present worst ms:"],
          backend=backend, extra={"SLOPPY_PLATFORM": "wayland", "SLOPPY_VSYNC": vsync},
          label=f"presentation-{backend}-{vsync}")

(OUT / "verification.json").write_text(json.dumps(results, indent=2) + "\n")
passed = sum(row["verified"] for row in results)
print(f"{passed}/{len(results)} probes verified; logs: {OUT}")
raise SystemExit(0 if passed == len(results) else 1)
