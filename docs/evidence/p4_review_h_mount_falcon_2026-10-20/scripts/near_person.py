"""Raw-point check of what stands on the track near the train in dumped Falcon frames, independent of the
detector's track model (which lost the bed at the end of the recording): the returns of the processed cloud
(detector frame after the mount correction) with |Y| < ``--half`` m, ``--x0``..``--x1`` m ahead and 0.2..2.2 m
above the calibrated mount's rail-head plane (z = ``--plane``, from falcon_pair.py's H′ record: -1.772 on the
whole recording once final). Per frame: their count, X range, Y range, height range above the plane and the
densest 0.5 m X bin. The tunnel ceiling (4.1-4.3 m above the plane) and the floor are outside the band.

    near_person.py <dump dir> <first> <last> [--plane -1.772] [--x0 1.5] [--x1 20] [--half 1.2]
"""
import argparse
import glob
import os

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("dump")
ap.add_argument("first", type=int)
ap.add_argument("last", type=int)
ap.add_argument("--plane", type=float, default=-1.772)
ap.add_argument("--x0", type=float, default=1.5)
ap.add_argument("--x1", type=float, default=20.0)
ap.add_argument("--half", type=float, default=1.2)
ap.add_argument("--suffix", default="", help="'.on' for falcon_pair.py dumps")
a = ap.parse_args()
for i in range(a.first, a.last + 1):
    p = os.path.join(a.dump, f"f{i:05d}{a.suffix}.npz")
    if not os.path.exists(p):
        continue
    z = np.load(p)
    xyz = z["xyz"].astype(np.float64)
    hp = xyz[:, 2] - a.plane
    m = (xyz[:, 0] > a.x0) & (xyz[:, 0] < a.x1) & (np.abs(xyz[:, 1]) < a.half) & (hp > 0.2) & (hp < 2.2)
    q = xyz[m]
    own = [k for k in z.files if k.startswith("own_")]
    if not len(q):
        print(f"frame {i}: 0 returns in the band; reported clusters {own}")
        continue
    hist, edges = np.histogram(q[:, 0], bins=np.arange(a.x0, a.x1 + 0.5, 0.5))
    b = int(np.argmax(hist))
    sel = (q[:, 0] >= edges[b]) & (q[:, 0] < edges[b + 1] + 0.5)
    print(f"frame {i}: {m.sum()} returns; densest X bin {edges[b]:.1f}-{edges[b] + 1.0:.1f} m: {sel.sum()} returns, "
          f"Y {q[sel, 1].min():+.2f}..{q[sel, 1].max():+.2f}, height above the plane "
          f"{(q[sel, 2] - a.plane).min():.2f}..{(q[sel, 2] - a.plane).max():.2f}; all: X {q[:, 0].min():.1f}..{q[:, 0].max():.1f}; "
          f"reported clusters {own}")
