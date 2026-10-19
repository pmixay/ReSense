"""Where the Falcon sees what: returns per range bin in the corridor, near the bed, and beyond 250 m.

Input: raw frames dumped by falcon_dual_stream.py (FALCON_DUMP; sensor frame = ROS FLU for this recording).
The bed plane comes from floor_fit.py (median over frames): height 1.984 m below the sensor, pitch -2.37 deg.
Uses no detector code. Frames 100-1500 are before the walking person appears (reviewed trajectory).

    python range_profile.py <dir with head_fNNNNN.npz>
"""
import glob
import sys

import numpy as np

FRAMES = (100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1300, 1400, 1500)
BINS = [(0, 50), (50, 100), (100, 150), (150, 200), (200, 250), (250, 300), (300, 400), (400, 520)]
TAN_PITCH, HEIGHT = np.tan(np.radians(-2.37)), 1.984

files = [f for f in sorted(glob.glob(sys.argv[1] + "/head_f*.npz")) if int(f[-9:-4]) in FRAMES]
rows, far = [], []
for f in files:
    d = np.load(f)
    x = d["xyz"].astype(np.float64)
    r = np.linalg.norm(x, axis=1)
    h = x[:, 2] - (-HEIGHT + TAN_PITCH * x[:, 0])          # height above the fitted near-field bed plane
    corridor = (np.abs(x[:, 1]) < 3) & (x[:, 0] > 2)
    row = []
    for lo, hi in BINS:
        m = (r >= lo) & (r < hi)
        row.append(((m & corridor).sum(), (m & corridor & (np.abs(h) < 0.5)).sum(),
                    (m & corridor & (h >= 0.5) & (h < 3.5)).sum(), (m & (np.abs(x[:, 1]) >= 3)).sum()))
    rows.append(row)
    m = r > 250
    far.append(np.c_[np.degrees(np.arctan2(x[m, 1], x[m, 0])), np.degrees(np.arcsin(x[m, 2] / r[m])), r[m],
                     d["inten"][m]])
R = np.array(rows).mean(axis=0)
print("returns per frame, mean of %d empty frames %s; corridor = |y| < 3 m" % (len(files), FRAMES))
print("range      | corridor total | near bed plane (|h|<0.5 m) | above bed 0.5-3.5 m | outside corridor")
for (lo, hi), v in zip(BINS, R):
    print(f"{lo:3d}-{hi:3d} m  | {v[0]:12.1f} | {v[1]:12.1f} | {v[2]:12.1f} | {v[3]:12.1f}")
far = np.vstack(far)
inten = np.concatenate([np.load(f)["inten"] for f in files[:3]])
print("returns > 250 m: n=%d; azimuth p5/p50/p95 %.1f/%.1f/%.1f deg; elevation p5/p50/p95 %.2f/%.2f/%.2f deg"
      % (len(far), *np.percentile(far[:, 0], [5, 50, 95]), *np.percentile(far[:, 1], [5, 50, 95])))
print("intensity: all returns median/p90 %d/%d; returns > 250 m median/p90 %d/%d"
      % (np.median(inten), np.percentile(inten, 90), np.median(far[:, 3]), np.percentile(far[:, 3], 90)))
