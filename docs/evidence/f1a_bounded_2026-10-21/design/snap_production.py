#!/usr/bin/env python3
"""The production rail_reference_check (RESENSE_REPO's resense) with rail_head_bounded off and on, on B1's 250
archived real ride states (compact snapshots: cluster states + the points the B1 rule reads). Per originally rejected
cluster: B1 (off) decision, bounded (on) decision. Limitation: the compact snapshots were made for the B1 rule; if
they omit footprint returns >= foot_max_top, condition 7 cannot fire here (rejections could be overstated).

    python snap_production.py <snapshot dir> <audit json> --out out.json
"""
import argparse, dataclasses, json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from resense.config import LowObjectConfig
from resense.lowobj import low_free_mask, rail_reference_check

ap = argparse.ArgumentParser(); ap.add_argument("snaps", type=Path); ap.add_argument("audit", type=Path)
ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()
audit = json.loads(a.audit.read_text())
want = {(r["frame"], r["cluster"]): r for r in audit["rows"]}
rows, maxh = [], -9.0
for path in sorted(a.snaps.glob("frame_*.npz")):
    d = np.load(path); fr = int(path.stem[6:])
    X, dy, h = d["X"].astype(np.float64), d["dy"], d["h"]
    if h.size:
        maxh = max(maxh, float(h.max()))
    cl = {}
    for key in d.files:
        if key.startswith("state_"):
            s, idx = d[key], d["idx_" + key[6:]]
            cl[int(key[6:])] = SimpleNamespace(points_idx=idx, kind="low", bbox_min=s[:3], bbox_max=s[3:6],
                lateral=float(s[6]), height_max=float(s[7]), low_height_weak=bool(s[8]), zone="gauge" if s[9] else "warning",
                reason="captured" if s[10] else "", size=s[3:6] - s[:3], distance=float(s[0]))
    if not cl:
        continue
    cs = list(cl.values())
    free = low_free_mask(X.size, cs, X, dy)
    res = {}
    for on in (False, True):
        cfg = dataclasses.replace(LowObjectConfig(), rail_head_bounded=on)
        out = rail_reference_check(cs, X, dy, h, cfg, 1.59, free)
        res[on] = {i for i, c in cl.items() if any(c is o for o in out)}
    for i in cl:
        if (fr, i) in want:
            rows.append(dict(frame=fr, cluster=i, b1_rejected=i in res[False], bounded_rejected=i in res[True],
                             audit_b1_rejected=want[(fr, i)]["candidate_weak"]))
        else:
            assert not (i in res[True] and i not in res[False]), ("new rejection outside the pre-repair set", fr, i)
flips = [r for r in rows if not r["b1_rejected"]]
summ = dict(originally_rejected=len(rows), b1_matches_audit=sum(r["b1_rejected"] == r["audit_b1_rejected"] for r in rows),
            b1_flips=len(flips), flips_rejected_by_bounded=sum(r["bounded_rejected"] for r in flips),
            b1_retained_still_rejected=sum(r["bounded_rejected"] for r in rows if r["b1_rejected"]),
            max_h_in_snapshots=round(maxh, 3))
json.dump(dict(summary=summ, rows=rows), open(a.out, "w"), indent=1); print(summ)
