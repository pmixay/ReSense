"""Offline proxy of v5c (track.axis_joint_reach_dual = EXT) from committed per-frame gate rows.

Input: the base run (K2 off) and the v5b run of the same gate (track rows of v5b carry the joint shape and the cap,
track.joint_reach). A base STOP-zone detection (zone gauge, no reason) that lies beyond v5b's cap is one v5b's cap
demoted. v5c would keep it strict when (a) it is inside the extended range, cap < d <= min(base axis_valid, cap + EXT),
and (b) it is also inside the gauge measured from v5b's joint axis (base detections are inside base's by definition).
This ignores tracker dynamics and the K1 switch inside the v5b run: it is a proxy, not a measurement."""
import glob
import json
import os
import sys

import numpy as np
base_dir, k2_dir, EXT = sys.argv[1], sys.argv[2], float(sys.argv[3])
HALF, EM = 1.05, 0.15 / 100.0

def cy(t, x):
    y = t['center'] + np.tan(t['yaw']) * x + 0.5 * t['curvature'] * x * x
    s, k = t.get('curv_step', 0.0), t.get('curv_knot', 0.0)
    if s and k > 0 and x > k:
        y += 0.5 * s * (x - k) ** 2
    return y

print(f"EXT = {EXT} m")
for f in sorted(glob.glob(os.path.join(k2_dir, '*.jsonl'))):
    name = os.path.basename(f)[:-6]
    B = [json.loads(line) for line in open(os.path.join(base_dir, name + '.jsonl'))]
    K = [json.loads(line) for line in open(f)]
    assert len(B) == len(K), name
    demoted, frames = 0, []
    for i, (b, k) in enumerate(zip(B, K)):
        t = k['track']
        reach = t.get('joint_reach', 0.0)
        if not t.get('joint_used') or not reach:
            continue
        for d in b['detections']:
            if d['zone'] != 'gauge' or d['reason'] or d['distance'] <= reach or d['distance'] > b['track']['axis_valid']:
                continue
            demoted += 1
            x, y = d['center'][0], d['center'][1]
            lat = y - cy(t, x)
            if d['distance'] <= min(b['track']['axis_valid'], reach + EXT) and abs(lat) - d['size'][1] / 2 <= HALF - EM * x:
                frames.append((i, reach, round(d['distance'], 1), d['lateral'], round(float(lat), 2), d['size'],
                               bool(k['obstacle'])))
    eps = []
    for fr in frames:
        if eps and fr[0] - eps[-1][-1][0] <= 3:
            eps[-1].append(fr)
        else:
            eps.append([fr])
    print(f"{name}: base STOP-zone detections beyond v5b's cap {demoted}; kept strict by v5c {len(frames)} "
          f"in {len(eps)} groups")
    for e in eps:
        print(f"   frames {e[0][0]}-{e[-1][0]}: cap {e[0][1]} m, distance {e[0][2]}-{e[-1][2]} m, base lateral "
              f"{e[0][3]}, joint lateral {e[0][4]}, size {e[0][5]}, v5b already STOP at the first: {e[0][6]}")
