#!/bin/bash
# One fresh, headless-rendered wake -> slate -> both doors -> passage -> title -> control.
# No BOTW_SKIP/PASSAGE/TITLE/position, inventory, story, or progress presets.
set -euo pipefail
cd "$(dirname "$0")/.."
# Compilation and CPU assertions do not occupy the shared render lock.
# This script locks only its one continuous game render; never wrap it in flock.
sloppy/bin/sloppy tools/opening_test.jo
mkdir -p build/opening-check
sloppy/bin/sloppy build game/main.jo -o build/opening-check/game
flock /tmp/botw-render.lock python3 - <<'PY'
import ctypes as ct
import ctypes.util
import os
import signal
import time
from pathlib import Path
import re
import subprocess
import sys

root = Path('build/opening-check')
# Failed reruns must not inherit checkpoint images from a prior success.
for image in root.glob('*.png'):
    image.unlink()
clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
# Camera keys use input.jo's fixed-step 0.04 rad/frame. Wait for each door's
# normal opening, walk round the slate pedestal, examine the second terminal,
# turn at the corridor bend and again after the mouth; never relocate the player.
script = ('600:w+,640:w-,655:e+,656:e-,'
          '800:a+,814:a-,830:right+,834:right-,'
          '850:w+,1013:w-,1030:e+,1031:e-,'
          '1180:d+,1194:d-,1210:left+,1214:left-,'
          '1230:w+,1360:w-,1360:right+,1385:right-,'
          '1390:w+,2210:w-,2220:left+,2226:left-,'
          '2240:w+,2850:w-')
# Honor inverted camera settings without changing the user's options file.
options = Path(os.environ.get('HOME', '.')) / '.botw-clone-options'
if options.is_file():
    for line in options.read_text().splitlines():
        if line.startswith('invert_x=') and float(line.split('=', 1)[1]) > 0.5:
            script = script.replace(':left', ':swap').replace(':right', ':left').replace(':swap', ':right')
# The scripted approach can enter the title around frame 2800; its 20.1 s
# crest/title beat then returns control after frame 4000. Retain a margin.
settings = {**clean, 'SLOPPY_PLATFORM': 'x11', 'SLOPPY_WINDOW': '960x540',
            'SLOPPY_INPUT': script, 'SLOPPY_FRAMES': '4300',
            'SLOPPY_SCREENSHOT': str(root / 'final.png'),
            'BOTW_OPENING_CAPTURE': str(root), 'BOTW_CAMDBG': '1'}
# Keep the game's own GPU context and unmap only its newly created test window.
# A separate Xvfb display is the fallback when no local X server is available.
x = None
display = None
try:
    x = ct.CDLL(ctypes.util.find_library('X11'))
    x.XOpenDisplay.argtypes = [ct.c_char_p]
    x.XOpenDisplay.restype = ct.c_void_p
    display = x.XOpenDisplay(None)
except (OSError, TypeError):
    pass
if display:
    # Other clients can close a window between querying its ID and its name.
    error_callback = ct.CFUNCTYPE(ct.c_int, ct.c_void_p, ct.c_void_p)
    ignore_stale_window = error_callback(lambda *_: 0)
    x.XSetErrorHandler.argtypes = [error_callback]
    x.XSetErrorHandler(ignore_stale_window)
    x.XDefaultRootWindow.argtypes = [ct.c_void_p]
    x.XDefaultRootWindow.restype = ct.c_ulong
    x.XQueryTree.argtypes = [ct.c_void_p, ct.c_ulong, ct.POINTER(ct.c_ulong),
                            ct.POINTER(ct.c_ulong), ct.POINTER(ct.POINTER(ct.c_ulong)),
                            ct.POINTER(ct.c_uint)]
    x.XFetchName.argtypes = [ct.c_void_p, ct.c_ulong, ct.POINTER(ct.c_void_p)]
    x.XUnmapWindow.argtypes = [ct.c_void_p, ct.c_ulong]
    x.XSync.argtypes = [ct.c_void_p, ct.c_int]
    x.XCloseDisplay.argtypes = [ct.c_void_p]
    x.XFree.argtypes = [ct.c_void_p]

    def windows():
        pending = [x.XDefaultRootWindow(display)]
        found = {}
        while pending and len(found) < 10000:
            wid = pending.pop()
            if wid in found:
                continue
            name = ct.c_void_p()
            title = ''
            if x.XFetchName(display, wid, ct.byref(name)) and name.value:
                title = ct.string_at(name).decode(errors='replace')
                x.XFree(name)
            found[wid] = title
            root_w, parent, count = ct.c_ulong(), ct.c_ulong(), ct.c_uint()
            children = ct.POINTER(ct.c_ulong)()
            if x.XQueryTree(display, wid, ct.byref(root_w), ct.byref(parent),
                            ct.byref(children), ct.byref(count)):
                pending.extend(children[i] for i in range(count.value))
                if children:
                    x.XFree(children)
        return found

    existing = set(windows())
    command = ['build/opening-check/game']
else:
    settings['SLOPPY_WINDOW'] = '480x270'
    command = ['xvfb-run', '-a', 'build/opening-check/game']

status = 1
errors = []
# Stream the camera trail to disk so progress can be inspected during a long run.
with (root / 'run.log').open('w') as log:
    proc = subprocess.Popen(command, env=settings, stdout=log,
                            stderr=subprocess.STDOUT, start_new_session=True)
    try:
        if display:
            deadline = time.monotonic() + 20
            hidden = False
            while proc.poll() is None and time.monotonic() < deadline:
                for wid, title in windows().items():
                    if wid not in existing and title == 'The Legend of Jo: Slop of the Wild':
                        x.XUnmapWindow(display, wid)
                        x.XSync(display, 0)
                        hidden = True
                        break
                if hidden:
                    break
                time.sleep(0.02)
            if not hidden:
                errors.append('could not hide the newly created test window')
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
        status = proc.wait(timeout=600)
    except subprocess.TimeoutExpired:
        errors.append('opening exceeded 600 seconds')
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=10)
    finally:
        if display:
            x.XCloseDisplay(display)
output = (root / 'run.log').read_text()
expected = ['wake-support', 'wake-rise', 'awake', 'slate-taken', 'door1-opening', 'door1-open',
            'door2-opening', 'door2-open', 'passage-reached', 'mouth-reached', 'title-crane', 'title-shown', 'control-returned']
events = re.findall(r'^opening: (\S+) frame (\d+) position (.+) captured (true|false)$', output, re.M)
if [e[0] for e in events] != expected:
    errors.append('missing, duplicated, or unordered checkpoints: ' + ', '.join(e[0] for e in events))
for name, frame, position, captured in events:
    if captured != 'true' or not (root / f'{name}.png').is_file():
        errors.append(f'failed image capture: {name}')
    print(f'{"PASS" if captured == "true" else "FAIL"}: {name} at frame {frame}; {position}')
if status or not (root / 'final.png').is_file():
    errors.append(f'render exit {status}')
print(('FAIL: ' + '; '.join(errors)) if errors else 'PASS: continuous opening; no gameplay presets')
print(f'Images and full camera trail: {root}/')
sys.exit(1 if errors else 0)
PY

# Frame-by-frame production crane continuity at five approach speeds/orientations.
sloppy/bin/sloppy tools/title_handoff_check.jo
