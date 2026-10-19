#!/usr/bin/env python3
"""K2-1: per-X median over frames of |axis(X) - wall-referenced track(X)| on roundT_pressureGate_roundT.

    k2_wall_error.py <true_axis.json (base run, true_axis_all.py)> <side +1 left / -1 right> <track.json> <base track.json> [k0 k1]

The wall-referenced track is frozen from the base run (round 3's investigate_curve/true_axis_all.py: the outer
wall followed outward from the near field, minus its near offset). It is defined only to wall_xmax + 15 m. The
axis of the measured tree comes from its own track rows (centre, tangent, curvature, curvature step). The two
are compared in the detector frame; the mount rotation of both runs must be equal (checked)."""
import json
import sys

import numpy as np


def axis(r, x):
    y = r["center"] + r["tan_yaw"] * x + r["half_curv"] * x * x
    if "half_step" in r:
        y += r["half_step"] * max(x - r["knot"], 0.0) ** 2
    return y


def main():
    ta = {r["k"]: r for r in json.load(open(sys.argv[1]))}
    side = int(sys.argv[2])
    rows = json.load(open(sys.argv[3]))["rows"]
    base_rows = {r["i"]: r for r in json.load(open(sys.argv[4]))["rows"]}
    k0, k1 = (int(sys.argv[5]), int(sys.argv[6])) if len(sys.argv) > 6 else (57, 117)
    mount_diff = [r["i"] for r in rows if k0 <= r["i"] <= k1 and r.get("R") != base_rows.get(r["i"], {}).get("R")]
    assert not mount_diff, f"mount rotation differs from the base run in frames {mount_diff[:10]}" 
    ref_rows = {r["k"]: r for r in ta.values()}
    XS = (80, 90, 100, 110, 120)
    err = {x: [] for x in XS}
    for r in rows:
        k = r["i"]
        t = ref_rows.get(k)
        if not (k0 <= k <= k1) or not t or not t.get("ok") or "center" not in r:
            continue
        c = t["coef"]
        for x in XS:
            if x > t["wall_xmax"] + 15:
                continue
            true_y = np.polyval(c, x) - side * t["off"]
            err[x].append(abs(axis(r, x) - true_y))
    out = {str(x): {"n": len(v), "median": round(float(np.median(v)), 3) if v else None,
                    "p90": round(float(np.percentile(v, 90)), 3) if v else None} for x, v in err.items()}
    out["frames_in_window"] = sum(k0 <= r["i"] <= k1 for r in rows)
    out["frames_with_reference"] = sum(1 for k in range(k0, k1 + 1) if ref_rows.get(k, {}).get("ok"))
    print(json.dumps(out))


if __name__ == "__main__":
    main()
