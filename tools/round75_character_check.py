#!/usr/bin/env python3
"""Matched gameplay-distance character/bird evidence against 3a99aaa.

prepare before|after; capture before|after [views...]. Each game render owns
one flock via round69_character_check; do not wrap this script in flock.
"""
import sys
sys.dont_write_bytecode=True
import round69_character_check as base
base.OUT=base.ROOT/'build/round75'
base.BASELINE='3a99aaa'
combat=base.VIEWS['combat'][0]
base.VIEWS={
 'camp':base.VIEWS['camp'],
 'camp300':(base.VIEWS['camp'][0],300),
 'blue-camp':({'BOTW_SKIP':'1','BOTW_AT':'-982,1654,0','BOTW_CAM':'-987,190.4,1646,1.05,-0.16'},120),
 'crow-spot':({'BOTW_CAM':'-946,188.0,1660,-0.75,-0.12'},150),
 'boars':({'BOTW_SKIP':'1','BOTW_CAM':'-946,188.0,1660,-0.75,-0.12'},150),
 'birds720':({'BOTW_SKIP':'1','BOTW_CAM':'-946,188.0,1660,-0.75,-0.12'},720),
 'title':({'BOTW_TITLE':'1','SLOPPY_INPUT':'10:w+'},600),
 **{f'combat{n}':(combat,n) for n in (155,300)}}
if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[2] not in ('before', 'after'):
        raise SystemExit(__doc__)
    if sys.argv[1] == 'prepare': base.prepare(sys.argv[2])
    elif sys.argv[1] == 'capture': base.capture(sys.argv[2],sys.argv[3:])
    else: raise SystemExit(__doc__)
