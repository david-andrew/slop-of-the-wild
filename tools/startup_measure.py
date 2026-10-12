#!/usr/bin/env python3
"""Time one launch under the caller's render lock, with observable frame milestones.

The first-frame line is the end of game update/draw, before runtime submit.
The capture line follows GPU readback and PNG write (frame index 1). Neither is
compositor delivery or scanout. Streaming receipt adds small pipe/scheduling lag.
"""
import subprocess
import sys
import time

start = time.monotonic()
proc = subprocess.Popen(['/usr/bin/time', '-f', 'startup_elapsed_s=%e',
                         'timeout', '180', *sys.argv[1:]],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
for line in proc.stdout:
    elapsed = time.monotonic() - start
    print(line, end='', flush=True)
    if line.startswith('first frame:'):
        print(f'startup_first_callback_end_s={elapsed:.6f}', flush=True)
    elif line.startswith('frame cpu:'):
        print(f'startup_first_capture_s={elapsed:.6f}', flush=True)
sys.exit(proc.wait())
