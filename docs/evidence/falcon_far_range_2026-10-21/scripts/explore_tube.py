#!/usr/bin/env python3
"""Design exploration (before PROTOCOL.md): from the recorded measure() bins of the v1.2.0 candidate
(run_far.py --detail), how often would the right-side bins confirm the left line inside a tube of
half-width T, and to what support?  Offline, recorded bins only.

    explore_tube.py <detail.jsonl> [--T 0.4]"""
import argparse
import json
from collections import Counter

import numpy as np


def tube_support(xs, ys, slope, icpt, T, gap=40.0, min_bins=4, span=80.0):
    o = np.argsort(xs)
    xs, ys = np.asarray(xs)[o], np.asarray(ys)[o]
    r = ys - (icpt + slope * xs)
    off = float(np.median(r))
    ok = np.abs(r - off) <= T
    end, last = None, None
    for i in range(xs.size):
        if not ok[i]:
            break                              # an observed bin off the tube ends the support
        if last is not None and xs[i] - xs[last] > gap:
            break
        last, end = i, i
    if end is None:
        return None
    x = xs[:end + 1]
    if x.size < min_bins or x[-1] - x[0] < span:
        return None
    return float(x[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("detail")
    ap.add_argument("--T", type=float, default=0.4)
    a = ap.parse_args()
    rows = [json.loads(line) for line in open(a.detail)]
    c, sup2, supl = Counter(), [], []
    for r in rows:
        d = r["far_measure"]["detail"]["sides"]
        L, Rt = d.get("left", {}), d.get("right", {})
        p = L.get("primary", {})
        if p.get("fail") is not None or "xs" not in p:
            c["left_not_primary"] += 1
            continue
        xs, ys, k = np.array(p["xs"]), np.array(p["ys"]), np.array(p["keep"], bool)
        sup = p["support"]
        m = k & (xs <= sup)
        sl, ic = np.polyfit(xs[m], ys[m], 1)
        s = Rt.get("second") or Rt.get("primary") or {}
        if "xs" not in s or len(s["xs"]) == 0:
            c["right_no_bins"] += 1
            supl.append(sup)
            continue
        t = tube_support(s["xs"], s["ys"], sl, ic, a.T)
        if t is None:
            c["right_not_confirming"] += 1
            supl.append(sup)
            continue
        c["two_sided"] += 1
        sup2.append(min(sup, t))
    print(dict(c))
    for name, v in (("two-sided support", sup2), ("left-only support", supl)):
        if v:
            v = np.array(v)
            print(name, "n", v.size, "p10/50/90", np.percentile(v, [10, 50, 90]).round(1), Counter(np.round(v).astype(int)).most_common(6))


if __name__ == "__main__":
    main()
