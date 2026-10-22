#!/usr/bin/env python3
"""Stage A of PROTOCOL.md: the frozen model on the held-out recordings, against the self-supervised truth.

    stage_a.py <held_dir> <out.json> [--recs A,B,...]

Reads <held_dir>/<rec>.npz (fa_extract.py) and <rec>_lab.npz (fa_labels.py), applies resense/models/far_axis_1.3.json
through resense.far_axis exactly as the detector does (profile -> features -> calibrated quantiles -> learned_axis),
and evaluates A1a-c, A2a-b, A3 per band, pooled and per recording.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../../../.."))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
from fa_train import load_extract  # noqa: E402
from resense import far_axis as fa  # noqa: E402

BANDS = [(60, 100), (100, 150), (150, 200), (200, 250)]
NAMES = {"roundT_squareT_pressureGate_squareT": "A", "roundT_doubleT": "B", "roundT_pressureGate_roundT": "C",
         "doubleT_platform": "doubleT_platform", "squareT_platform_squareT_switch": "squareT_platform"}


def inb(x, lo, hi):
    return (x >= lo) & ((x < hi) | ((hi == 250) & (x == 250)))


def pq(v):
    v = np.abs(np.asarray(v, float))
    return [round(float(np.percentile(v, 50)), 3), round(float(np.percentile(v, 90)), 3)] if v.size else None


def rows_of(held, rec, M):
    names, prof, state = load_extract([os.path.join(held, rec + ".npz")])
    L = np.load(os.path.join(held, rec + "_lab.npz"))
    xq = L["query_x"]
    out = {k: [] for k in ("x", "truth", "base", "k2", "lo", "mid", "hi", "frame")}
    rng = {"frame": [], "axis_valid": [], "to_x": [], "has60": []}
    for t in range(len(names)):
        st = state[t]
        la, Q = fa.learned_axis(M, prof[t], st, 40.0, 0.5, 250.0)
        b = fa.base_y(st, xq)
        k2 = b + fa.curve_offset(st, xq)
        v = L["valid"][t]
        rng["frame"].append(t); rng["axis_valid"].append(min(st["axis_valid"], 250.0)); rng["to_x"].append(la.to_x)
        rng["has60"].append(bool(v[xq >= 60].any()))
        for i in np.flatnonzero(v):
            out["x"].append(xq[i]); out["truth"].append(L["label"][t, i]); out["base"].append(b[i]); out["k2"].append(k2[i])
            out["lo"].append(b[i] + Q[i, 0]); out["mid"].append(b[i] + Q[i, 1]); out["hi"].append(b[i] + Q[i, 2])
            out["frame"].append(t)
    return {k: np.array(v) for k, v in out.items()}, {k: np.array(v) for k, v in rng.items()}


def band_table(R):
    tab = {}
    for lo, hi in BANDS:
        m = inb(R["x"], lo, hi)
        if not m.any():
            tab[f"{lo}-{hi}"] = {"n": 0}
            continue
        tr = R["truth"][m]
        inside = (tr >= R["lo"][m]) & (tr <= R["hi"][m])
        tab[f"{lo}-{hi}"] = {"n": int(m.sum()), "frames": int(np.unique(R["frame"][m]).size),
                             "model": pq(R["mid"][m] - tr), "k2": pq(R["k2"][m] - tr), "base": pq(R["base"][m] - tr),
                             "coverage": round(float(inside.mean()), 3),
                             "band_p50": round(float(np.median(R["hi"][m] - R["lo"][m])), 3)}
    return tab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("held")
    ap.add_argument("out")
    ap.add_argument("--recs", default=",".join(NAMES))
    ap.add_argument("--model", default=os.path.join(ROOT, "resense/models/far_axis_1.3.json"))
    a = ap.parse_args()
    M = fa.FarAxisModel.load(a.model)
    per, rngs, pooled = {}, {}, None
    for rec in a.recs.split(","):
        R, G = rows_of(a.held, rec, M)
        per[NAMES.get(rec, rec)] = R
        rngs[NAMES.get(rec, rec)] = G
    pooled = {k: np.concatenate([R[k] for R in per.values()]) for k in per[next(iter(per))]}
    res = {"model": a.model, "pooled": band_table(pooled), "per_recording": {k: band_table(R) for k, R in per.items()}}
    # criteria
    P = res["pooled"]
    A1a = all(v["model"][1] <= v["k2"][1] and v["model"][0] <= v["k2"][0] + 0.05 for v in P.values() if v["n"] >= 100)
    A1b = any(v["model"][1] <= 0.8 * v["k2"][1] for v in P.values() if v["n"] >= 100)
    A1c = all(v["model"][1] <= v["k2"][1] + 0.10 for r in ("B", "C") if r in res["per_recording"]
              for v in res["per_recording"][r].values() if v["n"] >= 50)
    A2a = all(v["coverage"] >= 0.85 for v in P.values() if v["n"] >= 100)
    band = pooled["hi"] - pooled["lo"]
    trusted = (band <= 0.5) & (pooled["x"] > 40)
    err = np.abs(pooled["mid"] - pooled["truth"])
    A2b_share = float((err[trusted] <= 0.35).mean()) if trusted.any() else None
    A2b = trusted.any() and A2b_share >= 0.99 and not (err[trusted] > 1.05).any()
    trusted_tab = {}
    for lo, hi in [(40, 60)] + BANDS:
        m = trusted & inb(pooled["x"], lo, hi)
        trusted_tab[f"{lo}-{hi}"] = {"rows": int(m.sum()), "of": int(inb(pooled["x"], lo, hi).sum()),
                                     "err_p90_max": [round(float(np.percentile(err[m], 90)), 3), round(float(err[m].max()), 3)] if m.any() else None}
    A3 = {}
    for r in ("B", "C"):
        if r in rngs:
            G = rngs[r]
            sel = G["has60"]
            gain = np.maximum(G["axis_valid"], G["to_x"]) - G["axis_valid"]
            A3[r] = {"frames": int(sel.sum()), "median_gain_m": round(float(np.median(gain[sel])), 1),
                     "frames_with_gain": int((gain[sel] > 0).sum()), "max_gain_m": round(float(gain[sel].max()), 1),
                     "median_axis_valid": round(float(np.median(G["axis_valid"][sel])), 1)}
    A3ok = all(v["median_gain_m"] >= 10.0 for v in A3.values()) and len(A3) == 2
    ext = {}
    for r, G in rngs.items():
        gain = np.maximum(G["axis_valid"], G["to_x"]) - G["axis_valid"]
        ext[r] = {"frames": int(len(gain)), "frames_extended": int((gain > 0).sum()),
                  "to_x_p50_where_trusted": round(float(np.median(G["to_x"][G["to_x"] > 0])), 1) if (G["to_x"] > 0).any() else 0.0}
    res["criteria"] = {"A1a": bool(A1a), "A1b": bool(A1b), "A1c": bool(A1c), "A2a": bool(A2a),
                       "A2b": bool(A2b), "A2b_share_within_0.35": A2b_share, "A3": bool(A3ok)}
    res["trusted_rows"] = trusted_tab
    res["A3"] = A3
    res["trust_extension"] = ext
    res["stage_A_pass"] = all(res["criteria"][k] for k in ("A1a", "A1b", "A1c", "A2a", "A2b", "A3"))
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("pooled", "criteria", "trusted_rows", "A3", "trust_extension", "stage_A_pass")},
                     indent=1))
    for r, t in res["per_recording"].items():
        print(r, json.dumps(t))


if __name__ == "__main__":
    main()
