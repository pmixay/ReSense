#!/usr/bin/env python3
"""Revision-2 design study: the face-toward-the-sensor signature with a lateral tolerance that admits the real
per-ring azimuth phases, on the ride rejections (dumps) and on B1's design snapshots (eligible flips): a footprint
return with another footprint return at |dx| <= DX, |ddy| <= DDY, 0.03 <= dh <= 0.30 below it (any footprint
return, not only the top surface).   python ride_face.py <dump dir> <snapshot dir> <audit json>"""
import glob, json, sys
from pathlib import Path
import numpy as np

def face(X, dy, h, foot, DX, DDY):
    F = np.flatnonzero(foot)
    for t in F:
        dh = h[t] - h[F]
        if ((np.abs(X[F] - X[t]) <= DX) & (np.abs(dy[F] - dy[t]) <= DDY) & (dh >= 0.03) & (dh <= 0.30)).any():
            return True
    return False

for DX, DDY in ((0.05, 0.02), (0.05, 0.05), (0.05, 0.07), (0.05, 0.10)):
    n = hit = 0
    for f in sorted(glob.glob(sys.argv[1] + "/*.npz")):
        d = np.load(f); X, dy, h, own, bb = d["X"].astype(float), d["dy"], d["h"], d["own"], d["bbox"]
        dd = dy[own]
        foot = (X >= bb[0]) & (X <= bb[3]) & (dy >= dd.min()) & (dy <= dd.max()) & (h < 0.35)
        n += 1; hit += face(X, dy, h, foot, DX, DDY)
    audit = json.loads(Path(sys.argv[3]).read_text()); m = k = 0
    for r in audit["rows"]:
        if r["candidate_weak"]:
            continue
        d = np.load(Path(sys.argv[2]) / f"frame_{r['frame']:05d}.npz")
        X, dy, h = d["X"].astype(float), d["dy"], d["h"]; st, idx = d[f"state_{r['cluster']}"], d[f"idx_{r['cluster']}"]
        dd = dy[idx]
        if dd.max() - dd.min() > 0.45 or abs(abs(float(st[6])) - 0.795) > 0.25:
            continue
        foot = (X >= st[0]) & (X <= st[3]) & (dy >= dd.min()) & (dy <= dd.max()) & (h < 0.35)
        m += 1; k += face(X, dy, h, foot, DX, DDY)
    print(f"dx {DX} ddy {DDY}: face in {hit}/{n} ride rejections, {k}/{m} eligible design flips")
