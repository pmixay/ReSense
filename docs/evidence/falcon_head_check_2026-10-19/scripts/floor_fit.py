"""Independent bed-plane fit on raw Falcon frames (ROS FLU sensor frame): z = a + b*x + c*y, RANSAC on near-field
bed points. Reports pitch = atan(b), roll = atan(c), height = -a and the fit residual. Uses no detector code.

    python floor_fit.py <dir with head_fNNNNN.npz>
"""
import glob
import sys

import numpy as np

FRAMES = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 100, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000)
rng = np.random.default_rng(0)


def fit(xyz):
    m = (xyz[:, 0] > 8) & (xyz[:, 0] < 60) & (np.abs(xyz[:, 1]) < 4.0) & (xyz[:, 2] < -1.2) & (xyz[:, 2] > -6.0)
    p = xyz[m].astype(np.float64)
    if len(p) < 500:
        return None
    best = None
    for _ in range(300):
        i = rng.choice(len(p), 3, replace=False)
        try:
            c = np.linalg.solve(np.c_[np.ones(3), p[i, 0], p[i, 1]], p[i, 2])
        except np.linalg.LinAlgError:
            continue
        inliers = (np.abs(p[:, 2] - (c[0] + c[1] * p[:, 0] + c[2] * p[:, 1])) < 0.08).sum()
        if best is None or inliers > best[0]:
            best = (inliers, c)
    c = best[1]
    for _ in range(3):
        k = np.abs(p[:, 2] - (c[0] + c[1] * p[:, 0] + c[2] * p[:, 1])) < 0.10
        c, *_ = np.linalg.lstsq(np.c_[np.ones(k.sum()), p[k, 0], p[k, 1]], p[k, 2], rcond=None)
    r = p[:, 2] - (c[0] + c[1] * p[:, 0] + c[2] * p[:, 1])
    k = np.abs(r) < 0.10
    return c, int(k.sum()), float(np.std(r[k]))


print("frame  n_bed  height_m  pitch_deg  roll_deg  resid_sd_m")
res = []
for f in sorted(glob.glob(sys.argv[1] + "/head_f*.npz")):
    n = int(f[-9:-4])
    if n not in FRAMES:
        continue
    out = fit(np.load(f)["xyz"])
    if out is None:
        print(f"{n:5d}  too few bed points")
        continue
    c, k, sd = out
    res.append((c[0], np.degrees(np.arctan(c[1])), np.degrees(np.arctan(c[2]))))
    print(f"{n:5d}  {k:6d}  {-c[0]:7.3f}  {np.degrees(np.arctan(c[1])):8.2f}  {np.degrees(np.arctan(c[2])):8.2f}  {sd:7.3f}")
r = np.array(res)
print("median over frames: height %.3f m, pitch %.2f deg, roll %.2f deg"
      % (-np.median(r[:, 0]), np.median(r[:, 1]), np.median(r[:, 2])))
