#!/usr/bin/env python3
"""Design study (own code, before pre-registration): which bounded head-top variant re-rejects B1's flipped real
rail fragments (B1 compact snapshots, the design set). Low-cluster footprints are excluded from every reference
region (as low_free_mask does). Rejection needs: the pre-repair rule rejected it (capped top < original + 0.01, from
B1's audit), narrow and reaching a rail line (production eligibility), every region present, uncapped top <= H + m,
and the near-head returns of the footprint (h >= H - m) at most `spread` wide across the track.

    python variants.py <snapshot dir> <audit json>
"""
import json
import sys
from pathlib import Path

import numpy as np

HALF, BAND, W, G, FMAX, TOL, MAXW = 0.795, 0.10, 5.0, 0.3, 0.35, 0.10, 0.45


def region_top(X, h, m, lo, hi):
    k = m & (X >= lo) & (X <= hi)
    return float(h[k].max()) if k.any() else None


def head(c, X, dy, h, free, variant):
    x0, x1 = c["x0"], c["x1"]
    d0, d1 = c["d0"], c["d1"]
    if d1 - d0 > MAXW:
        return None, "wide"
    sides = [s for s in (-1.0, 1.0) if d0 <= s * HALF + TOL and d1 >= s * HALF - TOL]
    if len(sides) != 1:
        return None, "no_rail_line"
    s = sides[0]
    ok = free & (h > -0.3) & (h < FMAX)
    own = ok & (np.abs(dy - s * HALF) <= BAND)
    oth = ok & (np.abs(dy + s * HALF) <= BAND)
    terms = [region_top(X, h, own, x0 - W, x0 - G), region_top(X, h, own, x1 + G, x1 + W)]
    if variant == "V1":
        terms += [region_top(X, h, oth, x0 - W, x0 - G), region_top(X, h, oth, x1 + G, x1 + W)]
    elif variant == "V1c":
        xc = 0.5 * (x0 + x1)
        terms += [region_top(X, h, oth, x0 - W, xc), region_top(X, h, oth, xc, x1 + W)]
    elif variant == "V2":
        terms += [region_top(X, h, oth, x0 - W, x1 + W)]
    elif variant == "V2n":
        terms += [region_top(X, h, oth, x0 - 2.0, x1 + 2.0)]
    elif variant == "V0":   # own two-sided only (no other-rail evidence)
        pass
    if any(t is None for t in terms):
        return None, "missing_region"
    return min(terms), "ok"


def main():
    snaps, audit = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text())
    by = {}
    for r in audit["rows"]:
        by.setdefault(r["frame"], []).append(r)
    res = {}
    for m in (0.02, 0.03, 0.04):
        for spread in (0.10, 9.0):
            for variant in ("V0", "V1", "V1c", "V2", "V2n"):
                n_flip = n_flip_rej = n_ret = n_ret_rej = 0
                for fr, rows in sorted(by.items()):
                    d = np.load(snaps / f"frame_{fr:05d}.npz")
                    X, dy, h = d["X"].astype(float), d["dy"], d["h"]
                    free = np.ones(X.size, bool)
                    for key in d.files:
                        if key.startswith("state_"):
                            st, idx = d[key], d["idx_" + key[6:]]
                            if idx.size:
                                dd = dy[idx]
                                free[idx] = False
                                free[(X >= st[0]) & (X <= st[3]) & (dy >= dd.min()) & (dy <= dd.max())] = False
                    for r in rows:
                        st, idx = d[f"state_{r['cluster']}"], d[f"idx_{r['cluster']}"]
                        dd = dy[idx]
                        c = dict(x0=float(st[0]), x1=float(st[3]), d0=float(dd.min()), d1=float(dd.max()))
                        foot = (X >= c["x0"]) & (X <= c["x1"]) & (dy >= c["d0"]) & (dy <= c["d1"]) & (h < FMAX)
                        top = max(float(st[7]), float(h[foot].max())) if foot.any() else float(st[7])
                        H, why = head(c, X, dy, h, free, variant)
                        rej = False
                        if H is not None and top <= H + m:
                            near = foot & (h >= H - m)
                            rej = (not near.any()) or float(dy[near].max() - dy[near].min()) <= spread
                        if r["candidate_weak"]:
                            n_ret += 1
                            n_ret_rej += rej
                        else:
                            n_flip += 1
                            n_flip_rej += rej
                res[f"m{m} spread{spread} {variant}"] = (n_flip_rej, n_flip, n_ret_rej, n_ret)
                print(f"m {m} spread {spread:4.2f} {variant:4s}: flips re-rejected {n_flip_rej}/{n_flip}; "
                      f"B1-retained also rejected here {n_ret_rej}/{n_ret}", flush=True)


if __name__ == "__main__":
    main()
