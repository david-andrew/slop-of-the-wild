#!/usr/bin/env python3
"""Run one X11 benchmark at exact client pixel size, under the caller's render lock.

Unmap only this child's window (like opening_check), then resize it before warmup.
--visible remaps a fixed-size managed dialog for presentation comparisons.
No desktop/display settings change. stdout/stderr and the child status pass through.
"""
import ctypes as ct
import ctypes.util
import os
import subprocess
import sys
from pathlib import Path
import time


def validate_capture(path, size, started_ns):
    """A completed short-lived client still needs fresh, exact-size evidence."""
    import struct
    capture = Path(path)
    if capture.stat().st_mtime_ns < started_ns:
        raise RuntimeError('capture predates this benchmark launch')
    with capture.open('rb') as f:
        header = f.read(24)
    if header[:8] != b'\x89PNG\r\n\x1a\n' or len(header) != 24 or struct.unpack('>II', header[16:24]) != size:
        raise RuntimeError('capture output size differs from requested X11 client')
    from PIL import Image
    with Image.open(capture) as image:
        image.verify()


def run(command, size, visible=False):
    x = ct.CDLL(ctypes.util.find_library('X11'))
    x.XOpenDisplay.argtypes = [ct.c_char_p]
    x.XOpenDisplay.restype = ct.c_void_p
    display = x.XOpenDisplay(None)
    if not display:
        raise RuntimeError('exact-size capture needs the local X11 display')
    callback_type = ct.CFUNCTYPE(ct.c_int, ct.c_void_p, ct.c_void_p)
    ignore_stale = callback_type(lambda *_: 0)
    x.XSetErrorHandler.argtypes = [callback_type]
    x.XSetErrorHandler(ignore_stale)
    x.XDefaultRootWindow.argtypes = [ct.c_void_p]
    x.XDefaultRootWindow.restype = ct.c_ulong
    x.XQueryTree.argtypes = [ct.c_void_p, ct.c_ulong, ct.POINTER(ct.c_ulong),
                            ct.POINTER(ct.c_ulong), ct.POINTER(ct.POINTER(ct.c_ulong)), ct.POINTER(ct.c_uint)]
    x.XFetchName.argtypes = [ct.c_void_p, ct.c_ulong, ct.POINTER(ct.c_void_p)]
    x.XGetWMProtocols.argtypes = [ct.c_void_p, ct.c_ulong, ct.POINTER(ct.POINTER(ct.c_ulong)), ct.POINTER(ct.c_int)]
    x.XInternAtom.argtypes = [ct.c_void_p, ct.c_char_p, ct.c_int]
    x.XInternAtom.restype = ct.c_ulong
    x.XChangeProperty.argtypes = [ct.c_void_p, ct.c_ulong, ct.c_ulong, ct.c_ulong,
                                 ct.c_int, ct.c_int, ct.c_void_p, ct.c_int]
    x.XUnmapWindow.argtypes = [ct.c_void_p, ct.c_ulong]
    x.XMapWindow.argtypes = [ct.c_void_p, ct.c_ulong]
    x.XDefaultScreen.argtypes = [ct.c_void_p]
    x.XDefaultScreen.restype = ct.c_int
    x.XWithdrawWindow.argtypes = [ct.c_void_p, ct.c_ulong, ct.c_int]
    class WindowAttributes(ct.Structure):
        _fields_ = [('background_pixmap',ct.c_ulong), ('background_pixel',ct.c_ulong),
                    ('border_pixmap',ct.c_ulong), ('border_pixel',ct.c_ulong),
                    ('bit_gravity',ct.c_int), ('win_gravity',ct.c_int), ('backing_store',ct.c_int),
                    ('backing_planes',ct.c_ulong), ('backing_pixel',ct.c_ulong), ('save_under',ct.c_int),
                    ('event_mask',ct.c_long), ('do_not_propagate_mask',ct.c_long),
                    ('override_redirect',ct.c_int), ('colormap',ct.c_ulong), ('cursor',ct.c_ulong)]
    x.XChangeWindowAttributes.argtypes = [ct.c_void_p,ct.c_ulong,ct.c_ulong,ct.POINTER(WindowAttributes)]
    class SizeHints(ct.Structure):
        _fields_ = [('flags', ct.c_long)] + [(name, ct.c_int) for name in
                    ['x', 'y', 'width', 'height', 'min_width', 'min_height', 'max_width', 'max_height',
                     'width_inc', 'height_inc', 'min_aspect_x', 'min_aspect_y', 'max_aspect_x', 'max_aspect_y',
                     'base_width', 'base_height', 'win_gravity']]
    class ConfigureEvent(ct.Structure):
        _fields_ = [('type', ct.c_int), ('serial', ct.c_ulong), ('send_event', ct.c_int),
                    ('display', ct.c_void_p), ('event', ct.c_ulong), ('window', ct.c_ulong),
                    ('x', ct.c_int), ('y', ct.c_int), ('width', ct.c_int), ('height', ct.c_int),
                    ('border_width', ct.c_int), ('above', ct.c_ulong), ('override_redirect', ct.c_int)]
    x.XSetWMNormalHints.argtypes = [ct.c_void_p, ct.c_ulong, ct.POINTER(SizeHints)]
    x.XSendEvent.argtypes = [ct.c_void_p, ct.c_ulong, ct.c_int, ct.c_long, ct.c_void_p]
    x.XGetGeometry.argtypes = [ct.c_void_p, ct.c_ulong, ct.POINTER(ct.c_ulong), ct.POINTER(ct.c_int),
                              ct.POINTER(ct.c_int), ct.POINTER(ct.c_uint), ct.POINTER(ct.c_uint),
                              ct.POINTER(ct.c_uint), ct.POINTER(ct.c_uint)]
    x.XResizeWindow.argtypes = [ct.c_void_p, ct.c_ulong, ct.c_uint, ct.c_uint]
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
            root, parent, count = ct.c_ulong(), ct.c_ulong(), ct.c_uint()
            children = ct.POINTER(ct.c_ulong)()
            if x.XQueryTree(display, wid, ct.byref(root), ct.byref(parent), ct.byref(children), ct.byref(count)):
                pending.extend(children[i] for i in range(count.value))
                if children:
                    x.XFree(children)
        return found

    delete_atom = x.XInternAtom(display, b'WM_DELETE_WINDOW', 0)
    def is_game_client(wid):
        # Narrow candidates using the runtime's WM_DELETE_WINDOW protocol.
        # Resource ownership below rejects compositor proxies that also copy it.
        protocols = ct.POINTER(ct.c_ulong)()
        count = ct.c_int()
        ok = x.XGetWMProtocols(display, wid, ct.byref(protocols), ct.byref(count))
        found = bool(ok and any(protocols[i] == delete_atom for i in range(count.value)))
        if protocols: x.XFree(protocols)
        return found

    # A compositor can copy BOTH title and WM protocols onto a proxy window.
    # XRes 1.2 identifies the resource owner, which must belong to this child tree.
    res_name = ctypes.util.find_library('XRes')
    if not res_name: raise RuntimeError('exact output requires libXRes ownership queries')
    res = ct.CDLL(res_name)
    class IdSpec(ct.Structure):
        _fields_ = [('client',ct.c_ulong), ('mask',ct.c_uint)]
    class IdValue(ct.Structure):
        _fields_ = [('spec',IdSpec), ('length',ct.c_long), ('value',ct.c_void_p)]
    res.XResQueryExtension.argtypes = [ct.c_void_p,ct.POINTER(ct.c_int),ct.POINTER(ct.c_int)]
    res.XResQueryVersion.argtypes = [ct.c_void_p,ct.POINTER(ct.c_int),ct.POINTER(ct.c_int)]
    major, minor = ct.c_int(), ct.c_int()
    event, error = ct.c_int(), ct.c_int()
    if not res.XResQueryExtension(display,ct.byref(event),ct.byref(error)) or not res.XResQueryVersion(display,ct.byref(major),ct.byref(minor)) or (major.value,minor.value)<(1,2):
        raise RuntimeError('exact output requires XRes 1.2 local client PIDs')
    res.XResQueryClientIds.argtypes = [ct.c_void_p,ct.c_long,ct.POINTER(IdSpec),ct.POINTER(ct.c_long),ct.POINTER(ct.POINTER(IdValue))]
    res.XResGetClientPid.argtypes = [ct.POINTER(IdValue)]
    res.XResGetClientPid.restype = ct.c_int
    res.XResClientIdsDestroy.argtypes = [ct.c_long,ct.POINTER(IdValue)]
    def owner_pid(wid):
        spec = IdSpec(client=wid,mask=2)
        count = ct.c_long(); values = ct.POINTER(IdValue)()
        if res.XResQueryClientIds(display,1,ct.byref(spec),ct.byref(count),ct.byref(values)) != 0:return -1
        try:
            for i in range(count.value):
                pid = res.XResGetClientPid(ct.byref(values[i]))
                if pid>0:return pid
            return -1
        finally:res.XResClientIdsDestroy(count,values)
    def child_pids(pid):
        found={pid};pending=[pid]
        while pending:
            current=pending.pop()
            try:children=(Path('/proc')/str(current)/'task'/str(current)/'children').read_text().split()
            except FileNotFoundError:continue
            for child in children:
                value=int(child)
                if value not in found:found.add(value);pending.append(value)
        return found

    existing = set(windows())
    child_env = os.environ.copy()
    child_env.setdefault('SLOPPY_FRAME_STATS', '1') # capture also identifies native/software presentation
    started_ns = time.time_ns()
    proc = subprocess.Popen(command, env=child_env)
    def completed_capture():
        status = proc.poll()
        if status is None:
            raise RuntimeError('child did not create its benchmark window')
        if status != 0:
            return status
        screenshot = child_env.get('SLOPPY_SCREENSHOT')
        if not screenshot:
            raise RuntimeError('short-lived child has no capture to verify')
        validate_capture(screenshot, size, started_ns)
        print(f'benchmark short-lived client: completed before geometry negotiation; fresh capture verified {size[0]}x{size[1]}; live geometry unobserved', flush=True)
        return status
    try:
        deadline = time.monotonic() + 30
        while proc.poll() is None and time.monotonic() < deadline:
            owned = child_pids(proc.pid)
            matches = [wid for wid, title in windows().items()
                       if wid not in existing and title == 'The Legend of Jo: Slop of the Wild' and is_game_client(wid) and owner_pid(wid) in owned]
            if matches:
                wid = matches[0]
                print(f'benchmark owned client: window {wid:#x} PID {owner_pid(wid)}',flush=True)
                if child_env.get('BOTW_BENCH_CPU_SET'):
                    cpus = {int(value) for value in child_env['BOTW_BENCH_CPU_SET'].split(',')}
                    pid = owner_pid(wid)
                    if not cpus or not cpus <= os.sched_getaffinity(pid):
                        raise RuntimeError('benchmark CPU set is outside the child allowed CPUs')
                    os.sched_setaffinity(pid, cpus)
                    print(f'benchmark main-thread affinity: PID {pid} CPUs {sorted(os.sched_getaffinity(pid))}', flush=True)
                hints = SizeHints(flags=(1 << 4) | (1 << 5), min_width=size[0], min_height=size[1],
                                  max_width=size[0], max_height=size[1])
                x.XSetWMNormalHints(display, wid, ct.byref(hints))
                # Let EGL establish its surface before asking the WM to unmanage
                # this test client. Tiling WMs can otherwise override every resize.
                time.sleep(.5)
                if proc.poll() is not None:
                    return completed_capture()
                x.XWithdrawWindow(display, wid, x.XDefaultScreen(display))
                x.XSync(display, 0)
                deadline = time.monotonic() + 5
                while True:
                    root, parent, count = ct.c_ulong(), ct.c_ulong(), ct.c_uint()
                    children = ct.POINTER(ct.c_ulong)()
                    ok = x.XQueryTree(display, wid, ct.byref(root), ct.byref(parent), ct.byref(children), ct.byref(count))
                    if children: x.XFree(children)
                    if ok and parent.value == root.value: break
                    if proc.poll() is not None: return completed_capture()
                    if time.monotonic() >= deadline: raise RuntimeError('WM did not withdraw benchmark client')
                    time.sleep(.01)
                if visible:
                    # GNOME can maximize a game client despite resize requests.
                    # A fixed dialog honors these size hints while retaining the
                    # ordinary managed/composited XWayland presentation path.
                    window_type = x.XInternAtom(display, b'_NET_WM_WINDOW_TYPE', 0)
                    dialog_type = ct.c_ulong(x.XInternAtom(display, b'_NET_WM_WINDOW_TYPE_DIALOG', 0))
                    x.XChangeProperty(display, wid, window_type, 4, 32, 0, ct.byref(dialog_type), 1)
                attrs = WindowAttributes(override_redirect=0 if visible else 1)
                x.XChangeWindowAttributes(display, wid, 1 << 9, ct.byref(attrs))
                x.XUnmapWindow(display, wid)
                x.XResizeWindow(display, wid, *size)
                if visible: x.XMapWindow(display, wid)
                x.XSync(display, 0)
                print(f'benchmark fixed output: {size[0]}x{size[1]} ({"visible managed" if visible else "hidden"} X11 client)', flush=True)
                break
            time.sleep(.01)
        else:
            return completed_capture()
        # WM negotiation can leave a late, obsolete ConfigureNotify in the game's
        # event queue. Publish only dimensions verified from the actual child client.
        # The WM withdrew it after EGL setup; this helper never reparents the surface.
        last_geometry = None
        while proc.poll() is None:
            root, gx, gy = ct.c_ulong(), ct.c_int(), ct.c_int()
            w, h, border, depth = ct.c_uint(), ct.c_uint(), ct.c_uint(), ct.c_uint()
            if x.XGetGeometry(display, wid, ct.byref(root), ct.byref(gx), ct.byref(gy),
                              ct.byref(w), ct.byref(h), ct.byref(border), ct.byref(depth)):
                observed = (w.value, h.value)
                if observed != last_geometry:
                    print(f'benchmark client geometry: {observed[0]}x{observed[1]} window {wid:#x}', flush=True)
                    last_geometry = observed
                if observed != size:
                    x.XResizeWindow(display, wid, *size)
                    x.XSync(display, 0)
                else:
                    event = ConfigureEvent(type=22, display=display, event=wid, window=wid,
                                           x=gx.value, y=gy.value, width=w.value, height=h.value)
                    storage = (ct.c_long * 24)()
                    ct.memmove(storage, ct.byref(event), ct.sizeof(event))
                    x.XSendEvent(display, wid, 0, 0, ct.byref(storage))
                    x.XSync(display, 0)
            time.sleep(.05)
        status = proc.wait()
        print(f'benchmark final client geometry: {last_geometry}', flush=True)
        screenshot = os.environ.get('SLOPPY_SCREENSHOT')
        if status == 0 and screenshot:
            validate_capture(screenshot, size, started_ns)
        return status
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        x.XCloseDisplay(display)


if __name__ == '__main__':
    arguments = sys.argv[1:]
    visible = arguments[0] == '--visible'
    if visible: arguments = arguments[1:]
    sys.exit(run(arguments[1:], tuple(map(int, arguments[0].split('x'))), visible))
