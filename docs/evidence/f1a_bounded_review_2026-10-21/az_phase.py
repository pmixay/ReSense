#!/usr/bin/env python3
"""Real Pandar128 data: do the 128 rings share one azimuth grid? (the synthetic caster's grid is shared, so its
vertical faces show returns stacked at the same lateral position, which amendment 1's face test relies on).
Per ring: azimuth phase modulo the 0.1 deg column step, from returns at 25-80 m (1 cm quantisation = <= 0.023 deg).
Reports each ring's circular-mean phase and its concentration R (1 = every return on one grid phase).
Positive control: the synthetic Pandar grid (resense.sensor.ray_directions, quantised to 1 cm the same way) must give
one phase for every ring.      python az_phase.py <cache dir> [frames...]"""
import sys, glob
import numpy as np
sys.path.insert(0, "/home/user/ReSense/scripts"); sys.path.insert(0, "/home/user/ReSense")
from cache_io import load_cache_array
from resense.sensor import ray_directions

STEP = 0.1

def phases(x, y, z, ring):
    r = np.sqrt(x * x + y * y)
    m = (r > 25) & (r < 80)
    az = np.degrees(np.arctan2(y[m], x[m]))
    ph = 2 * np.pi * (az / STEP)
    out = {}
    for k in np.unique(ring[m]):
        p = ph[ring[m] == k]
        if p.size < 50:
            continue
        v = np.exp(1j * p).mean()
        out[int(k)] = (np.degrees(np.angle(v)) / 360 * STEP, abs(v), p.size)
    return out

def report(name, res):
    ph = np.array([v[0] for v in res.values()]); R = np.array([v[1] for v in res.values()])
    # spread of the per-ring phases (circular)
    c = np.exp(1j * 2 * np.pi * ph / STEP).mean()
    print(f"{name}: rings {len(res)}, per-ring concentration R p10/p50 {np.percentile(R,10):.2f}/{np.median(R):.2f}, "
          f"phase across rings: resultant {abs(c):.2f} (1 = one shared grid), "
          f"phase range p5-p95 {np.percentile(ph,5):+.3f}..{np.percentile(ph,95):+.3f} deg")
    return ph, R

# positive control: synthetic grid at 40 m, quantised to 1 cm
d = ray_directions(); t = 40.0 / np.maximum(np.abs(d[:, 0]), 1e-3)
pts = np.round(d * t[:, None] / 0.01) * 0.01
rings = np.repeat(np.arange(128), d.shape[0] // 128)
report("synthetic grid (control)", phases(pts[:, 0], pts[:, 1], pts[:, 2], rings))
files = sorted(glob.glob(sys.argv[1] + "/*.npy"))
for f in [files[int(i)] for i in (sys.argv[2:] or [0, len(files) // 2])]:
    a = load_cache_array(f)
    x, y, z = (a[k].astype(float) * 0.01 for k in ("x", "y", "z"))
    ring = (a["ring"] & 0x7F).astype(int)
    ph, R = report(f.split("/")[-1], phases(x, y, z, ring))
    np.set_printoptions(precision=3, suppress=True)
    print("  first 24 rings' phase (deg):", np.round(ph[:24], 3))
