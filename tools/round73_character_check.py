#!/usr/bin/env python3
"""Foreground character acceptance views against e955219.

prepare before|after; capture before|after [views...].
Each game process owns one render flock through the shared capture helper.
Do not wrap this script in flock. Evidence stays under build/round73/.
"""
import sys

sys.dont_write_bytecode = True
import round69_character_check as base

base.OUT = base.ROOT / 'build/round73'
base.BASELINE = 'e955219'
combat = base.VIEWS['combat'][0]
base.VIEWS = {f'wake{n}': ({}, n) for n in (330, 420, 520)}
base.VIEWS.update({f'combat{n}': (combat, n) for n in (155, 300, 420)})
base.VIEWS.update({
    'camp': ({'BOTW_SKIP': '1', 'BOTW_CAM': '-947,243,1956,-0.85,-0.45'}, 120),
    'oldman': ({'BOTW_SKIP': '1', 'BOTW_AT': '-951,1876,2.5',
                'SLOPPY_INPUT': '5:w+,40:w-'}, 100),
})

if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[2] not in ('before', 'after'):
        raise SystemExit(__doc__)
    command, phase = sys.argv[1:3]
    if command == 'prepare':
        base.prepare(phase)
    elif command == 'capture':
        base.capture(phase, sys.argv[3:])
    else:
        raise SystemExit(__doc__)
