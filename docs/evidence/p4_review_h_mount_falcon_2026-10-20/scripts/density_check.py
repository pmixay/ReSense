"""Physical check of the Falcon density model (``resense.sensor.falcon_expected_points``, the outside-ROI raster
0.18 x 0.235 deg that ``small_target_limit('falcon_prime')`` uses) on the recording's real object: for every
detection of the shipped run that is a person STOP (frames 2972-4382, as the F1 lane and K2 reviews), the cluster's
returns ``n`` (the detector's own count, from falcon_pair.py's ``.on.x.jsonl``) against the model's expectation for a
flat target of the cluster's measured width and height at its distance; the ratio observed / expected by distance
band. A model that was optimistic would show ratios below 1; the ROI raster (0.088 x 0.06 deg) would show far above.
It checks the model's order of magnitude, not the 0.3 x 0.3 m / 3-return criterion itself.

    density_check.py <pair prefix>
"""
import json
import sys

import numpy as np

sys.path.insert(0, __import__("os").environ["RESENSE_REPO"])
from resense.sensor import falcon_expected_points  # noqa: E402

pre = sys.argv[1]
on = [json.loads(line) for line in open(pre + ".on.jsonl")]
x = [json.loads(line) for line in open(pre + ".on.x.jsonl")]
FALSE = {159, 2312, 2313, 2314} | set(range(4394, 4402))
rows = []
for r, xr in zip(on, x):
    if r["decision"] != "STOP" or r["i"] in FALSE or r["i"] > 4382:
        continue
    for d in xr["dets"]:
        if d["zone"] != "gauge" or d["misses"]:
            continue
        w, h = d["size"][1], d["size"][2]
        rows.append((d["d"], d["n"], float(falcon_expected_points(d["d"], max(w, 0.05), max(h, 0.05))), w, h))
a = np.array(rows)
print(f"person STOP detections (hit this frame): {len(a)}")
for lo, hi in ((0, 10), (10, 25), (25, 50), (50, 80), (80, 120), (120, 160)):
    m = (a[:, 0] >= lo) & (a[:, 0] < hi)
    if m.sum():
        ratio = a[m, 1] / a[m, 2]
        print(f"{lo:3d}-{hi:3d} m: {int(m.sum()):4d} detections, n median {np.median(a[m, 1]):6.1f}, model expects {np.median(a[m, 2]):6.1f}, "
              f"ratio observed/expected median {np.median(ratio):5.2f} (p10 {np.percentile(ratio, 10):5.2f}, p90 {np.percentile(ratio, 90):5.2f}), "
              f"cluster width x height median {np.median(a[m, 3]):.2f} x {np.median(a[m, 4]):.2f} m")
