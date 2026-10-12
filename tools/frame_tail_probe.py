#!/usr/bin/env python3
"""Separate game/GPU work from waits in EGL presentation using one hidden X11 window.

Both variants render identical frames into the game's real EGL window surface. The hidden
variant unmaps only its newly-created window, without altering the shared render lock.
Run: tools/frame_tail_probe.py build/round54-before build/round54/present-probe
"""
import argparse
import ctypes as ct
import ctypes.util
import os
from pathlib import Path
import subprocess
import time


def windows(x, display):
    root = x.XDefaultRootWindow(display)
    pending = [root]
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
        if x.XQueryTree(display, wid, ct.byref(root_w), ct.byref(parent), ct.byref(children), ct.byref(count)):
            pending.extend(children[i] for i in range(count.value))
            if children:
                x.XFree(children)
    return found


def capture(executable, output, hidden):
    x = ct.CDLL(ctypes.util.find_library('X11'))
    x.XOpenDisplay.argtypes = [ct.c_char_p]
    x.XOpenDisplay.restype = ct.c_void_p
    display = x.XOpenDisplay(None)
    if not display:
        raise RuntimeError('X11 is required')
    for name, args, result in [
        ('XDefaultRootWindow', [ct.c_void_p], ct.c_ulong),
        ('XFetchName', [ct.c_void_p, ct.c_ulong, ct.POINTER(ct.c_void_p)], ct.c_int),
        ('XQueryTree', [ct.c_void_p, ct.c_ulong, ct.POINTER(ct.c_ulong), ct.POINTER(ct.c_ulong), ct.POINTER(ct.POINTER(ct.c_ulong)), ct.POINTER(ct.c_uint)], ct.c_int),
        ('XUnmapWindow', [ct.c_void_p, ct.c_ulong], ct.c_int),
        ('XSync', [ct.c_void_p, ct.c_int], ct.c_int),
        ('XCloseDisplay', [ct.c_void_p], ct.c_int),
        ('XFree', [ct.c_void_p], ct.c_int),
    ]:
        f = getattr(x, name)
        f.argtypes, f.restype = args, result
    error_callback = ct.CFUNCTYPE(ct.c_int, ct.c_void_p, ct.c_void_p)
    ignore_stale_window = error_callback(lambda *_: 0)
    x.XSetErrorHandler.argtypes = [error_callback]
    x.XSetErrorHandler(ignore_stale_window)
    existing = set(windows(x, display))
    mode = 'unmapped' if hidden else 'mapped'
    prefix = output / mode
    clean = {k: v for k, v in os.environ.items() if not k.startswith(('BOTW_', 'SLOPPY_'))}
    clean.update(BOTW_SKIP='1', BOTW_TOWER='1', BOTW_AT='-560,1722,0',
                 SLOPPY_INPUT='5:w+', BOTW_SCALE='0.8', BOTW_FRAME_LOG='1',
                 BOTW_GPU='1', BOTW_NOVSYNC='1', SLOPPY_PLATFORM='x11',
                 SLOPPY_WINDOW='1280x720', SLOPPY_FRAMES='720',
                 SLOPPY_SCREENSHOT=str(prefix.with_suffix('.png')))
    with prefix.with_suffix('.log').open('w') as log:
        proc = subprocess.Popen([str(executable.resolve())], env=clean, stdout=log, stderr=subprocess.STDOUT)
        try:
            if hidden:
                deadline = time.monotonic() + 30
                found = False
                while proc.poll() is None and time.monotonic() < deadline:
                    for wid, title in windows(x, display).items():
                        if wid not in existing and title == 'The Legend of Jo: Slop of the Wild':
                            x.XUnmapWindow(display, wid)
                            x.XSync(display, 0)
                            found = True
                            break
                    if found:
                        break
                    time.sleep(.02)
                if not found:
                    raise RuntimeError('failed to identify this process\'s new game window')
            if proc.wait(timeout=300):
                raise RuntimeError('render failed')
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=10)
            x.XCloseDisplay(display)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--locked', action='store_true')
    args = parser.parse_args()
    if not args.locked:
        # The diagnostic owns its lock; each actual game process inherits it.
        subprocess.run(['flock', '/tmp/botw-render.lock', 'python3', __file__,
                        str(args.executable), str(args.output), '--locked'], check=True)
        return
    args.output.mkdir(parents=True, exist_ok=True)
    for hidden in [False, True]:
        capture(args.executable, args.output, hidden)


if __name__ == '__main__':
    main()
