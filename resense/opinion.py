"""A learned second opinion on a track before it becomes a STOP (27.09, P2 ride; off by default).

The tracker keeps, per track, a short record of its matched clusters (:func:`observation`). When a
track is about to become an obstacle (reported in zone gauge after not being one), the opinion
(:class:`TrackOpinion`) gives the probability that the track is a real object rather than
infrastructure from features aggregated over that record (:func:`track_features`: range, lateral
stability, approach consistency, height / size statistics, strict-envelope share, demotion
history, low / corridor kind). It is never a veto: a doubtful track beyond a near range must stay a
STOP candidate for a few more matched frames (``tracking.doubt_extra_hits``) and is advisory
meanwhile. The model is a small gradient-boosted tree ensemble stored as JSON
(``configs/track_opinion.json``, trained by ``scripts/track_opinion.py``) and evaluated with numpy.
"""
from __future__ import annotations

import json
import math
import os
from typing import List, Optional, Sequence

import numpy as np

# the fields of one observation (a matched cluster of a track), in order
OBS_FIELDS = ("distance", "lateral", "cz", "length", "width", "height", "height_min", "height_max",
              "n", "n_gauge", "vis", "low", "demoted", "column", "beyond")
OBS_KEEP = 15          # observations kept per track (the features use the last OBS_WINDOW)
OBS_WINDOW = 10

FEATURES = ["distance", "abs_lateral", "is_low", "frac_low", "hits", "lat_std", "lat_jump", "cz_std",
            "hmax_mean", "hmin_mean", "len_mean", "width_mean", "height_mean", "log_n_mean",
            "gauge_frac", "vis_mean", "frac_demoted", "frac_column", "frac_beyond", "dist_rough",
            "dist_step", "hit_fraction", "log_gauge"]

_BEYOND = ("beyond_axis", "beyond_height_ref")


def observation(cl) -> tuple:
    """The record of one matched cluster (``OBS_FIELDS``)."""
    s = cl.bbox_max - cl.bbox_min
    return (float(cl.distance), float(cl.lateral), float(cl.centroid[2]), float(s[0]), float(s[1]), float(s[2]),
            float(cl.height_min), float(cl.height_max), float(cl.n), float(cl.n_gauge),
            float(min(cl.n / max(cl.n_expected, 1.0), 5.0)), float(cl.kind == "low"), float(bool(cl.reason)),
            float(cl.reason == "column"), float(cl.reason in _BEYOND))


def track_features(obs: Sequence[tuple], hits: int, hit_fraction: float) -> np.ndarray:
    """The feature vector (``FEATURES``) of a track from its last observations (the current one last)."""
    o = np.asarray(obs[-OBS_WINDOW:], dtype=np.float64)
    d, lat, cz = o[:, 0], o[:, 1], o[:, 2]
    n = o.shape[0]
    dd = np.diff(d)
    rough = float(np.median(np.abs(np.diff(dd)))) if n >= 3 else 0.0
    step = float(-(d[-1] - d[0]) / (n - 1)) if n >= 2 else 0.0
    return np.array([
        d[-1], abs(lat[-1]), o[-1, 11], o[:, 11].mean(), float(min(hits, 30)),
        float(lat.std()), float(np.abs(np.diff(lat)).max()) if n >= 2 else 0.0, float(cz.std()),
        o[:, 7].mean(), o[:, 6].mean(), o[:, 3].mean(), o[:, 4].mean(), o[:, 5].mean(),
        float(np.log1p(o[:, 8]).mean()), float((o[:, 9] / np.maximum(o[:, 8], 1.0)).mean()), o[:, 10].mean(),
        o[:, 12].mean(), o[:, 13].mean(), o[:, 14].mean(), rough, step, float(hit_fraction),
        float(np.log1p(o[-1, 9])),
    ], dtype=np.float64)


class TrackOpinion:
    """A gradient-boosted tree ensemble (binary log-loss) read from JSON::

        {"features": [...], "init": f0, "learning_rate": lr,
         "trees": [{"feature": [...], "threshold": [...], "left": [...], "right": [...], "value": [...]}, ...]}

    a node with ``left == -1`` is a leaf (its ``value`` is the tree's output); ``x <= threshold``
    goes left, as in scikit-learn. :meth:`prob` returns the probability of a real object."""

    def __init__(self, spec: dict):
        self.features: List[str] = list(spec["features"])
        missing = [f for f in self.features if f not in FEATURES]
        if missing:
            raise ValueError(f"track opinion model uses unknown features {missing}")
        self.cols = np.array([FEATURES.index(f) for f in self.features], dtype=np.int64)
        self.init = float(spec["init"])
        self.lr = float(spec["learning_rate"])
        self.trees = [{k: np.asarray(t[k]) for k in ("feature", "threshold", "left", "right", "value")}
                      for t in spec["trees"]]

    @classmethod
    def load(cls, path: str) -> "TrackOpinion":
        with open(path, encoding="utf-8") as fh:
            return cls(json.load(fh))

    def margin(self, x: np.ndarray) -> float:
        v = np.asarray(x, dtype=np.float64)[self.cols]
        s = self.init
        for t in self.trees:
            i = 0
            while t["left"][i] >= 0:
                i = int(t["left"][i]) if v[int(t["feature"][i])] <= t["threshold"][i] else int(t["right"][i])
            s += self.lr * float(t["value"][i])
        return s

    def prob(self, x: np.ndarray) -> float:
        return 1.0 / (1.0 + math.exp(-self.margin(x)))


_CACHE: dict = {}


def load_opinion(path: str) -> Optional[TrackOpinion]:
    """The model at ``path`` (relative paths from the repository root, then the working directory);
    cached per path. None for an empty path."""
    if not path:
        return None
    if path not in _CACHE:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        p = path if os.path.isabs(path) or os.path.exists(path) else os.path.join(root, path)
        _CACHE[path] = TrackOpinion.load(p)
    return _CACHE[path]
