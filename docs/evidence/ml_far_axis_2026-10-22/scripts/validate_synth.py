#!/usr/bin/env python3
"""Known-answer check of the label pipeline on the ray-cast scenes (raycast_scenes.py + fa_extract.py):
labels built from the scenes' near-field rail midpoints and (a) the exact poses, (b) the exact frame-to-frame
motions with per-frame yaw noise / bias added, against the exact centreline of each frame.

    validate_synth.py <synth_dir> <out.json> [--scenes ...] [--noise 0,0 1e-4,0 3e-4,0 1e-4,2e-5]

Also reports the near-rail extractor alone (midpoints of each frame vs the exact centreline at the same X), and
the detector's own axes (base, K2 published) against the same truth, as a first look at the error to be removed.
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
from fa_labels import build_labels, poses_from_truth  # noqa: E402
from raycast_scenes import centreline, truth_y  # noqa: E402
from resense.far_axis import QUERY_X, base_y, curve_offset  # noqa: E402

BANDS = [(40, 60), (60, 100), (100, 150), (150, 200), (200, 250)]


def band_stats(err, valid, xq=QUERY_X):
    out = {}
    for lo, hi in BANDS:
        c = (xq >= lo) & (xq <= hi) if hi == 250 else (xq >= lo) & (xq < hi)
        e = np.abs(err[:, c][valid[:, c] & np.isfinite(err[:, c])])
        out[f"{lo}-{hi}"] = ({"n": int(e.size), "p50": round(float(np.percentile(e, 50)), 3),
                             "p90": round(float(np.percentile(e, 90)), 3), "max": round(float(e.max()), 3)}
                            if e.size else {"n": 0})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("synth")
    ap.add_argument("out")
    ap.add_argument("--scenes", default="straight,r300,r500,l700,r1000,entry400,scurve400,scurve700,exit500")
    ap.add_argument("--noise", nargs="*", default=["0,0", "1e-4,0", "3e-4,0", "0,2e-5", "1e-4,2e-5"])
    a = ap.parse_args()
    res = {}
    for sc in a.scenes.split(","):
        D = np.load(os.path.join(a.synth, sc + ".npz"))
        truth = json.load(open(os.path.join(a.synth, sc, "truth.json")))
        # (n, 261) centreline at X = 0..260, recomputed from the scene definition (NaN where unreachable)
        n = len(truth["frames"])
        s_, x_, y_, psi_, _ = centreline(sc, n * 1.1 + 280.0)
        Y = []
        for f in truth["frames"]:
            X0, Y0, h = f["pose"]
            m = (s_ >= f["s"] - 5) & (s_ <= f["s"] + 280)
            dx, dy = x_[m] - X0, y_[m] - Y0
            Y.append(truth_y(np.cos(h) * dx + np.sin(h) * dy, -np.sin(h) * dx + np.cos(h) * dy, np.arange(261.0)))
        Y = np.array(Y)
        ytrue = Y[:, QUERY_X.astype(int)]
        rails = list(D["rails"])
        # the near-rail extractor alone
        ex = []
        for k, r in enumerate(rails):
            r = r[np.isfinite(r[:, 0])]
            if len(r):
                ex.append(r[:, 1] - np.interp(r[:, 0], np.arange(261.0), Y[k]))  # rails are within 34 m: always reachable
        ex = np.abs(np.concatenate(ex)) if ex else np.zeros(0)
        st = [json.loads(s) for s in D["state"]]
        base = np.array([base_y(s, QUERY_X) for s in st])
        pub = base + np.array([curve_offset(s, QUERY_X) for s in st])
        r = {"rails_per_frame": round(float(np.mean([np.isfinite(x[:, 0]).sum() for x in rails])), 2),
             "rail_mid_err": {"n": int(ex.size), "p50": round(float(np.median(ex)), 3),
                              "p90": round(float(np.percentile(ex, 90)), 3), "max": round(float(ex.max()), 3)},
             "labels": {}}
        for nz in a.noise:
            sd, bias = (float(v) for v in nz.split(","))
            P, segs = poses_from_truth(truth, sd, bias)
            lab, cnt, spr, chain, rep, valid = build_labels(P, segs, rails, np.zeros(len(P), bool))
            r["labels"][nz] = {"valid_share": round(float(valid.mean()), 3), **band_stats(lab - ytrue, valid)}
            if nz == "0,0":
                anyl = np.isfinite(lab)
                r["detector_base"] = band_stats(base - ytrue, anyl)
                r["detector_k2_published"] = band_stats(pub - ytrue, anyl)
                np.savez_compressed(os.path.join(a.synth, sc + "_lab.npz"), label=lab, valid=valid, truth=ytrue,
                                    base=base, pub=pub)
        res[sc] = r
        print(sc, json.dumps(r["rail_mid_err"]), json.dumps(r["labels"]["0,0"]), flush=True)
    json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
