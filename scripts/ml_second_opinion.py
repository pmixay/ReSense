#!/usr/bin/env python3
"""Learned second opinion on the geometric candidates (experiment, v0.6).

Trains a gradient-boosted classifier on ``scripts/ml_dataset.py`` output (cluster descriptors;
positives = objects ray-cast into the moving real ride, negatives = every gauge candidate on the
obstacle-free recordings) and reports how many negative candidates it would remove at a fixed
recall of the positive ones - on data it did not see: the **last 40 % of the ride** (time split)
and **other background sequences** for the positives.

    python scripts/ml_second_opinion.py out/ml/dataset.npz --out out/ml/report.json
"""
from __future__ import annotations

import argparse
import json

import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score
    z = np.load(a.dataset, allow_pickle=False)
    feats = [str(f) for f in z["features"]]
    Xn, gn, Xp, gp, kp, dp = z["X_neg"], z["g_neg"], z["X_pos"], z["g_pos"], z["k_pos"], z["d_pos"]
    ride = gn[gn >= 0]
    t_split = np.quantile(ride, 0.6) if ride.size else 0.0
    n_tr = (gn < 0) | (gn <= t_split)                 # the five bags + the first 60 % of the ride
    seqs = np.unique(gp)
    p_tr = np.isin(gp, seqs[: len(seqs) // 2])        # the first half of the background sequences
    X_tr = np.concatenate([Xn[n_tr], Xp[p_tr]])
    y_tr = np.concatenate([np.zeros(n_tr.sum()), np.ones(p_tr.sum())])
    X_te = np.concatenate([Xn[~n_tr], Xp[~p_tr]])
    y_te = np.concatenate([np.zeros((~n_tr).sum()), np.ones((~p_tr).sum())])
    w = np.where(y_tr == 1, 0.5 / max(y_tr.mean(), 1e-9), 0.5 / max(1 - y_tr.mean(), 1e-9))
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                         l2_regularization=1.0, random_state=0)
    clf.fit(X_tr, y_tr, sample_weight=w)
    p = clf.predict_proba(X_te)[:, 1]
    auc = roc_auc_score(y_te, p)
    out = {"features": feats, "train": {"neg": int(n_tr.sum()), "pos": int(p_tr.sum())},
           "test": {"neg": int((~n_tr).sum()), "pos": int((~p_tr).sum())}, "auc": round(float(auc), 4), "at_recall": {}}
    pp, pn = p[y_te == 1], p[y_te == 0]
    for rec in (0.99, 0.97, 0.95, 0.90):
        thr = float(np.quantile(pp, 1 - rec))
        out["at_recall"][str(rec)] = {"threshold": round(thr, 4), "negatives_removed": round(float((pn < thr).mean()), 3)}
    # which positives does it lose at 97 %: by kind and range
    thr = out["at_recall"]["0.97"]["threshold"]
    kt, dt_ = kp[~p_tr], dp[~p_tr]
    lost = {}
    for k in np.unique(kt):
        m = kt == k
        lost[str(k)] = {"kept": round(float((pp[m] >= thr).mean()), 3), "n": int(m.sum())}
    out["kept_by_kind_at_0.97"] = lost
    bins = [(0, 50), (50, 100), (100, 150), (150, 250)]
    out["kept_by_range_at_0.97"] = {f"{lo}-{hi}": round(float((pp[(dt_ >= lo) & (dt_ < hi)] >= thr).mean()), 3)
                                    if ((dt_ >= lo) & (dt_ < hi)).any() else None for lo, hi in bins}
    print(json.dumps(out, indent=1))
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
