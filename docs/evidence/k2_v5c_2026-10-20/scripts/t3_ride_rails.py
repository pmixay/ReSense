"""T3, ride part, second rails method (t3_ride.py's lateral band from one axis caught platform edges on the ride: fitted
gauge 1.7-1.9 m). From t3_ride.py's dumps: rail-head returns (|h| < 0.05 m) in 2 m bins from 6 m to the detection
- 2 m; in each bin, within 1.4 m of the mean of the two axes, the pair of 0.04 m histogram peaks whose spacing is
closest to 1.52 m (accepted within 0.12 m, both peaks >= 3 returns) gives the two rails; their midpoints are fitted
with a robust quadratic in X (a line with fewer than 6 bins) and taken at the detection's distance. Printed per
removed strict detection: bins used, each axis minus that midpoint, and the detection's lateral from the midpoint.

    python t3_ride_rails.py <ride_nd4.pkl> <rows> [<more pkl> <rows> ...]
"""
import sys

import numpy as np
import pickle


def mids(d0, dk, xmax):
    xyz, h = d0["xyz"], d0["h"]
    out = []
    for x0 in np.arange(6.0, xmax - 2.0, 2.0):
        xc = x0 + 1.0
        a = 0.5 * (float(d0["model"].center_y(np.array([xc]))[0]) + float(dk["model"].center_y(np.array([xc]))[0]))
        m = (xyz[:, 0] >= x0) & (xyz[:, 0] < x0 + 2) & (np.abs(h) < 0.05) & (np.abs(xyz[:, 1] - a) < 1.4)
        y = xyz[m, 1]
        if y.size < 6:
            continue
        hist, e = np.histogram(y, bins=np.arange(a - 1.4, a + 1.4001, 0.04))
        pk = [k for k in range(1, len(hist) - 1) if hist[k] >= 3 and hist[k] >= hist[k - 1] and hist[k] >= hist[k + 1]]
        best = None
        for i in pk:
            for j in pk:
                if j > i:
                    gap = (j - i) * 0.04
                    if abs(gap - 1.52) < 0.12 and (best is None or abs(gap - 1.52) < abs(best[2] - 1.52)):
                        best = (i, j, gap)
        if best is None:
            continue
        ci = lambda k: float(np.median(y[(y >= e[k] - 0.02) & (y < e[k + 1] + 0.02)]))  # noqa: E731
        out.append((xc, 0.5 * (ci(best[0]) + ci(best[1])), ci(best[1]) - ci(best[0])))
    return np.array(out)


args = sys.argv[1:]
print(" row     d   bins  span     gauge | off-mid  K2-mid | det from: true   off    K2")
for pkl, rows in zip(args[::2], args[1::2]):
    D = pickle.load(open(pkl, "rb"))
    a, _, b = rows.partition("-")
    for i in range(int(a), int(b or a) + 1):
        if i not in D["off"]:
            continue
        d0, dk = D["off"][i], D["k2"][i]
        for det in d0["dets"]:
            if det["zone"] != "gauge" or det["reason"]:
                continue
            X, Y = det["center"][0], det["center"][1]
            m = mids(d0, dk, X)
            if len(m) < 3:
                print(f"{i:5d} {det['distance']:5.1f}  {len(m)} bins: not measurable")
                continue
            deg = 2 if len(m) >= 6 else 1
            p = np.polyfit(m[:, 0], m[:, 1], deg)
            for _ in range(3):
                r = m[:, 1] - np.polyval(p, m[:, 0])
                keep = np.abs(r) < max(0.05, 2.5 * np.median(np.abs(r)))
                if keep.sum() < deg + 2:
                    break
                p = np.polyfit(m[keep, 0], m[keep, 1], deg)
            mid = float(np.polyval(p, X))
            ao = float(d0["model"].center_y(np.array([X]))[0])
            ak = float(dk["model"].center_y(np.array([X]))[0])
            print(f"{i:5d} {det['distance']:5.1f}  {len(m):3d}  {m[0, 0]:4.0f}-{m[-1, 0]:3.0f}  {np.median(m[:, 2]):.3f} | "
                  f"{ao - mid:+.2f}   {ak - mid:+.2f}  | {Y - mid:+.2f}  {Y - ao:+.2f} {Y - ak:+.2f}")
