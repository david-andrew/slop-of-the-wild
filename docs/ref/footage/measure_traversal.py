#!/usr/bin/env python3
"""Reproduce traversal annotations; never treats screen displacement as world distance.

Requires Python, numpy, opencv-python-headless and ffprobe. Videos remain ignored.
  python measure_traversal.py --climb raw/u02-014.mp4 --nintendo PATH/run.mp4 --run raw/u02-004.mp4 --out traversal-reference.json
Manual points/windows below are inputs, not detections. World-scale results are conditional.
"""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

import cv2
import numpy as np

CLIMB_POINTS = [
    (30, (448, 233), (448, 279)),
    (60, (448, 235), (449, 280)),
    (90, (447, 256), (447, 302)),
    (120, (446, 254), (447, 299)),
    (150, (448, 249), (448, 296)),
]
EXPECTED_SHA256 = {
    'retail_climb': 'e5680dabadb74722c8229ac06a74643ab55c650bc488b59f97c614863b727852',
    'retail_run': 'da0aaf59ef58c7424ade4c478ca4e1385b53ed1337f16421ef8052b7efb094e8',
    'nintendo_run': 'e5052714dd8f006175ef008215505978ca4fb68571594724ad373e7ec58991a5',
}
SCALE_POINTS = {'frame': 0, 'head': [434, 192], 'hip': [426, 270], 'foot_y': 350}
LUNGE_POINTS = [(1386, (634, 312), (635, 416)), (1400, (632, 325), (630, 422))]


def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'frame=best_effort_timestamp_time:stream=width,height,r_frame_rate,nb_frames',
        '-of', 'json', str(path)]))


def frames(path, indices):
    cap = cv2.VideoCapture(str(path))
    result = {}
    for i in range(max(indices) + 1):
        ok, im = cap.read()
        if not ok:
            raise ValueError(f'Video ended at frame {i}')
        if i in indices:
            result[i] = im
    cap.release()
    return result


def descriptor(im, mode):
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    mask = np.zeros(im.shape[:2], np.uint8)
    if mode == 'climb':
        mask[90:430, 230:730] = 255
        mask[110:330, 350:480] = 0
    else:
        mask[50:700, 200:1050] = 255
        mask[200:550, 535:775] = 0
        mask[(hsv[:, :, 1] < 35) & (hsv[:, :, 2] > 170)] = 0
    mask[(hsv[:, :, 0] > 25) & (hsv[:, :, 0] < 95) & (hsv[:, :, 1] > 65)] = 0
    return cv2.SIFT_create(nfeatures=4000 if mode == 'climb' else 5000).detectAndCompute(
        cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), mask)


def homography(a, b):
    matches = cv2.BFMatcher().knnMatch(a[1], b[1], k=2)
    good = [x for x, y in matches if x.distance < .65 * y.distance]
    x = np.float32([a[0][m.queryIdx].pt for m in good])
    y = np.float32([b[0][m.trainIdx].pt for m in good])
    cv2.setRNGSeed(0)
    h, inliers = cv2.findHomography(x, y, cv2.RANSAC, 1.5)
    if h is None or int(inliers.sum()) < 40:
        raise ValueError('Insufficient scenery registration; inspect footage rather than fabricate motion')
    return h, {'matches': len(good), 'inliers': int(inliers.sum())}


def project(h, p):
    q = h @ np.array([*p, 1.])
    return q[:2] / q[2]


def source(path, url, page):
    p = probe(path)
    return {'url': url, 'page': page, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'stream': p['streams'][0], 'decoded_frames': len(p['frames']),
            'pts': [float(f['best_effort_timestamp_time']) for f in p['frames']]}


def interval(pts, windows):
    lo, hi = windows
    centers = [sum(w) // 2 for w in windows]
    return {'frame_windows': windows, 'center_frames': centers,
            'frames_counted': centers[1] - centers[0],
            'center_seconds': pts[centers[1]] - pts[centers[0]],
            'bounds_seconds': [pts[hi[0]] - pts[lo[1]], pts[hi[1]] - pts[lo[0]]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--climb', type=Path, required=True)
    parser.add_argument('--nintendo', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    sources = {
        'retail_climb': source(args.climb, 'https://mp4.mega64.net/botw/u02/014.mp4',
                               'https://www.lp.zone/t/1969/10'),
        'retail_run': source(args.run, 'https://mp4.mega64.net/botw/u02/004.mp4', 'https://www.lp.zone/t/1969/10'),
        'nintendo_run': source(args.nintendo, 'https://www.nintendo.com/jp/zelda/botw/assets/movie/run.mp4',
                               'https://www.nintendo.com/jp/zelda/botw/world.html'),
    }
    for key, item in sources.items():
        if item['sha256'] != EXPECTED_SHA256[key]:
            raise ValueError(f'{key}: source hash changed; re-annotate rather than reuse these frame windows')
    indices = list(range(0, 151, 5))
    images = frames(args.climb, indices)
    transforms = {0: np.eye(3)}
    quality = []
    last = descriptor(images[0], 'climb')
    for i in indices[1:]:
        now = descriptor(images[i], 'climb')
        h, q = homography(now, last)
        transforms[i] = transforms[i - 5] @ h
        quality.append({'frame': i, **q})
        last = now
    # Capsule height is a scale PROXY, not a measured mesh height. Keep these results provisional.
    head_hip = math.dist(SCALE_POINTS['head'], SCALE_POINTS['hip'])
    torso_m = 1.6 * head_hip / (SCALE_POINTS['foot_y'] - SCALE_POINTS['head'][1])
    rows = []
    pts = sources['retail_climb']['pts']
    for l, r in zip(CLIMB_POINTS, CLIMB_POINTS[1:]):
        h = np.linalg.inv(transforms[r[0]]) @ transforms[l[0]]
        head, hip = project(h, l[1]), project(h, l[2])
        torso_px = (np.linalg.norm(hip - head) + math.dist(r[1], r[2])) / 2
        rise_px = float(head[1] - r[1][1])
        dt = pts[r[0]] - pts[l[0]]
        rows.append({'frames': [l[0], r[0]], 'seconds': dt,
                     'registered_head_rise_px': rise_px, 'mean_projected_torso_px': float(torso_px),
                     'torso_lengths_per_second': rise_px / torso_px / dt})
    rate = sum(r['torso_lengths_per_second'] * r['seconds'] for r in rows) / sum(r['seconds'] for r in rows)
    limages = frames(args.nintendo, [1386, 1400])
    h, quality_l = homography(descriptor(limages[1386], 'lunge'), descriptor(limages[1400], 'lunge'))
    head, hip = project(h, LUNGE_POINTS[0][1]), project(h, LUNGE_POINTS[0][2])
    torso_px = (np.linalg.norm(hip - head) + math.dist(LUNGE_POINTS[1][1], LUNGE_POINTS[1][2])) / 2
    lunge_rise = float(head[1] - LUNGE_POINTS[1][1][1]) / torso_px
    observations = {
        'climb_speed': {'value': rate * torso_m, 'unit': 'm/s', 'uncertainty': .30, 'confidence': 'L',
                        'status': 'conditional_scale_inference', 'score_pool': 'inferred',
                        'frames': [30, 150], 'frames_counted': 120, 'seconds': pts[150] - pts[30],
                        'torso_lengths_per_second': rate, 'intervals': rows},
        'climb_lunge_rise': {'value': lunge_rise * torso_m, 'unit': 'm', 'uncertainty': .60, 'confidence': 'L',
                             'status': 'conditional_scale_inference', 'score_pool': 'inferred',
                             'frames': [1386, 1400], 'frames_counted': 14, 'torso_lengths': lunge_rise,
                             'registered_head_rise_px': float(head[1] - 325),
                             'mean_projected_torso_px': float(torso_px), 'registration': quality_l},
        'climb_lunge_duration': {**interval(sources['nintendo_run']['pts'], [[1384,1388],[1398,1402]]),
                                'confidence': 'L', 'score_pool': 'footage',
                                'definition': 'Visible rapid upward lunge initiation to hands reaching the upper edge; not button latency.'},
        'mantle_duration': {**interval(sources['nintendo_run']['pts'], [[1400,1404],[1424,1428]]),
                            'confidence': 'L', 'score_pool': 'footage',
                            'definition': 'Hands reaching upper edge to supported locomotion atop it; not an idle finish.'},
    }
    # Observe NET camera rotation, not auto-follow. Translation is small relative to the distant horizon.
    run_images = frames(args.run, [0, 5, 10])
    def far_descriptor(im):
        mask = np.zeros(im.shape[:2], np.uint8)
        mask[45:180, 100:820] = 255
        return cv2.SIFT_create(nfeatures=4000).detectAndCompute(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), mask)
    focal = 504 / (2 * math.tan(math.radians(25)))  # conditional 50-degree vertical FOV
    intrinsic = np.array([[focal,0,448],[0,focal,252],[0,0,1.]])
    rotation = np.eye(3)
    camera_quality = []
    for lo, hi in [(0,5),(5,10)]:
        a, b = far_descriptor(run_images[lo]), far_descriptor(run_images[hi])
        pairs = cv2.BFMatcher().knnMatch(a[1], b[1], k=2)
        good = [x for x,y in pairs if x.distance < .65*y.distance]
        x = np.float32([a[0][m.queryIdx].pt for m in good])
        y = np.float32([b[0][m.trainIdx].pt for m in good])
        cv2.setRNGSeed(0)
        h, ins = cv2.findHomography(x, y, cv2.RANSAC, 1.5)
        if h is None or ins.sum() < 30:
            raise ValueError('Camera registration lacks sufficient horizon inliers')
        r = np.linalg.inv(intrinsic) @ h @ intrinsic
        r /= np.cbrt(np.linalg.det(r))
        u, singular, vt = np.linalg.svd(r)
        rotation = (u @ vt) @ rotation
        camera_quality.append({'frames':[lo,hi], 'inliers':int(ins.sum()),
                               'singular_values_before_rotation_projection':singular.tolist()})
    observations['camera_net_yaw_during_run'] = {
        'value': math.degrees(math.atan2(rotation[0,2],rotation[2,2])), 'unit':'deg',
        'uncertainty':5.0, 'confidence':'L', 'status':'conditional_fov_camera_observation',
        'score_pool':'diagnostic', 'frames':[0,10], 'frames_counted':10,
        'seconds':sources['retail_run']['pts'][10]-sources['retail_run']['pts'][0],
        'method':'Distant-horizon SIFT/RANSAC homographies, K-inverse H K, nearest rotation via SVD; assumed vertical FOV 50 degrees.',
        'registration':camera_quality,
        'limitation':'NET rotation includes unknown right-stick input. This cannot supply an auto-yaw rate or lag time constant; do not compare it to a no-camera-input simulation.'}
    for s in sources.values():
        del s['pts']
    result = {'annotated': '2026-10-09', 'frame_numbering': 'zero-based decoded order; seconds from ffprobe presentation timestamps',
              'software': {'opencv': cv2.__version__, 'numpy': np.__version__}, 'sources': sources,
              'manual_annotations': {'climb_frame_head_hip_xy': CLIMB_POINTS, 'scale': SCALE_POINTS,
                                     'lunge_frame_head_hip_xy': LUNGE_POINTS, 'point_allowance_px': 5},
              'scale_proxy': {'capsule_height_m': 1.6, 'inferred_head_hip_m': torso_m,
                              'source': '../phys.yml CharacterController/Forms/Form_0 ShapeParam_0 translate_0.y',
                              'warning': 'Capsule height is NOT mesh stature. Running calibration pose, torso flexion, slope, parallax and rock nonplanarity make metre results conditional.'},
              'registration': {'method': 'SIFT scenery only, Lowe ratio .65, RANSAC 1.5 px; cumulative 5-frame homographies; local torso scale after registration',
                               'climb_quality': quality}, 'observations': observations,
              'limitations': ['One retail climb and one prerelease promotional lunge/mantle, not controlled repeat trials.',
                              'No controller overlay: stick magnitude, jump charge and camera inputs unknown.',
                              'Nintendo HUD hidden, build/platform and real-time playback unverified; retail author describes climbing.',
                              'Metre tolerances are conservative annotation/scale allowances, not statistical confidence intervals.',
                              'Lunge ends at an edge: rise is edge-limited, not maximum unconstrained jump height.',
                              'A homography stabilizes scenery; it does not by itself provide metric rectification.',
                              'Only durations enter measured-reference agreement. Conditional metre estimates are printed separately.']}
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    for k,v in observations.items():
        print(k, v.get('value',v.get('center_seconds')), v.get('uncertainty',v.get('bounds_seconds')))

if __name__ == '__main__':
    main()
