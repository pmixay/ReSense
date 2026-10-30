#!/usr/bin/env python3
"""Train / cross-validate / export the learned far axis (resense/far_axis.py).

    fa_train.py dataset <extract.npz ...> --labels <labels.npz> --out rows.npz [--pieces 8]
    fa_train.py cv rows.npz --out cv.json [--oof oof.npz]
    fa_train.py fit rows.npz --out model.json --report report.json
    fa_train.py apply model.json <extract.npz ...> --labels <labels.npz> --out eval.npz   (held-out lines)

Rows: one per (frame, query distance) with a valid label; target = label - base model lateral (the residual the
model predicts). ``piece`` = the gate's ride piece (np.array_split of the ride into 8): grouped cross-validation
holds out one piece at a time and purges every training row whose label reaches into the held-out piece (its chain
of later frames crosses the boundary), so no stretch of track is on both sides.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, ROOT)
from resense import far_axis as fa  # noqa: E402

QUANTILES = (0.05, 0.5, 0.95)
PARAMS = dict(max_iter=400, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=80, l2_regularization=1.0,
              random_state=0)
BANDS = [(40, 60), (60, 100), (100, 150), (150, 200), (200, 250)]


def load_extract(files):
    D = [np.load(f) for f in files]
    names, prof, state = [], [], []
    seen = set()
    for d in D:
        dn, ds = d["names"], d["state"]                         # an NpzFile decompresses on every access: once
        dp = list(zip(d["prof_side"], d["prof_vault"], d["prof_bed"]))
        for k, n in enumerate(dn):
            if str(n) in seen:                   # the 1-frame overlap of consecutive pieces: keep the earlier one
                continue
            seen.add(str(n))
            names.append(str(n))
            prof.append(dp[k])
            state.append(json.loads(str(ds[k])))
    return names, prof, state


def rows_for(names, prof, state, L, piece_of=None):
    lab, valid, chain = L["label"], L["valid"], L["chain"]
    lnames = [str(n) for n in L["names"]]
    xq = L["query_x"]
    assert lnames == names, "labels and extraction differ in frames"
    F, y, base, k2, far, meta = [], [], [], [], [], []
    for t in range(len(names)):
        if not valid[t].any():
            continue
        Ft = fa.query_features(prof[t], state[t], xq)
        b = fa.base_y(state[t], xq)
        c = b + fa.curve_offset(state[t], xq)
        f = b + fa.far_offset(state[t], xq)
        for i in np.flatnonzero(valid[t]):
            F.append(Ft[i]); y.append(lab[t, i] - b[i]); base.append(b[i]); k2.append(c[i]); far.append(f[i])
            meta.append((t, i, chain[t, i], -1 if piece_of is None else piece_of[t]))
    meta = np.array(meta, dtype=np.int64).reshape(-1, 4)
    return dict(F=np.array(F), y=np.array(y), base=np.array(base), k2=np.array(k2), far=np.array(far),
                frame=meta[:, 0], qi=meta[:, 1], chain=meta[:, 2], piece=meta[:, 3], x=xq[meta[:, 1]],
                label=np.array(y) + np.array(base))


def cmd_dataset(a):
    names, prof, state = load_extract(a.files)
    L = np.load(a.labels)
    n = len(names)
    piece_of = np.zeros(n, dtype=np.int64)
    for k, idx in enumerate(np.array_split(np.arange(n), a.pieces)):
        piece_of[idx] = k
    R = rows_for(names, prof, state, L, piece_of)
    np.savez_compressed(a.out, **R, features=np.array(fa.FEATURES), names=np.array(names))
    print(a.out, len(R["y"]), "rows from", len(set(R["frame"].tolist())), "frames")


def fit_q(F, y, q, params=PARAMS):
    from sklearn.ensemble import HistGradientBoostingRegressor
    m = HistGradientBoostingRegressor(loss="quantile", quantile=q, **params)
    m.fit(F, y)
    return m


def band_of(x):
    for lo, hi in BANDS:
        if lo <= x < hi or (hi == 250 and x == 250):
            return f"{lo}-{hi}"
    return None


def report(R, pred, label="model", ref="base"):
    """Axis lateral error p50 / p90 per band for the model (``ref`` axis + predicted residual) against the base and
    the K2 published axes, and the calibration of the band [lo, hi] (share of truth inside)."""
    out = {}
    truth = R["label"]
    refv = R[ref]
    for lo, hi in BANDS:
        m = (R["x"] >= lo) & ((R["x"] < hi) | ((hi == 250) & (R["x"] == 250)))
        if not m.any():
            continue
        e_m = np.abs(refv[m] + pred[m, 1] - truth[m])
        e_b = np.abs(R["base"][m] - truth[m])
        e_k = np.abs(R["k2"][m] - truth[m])
        e_f = np.abs(R["far"][m] - truth[m])
        inside = (truth[m] >= refv[m] + pred[m, 0]) & (truth[m] <= refv[m] + pred[m, 2])
        width = pred[m, 2] - pred[m, 0]
        out[f"{lo}-{hi}"] = {
            "n": int(m.sum()), "frames": int(len(set(R["frame"][m].tolist()))),
            label: [round(float(np.percentile(e_m, 50)), 3), round(float(np.percentile(e_m, 90)), 3)],
            "base": [round(float(np.percentile(e_b, 50)), 3), round(float(np.percentile(e_b, 90)), 3)],
            "k2_published": [round(float(np.percentile(e_k, 50)), 3), round(float(np.percentile(e_k, 90)), 3)],
            "far_line": [round(float(np.percentile(e_f, 50)), 3), round(float(np.percentile(e_f, 90)), 3)],
            "coverage": round(float(inside.mean()), 3),
            "band_width_p50": round(float(np.median(width)), 3),
            "share_band_le_0.5": round(float((width <= 0.5).mean()), 3),
            "coverage_band_le_0.5": round(float(inside[width <= 0.5].mean()), 3) if (width <= 0.5).any() else None,
        }
    return out


def conformal_margins(R, pred, xq, rows=None, level=0.9):
    """Split-conformal margins per query distance: the ``level`` quantile of max(lo - y, y - hi) over the given rows
    (pooled with the neighbouring query distances for stability); the calibrated band is [lo - m, hi + m]."""
    rows = np.ones(len(R["y"]), bool) if rows is None else rows
    E = np.maximum(pred[:, 0] - R["t"], R["t"] - pred[:, 2])
    m = np.zeros(len(xq))
    for i, x in enumerate(xq):
        sel = rows & (np.abs(R["x"] - x) <= 10.0)
        m[i] = float(np.quantile(E[sel], level)) if sel.sum() >= 50 else np.nan
    m = np.maximum(np.nan_to_num(m, nan=np.nanmax(m)), 0.0)
    return np.maximum.accumulate(m)          # never narrower farther out


def cmd_cv(a):
    R = dict(np.load(a.rows))
    R["t"] = R["label"] - R[a.ref]
    pieces = np.unique(R["piece"])
    oof = np.full((len(R["y"]), 3), np.nan)
    t0 = time.time()
    for p in pieces:
        test = R["piece"] == p
        # purge: training rows of other pieces whose label chain reaches into piece p (frames are contiguous)
        fr = R["frame"]
        pf = fr[test]
        lo, hi = pf.min(), pf.max()
        reach = fr + R["chain"]
        test_reach = int(reach[test].max())
        # ... and the frames after it whose own stretch of track the held-out labels already cover
        train = ~test & ~((fr < lo) & (reach >= lo)) & ~((fr > hi) & (fr <= test_reach))
        for j, q in enumerate(QUANTILES):
            m = fit_q(R["F"][train], R["t"][train], q)
            oof[test, j] = m.predict(R["F"][test])
        print("piece", p, int(test.sum()), "test rows,", int(train.sum()), "train,", round(time.time() - t0), "s",
              flush=True)
    oof = np.sort(oof, axis=1)
    xq = fa.QUERY_X
    # conformal margins for each piece from the OTHER pieces' out-of-fold residuals (honest coverage)
    cal = oof.copy()
    for p in pieces:
        test = R["piece"] == p
        mp = conformal_margins(R, oof, xq, rows=~test)
        mi = mp[np.searchsorted(xq, R["x"][test])]
        cal[test, 0] -= mi
        cal[test, 2] += mi
    margins = conformal_margins(R, oof, xq)
    sub = lambda m: {k: (v[m] if np.ndim(v) and len(v) == len(R["y"]) else v) for k, v in R.items()}  # noqa: E731
    rep = {"ref": a.ref, "overall": report(R, oof, ref=a.ref), "calibrated": report(R, cal, ref=a.ref),
           "margins": dict(zip(xq.astype(int).tolist(), np.round(margins, 3).tolist())),
           "per_piece_calibrated": {int(p): report(sub(R["piece"] == p), cal[R["piece"] == p], ref=a.ref)
                                    for p in pieces}}
    j = fa.FEATURES.index("f_quad")
    fq = np.where(np.isfinite(R["F"][:, j]), R["F"][:, j], 0.0)
    rep["follower_quad_only"] = report(R, np.stack([fq, fq, fq], 1), "follower")
    json.dump(rep, open(a.out, "w"), indent=1)
    if a.oof:
        np.savez_compressed(a.oof, oof=oof, cal=cal, margins=margins)
    for b, v in rep["overall"].items():
        print("raw ", b, v)
    for b, v in rep["calibrated"].items():
        print("cal ", b, {k: v[k] for k in ("model", "k2_published", "coverage", "band_width_p50", "share_band_le_0.5",
                                            "coverage_band_le_0.5")})
    for b, v in rep["follower_quad_only"].items():
        print("fol ", b, v["follower"])


def export(models, features, quantiles, xq):
    spec = {"features": list(features), "quantiles": list(quantiles), "query_x": [float(x) for x in xq], "models": []}
    for m in models:
        trees = []
        for pred in m._predictors:
            nodes = pred[0].nodes
            trees.append({"feature": nodes["feature_idx"].astype(int).tolist(),
                          "threshold": [float(v) for v in nodes["num_threshold"]],
                          "left": [int(l) if not leaf else -1 for l, leaf in zip(nodes["left"], nodes["is_leaf"])],
                          "right": [int(r) if not leaf else -1 for r, leaf in zip(nodes["right"], nodes["is_leaf"])],
                          "value": [float(v) for v in nodes["value"]],
                          "missing_left": [int(v) for v in nodes["missing_go_to_left"]]})
        spec["models"].append({"baseline": float(np.ravel(m._baseline_prediction)[0]), "trees": trees})
    return spec


def cmd_fit(a):
    R = dict(np.load(a.rows))
    t0 = time.time()
    models = [fit_q(R["F"], R["y"], q) for q in QUANTILES]
    spec = export(models, fa.FEATURES, QUANTILES, fa.QUERY_X)
    cv = json.load(open(a.cv))
    assert cv["ref"] == "base"
    spec["margin"] = [float(cv["margins"][str(int(x))]) for x in fa.QUERY_X]
    json.dump(spec, open(a.out, "w"), separators=(",", ":"))
    # the numpy evaluator must equal scikit-learn
    M = fa.FarAxisModel(spec)
    sk = np.stack([m.predict(R["F"]) for m in models], 1)
    npy = M.predict_raw(R["F"])
    rep = {"rows": int(len(R["y"])), "frames": int(len(set(R["frame"].tolist()))), "quantiles": QUANTILES,
           "params": PARAMS, "features": fa.FEATURES, "fit_s": round(time.time() - t0, 1),
           "export_max_abs_diff": float(np.max(np.abs(np.sort(sk, axis=1) - npy))),
           "margins_from": a.cv, "margin": spec["margin"], "cv": cv,
           "trees": [len(m._predictors) for m in models], "file_bytes": os.path.getsize(a.out),
           "in_sample": report(R, M.predict(R["F"]))}
    try:
        from sklearn.inspection import permutation_importance  # noqa: F401
    except Exception:
        pass
    json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != "in_sample"}))


def cmd_apply(a):
    names, prof, state = load_extract(a.files)
    L = np.load(a.labels)
    R = rows_for(names, prof, state, L)
    M = fa.FarAxisModel.load(a.model)
    pred = M.predict(R["F"])
    np.savez_compressed(a.out, pred=pred, **R)
    rep = report(R, pred)
    json.dump(rep, open(a.out.replace(".npz", ".json"), "w"), indent=1)
    for b, v in rep.items():
        print(b, v)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("dataset"); p.add_argument("files", nargs="+"); p.add_argument("--labels", required=True)
    p.add_argument("--out", required=True); p.add_argument("--pieces", type=int, default=8)
    p = sub.add_parser("cv"); p.add_argument("rows"); p.add_argument("--out", required=True); p.add_argument("--oof", default="")
    p.add_argument("--ref", default="base", choices=["base", "k2"])
    p = sub.add_parser("fit"); p.add_argument("rows"); p.add_argument("--out", required=True); p.add_argument("--report", required=True)
    p.add_argument("--cv", required=True, help="the cv json (ref base) whose conformal margins the model carries")
    p = sub.add_parser("apply"); p.add_argument("model"); p.add_argument("files", nargs="+")
    p.add_argument("--labels", required=True); p.add_argument("--out", required=True)
    a = ap.parse_args()
    {"dataset": cmd_dataset, "cv": cmd_cv, "fit": cmd_fit, "apply": cmd_apply}[a.cmd](a)


if __name__ == "__main__":
    main()
