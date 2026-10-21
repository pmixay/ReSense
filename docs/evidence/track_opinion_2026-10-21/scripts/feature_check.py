#!/usr/bin/env python3
"""PROTOCOL §2 step 2: do the synthetic positives look like real objects, feature by feature?

For every real positive row (STOP-candidate rows of a labelled real object: ``doubleT_obstacle`` labels,
the Falcon person) and every feature: is the real value inside the [2.5 %, 97.5 %] range of the synthetic
positive STOP-candidate rows of the same kind family within +-10 m of its distance? A feature fails when
fewer than 80 % of the rows of a real set are inside.

    feature_check.py --syn p1.npz p2.npz ... --real dto=test_dto.npz:person,railobj \\
        --real falcon=falcon_rows.npz:person,hivis --out check.json
"""
import argparse
import json

import numpy as np


def load(paths):
    X, P, M = [], [], []
    for p in paths:
        z = np.load(p)
        X.append(z["X"])
        P.append(z["piece"].astype(str))
        M.append(z["M"])
        feats = [str(f) for f in z["features"]]
    return np.concatenate(X), np.concatenate(P), np.concatenate(M), feats


def kind_of(piece):
    k = piece.split(":")[2]
    for tag in ("_far", "_st", "_tw", "_aw", "_cx", "_cross"):
        k = k.replace(tag, "")
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--syn", nargs="+", required=True)
    ap.add_argument("--real", action="append", required=True, help="name=path:kind,kind")
    ap.add_argument("--band", type=float, default=10.0)
    ap.add_argument("--min-share", type=float, default=0.8)
    ap.add_argument("--min-syn", type=int, default=30, help="synthetic rows needed in a band to judge a real row")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Xs, Ps, Ms, feats = load(a.syn)
    sel = (Ms[:, 6] == 1) & (Ms[:, 2] > 0)
    Xs, Ps, Ms = Xs[sel], Ps[sel], Ms[sel]
    ks = np.array([kind_of(p) for p in Ps])
    out = {"features": feats, "real": {}, "fail": []}
    for spec in a.real:
        name, rest = spec.split("=", 1)
        path, kinds = rest.split(":")
        Xr, _, Mr, _ = load([path])
        r = (Mr[:, 6] == 1) & (Mr[:, 2] > 0)
        Xr, Mr = Xr[r], Mr[r]
        fam = np.isin(ks, kinds.split(","))
        res = {"rows": int(len(Xr)), "dist_range": [float(Mr[:, 4].min()), float(Mr[:, 4].max())] if len(Xr) else None,
               "kinds": kinds, "per_feature": {}}
        for j, f in enumerate(feats):
            inside, judged = 0, 0
            for x, d in zip(Xr[:, j], Mr[:, 4]):
                b = fam & (np.abs(Ms[:, 4] - d) <= a.band)
                if b.sum() < a.min_syn:
                    continue
                lo, hi = np.quantile(Xs[b, j], [0.025, 0.975])
                judged += 1
                inside += int(lo - 1e-9 <= x <= hi + 1e-9)
            share = inside / judged if judged else None
            res["per_feature"][f] = {"judged": judged, "share_inside": None if share is None else round(share, 3),
                                     "real_median": round(float(np.median(Xr[:, j])), 4) if len(Xr) else None,
                                     "syn_median_family": round(float(np.median(Xs[fam, j])), 4) if fam.any() else None}
            if share is not None and share < a.min_share:
                out["fail"].append([name, f, round(share, 3)])
        out["real"][name] = res
    out["fail_features"] = sorted({f for _, f, _ in out["fail"]})
    json.dump(out, open(a.out, "w"), indent=1)
    for name, res in out["real"].items():
        print(name, res["rows"], res["dist_range"])
        for f, v in res["per_feature"].items():
            print(f"  {f:14s} judged {v['judged']:4d} inside {v['share_inside']}  real {v['real_median']}  syn {v['syn_median_family']}")
    print("FAIL:", out["fail_features"])


if __name__ == "__main__":
    main()
