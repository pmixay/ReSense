"""Independent check of review A finding 1: directional_axes on a synthetic full-revolution open-air scan.
Ground plane 1.9 m below the sensor, azimuth -104..+106 deg (DATASET.md), Pandar-like elevations -25..+15 deg,
a small share of returns above the sensor (masts / wires), vs a forward-only +-50 deg scan (positive control)."""
import sys
import numpy as np
sys.path.insert(0, sys.argv[1])
from resense.calibration import directional_axes
rng = np.random.default_rng(0)
def scan(az0, az1, above_frac, n=60000):
    az = np.radians(rng.uniform(az0, az1, n)); el = np.radians(rng.uniform(-25, -1, n))
    r = 1.9 / np.tan(-el)                       # hits on the ground plane
    keep = r < 120
    az, el, r = az[keep], el[keep], r[keep]
    pts = np.stack([r * np.cos(az), r * np.sin(az), np.full(r.size, -1.9)], 1)
    m = int(above_frac * len(pts))              # returns above the sensor (masts, wires, trees)
    a2 = np.radians(rng.uniform(az0, az1, m)); e2 = np.radians(rng.uniform(1, 15, m)); r2 = rng.uniform(5, 60, m)
    up = np.stack([r2 * np.cos(e2) * np.cos(a2), r2 * np.cos(e2) * np.sin(a2), r2 * np.sin(e2)], 1)
    return np.concatenate([pts, up]).astype(np.float32)
for name, az0, az1, fr in (("full rev, 0.2 % above", -104, 106, 0.002), ("full rev, 1 % above", -104, 106, 0.01),
                           ("full rev, 3 % above", -104, 106, 0.03), ("full rev, 10 % above", -104, 106, 0.10),
                           ("forward +-50, 0.2 % above (control)", -50, 50, 0.002), ("forward +-50, 10 % above", -50, 50, 0.10)):
    p = scan(az0, az1, fr)
    f, u = directional_axes(p)
    print(f"{name:38s} pos-frac {np.round((p > 0).mean(0), 3)} -> forward {f}, up {u}")
