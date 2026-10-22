#!/usr/bin/env python3
"""Per-detection context features from the competitor survey (ideas 1 and 5), computed on the sealed detector.

Runs the *unchanged* detector over a cached recording (same stamps, fresh detector, no speed, exactly as
``scripts/eval_real.py:run_piece``) and, for every STOP detection (``res.detections``) and CAUTION detection
(``res.warnings``), measures the raw points of the processed cloud around it, in track coordinates
(``dy`` = y - axis(x), ``h`` = z - rail head(x)).  Output: one JSON line per frame, the detector's own
``to_dict()`` (for the instrumentation-equality check) plus a ``feat`` list.

Features (ported by description from docs/COMPETITOR_SURVEY_2026-10.md section 3, thresholds applied later,
never tuned here):
  behind_n     idea 1 (hakatanon ``behind_n``): returns just behind the object, in its lateral band and height band
  front_maxh   idea 1 (hakatanon ``front_maxh``): highest return in front of the object, in its lateral band, below its top
  attach       idea 1 (attachment ratio): returns within 0.35 + 0.008 d around the object but outside it, over its own
  run_m        idea 5 (collinearity / continuation): length of the line of same-lateral, same-height returns through the object
Not ported: the per-laser-row depth-edge test (needs the ring of every processed point and a threshold the survey
does not give).
"""
import json
import os
import sys

import numpy as np

REPO = os.environ.get("RESENSE_REPO", "/home/user/ReSense")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

BEAM = 0.00218          # Pandar128 fine vertical spacing, rad
SENSOR_H = 1.5          # default sensor height, m (resense.track.default_track_model)


def floor_step(d):
    """Range spacing of two neighbouring floor returns at distance d (m)."""
    return d * d * BEAM / SENSOR_H


def features(res, det, dy, h, x, y, z):
    cx, cy, cz = (float(v) for v in det.center)
    sx, sy, sz = (float(v) for v in det.size)
    x0, x1 = cx - sx / 2.0, cx + sx / 2.0
    cdy = cy - float(res.track.center_y(np.array([cx]))[0])
    own = ((x >= x0 - 0.05) & (x <= x1 + 0.05) & (np.abs(y - cy) <= sy / 2.0 + 0.05)
           & (np.abs(z - cz) <= sz / 2.0 + 0.05))
    f = {"x0": round(x0, 2), "x1": round(x1, 2), "cdy": round(cdy, 3), "lat_check": round(cdy - float(det.lateral), 3),
         "n_own": int(own.sum())}
    if own.sum() < 1:
        f["ok"] = False
        return f
    f["ok"] = True
    f["lat_mean"] = round(float(dy[own].mean()), 3)
    f["lat_mean_check"] = round(float(dy[own].mean()) - float(det.lateral), 3)
    low, top = float(h[own].min()), float(h[own].max())
    f["low"], f["top"] = round(low, 3), round(top, 3)
    d = float(det.distance)
    L = float(np.clip(1.5 * floor_step(d), 2.0, 30.0))
    f["L"] = round(L, 2)
    band = np.abs(dy - cdy) <= 0.3
    # idea 1: opacity. Returns behind the object in its band and height range: a solid object leaves a shadow.
    m = band & (x > x1 + 0.3) & (x < x1 + 0.3 + L) & (h >= low - 0.05) & (h <= top + 0.3)
    f["behind_n"] = int(m.sum())
    # idea 1: front lift. The highest return in front of the object, below its top, in its band.
    m = band & (x < x0 - 0.3) & (x > x0 - 0.3 - L) & (h < top)
    f["front_maxh"] = round(float(h[m].max()), 3) if m.any() else None
    f["front_n"] = int(m.sum())
    # idea 1: attachment ratio. Outside returns within r of the object over the object's own returns.
    r = 0.35 + 0.008 * d
    ring = ((x >= x0 - r) & (x <= x1 + r) & (np.abs(dy - cdy) <= sy / 2.0 + r) & (h >= low - r) & (h <= top + r))
    f["attach"] = round(float((ring & ~own).sum()) / max(1, int(own.sum())), 3)
    # idea 5: a line of same-lateral, same-height returns through the object (2 m bins, one gap allowed).
    lat_h = (np.abs(dy - cdy) <= 0.25) & (h >= low - 0.1) & (h <= top + 0.1)
    edges = np.arange(np.floor(x0 - 40.0), np.ceil(x1 + 40.0) + 2.0, 2.0)
    occ = np.histogram(x[lat_h], bins=edges)[0] > 0
    own_bins = np.where((edges[:-1] <= x1) & (edges[1:] >= x0))[0]
    if own_bins.size:
        lo, hi = int(own_bins.min()), int(own_bins.max())
        occ[lo:hi + 1] = True
        a = lo
        gap = 0
        while a - 1 >= 0 and (occ[a - 1] or gap < 1):
            gap = 0 if occ[a - 1] else gap + 1
            a -= 1
            if gap > 1:
                break
        b = hi
        gap = 0
        while b + 1 < occ.size and (occ[b + 1] or gap < 1):
            gap = 0 if occ[b + 1] else gap + 1
            b += 1
            if gap > 1:
                break
        # trim trailing empty bins left by the allowed gap
        while a < lo and not occ[a]:
            a += 1
        while b > hi and not occ[b]:
            b -= 1
        f["run_m"] = float((b - a + 1) * 2.0)
    else:
        f["run_m"] = 0.0
    return f


def main():
    cache, bag, out = sys.argv[1], sys.argv[2], sys.argv[3]
    import eval_real
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    from scripts.cache_io import cache_file_stem, cache_files, load_cache_array, load_cache_stamps
    cfg = DetectorConfig.from_dict(eval_real.load_cfg_dict(os.path.join(REPO, "configs", "default.yaml"), []))
    d = os.path.join(cache, bag)
    files = cache_files(d)
    stamps = load_cache_stamps(d)
    det = Detector(cfg)
    with open(out, "w", encoding="utf-8") as fh:
        for i, fpath in enumerate(files):
            stem = cache_file_stem(fpath)
            idx = int(stem.rsplit("_", 1)[1])
            fr = frame_from_compact(load_cache_array(fpath), cfg.sensor, stamp=stamps.get(stem, i * 0.1), frame_id=stem)
            res = det.process(fr)
            rd = res.to_dict()
            rd["frame"] = idx
            rd["frame_id"] = stem
            feats = []
            if (res.detections or res.warnings) and res.xyz is not None:
                xyz = np.asarray(res.xyz, dtype=np.float64)
                x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
                dy = y - res.track.center_y(x)
                h = z - res.track.rail_z(x)
                for level, lst in (("stop", res.detections), ("warn", res.warnings)):
                    for dt in lst:
                        ft = features(res, dt, dy, h, x, y, z)
                        ft.update({"level": level, "id": int(dt.id), "distance": round(float(dt.distance), 2)})
                        feats.append(ft)
            rd["feat"] = feats
            fh.write(json.dumps(rd) + "\n")


if __name__ == "__main__":
    main()
