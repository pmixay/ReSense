"""Strict detections that K2 v5b removes, per gate recording: base run (K2 off) vs v5b run, same frames (the committed
per-frame gate rows, as for ../k2_v5c_2026-10-20/scripts/dual_proxy.py). A base strict detection (zone gauge, no
reason) is 'removed' when the v5b frame has no strict detection within 2 m. For each: recording, frame, distance, v5b
joint_reach (0 = no cap), v5b axis_valid, joint_used, lateral of its centre from the base axis and from v5b's axis.
Prints counts per distance band; writes every row to <out.json>.

    python k2_removed.py <base gate work dir> <v5b gate work dir> <out.json>
"""
import glob, json, os, sys, collections
import numpy as np
base_dir, k2_dir = sys.argv[1], sys.argv[2]
def cy(t, x):
    y = t['center'] + np.tan(t['yaw']) * x + 0.5 * t['curvature'] * x * x
    s, k = t.get('curv_step', 0.0), t.get('curv_knot', 0.0)
    if s and k > 0 and x > k:
        y += 0.5 * s * (x - k) ** 2
    return y
strict = lambda d: d['zone'] == 'gauge' and not d['reason']
rows = []
for f in sorted(glob.glob(os.path.join(k2_dir, '*.jsonl'))):
    name = os.path.basename(f)[:-6]
    B = [json.loads(l) for l in open(os.path.join(base_dir, name + '.jsonl'))]
    K = [json.loads(l) for l in open(f)]
    for i, (b, k) in enumerate(zip(B, K)):
        kd = [d for d in k['detections'] if strict(d)]
        for d in b['detections']:
            if not strict(d) or any(abs(e['distance'] - d['distance']) <= 2.0 for e in kd):
                continue
            t = k['track']; x, y = d['center'][0], d['center'][1]
            rows.append((name, i, round(d['distance'], 1), t.get('joint_reach', 0.0), t['axis_valid'], bool(t.get('joint_used')),
                         round(y - cy(b['track'], x), 2), round(y - cy(t, x), 2)))
by = collections.defaultdict(list)
for r in rows:
    by[r[0]].append(r)
for name, rs in by.items():
    ds = np.array([r[2] for r in rs])
    print(f"{name}: {len(rs)} removed strict dets; distance bins <30 {np.sum(ds<30)}, 30-60 {np.sum((ds>=30)&(ds<60))}, 60-90 {np.sum((ds>=60)&(ds<90))}, >=90 {np.sum(ds>=90)}; beyond cap {sum(1 for r in rs if r[3] and r[2] > r[3])}")
json.dump(rows, open(sys.argv[3], 'w'))
