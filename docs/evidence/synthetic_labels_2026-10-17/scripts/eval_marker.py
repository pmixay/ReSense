#!/usr/bin/env python3
"""Check the intensity-1 marker against the exact inserted points (platform frames 0-314, every 3rd).

    eval_marker.py <synthetic_platform cache> <cloud_with_fake_obj cache> <out.json>

Per marker cluster (DBSCAN 0.5 m / 4 points on intensity-1 points): size, share of exactly-new
points ("true"), purity of the grown box, range and extent; per frame the number of exactly-new
points. Summarized in ../marker_check.json.
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.cluster import DBSCAN

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
from label_marked_objects import exact_points  # noqa: E402


def main():
    cache, ref, out_path = sys.argv[1:4]
    fs = sorted(glob.glob(cache + "/f_*.npz"))
    rf = sorted(glob.glob(ref + "/f_*.npz"))
    out = []
    for k in range(0, 315, 3):
        d = np.load(fs[k])
        xyz, inten = d["xyz"], d["inten"]
        ex = set(exact_points(xyz, np.load(rf[k + 1195])["xyz"]).tolist())
        one = np.flatnonzero(inten == 1.0)
        lab = DBSCAN(eps=0.5, min_samples=4).fit_predict(xyz[one])
        for c in np.unique(lab[lab >= 0]):
            idx = one[lab == c]
            x = xyz[idx]
            lo, hi = x.min(0) - 0.15, x.max(0) + 0.15
            box = np.all((xyz >= lo) & (xyz <= hi), axis=1)
            out.append({"k": k, "n": int(idx.size), "true": float(np.mean([i in ex for i in idx])),
                        "purity": float(np.mean(inten[box] == 1.0)), "range": float(np.linalg.norm(x.mean(0))),
                        "ext": (x.max(0) - x.min(0)).round(2).tolist(),
                        "zmin": float(x[:, 2].min()), "zmax": float(x[:, 2].max())})
        out.append({"k": k, "exact_total": len(ex)})
    json.dump(out, open(out_path, "w"))


if __name__ == "__main__":
    main()
