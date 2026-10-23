#!/usr/bin/env python3
"""Raw-point check of the Falcon person frames and the rule trace for the not-STOP finding (item 6).

Reads the clouds dumped by run_falcon.py (vehicle frame, node decode) and the per-frame records of the control
(v1.2.0) and the candidate. For each frame the person-like set is computed WITHOUT the track model: returns with
X >= 2.4 m, |Y| < 0.9 m, 0.2-1.6 m above the mount plane (the plane z = -sensor height from the calibration, which is
constant), X below the nearest return + 8 m. Then, from the detector's own corridor coordinates (dy, h) of the same
returns: how many are inside the strict gauge polygon, below the gauge floor (h < 0.12 above the MODEL rail head),
nearer than gauge.range_min, and where the model bed is against the plane.

    person_check.py CTL_PREFIX CAND_PREFIX DUMPDIR --first 4360 --last 4430 --out OUT.tsv
"""
import argparse, json, os, sys
import numpy as np

ROOT = os.environ["RESENSE_REPO"]
sys.path.insert(0, ROOT)
from resense.config import GaugeConfig  # noqa: E402
from resense.gauge import point_in_polygon  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("ctl"); ap.add_argument("cand"); ap.add_argument("dump")
ap.add_argument("--first", type=int, default=4360); ap.add_argument("--last", type=int, default=4430)
ap.add_argument("--out", required=True)
a = ap.parse_args()
L = lambda p: [json.loads(l) for l in open(p)]
rc, rk, xc = L(a.ctl + ".jsonl"), L(a.cand + ".jsonl"), L(a.ctl + ".x.jsonl")
cc, ck = L(a.ctl + ".c.jsonl"), L(a.cand + ".c.jsonl")
gcfg = GaugeConfig()
rows = []
hdr = ["frame", "ctl_decision", "n_person", "x_near", "x_p50", "y_lo", "y_hi", "hm_max", "in_strict_gauge", "below_gauge_floor",
       "nearer_than_range_min", "bed_minus_plane_at_p50", "model_h_p50", "ctl_clear", "cand_clear", "node_ctl", "node_cand",
       "ctl_clear_beyond_nearest", "cand_clear_beyond_nearest", "lock", "n_dets", "n_warns"]
for i in range(a.first, a.last + 1):
    f = os.path.join(a.dump, f"f{i:05d}.npz")
    if not os.path.exists(f):
        continue
    d = np.load(f)
    xyz, dy, h, plane = d["xyz"], d["dy"], d["h"], float(d["plane"])
    hm = xyz[:, 2] - plane
    base = (xyz[:, 0] >= 2.4) & (np.abs(xyz[:, 1]) < 0.9) & (hm > 0.2) & (hm < 1.6)
    if not base.any():
        rows.append([i, rc[i]["decision"], 0] + [""] * 10 + [rc[i]["clear"], rk[i]["clear"], "", "", "", "", rc[i]["rail_lock"], len(rc[i]["dets"]), len(rc[i]["warns"])])
        continue
    x0 = xyz[base, 0].min()
    sel = base & (xyz[:, 0] < x0 + 8.0)
    X = xyz[sel, 0]
    n = int(sel.sum())
    strict = point_in_polygon(dy[sel], h[sel], gcfg.profile)
    p50 = float(np.median(X))
    bed = float(np.interp(p50, d["grid"], d["rail_z"])) - plane
    near = float(X.min())
    nodec = ck[i]["conservative"]["clear"]
    rows.append([i, rc[i]["decision"], n, round(near, 2), round(p50, 2), round(float(xyz[sel, 1].min()), 2),
                 round(float(xyz[sel, 1].max()), 2), round(float(hm[sel].max()), 2), int((strict & (X >= gcfg.range_min)).sum()),
                 int((h[sel] < 0.12).sum()), int((X < gcfg.range_min).sum()), round(bed, 2), round(float(np.median(h[sel])), 2),
                 rc[i]["clear"], rk[i]["clear"], cc[i]["conservative"]["clear"], nodec,
                 int(rc[i]["clear"] > near + 1e-9 and rc[i]["decision"] != "STOP"),
                 int(rk[i]["clear"] > near + 1e-9 and rk[i]["decision"] != "STOP"),
                 rc[i]["rail_lock"], len(rc[i]["dets"]), len(rc[i]["warns"])])
with open(a.out, "w") as fo:
    fo.write("\t".join(hdr) + "\n")
    for r in rows:
        fo.write("\t".join(str(v) for v in r) + "\n")
print("frames", len(rows), "control clear beyond nearest return (non-STOP):", sum(r[17] == 1 for r in rows if r[17] != ""),
      "| candidate:", sum(r[18] == 1 for r in rows if r[18] != ""))
