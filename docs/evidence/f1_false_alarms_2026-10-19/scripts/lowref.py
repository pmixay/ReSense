"""Read-only F1 measurement helper: for every low cluster of a processed frame, its top against the
frame's own rail lines (the quantities ``lowobj.rail_reference_check`` thresholds), computed from the
detector state after ``Detector.process`` returned. Never changes detector state.

``patch_detector(sink)`` wraps ``Detector.process`` so that any driver (the judge's ``range_test.py``,
``replay.py``) records one entry per processed frame into ``sink`` (a list).
"""
from __future__ import annotations

import numpy as np

from resense.lowobj import _band_line, local_rail_reference


def low_info(det, c) -> dict:
    cfg = det.cfg
    X = det._frame_xyz[:, 0]
    _dy_all, h_all = det._frame_hd
    dy = det._dy_rail
    half = 0.5 * float(cfg.track.rails_spacing)
    x0, x1, w = float(c.bbox_min[0]), float(c.bbox_max[0]), float(cfg.lowobj.local_rail_window)
    band = float(cfg.lowobj.local_rail_band)
    lines = [_band_line(X, dy, h_all, s * half - band, s * half + band, x0 - w, x1 + w, x0 - 0.3, x1 + 0.3,
                        0.5, 1, int(cfg.lowobj.local_rail_min_bins)) for s in (-1.0, 1.0)]
    ref = local_rail_reference(c, X, dy, h_all, cfg.lowobj, cfg.track.rails_spacing)
    own = None
    if c.points_idx.size:
        d = dy[c.points_idx]
        own = _band_line(X, dy, h_all, float(d.min()), float(d.max()), x0 - w, x1 + w, x0 - 0.3, x1 + 0.3, 0.25, 2, 4)
    r = lambda v: None if v is None else round(float(v), 3)  # noqa: E731
    return {"d": round(float(c.distance), 2), "lat": round(float(c.lateral), 3), "top": r(c.height_max),
            "hmin": r(c.height_min), "size": [round(float(v), 3) for v in c.size], "n": int(c.n),
            "zone": c.zone, "reason": c.reason, "weak": bool(c.low_height_weak), "rail_line": bool(c.rail_line),
            "lineR": r(lines[0]), "lineL": r(lines[1]), "ref": r(ref), "own_band": r(own),
            "rail_slabs": int(det.track.rail_slabs)}


def frame_info(det, res) -> list:
    out = [low_info(det, c) for c in res.candidates if c.kind == "low"]
    out += [dict(low_info(det, c), weak=True) for c in det._low_height if c.kind == "low"]
    return out


def patch_detector(sink: list):
    from resense.detector import Detector
    orig = Detector.process

    def process(self, frame, *a, **k):
        res = orig(self, frame, *a, **k)
        try:
            sink.append(frame_info(self, res))
        except Exception as exc:  # measurement must never break the run
            sink.append([{"error": repr(exc)}])
        return res

    Detector.process = process
    return orig
