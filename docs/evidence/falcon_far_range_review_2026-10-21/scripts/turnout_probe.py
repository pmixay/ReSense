#!/usr/bin/env python3
"""Reviewer's attack on the rev-2 turnout guards (A6, C3): a diverging track leaves between tight boundaries
(lateral <= 2.5 m) through an opening SHORTER than the guard's sqrt(2 R (d + 1.6)), yet physically passable.

Geometry (top view, track frame; the near model is straight): our track curves away from Xc with radius R towards
side s. On side s the boundary is either a column row (a 0.6 m column every `spacing` m: the gaps between columns are
the opening) or a dense wall with one opening [g0, g1]. Every structure point that would lie inside the train's
envelope (|y - centre(x)| < 1.6 m + 0.1 m) is removed, so the scene is physically consistent: whatever is kept, the
train passes. The other side is a dense straight wall (the boundary of the straight track), which the diverging track
moves away from. The opening length the train actually needs is printed (`needed`, from the first to the last X at
which the envelope overlaps the boundary line), next to the guard's threshold.

Fail-safe as the protocol (|far lateral - true centre| <= sigma + 0.3 m and <= 1.05 m in (join, valid]).

    turnout_probe.py --out turnout_probe.json      (RESENSE_REPO / PYTHONPATH: the checkout under test)
"""
import argparse
import json
import sys

import numpy as np

sys.path.insert(0, "/home/user/ReSense/docs/evidence/falcon_far_range_2026-10-21/scripts")
from neg_controls import check, model  # noqa: E402
from resense.config import FarRangeConfig  # noqa: E402
from resense.farline import FarAxisTracker  # noqa: E402

HALF = 1.6


def centre(X, xc, R, s):
    return s * np.where(X > xc, 0.5 * (X - xc) ** 2 / R, 0.0)


def scene(k, xc, R, s, d, kind, spacing, opening):
    rng = np.random.default_rng(k)
    pts = []
    # far side: a dense straight wall at -s * 1.9 (the train moves away from it)
    X = np.repeat(np.arange(52.0, 400.0, 1.0), 6)
    pts.append(np.stack([X, -s * 1.9 + rng.normal(0, 0.03, X.size), -1.75 + rng.uniform(1.1, 2.6, X.size)], 1))
    # near side: the boundary at s * d
    if kind == "columns":
        cs = []
        for c in np.arange(52.5, 400.0, spacing):
            Xc_ = np.repeat(c + np.array([0.0, 0.3, 0.6]), 4)
            cs.append(Xc_)
        X = np.concatenate(cs)
    else:
        X = np.repeat(np.arange(52.0, 400.0, 1.0), 6)
        X = X[~((X >= opening[0]) & (X < opening[1]))]
    Y = s * d + rng.normal(0, 0.03, X.size)
    p = np.stack([X, Y, -1.75 + rng.uniform(1.1, 2.6, X.size)], 1)
    inside = np.abs(p[:, 1] - centre(p[:, 0], xc, R, s)) < HALF + 0.1
    removed = int(inside.sum())
    pts.append(p[~inside])
    return np.concatenate(pts).astype(np.float32), removed


def needed(xc, R, d):
    """Along-track length over which the envelope overlaps the boundary line at lateral d."""
    a = np.sqrt(2 * R * max(d - HALF, 0.0))
    b = np.sqrt(2 * R * (d + HALF))
    return float(b - a), float(xc + a), float(xc + b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cfg = FarRangeConfig(enabled=True)
    print("axis_stable", cfg.axis_stable, "turnout_radius", getattr(cfg, "axis_turnout_radius", None),
          "max_boundary_lateral", getattr(cfg, "axis_max_boundary_lateral", None))
    rows = []
    for R in (200.0, 300.0):
        for d in (1.9, 2.2, 2.5):
            need, x_in, x_out = needed(0.0, R, d)
            guard = float(np.sqrt(2 * 200.0 * (d + HALF)))
            for kind, spacing in (("columns", 30.0), ("columns", 25.0), ("wall", None)):
                for xc in (110.0, 140.0):
                    for s in (1.0, -1.0):
                        opening = (xc + x_in - 0.5, xc + x_out + 0.5) if kind == "wall" else None
                        m = model()
                        tr = FarAxisTracker(cfg)
                        worst, fail, acc, valids, rem = 0.0, None, 0, [], 0
                        truth = lambda X, xc=xc, R=R, s=s: centre(X, xc, R, s)  # noqa: E731
                        for k in range(12):
                            xyz, rem = scene(k, xc, R, s, d, kind, spacing, opening)
                            far = tr.update(xyz, m, 400.0, dt=0.1)
                            if far is None:
                                continue
                            acc += 1
                            valids.append(far.valid)
                            ok, e, x = check(far, m, truth)
                            worst = max(worst, e)
                            if not ok and fail is None:
                                fail = {"frame": k, "err": round(e, 2), "at": x, "valid": far.valid, "sides": far.sides}
                        r = {"R": R, "d": d, "kind": kind, "spacing": spacing, "xc": xc, "side": s,
                             "opening_needed_m": round(need, 1), "opening_given_m": None if kind != "wall" else round(opening[1] - opening[0], 1),
                             "guard_threshold_m": round(guard, 1), "points_removed_in_envelope": rem,
                             "accepted_frames": acc, "max_valid": max(valids) if valids else None,
                             "max_err": round(worst, 2), "fail_safe": fail is None, "first_failure": fail}
                        rows.append(r)
                        print(json.dumps(r))
    json.dump(rows, open(a.out, "w"), indent=1)
    print("fail-safe", sum(r["fail_safe"] for r in rows), "/", len(rows))


if __name__ == "__main__":
    main()
