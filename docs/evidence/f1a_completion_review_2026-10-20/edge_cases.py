#!/usr/bin/env python3
"""Reviewer script (own): edge cases of ``lowobj._rail_surface_reference`` and of its call site in
``rail_reference_check`` on the checkout in RESENSE_REPO (candidate a77d884).

Each case prints the outcome (value / None / exception).  The safe outcome of 'the head surface cannot be found' is
None -> the cluster is NOT rejected -> the alarm path stays open (fail-open).  Cases:
empty / 1 / 2-element arrays, NaN and inf heights, a single return held twice (the duplicate must not count as two),
two distinct returns, rails_spacing 0 / NaN, NaN cluster bbox, float32 inputs, a zero-width cluster, the new path with
``free=None`` (the unsafe ablation), missing second rail (``local_rail_reference`` None), and run time for a
pathologically dense band (100 000 returns in the window).

    RESENSE_REPO=<checkout> python edge_cases.py
"""
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = os.environ["RESENSE_REPO"]
sys.path.insert(0, ROOT)
sys.path.insert(0, str(Path(ROOT) / "tests"))

from resense.config import LowObjectConfig  # noqa: E402
from resense.lowobj import _rail_surface_reference, low_free_mask, rail_reference_check  # noqa: E402
from test_f1_false_alarms import HALF, _low, _rails  # noqa: E402

CFG = LowObjectConfig()
SP = 1.59


def run(name, fn):
    try:
        print(f"{name:62s} -> {fn()}")
    except Exception as e:  # noqa: BLE001
        print(f"{name:62s} -> EXCEPTION {type(e).__name__}: {e}")


def cl(lat=HALF, width=0.3):
    return _low(40.0, lat, 0.10, width=width, idx=np.array([0]))


def surf(X, dy, h, c=None, cfg=CFG, sp=SP, d0=HALF - 0.12, d1=HALF + 0.12):
    c = c or cl()
    return _rail_surface_reference(c, np.asarray(X), np.asarray(dy), np.asarray(h), d0, d1, cfg, sp)


e = np.array([])
run("empty arrays", lambda: surf(e, e, e))
run("one return on each side (any height -0.2)", lambda: surf([36.0, 44.0], [HALF, HALF], [-0.2, -0.2]))
run("two returns before only", lambda: surf([36.0, 37.0], [HALF, HALF + 0.01], [0.2, 0.2]))
side = lambda h1, h2: surf([36.0, 37.0, 44.0], [HALF, HALF + 0.01, HALF], [h1, h2, 0.0])  # noqa: E731
run("two distinct returns 0.2 before, bed return after", lambda: side(0.2, 0.2))
run("ONE return held twice (duplicate) before, bed after", lambda: surf([36.0, 36.0, 44.0], [HALF, HALF, HALF], [0.2, 0.2, 0.0]))
run("NaN heights everywhere", lambda: surf([36.0, 37.0, 44.0], [HALF] * 3, [np.nan] * 3))
run("one NaN among two good returns", lambda: surf([36.0, 37.0, 38.0, 44.0], [HALF, HALF + 0.01, HALF, HALF], [0.2, 0.2, np.nan, 0.0]))
run("+inf height (excluded by h < foot_max_top)", lambda: surf([36.0, 37.0, 44.0], [HALF] * 3, [np.inf, np.inf, 0.0]))
run("NaN in X", lambda: surf([np.nan, 37.0, 44.0], [HALF] * 3, [0.2, 0.2, 0.0]))
run("rails_spacing = 0", lambda: surf([36.0, 37.0, 44.0], [HALF, HALF + 0.01, HALF], [0.2, 0.2, 0.0], sp=0.0))
run("rails_spacing = NaN", lambda: surf([36.0, 37.0, 44.0], [HALF, HALF + 0.01, HALF], [0.2, 0.2, 0.0], sp=float("nan")))
run("rails_spacing = None", lambda: surf([36.0, 37.0, 44.0], [HALF, HALF + 0.01, HALF], [0.2, 0.2, 0.0], sp=None))
c_nan = cl()
c_nan.bbox_min[0] = np.nan
run("cluster bbox x NaN", lambda: surf([36.0, 37.0, 44.0], [HALF, HALF + 0.01, HALF], [0.2, 0.2, 0.0], c=c_nan))
run("float32 inputs", lambda: surf(np.array([36.0, 37.0, 44.0], np.float32), np.array([HALF, HALF + 0.01, HALF], np.float32),
                                   np.array([0.2, 0.2, 0.0], np.float32)))
run("zero-width cluster (bbox width 0)", lambda: surf([36.0, 37.0, 44.0], [HALF, HALF + 0.01, HALF], [0.2, 0.2, 0.0],
                                                      c=cl(width=0.0), d0=HALF, d1=HALF))
run("lateral band does not reach a rail line (centre)", lambda: surf([36.0, 37.0, 44.0], [0.0, 0.01, 0.0], [0.2, 0.2, 0.0], c=cl(0.0), d0=-0.1, d1=0.1))

# call-site behaviours through rail_reference_check
X, dy, h = _rails(30.0, 50.0, left=0.11, right=0.11)
xs = np.arange(31.0, 50.0, 2.0)
X, dy, h = np.r_[X, xs], np.r_[dy, np.full(xs.size, HALF + 0.11)], np.r_[h, np.full(xs.size, 0.20)]
i = X.size
X, dy, h = np.r_[X, [40.05, 40.25, 40.15]], np.r_[dy, [HALF - 0.12, HALF + 0.12, HALF + 0.02]], np.r_[h, [0.10, 0.10, 0.20]]
c = _low(40.0, HALF, 0.10, width=0.30, idx=np.array([i, i + 1]))
free = low_free_mask(X.size, [c], X, dy)
run("call site, free mask present (expected: rejected)", lambda: len(rail_reference_check([c], X, dy, h, CFG, SP, free)))
run("call site, free=None (unsafe ablation; expected: not rejected)", lambda: len(rail_reference_check([c], X, dy, h, CFG, SP, None)))
cfg0 = LowObjectConfig(local_rail_margin=0.0)
run("call site, local_rail_margin=0 (switch off; expected: not rejected)", lambda: len(rail_reference_check([c], X, dy, h, cfg0, SP, free)))
# a missing own rail line: remove the + rail's web returns (|dy - HALF| < 0.1 outside the cluster) but keep the head
# returns at dy = HALF + 0.11 and the other rail: local_rail_reference (original) has no line for the cluster's side
# -> None -> the new path must not run -> the cluster is kept
gone = (np.abs(dy - HALF) < 0.1) & (np.arange(X.size) < i)
keep = ~gone
cc = _low(40.0, HALF, 0.10, width=0.30, idx=np.array([int(keep[:i].sum()), int(keep[:i].sum()) + 1]))
fr = low_free_mask(int(keep.sum()), [cc], X[keep], dy[keep])
run("call site, own rail line absent (original ref None; expected: kept)",
    lambda: len(rail_reference_check([cc], X[keep], dy[keep], h[keep], CFG, SP, fr)))
# positive control for the same arrays: put the web back -> rejected
fr2 = low_free_mask(X.size, [c], X, dy)
run("  same scene with the own rail's web present (control; expected: rejected)",
    lambda: len(rail_reference_check([c], X, dy, h, CFG, SP, fr2)))

# run time on a pathologically dense window
rng = np.random.default_rng(1)
n = 100_000
Xd = np.r_[rng.uniform(35.0, 45.0, n), [40.05, 40.25, 40.15]]
dyd = np.r_[rng.uniform(HALF - 0.12, HALF + 0.12, n), [HALF - 0.12, HALF + 0.12, HALF + 0.02]]
hd = np.r_[rng.uniform(-0.1, 0.25, n), [0.10, 0.10, 0.2]]
cd = _low(40.0, HALF, 0.10, width=0.30, idx=np.array([n, n + 1]))
t0 = time.perf_counter()
r = _rail_surface_reference(cd, Xd[:n], dyd[:n], hd[:n], HALF - 0.12, HALF + 0.12, CFG, SP)
print(f"{'100k returns in the window: time (s) / value':62s} -> {time.perf_counter() - t0:.3f} / {r}")
