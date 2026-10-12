#!/usr/bin/env python3
"""Exercise short-lived child discovery without a game context or rendering."""
import os
import argparse
from pathlib import Path
import sys
import tempfile
import time

from PIL import Image
from performance_window import run, validate_capture

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'build/performance-window-check')
    out = parser.parse_args().output.resolve()
    assert out.is_relative_to(ROOT/'build'), 'scratch evidence must stay under build/'
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out) as directory:
        capture = Path(directory) / 'capture.png'
        original = os.environ.get('SLOPPY_SCREENSHOT')
        os.environ['SLOPPY_SCREENSHOT'] = str(capture)
        try:
            command = [sys.executable, '-c', 'import os; from PIL import Image; Image.new("RGB", (1280,720)).save(os.environ["SLOPPY_SCREENSHOT"])']
            assert run(command, (1280,720)) == 0
            assert run([sys.executable, '-c', 'raise SystemExit(9)'], (1280,720)) == 9
            for label, action in (
                ('stale', lambda: validate_capture(capture,(1280,720),time.time_ns()+1)),
                ('wrong-size', lambda: validate_capture(capture,(640,360),0)),
                ('no-fresh-capture', lambda: run([sys.executable,'-c','pass'],(1280,720))),
            ):
                try: action()
                except RuntimeError: print(f'PASS benchmark rejects {label}')
                else: raise AssertionError(f'accepted {label}')
            capture.write_bytes(capture.read_bytes()[:24])
            try: validate_capture(capture,(1280,720),0)
            except (OSError, SyntaxError): print('PASS benchmark rejects incomplete PNG')
            else: raise AssertionError('accepted incomplete PNG')
        finally:
            if original is None: os.environ.pop('SLOPPY_SCREENSHOT',None)
            else: os.environ['SLOPPY_SCREENSHOT'] = original
    print('PASS benchmark completed-child capture, failure status and evidence validation')


if __name__ == '__main__':
    main()
