#!/usr/bin/env python3
"""CPU-only contention around one benchmark; caller already owns its render lock."""
import subprocess
import sys
import os
import signal


def main():
    count = int(sys.argv[1])
    assert 1 <= count <= 16
    workers = []
    client = None
    def interrupted(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        # Integer arithmetic keeps Python workers busy without windows, GPU
        # contexts, disk writes or an ever-growing allocation footprint.
        program = 'x=1\nwhile True:\n for _ in range(10000): x=(x*1664525+1013904223)&0xffffffff\n'
        for _ in range(count):
            workers.append(subprocess.Popen([sys.executable, '-c', program], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        print(f'controlled CPU contention: {count} workers; one locked game renderer', flush=True)
        client = subprocess.Popen(sys.argv[2:], start_new_session=True)
        return client.wait()
    finally:
        if client is not None and client.poll() is None:
            try: os.killpg(client.pid, signal.SIGTERM)
            except ProcessLookupError: pass
            try: client.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try: os.killpg(client.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                client.wait()
        for worker in workers: worker.terminate()
        for worker in workers: worker.wait()


if __name__ == '__main__':
    sys.exit(main())
