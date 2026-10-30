"""Diagnostic mirror of resense.farline.measure that also returns the per-side bins and the reason a
side or the frame failed. Read-only: it is called beside the detector's own measure() (hook below),
and its verdict is checked against measure()'s on every traced frame (hook asserts equality)."""
import numpy as np

import resense.farline as FL


def side_detail(xs, ys, cfg, min_bins):
    """FL._side_line with the reason of a failure."""
    d = {"n_bins": int(xs.size)}
    if xs.size < min_bins:
        return None, {**d, "fail": "few_bins"}
    o = np.argsort(xs)
    xs, ys = xs[o], ys[o]
    keep = np.ones(xs.size, dtype=bool)
    for _ in range(3):
        if keep.sum() < min_bins:
            return None, {**d, "fail": "few_kept"}
        p = np.polyfit(xs[keep], ys[keep], 1)
        keep = np.abs(ys - np.polyval(p, xs)) < 2.0 * cfg.axis_max_rms
    end, last, run, stop = -1, None, 0, "end"
    for i in range(xs.size):
        if keep[i]:
            if last is not None and xs[i] - xs[last] > cfg.axis_max_gap:
                stop = f"gap@{xs[last]:.0f}-{xs[i]:.0f}"
                break
            last, run, end = i, 0, i
        else:
            run += 1
            if last is not None and run >= cfg.axis_max_rejected_run:
                stop = f"rejrun@{xs[i]:.0f}"
                break
    d.update(xs=[round(float(v), 1) for v in xs], ys=[round(float(v), 2) for v in ys],
             keep=[bool(k) for k in keep], stop=stop)
    if end < 0:
        return None, {**d, "fail": "no_end"}
    sup = keep.copy()
    sup[end + 1:] = False
    if sup.sum() < min_bins:
        return None, {**d, "fail": "few_support"}
    x, y = xs[sup], ys[sup]
    d["support"] = float(x.max())
    if x.max() - x.min() < cfg.axis_min_span:
        return None, {**d, "fail": "span"}
    p = np.polyfit(x, y, 1)
    res = y - np.polyval(p, x)
    rms = float(np.sqrt(np.mean(res ** 2)))
    d["rms"] = round(rms, 3)
    if rms > cfg.axis_max_rms:
        return None, {**d, "fail": "rms"}
    if abs(float(np.mean(res[-3:]))) > cfg.axis_max_rms:
        return None, {**d, "fail": "last_stretch"}
    q = np.polyfit(x, y, 2)
    grid = np.linspace(x.min(), x.max(), 32)
    bow = float(np.max(np.abs(np.polyval(q, grid) - np.polyval(p, grid))))
    d["bow"] = round(bow, 3)
    if bow > cfg.axis_max_bow:
        return None, {**d, "fail": "bow"}
    r = FL._side_line(xs, ys, cfg, min_bins)
    return r, {**d, "fail": None, "slope": None if r is None else r[0]}


def measure_detail(xyz, model, cfg, max_range):
    """The bins exactly as FL.measure builds them; per side the primary and the second-side verdicts."""
    X, Y, Z = xyz[:, 0].astype(np.float64), xyz[:, 1].astype(np.float64), xyz[:, 2].astype(np.float64)
    j = cfg.axis_join
    lo, hi = cfg.axis_fit_range[0], min(cfg.axis_fit_range[1], max_range)
    sel = (X > lo) & (X < hi)
    out = {"sides": {}}
    if sel.sum() < 50:
        return {**out, "fail": "few_points"}
    X, Y, Z = X[sel], Y[sel], Z[sel]
    yj = float(model.center_y(np.array([j]))[0])
    tj = float(np.tan(model.yaw) + model.curvature * j)
    out["tj"] = tj
    dy0 = Y - (yj + tj * (X - j))
    h = Z - model.rail_z(X)
    band = ((h > cfg.axis_band[0]) & (h < cfg.axis_band[1]) & (np.abs(dy0) > cfg.axis_lateral[0])
            & (np.abs(dy0) < cfg.axis_lateral[1]))
    edges = np.arange(lo, hi + cfg.axis_bin, cfg.axis_bin)
    for s in (1.0, -1.0):
        m = band & (np.sign(dy0) == s)
        name = "left" if s > 0 else "right"
        if m.sum() < cfg.axis_min_points * min(cfg.axis_min_bins, cfg.axis_second_min_bins):
            out["sides"][name] = {"fail": "few_points"}
            continue
        idx = np.digitize(X[m], edges) - 1
        a, yy = np.abs(dy0[m]), Y[m]
        xs, ys = [], []
        for b in np.unique(idx):
            q = np.flatnonzero(idx == b)
            if q.size < cfg.axis_min_points or b < 0 or b >= edges.size - 1:
                continue
            k = q[np.argsort(a[q])[int(0.1 * q.size)]]
            xs.append(0.5 * (edges[b] + edges[b + 1]))
            ys.append(yy[k])
        xs, ys = np.asarray(xs), np.asarray(ys)
        f1, d1 = side_detail(xs, ys, cfg, cfg.axis_min_bins)
        rec = {"primary": d1}
        if f1 is None:
            f2, d2 = side_detail(xs, ys, cfg, cfg.axis_second_min_bins)
            rec["second"] = d2
        out["sides"][name] = rec
    return out


class Hook:
    """Wraps FL.measure: returns the original's result unchanged, records the detail per call."""

    def __init__(self):
        self.orig = FL.measure
        self.last = None

    def __call__(self, xyz, model, cfg, max_range):
        r = self.orig(xyz, model, cfg, max_range)
        self.last = {"result": None if r is None else [round(float(r[0]), 6), round(float(r[1]), 6), round(float(r[2]), 1), int(r[3])],
                     "detail": measure_detail(xyz, model, cfg, max_range)}
        return r

    def install(self):
        FL.measure = self
