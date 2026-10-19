#!/usr/bin/env python3
"""Leave-out test of the raster reconstruction used by the injector (``inject.raster_rays``).

On 6 empty frames, in every scan line crossing the far-track window (raw azimuth |az| < 10 deg,
elevation -3.6 .. -1.6 deg), blocks of returned rays (+-12 and +-25 scan_idx, i.e. gaps as wide as
the open-tunnel gaps) centred at several azimuths are removed and reconstructed by the same linear
interpolation; the error against their measured directions is reported, overall and for the
far-track core |az| < 3 deg. Also checks that line identity (scan_id, flags & 3, scan_idx) is a ray:
multiple returns of one key share a direction.
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CACHE = Path("/home/user/data/falcon")


def ang(xyz):
    r = np.linalg.norm(xyz, axis=1)
    return np.degrees(np.arctan2(xyz[:, 1], xyz[:, 0])), np.degrees(np.arcsin(xyz[:, 2] / r)), r


res = {"frames": [100, 300, 500, 700, 900, 1100], "gaps": {}}
multi = []
for G in (12, 25):
    E, Ec = [], []
    for fi in res["frames"]:
        d = np.load(CACHE / f"f_{fi:05d}.npz")
        az, el, r = ang(d["xyz"].astype(np.float64))
        L = d["scan_id"].astype(int) * 4 + (d["flags"] & 3)
        six = d["scan_idx"].astype(int)
        f = d["is2"] == 0
        if G == 12:
            key = L * 4096 + six
            u, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
            for k in np.flatnonzero(cnt > 1)[:2000]:
                m = inv == k
                multi.append(max(np.ptp(az[m]), np.ptp(el[m])))
        for line in np.unique(L[(np.abs(az) < 10) & (el > -3.6) & (el < -1.6) & f]):
            m = np.flatnonzero((L == line) & f & (np.abs(az) < 14))
            s, a, e = six[m], az[m], el[m]
            for c0 in (-6.0, -3.5, -1.5, 1.5, 2.0, 4.0, 7.0):
                k = np.argmin(np.abs(a - c0))
                if abs(a[k] - c0) > 0.5:
                    continue
                sc = s[k]
                gap = np.abs(s - sc) <= G
                if gap.sum() < G or (s < sc - G).sum() < 2 or (s > sc + G).sum() < 2:
                    continue
                o = np.argsort(s[~gap])
                pa = np.interp(s[gap], s[~gap][o], a[~gap][o])
                pe = np.interp(s[gap], s[~gap][o], e[~gap][o])
                err = np.c_[pa - a[gap], pe - e[gap]]
                E.append(err)
                if abs(c0) < 3:
                    Ec.append(err)
    for name, X in (("all", E), ("core_abs_az_lt_3", Ec)):
        A = np.abs(np.vstack(X))
        res["gaps"][f"+-{G}_{name}"] = {"rays": int(len(A)),
                                       "az_err_deg_p50_p95_p99_max": np.percentile(A[:, 0], [50, 95, 99, 100]).round(4).tolist(),
                                       "el_err_deg_p50_p95_p99_max": np.percentile(A[:, 1], [50, 95, 99, 100]).round(4).tolist()}
res["multi_return_rays_direction_spread_deg_p50_p99_max"] = np.percentile(multi, [50, 99, 100]).round(4).tolist()
res["raster_steps_deg"] = "ROI lines: 0.088 deg azimuth per scan_idx; non-ROI lines 0.176; ROI line spacing ~0.06-0.1 deg"
(HERE.parent / "raster_validation.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
