#!/usr/bin/env python3
"""Look for the source frames of the synthetic bags among the locally decoded organizer recordings.

    find_source_local.py <decoded dir>

Five frames per synthetic bag; 300 random points with intensity > 3 (never inserted) each, hashed on
their exact float32 xyz; every frame of every other decoded recording is searched. Prints the best
match per query frame (matched points of 300). Result: ../find_source_local.txt.
"""
import glob
import os
import sys

import numpy as np


def h(xyz):
    u = np.ascontiguousarray(xyz, dtype=np.float32).view(np.uint32).astype(np.uint64)
    return ((u[:, 0] * np.uint64(0x9E3779B97F4A7C15)) ^ (u[:, 1] * np.uint64(0xC2B2AE3D27D4EB4F))
            ^ (u[:, 2] * np.uint64(0x165667B19E3779F9)))


def main():
    D = sys.argv[1]
    queries = {}
    for b in ("synthetic_platform", "synthetic_switch", "synthetic_tunnels"):
        fs = sorted(glob.glob(f"{D}/{b}/f_*.npz"))
        for k in sorted({0, len(fs) // 4, len(fs) // 2, 3 * len(fs) // 4, len(fs) - 1}):
            d = np.load(fs[k])
            x = d["xyz"]
            ok = (d["inten"] > 3) & (np.abs(x).sum(1) > 0)
            sel = np.random.default_rng(0).choice(np.flatnonzero(ok), 300, replace=False)
            queries[(b, k, len(fs))] = h(x[sel])
    best = {q: (0, None) for q in queries}
    for src in sorted(os.listdir(D)):
        if src.startswith("synthetic"):
            continue
        print(src, flush=True)
        for f in sorted(glob.glob(f"{D}/{src}/f_*.npz")):
            hs = np.sort(h(np.load(f)["xyz"]))
            if not hs.size:
                continue
            for q, qh in queries.items():
                p = np.minimum(np.searchsorted(hs, qh), hs.size - 1)
                n = int((hs[p] == qh).sum())
                if n > best[q][0]:
                    best[q] = (n, f"{src}/{os.path.basename(f)}")
    for q, v in best.items():
        print(q, v)


if __name__ == "__main__":
    main()
