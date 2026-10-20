"""Crop dumped Falcon frames (falcon_trace.py / falcon_pair.py) for the committed record: 0..25 m ahead (0..60 m for
frames before 4100, the person at ~48 m) and |Y| < 3.5 m. ``xyz`` is cut; ``dy`` and ``h`` (the model's corridor
coordinates, not used by the pictures or near_person.py) are left out; index arrays (own_*, hm_*) are remapped to
the cut cloud (indices outside are dropped, counted in ``dropped_<key>`` and printed); other arrays are kept.

    crop_dump.py <dump dir> <out dir>
"""
import glob
import os
import sys

import numpy as np

src, dst = sys.argv[1:3]
os.makedirs(dst, exist_ok=True)
for p in sorted(glob.glob(os.path.join(src, "*.npz"))):
    z = np.load(p)
    xyz = z["xyz"]
    frame = int(os.path.basename(p)[1:6])
    keep = (xyz[:, 0] >= 0) & (xyz[:, 0] <= (60 if frame < 4100 else 25)) & (np.abs(xyz[:, 1]) < 3.5)
    new = np.full(len(xyz), -1, np.int64)
    new[keep] = np.arange(int(keep.sum()))
    out = {}
    for k in z.files:
        v = z[k]
        if k == "xyz":
            out[k] = v[keep]
        elif k in ("dy", "h"):
            continue
        elif k.startswith(("own_", "hm_")):
            m = new[v]
            out[k] = m[m >= 0]
            out[f"dropped_{k}"] = np.int64((m < 0).sum())
            if (m < 0).any():
                q = xyz[v[m < 0]]
                print(f"{os.path.basename(p)} {k}: {int((m < 0).sum())} of {len(v)} indices outside, "
                      f"X {q[:, 0].min():.1f}..{q[:, 0].max():.1f} Y {q[:, 1].min():.1f}..{q[:, 1].max():.1f}")
        else:
            out[k] = v
    np.savez_compressed(os.path.join(dst, os.path.basename(p)), **out)
print("cropped", len(glob.glob(os.path.join(dst, "*.npz"))))
