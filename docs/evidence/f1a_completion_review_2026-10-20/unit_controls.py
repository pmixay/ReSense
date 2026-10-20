#!/usr/bin/env python3
"""Reviewer script (own): exact threshold behaviour and adversarial controls of the F1a completion at the level of
``Detector._rail_reference`` (the production call site, as the repo's own tests use it), on the repo's fixtures
(tests/test_f1_false_alarms.py: ``_rails``, ``_low``; scene geometry of tests/test_f1a_continuation.py).

Decision names: KEEP = the cluster stays an ordinary low cluster (the alarm path stays open);
HIDE = it is rejected (weak low evidence, can never start a STOP).

    RESENSE_REPO=<checkout> python unit_controls.py <out json>

Run once per checkout (reference f56ad5e, parent 450a99f, candidate a77d884); compare with unit_compare.py.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = os.environ["RESENSE_REPO"]
sys.path.insert(0, ROOT)
sys.path.insert(0, str(Path(ROOT) / "tests"))

from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from test_f1_false_alarms import HALF, _low, _rails  # noqa: E402


def scene(side=1, top=0.20, head=0.20, head_step=2.0, head_range=(31.0, 50.0), extra=(), noise=0.0, rng=None,
          lat=None, width=0.30, strays_at=(), clamp=None, n_top=1, per_ring=1, slope=0.0):
    """Rails on both sides (web 0.11, one return per 0.4 m), the head's top surface ``head`` on the cluster's side
    (outside edge of the narrow footprint, one return per ``head_step`` m over ``head_range``), the fragment (two
    low returns at 0.10 and one upper return at ``top``).  ``extra`` = extra free returns (x, dy_offset, h);
    ``strays_at`` = x of two extra free returns at height ``top`` on the same rail line (the object's own unclustered
    returns); ``clamp`` = (x, h): two extra free returns at height h on the rail line (a local rise)."""
    X, dy, h = _rails(30.0, 50.0, left=0.11, right=0.11)
    xs = np.arange(head_range[0], head_range[1], head_step)
    if xs.size:
        for j in range(per_ring):          # per_ring distinct returns per ring crossing (0.07 m apart across)
            X = np.r_[X, xs]
            dy = np.r_[dy, np.full(xs.size, side * (HALF + 0.11 + 0.03 * j))]
            hh = head + slope * (xs - 40.0)
            if noise and rng is not None:
                hh = hh + rng.normal(0.0, noise, xs.size)
            h = np.r_[h, hh]
    for x, d, v in extra:
        X, dy, h = np.r_[X, x], np.r_[dy, side * (HALF + d)], np.r_[h, v]
    for x in strays_at:
        X = np.r_[X, [x, x + 0.07]]
        dy = np.r_[dy, [side * (HALF + 0.11)] * 2]
        h = np.r_[h, [top, top]]
    if clamp is not None:
        X = np.r_[X, [clamp[0], clamp[0] + 0.07]]
        dy = np.r_[dy, [side * (HALF + 0.11)] * 2]
        h = np.r_[h, [clamp[1], clamp[1]]]
    i = X.size
    tops = top if not (noise and rng is not None) else top + rng.normal(0.0, noise, n_top)
    tops = np.atleast_1d(tops)
    X = np.r_[X, [40.05, 40.25], 40.10 + 0.04 * np.arange(tops.size)]
    c_lat = side * HALF if lat is None else lat
    tail = np.full(tops.size, 0.02)
    dy = np.r_[dy, side * np.array([HALF - 0.12, HALF + 0.12]), side * HALF + tail] if lat is None else \
        np.r_[dy, np.array([lat - 0.12, lat + 0.12]), lat + tail]
    h = np.r_[h, [0.10, 0.10], tops]
    c = _low(40.0, c_lat, 0.10, width=width, idx=np.array([i, i + 1]))
    return X, dy, h, c


def decide(X, dy, h, c, neighbours=()):
    det = Detector(DetectorConfig())
    det._low_height = list(neighbours)
    kept = det._rail_reference([c], np.column_stack([X, dy, h]), dy, h)
    return "KEEP" if kept else "HIDE"


def main():
    out = []

    def rec(name, **kw):
        d = kw.pop("_decision")
        out.append(dict(name=name, params={k: (v if not isinstance(v, np.ndarray) else v.tolist()) for k, v in kw.items()},
                        decision=d))

    # 1. exact threshold: head surface 0.20, fragment top = head + delta
    for side in (1, -1):
        for delta in (-0.06, -0.02, 0.0, 0.02, 0.04, 0.05, 0.0501, 0.06, 0.08, 0.10, 0.15, 0.20):
            rec("sweep_top", side=side, head=0.20, delta=delta, _decision=decide(*scene(side, top=0.20 + delta)))
    # 1b. the same with a lower head (0.11 = the web only: no head surface above the web)
    for delta in (0.0, 0.02, 0.05, 0.0501, 0.10):
        rec("sweep_top_head0.11", head=0.11, delta=delta, _decision=decide(*scene(1, top=0.11 + delta, head=0.11)))
    # 2. the 2-distinct-return support: how many returns near the top are needed
    for n_head in (0, 1, 2, 3):
        xs = (40.5 + 0.0, 42.0, 44.0)[:n_head]
        extra = [(x, 0.11, 0.20) for x in xs]
        rec("head_returns_count", n=n_head, _decision=decide(*scene(1, top=0.20, head=0.11, head_range=(31.0, 31.0),
                                                                    extra=extra)))
    # 2b. head height varying along the track (model-plane error slope, m per m): the object is 0.10 above the LOCAL
    # head at its own position (x = 40), the head returns are h = 0.20 + slope * (x - 40)
    for slope in (-0.02, -0.01, -0.006, 0.0, 0.006, 0.008, 0.01, 0.012, 0.02, 0.04):
        rec("head_slope", slope=slope, local_head=0.20, top=0.30,
            _decision=decide(*scene(1, top=0.30, head=0.20, slope=slope)))
    # 3. adversarial: the object's own unclustered returns (two returns, same height as the object, outside
    # every low footprint) -- object top 0.21 = 10 cm above the 0.11 rail
    for where in (40.5, 41.0, 41.5, 43.0, 44.5, 46.0):
        rec("object_own_unclustered_returns", strays_x=where, top=0.21, head=0.11,
            _decision=decide(*scene(1, top=0.21, head=0.11, head_range=(31.0, 31.0), strays_at=(where,))))
    for where in (40.5, 43.0, 46.0):
        rec("object_own_unclustered_returns_ABOVE_rail_edge", strays_x=where, top=0.31, head=0.11,
            _decision=decide(*scene(1, top=0.31, head=0.11, head_range=(31.0, 31.0), strays_at=(where,))))
    # 3b. the same two strays 6 m away (outside the +-5 m window): must not matter
    rec("object_own_unclustered_returns", strays_x=47.0, top=0.21, head=0.11, note="6.7 m after, outside window",
        _decision=decide(*scene(1, top=0.21, head=0.11, head_range=(31.0, 31.0), strays_at=(47.0,))))
    # 4. one-sided head surface (the other side has only the web/bed returns)
    rec("head_before_only", _decision=decide(*scene(1, top=0.20, head_range=(31.0, 39.5))))
    rec("head_after_only", _decision=decide(*scene(1, top=0.20, head_range=(40.6, 50.0))))
    # 5. a local rise on the rail line within the window: object 10 cm above the head (top 0.30 over head 0.20)
    for cx, ch in ((36.0, 0.30), (36.0, 0.25), (44.0, 0.30), (46.0, 0.30), (47.0, 0.30)):
        rec("local_rise_on_rail_line", at_x=cx, rise_h=ch, head=0.20, top=0.30,
            _decision=decide(*scene(1, top=0.30, head=0.20, clamp=(cx, ch))))
    for cx, ch in ((36.0, 0.30), (36.0, 0.34)):
        rec("local_rise_on_rail_line_top0.34", at_x=cx, rise_h=ch, head=0.20, top=0.34,
            _decision=decide(*scene(1, top=0.34, head=0.20, clamp=(cx, ch))))
    # 6. head above the cap: rail returns at 0.30..0.34 (model plane 0.30+ below the head)
    for head in (0.28, 0.30, 0.32, 0.34, 0.36):
        for delta in (0.02, 0.05, 0.10):
            top = min(head + delta, 0.349)
            rec("high_head_cap", head=head, delta=delta, top=round(top, 4), _decision=decide(*scene(1, top=top, head=head)))
    # 7. not eligible (control: must be KEEP everywhere): centre of the track, wide
    X, dy, h, c = scene(1, top=0.20)
    rec("not_on_rail_centre", _decision=decide(*scene(1, top=0.20, lat=0.0)))
    c.bbox_min[1], c.bbox_max[1] = HALF - 0.30, HALF + 0.30
    rec("wide_cluster", _decision=decide(X, dy, h, c))
    # 8. noise Monte Carlo.  Scenario names: 'pessimistic' = dense head returns (1 per metre) and ONE object upper
    # return; 'sparse' = one head return per ring crossing (2.3 m, as at 40 m) and the object's top seen by 4
    # returns; 'dense' = 3 head returns per crossing, 4 object returns.  Noise sigma on all heights.
    for scen, kw in (("pessimistic", dict(head_step=1.0, n_top=1, per_ring=1)),
                     ("sparse", dict(head_step=2.3, n_top=4, per_ring=1)),
                     ("dense", dict(head_step=2.3, n_top=4, per_ring=3))):
        for sigma in (0.01, 0.015, 0.02, 0.03):
            for delta in (0.06, 0.08, 0.10):
                rng = np.random.default_rng(12345)
                n_hide = 0
                N = 500
                for _ in range(N):
                    n_hide += decide(*scene(1, top=0.20 + delta, head=0.20, noise=sigma, rng=rng, **kw)) == "HIDE"
                rec("noise_mc", scenario=scen, sigma=sigma, delta=delta, trials=N, hide_fraction=n_hide / N,
                    _decision=f"{n_hide}/{N} HIDE")
    Path(sys.argv[1]).write_text(json.dumps(dict(repo=ROOT, rows=out), indent=1) + "\n")
    print(ROOT, len(out), "rows")


if __name__ == "__main__":
    main()
