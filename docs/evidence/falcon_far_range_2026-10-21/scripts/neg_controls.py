#!/usr/bin/env python3
"""Synthetic negative controls of the far axis (PROTOCOL.md section 3), for the 19.10 axis (axis_stable off)
and the 21.10 one (on). Boundaries are synthetic tunnel walls / column rows around a known true centre line;
the near model is straight (it never sees a curve that starts beyond the join).

Fail-safe: in every frame where a far axis is returned, for X in (join, valid] (5 m grid):
|far lateral - true centre| <= sigma(X) + 0.3 m and <= 1.05 m (strict-gauge half-width). Rejecting is fine.

    neg_controls.py --out neg_controls.json
"""
import argparse
import json

import numpy as np

from resense.config import FarRangeConfig
from resense.farline import FarAxisTracker
from resense.track import TrackModel

NEAR_AV = 175.0     # the near model's trust (the upper end seen on the recording; the 19.10 one-side cap)


def model():
    m = TrackModel(floor_coef=np.array([0.0, 0.0, -1.95]), floor_range=(5.0, 90.0), center=0.0,
                   yaw=0.0, curvature=0.0, rail_offset=0.2)
    m.axis_valid = NEAR_AV
    return m


def arc(X, xc, radius):
    return np.where(X > xc, 0.5 * (X - xc) ** 2 / radius, 0.0)


def wall(fy, s, x0, x1, rng, lat=1.9, step=1.0, n=6, skip=None):
    X = np.repeat(np.arange(x0, x1, step), n).astype(float)
    if skip is not None:
        X = X[~((X >= skip[0]) & (X < skip[1]))]
    return np.stack([X, fy(X) + s * lat + rng.normal(0, 0.03, X.size), -1.75 + rng.uniform(1.1, 2.6, X.size)], 1)


def columns(fy, s, x0, x1, rng, spacing=30.0, lat=1.9, family=0.2):
    pts = []
    for n, c in enumerate(np.arange(x0, x1, spacing)):
        X = np.repeat(c + np.array([0.0, 0.3, 0.6]), 4)
        off = family if n % 2 else -family
        pts.append(np.stack([X, fy(X) + s * (lat + off) + rng.normal(0, 0.03, X.size),
                             -1.75 + rng.uniform(1.1, 2.6, X.size)], 1))
    return np.concatenate(pts) if pts else np.zeros((0, 3))


def check(far, m, truth):
    X = np.arange(55.0, far.valid + 1.0, 5.0)
    X = X[X > far.join]
    if X.size == 0:
        return True, 0.0, None
    err = np.abs(far.offset(X, m) - truth(X))
    ok = bool(np.all(err <= far.sigma(X) + 0.3) and np.all(err <= 1.05))
    return ok, float(err.max()), float(X[err.argmax()])


def run(cfg, frames, truth_of, n):
    """frames(k) -> xyz; truth_of(k) -> callable centre. Returns the case summary."""
    m = model()
    tr = FarAxisTracker(cfg)
    acc, worst, fail = 0, 0.0, None
    valids = []
    for k in range(n):
        far = tr.update(frames(k).astype(np.float32), m, 400.0, dt=0.1)
        if far is None:
            continue
        acc += 1
        valids.append(far.valid)
        ok, e, x = check(far, m, truth_of(k))
        worst = max(worst, e)
        if not ok and fail is None:
            fail = {"frame": k, "err": round(e, 2), "at": x, "valid": far.valid, "sides": far.sides,
                    "sigma": round(float(far.sigma(np.array([x]))[0]), 2)}
    return {"accepted_frames": acc, "max_err": round(worst, 2), "max_valid": max(valids) if valids else None,
            "fail_safe": fail is None, "first_failure": fail}


def cases():
    zero = lambda X: 0 * X  # noqa: E731
    out = []
    # A. the review's curves (both walls follow the track), with and without an occluded inner wall
    for occl in (False, True):
        for xc in (120.0, 160.0, 200.0, 240.0):
            for R in (300.0, 600.0, 1000.0, 3000.0):
                f = lambda X, xc=xc, R=R: arc(X, xc, R)  # noqa: E731

                def fr(k, f=f, xc=xc, occl=occl):
                    r = np.random.default_rng(k)
                    inner = wall(f, -1.0, 52, 400 if not occl else xc + 20, r)
                    return np.concatenate([wall(f, 1.0, 52, 400, r), inner])
                out.append(("A_curve", {"xc": xc, "R": R, "occluded_inner": occl}, fr, f, 12, True))
    # B. one diverging wall, the other absent or ending at 120 m
    for sl in (0.003, 0.006, 0.009):
        for other in (None, 120.0):
            def fr(k, sl=sl, other=other):
                r = np.random.default_rng(k)
                p = [wall(lambda X: sl * np.maximum(X - 50, 0), 1.0, 52, 350, r)]
                if other:
                    p.append(wall(zero, -1.0, 52, other, r))
                return np.concatenate(p)
            out.append(("B_diverging", {"slope": sl, "other_end": other}, fr, zero, 12, True))
    # C. one straight wall (station, parked train) while the track curves away from it
    for xc, R in ((100.0, 300.0), (120.0, 500.0), (150.0, 600.0)):
        f = lambda X, xc=xc, R=R: -arc(X, xc, R)  # noqa: E731
        out.append(("C_one_wall_curving_away", {"xc": xc, "R": R},
                    lambda k: wall(zero, 1.0, 52, 400, np.random.default_rng(k)), f, 12, True))
    # D. parked straight train 60-260 m at lateral 2.2, own walls to 100 m, track curves away
    for xc, R in ((110.0, 300.0), (130.0, 400.0)):
        f = lambda X, xc=xc, R=R: -arc(X, xc, R)  # noqa: E731

        def fr(k, f=f):
            r = np.random.default_rng(k)
            return np.concatenate([wall(zero, 1.0, 60, 260, r, lat=2.2), wall(f, 1.0, 52, 100, r), wall(f, -1.0, 52, 100, r)])
        out.append(("D_parked_train", {"xc": xc, "R": R}, fr, f, 12, True))
    # E. straight wall plus a second side ending early; the track curves away just after it
    for cend in (135.0, 150.0, 190.0):
        for R in (300.0, 600.0):
            f = lambda X, c=cend, R=R: -arc(X, c + 5.0, R)  # noqa: E731

            def fr(k, f=f, cend=cend):
                r = np.random.default_rng(k)
                return np.concatenate([wall(zero, 1.0, 52, 400, r), wall(f, -1.0, 52, cend, r)])
            out.append(("E_second_side_ends", {"second_end": cend, "R": R}, fr, f, 12, True))
    # F. S-curve jogs over 130-190 m (both walls follow)
    for jog in (0.25, 0.6, 1.5):
        f = lambda X, j=jog: j * np.clip((X - 130.0) / 60.0, 0, 1) ** 2 * (3 - 2 * np.clip((X - 130.0) / 60.0, 0, 1))  # noqa: E731
        out.append(("F_s_jog", {"jog": jog},
                    lambda k, f=f: np.concatenate([wall(f, 1.0, 52, 400, np.random.default_rng(k)),
                                                   wall(f, -1.0, 52, 400, np.random.default_rng(k + 50))]), f, 12, True))
    # G. a niche (no points 150-160) or a recess (1 m further out) followed by a curve R 300 from 160
    f = lambda X: arc(X, 160.0, 300.0)  # noqa: E731
    out.append(("G_niche_then_curve", {}, lambda k: np.concatenate([wall(f, 1.0, 52, 400, np.random.default_rng(k), skip=(150, 160)),
                                                                     wall(f, -1.0, 52, 400, np.random.default_rng(k + 50), skip=(150, 160))]), f, 12, True))

    def recess(k):
        r = np.random.default_rng(k)
        a = wall(f, 1.0, 52, 400, r)
        a[(a[:, 0] >= 150) & (a[:, 0] < 160), 1] += 1.0
        return np.concatenate([a, wall(f, -1.0, 52, 400, r)])
    out.append(("G_recess_then_curve", {}, recess, f, 12, True))
    # H. new: a sparse column row following the track, which curves away from / towards a straight wall
    for sign in (1.0, -1.0):
        for xc in (120.0, 160.0, 200.0, 240.0):
            for R in (300.0, 600.0, 1000.0, 3000.0):
                f = lambda X, xc=xc, R=R, sign=sign: -sign * arc(X, xc, R)  # noqa: E731
                out.append(("H_row_follows_curve", {"away": sign > 0, "xc": xc, "R": R},
                            lambda k, f=f: np.concatenate([wall(zero, 1.0, 52, 400, np.random.default_rng(k)),
                                                           columns(f, -1.0, 52.5, 400, np.random.default_rng(k + 50))]), f, 12, True))
    # I. new: the same, the row seen only in alternate frames
    for xc in (120.0, 200.0):
        for R in (300.0, 1000.0):
            f = lambda X, xc=xc, R=R: -arc(X, xc, R)  # noqa: E731

            def fr(k, f=f):
                p = [wall(zero, 1.0, 52, 400, np.random.default_rng(k))]
                if k % 2 == 0:
                    p.append(columns(f, -1.0, 52.5, 400, np.random.default_rng(k + 50)))
                return np.concatenate(p)
            out.append(("I_row_alternate_frames", {"xc": xc, "R": R}, fr, f, 20, True))
    # J. new: moving scene at 20 m/s, the curve start approaching, the row seen in 2 of 3 frames
    for R in (300.0, 600.0):
        def truth_of(k, R=R):
            return lambda X: -arc(X, 300.0 - 2.0 * k, R)

        def fr(k, R=R):
            p = [wall(lambda X: 0 * X, 1.0, 52, 400, np.random.default_rng(k))]
            if k % 3:
                p.append(columns(truth_of(k), -1.0, 52.5 - (2.0 * k) % 30.0, 400, np.random.default_rng(k + 50)))
            return np.concatenate(p)
        out.append(("J_moving_curve_approach", {"R": R}, fr, truth_of, 100, True))
    # K. reported only: a turnout leaving a straight two-wall tunnel through a 35 m gap in the left wall
    #    (bins 147.5 and 187.5 m: 40 m apart, the longest gap the support bridges)
    for R in (300.0, 600.0):
        f = lambda X, R=R: arc(X, 150.0, R)  # noqa: E731
        out.append(("K_turnout_through_gap", {"R": R, "gap": [150, 185]},
                    lambda k: np.concatenate([wall(lambda X: 0 * X, 1.0, 52, 400, np.random.default_rng(k), skip=(150, 185)),
                                              wall(lambda X: 0 * X, -1.0, 52, 400, np.random.default_rng(k + 50))]), f, 12, False))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = {}
    for label, stable in (("axis_19_10", False), ("axis_stable", True)):
        cfg = FarRangeConfig(enabled=True, axis_stable=stable)
        rows = []
        for name, params, fr, truth, n, required in cases():
            truth_of = truth if name == "J_moving_curve_approach" else (lambda k, t=truth: t)
            s = run(cfg, fr, truth_of, n)
            rows.append({"case": name, **params, "required": required, **s})
        req = [r for r in rows if r["required"]]
        res[label] = {"cases": len(rows), "required": len(req), "required_fail_safe": sum(r["fail_safe"] for r in req),
                      "failures": [r for r in rows if not r["fail_safe"]], "rows": rows}
        print(label, "required fail-safe", res[label]["required_fail_safe"], "/", len(req),
              "| failures:", [(r["case"], {k: r[k] for k in r if k in ("xc", "R", "slope", "second_end", "jog", "away")}, r["first_failure"]) for r in res[label]["failures"]])
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
