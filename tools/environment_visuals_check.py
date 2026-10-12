#!/usr/bin/env python3
"""Headless production grading check: both camera paths refresh environment values."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent.parent
source = (root / 'game/main.jo').read_text()
step = source.split('simulation_step = (dt: f64):', 1)[1]
assert step.index('env_update(dt, false)') < step.index('environment_visuals_update()') < step.index('if free_cam:'), \
    'environment grading must refresh before the free-camera return'
helper = source.split('environment_visuals_update = ():', 1)[1].split('\nsimulation_step =', 1)[0]
out = root / 'build/environment-visuals-check'
out.mkdir(parents=True, exist_ok=True)
fixture = f"""use '{root / 'game/env.jo'}'
use '{root / 'game/post.jo'}'
use '{root / 'game/fx.jo'}'
environment_visuals_update = ():{helper}
checks = 0
loop hour in [6.4, 11.0, 23.0]:
    loop weather in [Weather.clear, Weather.cloudy, Weather.rain, Weather.storm]:
        env = Env(hour = hour, weather = weather, weather_t = 1e9,
            clouds = if weather == .storm: 0.95 else if weather == .rain: 0.85 else if weather == .cloudy: 0.74 else: 0.22,
            rain = if weather == .storm: 1.0 else if weather == .rain: 0.75 else: 0.0,
            storm_k = if weather == .storm: 1.0 else: 0.0)
        env_update(0.0, false)
        environment_visuals_update()
        grade = vec3(f32(post.sat), f32(post_moon), f32(post_golden))
        light = fx_light
        # A camera switch must replace stale daytime/indoor values, not inherit them.
        loop camera_mode in [false, true]:
            post.sat = 9.0
            post_moon = 9.0
            post_golden = 9.0
            fx_light = vec3(9, 9, 9)
            environment_visuals_update()
            assert(length(vec3(f32(post.sat), f32(post_moon), f32(post_golden)) - grade) < 0.000001)
            assert(length(fx_light - light) < 0.000001)
            checks += 1
        if hour == 23.0: assert(post_moon > 0.99 and post_golden == 0.0)
        if weather == .storm: assert(post.sat < 1.07 and post_golden == 0.0)
print("PASS environment visuals: {{checks}} refreshes across dawn/day/night and four weathers; production call precedes both camera paths")
"""
(out / 'fixture.jo').write_text(fixture)
subprocess.run([str(root / 'sloppy/bin/sloppy'), str(out / 'fixture.jo')], cwd=root, check=True)
