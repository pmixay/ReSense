#!/usr/bin/env python3
"""Reviewer's far-axis probes (FarAxisTracker alone, synthetic boundaries; scenes the author did not use).

Uses the author's helpers (wall, columns, check, model) from neg_controls.py so that the positive control is the
author's own result: the author's case J (curve approaching at 20 m/s) must come out fail-safe here too.

Fail-safe as the author's protocol section 3: in every frame where a far axis is returned, for X in (join, valid]:
|far lateral - true centre| <= sigma(X) + 0.3 and <= 1.05 m. Extra columns: the largest error, and the
largest error relative to the object test (a 0.5 m wide object on the true centre leaves the shrunk strict gauge
when err - 0.25 > 1.05 - sigma(X)).

    tracker_probe.py --out probes.json
"""
import argparse
import json
import sys

import numpy as np

sys.path.insert(0, "/home/user/ReSense/docs/evidence/falcon_far_range_2026-10-21/scripts")
from neg_controls import arc, check, columns, model, wall  # noqa: E402
from resense.config import FarRangeConfig  # noqa: E402
from resense.farline import FarAxisTracker  # noqa: E402


def run(cfg, frames, truth_of, n, dt=0.1):
    m = model()
    tr = FarAxisTracker(cfg)
    acc, worst, fail, lost_obj, valids = 0, 0.0, None, None, []
    for k in range(n):
        far = tr.update(frames(k).astype(np.float32), m, 400.0, dt=dt)
        if far is None:
            continue
        acc += 1
        valids.append(far.valid)
        truth = truth_of(k)
        ok, e, x = check(far, m, truth)
        worst = max(worst, e)
        X = np.arange(55.0, far.valid + 1.0, 5.0)
        if X.size:
            err = np.abs(far.offset(X, m) - truth(X))
            bad = err - 0.25 > 1.05 - far.sigma(X)
            if bad.any() and lost_obj is None:
                lost_obj = {"frame": k, "X": float(X[bad][0]), "err": round(float(err[bad][0]), 2),
                            "sigma": round(float(far.sigma(X[bad][:1])[0]), 2), "valid": far.valid}
        if not ok and fail is None:
            fail = {"frame": k, "err": round(e, 2), "at": x, "valid": far.valid, "sides": far.sides,
                    "sigma": round(float(far.sigma(np.array([x]))[0]), 2)}
    return {"accepted_frames": acc, "max_err": round(worst, 2), "max_valid": max(valids) if valids else None,
            "fail_safe": fail is None, "first_failure": fail, "object_lost": lost_obj}


def cases():
    out = []
    zero = lambda X: 0 * X  # noqa: E731
    # P0 positive control: the author's case J (20 m/s, row in 2 of 3 frames, R 300)
    for R in (300.0, 600.0):
        def truth_of(k, R=R):
            return lambda X: -arc(X, 300.0 - 2.0 * k, R)

        def fr(k, R=R):
            p = [wall(lambda X: 0 * X, 1.0, 52, 400, np.random.default_rng(k))]
            if k % 3:
                p.append(columns(truth_of(k), -1.0, 52.5 - (2.0 * k) % 30.0, 400, np.random.default_rng(k + 50)))
            return np.concatenate(p)
        out.append(("P0_author_J", {"R": R}, fr, truth_of, 100, 0.1))
    # V: true speed v (the history assumes 25 m/s). Both sides follow a curve whose start approaches at v; the primary
    # wall has a 55 m gap (as on the recording, 195-250 m relative) that moves with the scene, the curve starts in it.
    for v in (0.0, 10.0, 25.0, 30.0, 40.0):
        for R in (300.0, 1000.0):
            for start in (230.0, 175.0):
                def truth_of(k, v=v, R=R, start=start):
                    return lambda X: arc(X, start - v * 0.1 * k, R)

                def fr(k, v=v, R=R, start=start):
                    s = v * 0.1 * k
                    f = truth_of(k)
                    gap = (start - 35.0 - s, start + 20.0 - s)
                    return np.concatenate([wall(f, 1.0, 52, 400, np.random.default_rng(k), skip=gap),
                                           columns(f, -1.0, 52.5 + (-s) % 30.0, 400, np.random.default_rng(k + 50))])
                n = 60 if v == 0 else min(60, int((start - 70.0) / (v * 0.1)))
                out.append(("V_speed_curve_in_gap", {"v": v, "R": R, "curve_start0": start, "frames": n}, fr, truth_of, n, 0.1))
    # V2: the same with dt = 0.2 s per frame (a 5 Hz input or every other frame dropped), v 25 / 30 m/s
    for v in (25.0, 30.0):
        for R in (300.0,):
            def truth_of(k, v=v, R=R):
                return lambda X: arc(X, 230.0 - v * 0.2 * k, R)

            def fr(k, v=v, R=R):
                s = v * 0.2 * k
                f = truth_of(k)
                return np.concatenate([wall(f, 1.0, 52, 400, np.random.default_rng(k), skip=(195 - s, 250 - s)),
                                       columns(f, -1.0, 52.5 + (-s) % 30.0, 400, np.random.default_rng(k + 50))])
            out.append(("V2_speed_dt0.2", {"v": v, "R": R}, fr, truth_of, int(160.0 / (v * 0.2)), 0.2))
    # S: a skewed structure pair: wall and column row both diverge from a straight track at slope s from 50 m
    # (a straight structure beside a track with a small angle; the kink limit with two sides is 0.01)
    for s in (0.003, 0.006, 0.009):
        f = lambda X, s=s: s * np.maximum(X - 50.0, 0.0)  # noqa: E731
        out.append(("S_skewed_pair", {"slope": s},
                    lambda k, f=f: np.concatenate([wall(f, 1.0, 52, 400, np.random.default_rng(k)),
                                                   columns(f, -1.0, 52.5, 400, np.random.default_rng(k + 50))]),
                    zero, 12, 0.1))
    # W: wide straight structures (lateral 3.5 m, inside the 1.2-4.0 m band) on both sides, the track curves between
    # them (physically possible while the curve departs < ~1.6 m)
    for xc in (100.0, 130.0, 160.0):
        for R in (600.0, 1000.0, 3000.0):
            f = lambda X, xc=xc, R=R: arc(X, xc, R)  # noqa: E731
            out.append(("W_wide_straight_sides_track_curves", {"xc": xc, "R": R},
                        lambda k: np.concatenate([wall(zero, 1.0, 52, 400, np.random.default_rng(k), lat=3.5),
                                                  columns(zero, -1.0, 52.5, 400, np.random.default_rng(k + 50), lat=3.5)]),
                        f, 12, 0.1))
    # O: a straight row of another track / a platform edge (right) plus a dense left wall that follows our track
    # which curves to the right from xc (the left wall bends with it; the row stays straight)
    for xc in (120.0, 160.0):
        for R in (600.0, 3000.0):
            f = lambda X, xc=xc, R=R: -arc(X, xc, R)  # noqa: E731
            out.append(("O_other_track_row", {"xc": xc, "R": R},
                        lambda k, f=f: np.concatenate([wall(f, 1.0, 52, 400, np.random.default_rng(k)),
                                                       columns(zero, -1.0, 52.5, 400, np.random.default_rng(k + 50), lat=2.6)]),
                        f, 12, 0.1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = {}
    for label, stable in (("axis_19_10", False), ("axis_stable", True)):
        cfg = FarRangeConfig(enabled=True, axis_stable=stable)
        rows = []
        for name, params, fr, truth, n, dt in cases():
            truth_of = truth if name.startswith(("P0", "V")) else (lambda k, t=truth: t)
            s = run(cfg, fr, truth_of, n, dt)
            rows.append({"case": name, **params, **s})
            print(label, name, params, {k: s[k] for k in ("accepted_frames", "max_err", "max_valid", "fail_safe")},
                  s["first_failure"], s["object_lost"], flush=True)
        res[label] = rows
    json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
