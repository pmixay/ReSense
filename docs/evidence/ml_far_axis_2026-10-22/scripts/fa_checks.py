#!/usr/bin/env python3
"""Checks of the self-supervised labels on real data that do not go through the label's own odometry chain.

    fa_checks.py walls <extract.npz ...> --labels L.npz --out walls.json
        Where frame t itself observes BOTH tunnel boundaries at distance X (the profile of resense.far_axis), each
        referenced to its own near-field (10-40 m) distance, their midline offset is a direct, single-frame,
        odometry-free measurement of where the track is at X (exact in a tube of constant width, a bias where the
        width changes: platforms, double-track halls). Compared with label - base per band; also against the base
        model alone (a positive control: the comparison must see the base model's known error).
    fa_checks.py speed <extract.npz ...> --labels L.npz --intake docs/extended_dataset_intake.json --out speed.json
        ICP travel per ride split (the repaired motions composed) against the organizers' per-split train speed
        (``speed_tracks``, from the detector's tracked structures, not from ICP) x the split duration.
    fa_checks.py driven <extract.npz ...> --labels L.npz [--poses b6_poses.json] --out driven.json
        The driven path (the sensor positions of later frames brought into frame t, by our poses or by the B6
        poses) plus a constant mount offset (median label - path at 40 m) against the rail-stitched label.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "../../../..")))
from fa_train import BANDS, load_extract  # noqa: E402
from resense import far_axis as fa  # noqa: E402


def pstats(v):
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    if not v.size:
        return {"n": 0}
    a = np.abs(v)
    return {"n": int(v.size), "median": round(float(np.median(v)), 3), "abs_p50": round(float(np.percentile(a, 50)), 3),
            "abs_p90": round(float(np.percentile(a, 90)), 3)}


def in_band(x, lo, hi):
    return (x >= lo) & ((x < hi) | ((hi == 250) & (x == 250)))


def cmd_walls(a):
    names, prof, state = load_extract(a.files)
    L = np.load(a.labels)
    xq = L["query_x"]
    li, ri = fa.FEATURES.index("l_off"), fa.FEATURES.index("r_off")
    rows = []
    for t in range(len(names)):
        F = fa.query_features(prof[t], state[t], xq)
        b = fa.base_y(state[t], xq)
        for i, x in enumerate(xq):
            if not (np.isfinite(F[i, li]) and np.isfinite(F[i, ri])):
                continue
            # both sides seen within +-5 m of X with at least 3 returns per bin; the bins' widths must agree
            lab = L["label"][t, i] - b[i] if L["valid"][t, i] else np.nan
            rows.append((x, 0.5 * (F[i, li] + F[i, ri]), lab, abs(F[i, li] - F[i, ri])))
    R = np.array(rows)
    out = {"rows_both_sides": int(len(R)), "bands": {}}
    for lo, hi in BANDS:
        m = in_band(R[:, 0], lo, hi) & np.isfinite(R[:, 2])
        # parallel walls only: the two sides moved by the same amount within 0.3 m (a tube, not a platform end)
        par = m & (R[:, 3] <= 0.3)
        out["bands"][f"{lo}-{hi}"] = {
            "label_minus_walls": pstats(R[par, 2] - R[par, 1]),
            "base_minus_walls (positive control: the base model's own error)": pstats(-R[par, 1]),
            "label_minus_walls_all_widths": pstats(R[m, 2] - R[m, 1]),
        }
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


def cmd_speed(a):
    from fa_labels import repair
    D = [np.load(f) for f in a.files]
    names, T, fit, stamps = [], [], [], []
    seen = set()
    for d in D:
        dn, dT, df, dst = d["names"], d["T"], d["fitness"], d["stamps"]
        for k, n in enumerate(dn):
            if str(n) in seen:
                continue
            seen.add(str(n))
            names.append(str(n)); T.append(dT[k]); fit.append(df[k]); stamps.append(dst[k])
    T, rep = repair(np.array(T), np.array(fit))
    intake = {f["n"]: f for f in json.load(open(a.intake))["files"]}
    split = np.array([int(n.split("_")[2]) for n in names])
    dx = np.array([t[0, 3] for t in T])
    stamps = np.array(stamps)
    rows = []
    for s in np.unique(split):
        m = np.flatnonzero(split == s)
        m = m[1:] if m[0] == 0 else m
        v = intake.get(int(s), {}).get("speed_tracks")
        if not v or len(m) < 40:
            continue
        dur = stamps[m[-1]] - stamps[m[0] - 1]
        rows.append((int(s), float(np.nansum(dx[m])), float(v) * dur, int(rep[m].sum())))
    R = np.array(rows)
    moving = R[:, 2] > 5.0
    ratio = R[moving, 1] / R[moving, 2]
    out = {"splits": int(len(R)), "moving_splits": int(moving.sum()),
           "icp_over_reference": {"median": round(float(np.median(ratio)), 4),
                                  "p10": round(float(np.percentile(ratio, 10)), 4),
                                  "p90": round(float(np.percentile(ratio, 90)), 4)},
           "total_icp_m": round(float(R[:, 1].sum()), 1), "total_reference_m": round(float(R[:, 2].sum()), 1),
           "rows": R.tolist()}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))


def cmd_driven(a):
    L = np.load(a.labels)
    xq = L["query_x"]
    if a.poses:
        rows = json.load(open(a.poses))["rows"]
        P, seg = [], 0
        cur = np.eye(4)
        segs = []
        for k, r in enumerate(rows):
            if r["T"] is None:
                seg += k > 0
                cur = np.eye(4)
            else:
                cur = cur @ np.array(r["T"])
            P.append(cur.copy()); segs.append(seg)
        P, segs = np.array(P), np.array(segs)
    else:
        P, segs = L["poses"], L["segs"]
    n = min(len(P), len(L["label"]))
    # amendment A1: B6 motions whose forward step differs from ours by more than 0.1 m (shown wrong by the detector's
    # independent speed estimate) end the B6 driven path of every frame before them
    defect = np.zeros(n, dtype=bool)
    if a.poses and a.b6_trust:
        Lp = L["poses"]
        for k in range(1, n):
            if rows[k]["T"] is not None:
                ours = (np.linalg.inv(Lp[k - 1]) @ Lp[k])[0, 3]
                defect[k] = abs(rows[k]["T"][0][3] - ours) > 0.1
    path = np.full((n, len(xq)), np.nan)
    for t in range(n):
        Pinv = np.linalg.inv(P[t])
        pts = []
        for j in range(t + 1, n):
            if segs[j] != segs[t] or defect[j]:
                break
            p = (Pinv @ P[j])[:3, 3]
            pts.append(p)
            if p[0] > xq.max() + 5:
                break
        if len(pts) < 2:
            continue
        pts = np.array(pts)
        ok = np.concatenate([[True], np.diff(pts[:, 0]) > 0])
        pts = pts[ok]
        if len(pts) < 2:
            continue
        inr = (xq >= pts[0, 0]) & (xq <= pts[-1, 0])
        path[t, inr] = np.interp(xq[inr], pts[:, 0], pts[:, 1])
    lab = np.where(L["valid"][:n], L["label"][:n], np.nan)
    off = np.nanmedian(lab[:, 0] - path[:, 0])            # the sensor's lateral mount offset from the track centre
    d = lab - (path + off)
    out = {"poses": a.poses or "own ICP", "mount_offset": round(float(off), 3), "b6_defective_motions": int(defect.sum()),
           "bands": {}}
    for lo, hi in BANDS:
        c = in_band(xq, lo, hi)
        out["bands"][f"{lo}-{hi}"] = pstats(d[:, c].ravel())
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("walls", "speed", "driven"):
        p = sub.add_parser(name)
        p.add_argument("files", nargs="*")
        p.add_argument("--labels", required=True)
        p.add_argument("--out", required=True)
        p.add_argument("--intake", default="")
        p.add_argument("--poses", default="")
        p.add_argument("--b6-trust", action="store_true", help="amendment A1: stop a B6 path at a defective B6 motion")
    a = ap.parse_args()
    {"walls": cmd_walls, "speed": cmd_speed, "driven": cmd_driven}[a.cmd](a)


if __name__ == "__main__":
    main()
