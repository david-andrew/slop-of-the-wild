#!/usr/bin/env python3
"""Matched round 71 sky/storm/snow captures and CPU tails; self-locking."""
import sys
sys.dont_write_bytecode = True
import task70_weather_capture as capture

capture.SCENES = {
    'golden': dict(BOTW_AT='-1030,1805,1.57', BOTW_HOUR='18.6'),
    'storm': dict(BOTW_AT='-1000,1620,3.14', BOTW_WEATHER='storm'),
    'storm-morning': dict(BOTW_AT='-1000,1620,3.14', BOTW_HOUR='7', BOTW_WEATHER='storm'),
    'snow': dict(BOTW_AT='-1060,2230,2.0'),
    'firs': dict(BOTW_CAM='-880,206,2273,2.60,-0.16'),
    'forest-clear': dict(BOTW_AT='-1000,1620,3.14'),
}
if __name__ == '__main__':
    capture.main()
