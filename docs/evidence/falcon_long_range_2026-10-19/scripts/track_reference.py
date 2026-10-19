#!/usr/bin/env python3
"""Fixed raw-frame track reference for the injector, from raw points only (no detector output).

Rails: on 21 empty frames (100..1100 step 50) the rail heads are the two lateral peaks of the
90th-percentile height (pitch-levelled by the nominal 2.39 deg, bed band only) per 5 cm bin.
Per along-range slab: left/right rail lateral and rail-head z. The far reference line is the
straight fit of the rail centre over 30..90 m (where the near-field drift has ended); the rail-head
height is a straight fit of z over 8..90 m. The reviewed person path (atlas anchors) is compared.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

CACHE = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/user/data/falcon")
OUT = Path(__file__).resolve().parents[1] / "track_reference.json"
REPO = Path(os.environ.get("RESENSE_REPO", Path(__file__).resolve().parents[4]))

P = [np.load(CACHE / f"f_{i:05d}.npz")["xyz"].astype(np.float64) for i in range(100, 1101, 50)]
xyz = np.vstack(P)
x, y, z = xyz.T
lev = np.tan(np.radians(2.39))
zz = z + x * lev
rows = []
for lo in list(range(6, 40, 3)) + list(range(40, 96, 6)):
    hi = lo + (3 if lo < 40 else 6)
    m = (x > lo) & (x < hi) & (np.abs(y) < 2.5) & (zz < -1.5) & (zz > -2.4)
    bins = np.arange(-2.5, 2.5001, 0.05)
    idx = np.digitize(y[m], bins)
    prof = np.array([np.percentile(zz[m][idx == k], 90) if (idx == k).sum() > 3 else -9 for k in range(1, len(bins))])
    c = bins[:-1] + 0.025
    # the two most prominent ridges 1.45..1.75 m apart (rail head pair, gauge 1.52 + head width)
    best = None
    for i in range(len(c)):
        for j in range(i + 1, len(c)):
            sep = c[j] - c[i]
            if 1.45 <= sep <= 1.75 and prof[i] > -1.95 and prof[j] > -1.95:
                base = np.median(prof[max(0, i - 6): j + 7])
                score = min(prof[i], prof[j]) - base
                if best is None or score > best[0]:
                    best = (score, c[i], c[j], prof[i], prof[j])
    if best and best[0] > 0.06:
        xm = 0.5 * (lo + hi)
        rows.append({"x": xm, "right": best[1], "left": best[2], "centre": 0.5 * (best[1] + best[2]),
                     "gauge": best[2] - best[1], "head_z": 0.5 * (best[3] + best[4]) - xm * lev, "score": best[0]})
R = {k: np.array([r[k] for r in rows]) for k in rows[0]}
far = (R["x"] >= 30) & (R["x"] <= 90)
pc = np.polyfit(R["x"][far], R["centre"][far], 1)
pz = np.polyfit(R["x"][R["x"] >= 8], R["head_z"][R["x"] >= 8], 1)
atlas = json.loads((REPO / "docs/evidence/n2_falcon_2026-10-18/raw_person_review/atlas_proposals.json").read_text())
A = [a for a in atlas["anchors"] if a["episode"].startswith("main")]
ac = np.array([a["discovery_center"] for a in A])
person_lat = ac[:, 1] - np.polyval(pc, ac[:, 0])
bands = {}
for lo, hi in [(0, 60), (60, 130), (130, 200), (200, 250)]:
    m = (ac[:, 0] >= lo) & (ac[:, 0] < hi)
    bands[f"{lo}-{hi}"] = {"n": int(m.sum()), "mean": round(float(person_lat[m].mean()), 3),
                          "sd": round(float(person_lat[m].std()), 3)}
# far height: the rail-head line seen from the sensor bends (grade); the walking person's top
# (raw max z near each reviewed anchor, 20..250 m) gives the slope over the long baseline, the
# rail heads 8..90 m the offset at that slope
tops = []
for a in A:
    c0 = np.array(a["discovery_center"]); b0 = np.array(a["discovery_bbox"])
    q = np.load(CACHE / f"f_{a['frame']:05d}.npz")["xyz"].astype(np.float64)
    m = ((np.abs(q[:, 0] - c0[0]) < 0.6) & (q[:, 1] > b0[0, 1] - 0.15) & (q[:, 1] < b0[1, 1] + 0.15)
         & (q[:, 2] > b0[0, 2] - 2.5) & (q[:, 2] < b0[1, 2] + 0.6))
    if m.sum() >= 3 and c0[0] > 20:
        tops.append((c0[0], q[m, 2].max()))
tops = np.array(tops)
ptop = np.polyfit(tops[:, 0], tops[:, 1], 1)
c_far = float(ptop[0])
sel = R["x"] >= 8
z0_far = float(np.mean(R["head_z"][sel] - c_far * R["x"][sel]))
top_above = tops[:, 1] - (z0_far + c_far * tops[:, 0])
top_bands = {}
for lo, hi in [(20, 60), (60, 130), (130, 200), (200, 250)]:
    m = (tops[:, 0] >= lo) & (tops[:, 0] < hi)
    top_bands[f"{lo}-{hi}"] = {"n": int(m.sum()), "median": round(float(np.median(top_above[m])), 3)}
res = {"person_top_slope": c_far, "person_top_above_reference": top_bands,
       "rail_head_resid_at_far_slope_sd": float(np.std(R["head_z"][sel] - (z0_far + c_far * R["x"][sel]))),
       "slabs": rows, "centre_fit_30_90": pc.tolist(), "head_z_fit_8_90": pz.tolist(),
       "pitch_from_head_deg": float(np.degrees(np.arctan(pz[0]))),
       "centre_resid_sd": float(np.std(R["centre"][far] - np.polyval(pc, R["x"][far]))),
       "head_resid_sd": float(np.std(R["head_z"][R["x"] >= 8] - np.polyval(pz, R["x"][R["x"] >= 8]))),
       "person_lateral_vs_reference": bands,
       "track_rails_only": {"a": float(pc[1]), "b": float(pc[0]), "z0": float(pz[1]), "c": float(pz[0])},
       "track": {"a": float(pc[1]), "b": float(pc[0]), "z0": z0_far, "c": c_far}}
OUT.write_text(json.dumps(res, indent=1))
for r in rows:
    print({k: round(v, 3) for k, v in r.items()})
print(json.dumps({k: v for k, v in res.items() if k != "slabs"}, indent=1))
