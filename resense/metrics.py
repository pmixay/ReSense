"""Evaluation: match detections against ground truth, recall vs range, false positives."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

RANGE_BINS = [(0, 50), (50, 100), (100, 150), (150, 200), (200, 300)]


@dataclass
class GTObstacle:
    distance: float       # m along the track (nearest face)
    lateral: float        # m from the track axis
    size: Sequence[float] = (0.5, 0.5, 0.5)
    label: str = "obstacle"
    in_gauge: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> "GTObstacle":
        return cls(distance=float(d["distance"]), lateral=float(d.get("lateral", 0.0)),
                   size=tuple(d.get("size", (0.5, 0.5, 0.5))), label=d.get("label", "obstacle"),
                   in_gauge=bool(d.get("in_gauge", True)))


def match(det_distance: float, det_lateral: float, gt: GTObstacle,
          tol_base: float = 2.0, tol_rel: float = 0.03, lateral_tol: float = 1.0) -> bool:
    tol = max(tol_base, tol_rel * gt.distance) + 0.5 * max(gt.size[0], 0.0)
    return abs(det_distance - gt.distance) <= tol and abs(det_lateral - gt.lateral) <= lateral_tol


@dataclass
class Evaluation:
    n_frames: int = 0
    n_empty_frames: int = 0
    fp_frames: int = 0                     # empty frames with an obstacle alarm
    fp_detections: int = 0                 # unmatched gauge detections (all frames)
    tp: int = 0
    fn: int = 0
    per_bin: Dict[str, List[int]] = field(default_factory=dict)   # "lo-hi": [tp, total]
    first_detection: Dict[str, float] = field(default_factory=dict)  # gt label -> max distance detected
    latency_ms: List[float] = field(default_factory=list)

    def add_frame(self, result_dict: dict, gts: Sequence[GTObstacle], use_candidates: bool = False) -> None:
        self.n_frames += 1
        dets = result_dict["detections"]
        if use_candidates:
            dets = dets + result_dict.get("warnings", [])
        self.latency_ms.append(result_dict.get("timing_ms", {}).get("total", 0.0))
        used = np.zeros(len(dets), dtype=bool)
        gauge_gts = [g for g in gts if g.in_gauge]
        if not gauge_gts:
            self.n_empty_frames += 1
            if result_dict["obstacle"]:
                self.fp_frames += 1
        for g in gauge_gts:
            key = None
            for lo, hi in RANGE_BINS:
                if lo <= g.distance < hi:
                    key = f"{lo}-{hi}"
            if key is None:
                key = f"{RANGE_BINS[-1][1]}+"
            self.per_bin.setdefault(key, [0, 0])
            self.per_bin[key][1] += 1
            hit = False
            for i, d in enumerate(dets):
                if not used[i] and match(d["distance"], d["lateral"], g):
                    used[i] = True
                    hit = True
                    break
            if hit:
                self.tp += 1
                self.per_bin[key][0] += 1
                self.first_detection[g.label] = max(self.first_detection.get(g.label, 0.0), g.distance)
            else:
                self.fn += 1
        self.fp_detections += int((~used).sum())

    def summary(self) -> dict:
        rec = {k: (v[0] / v[1] if v[1] else None) for k, v in sorted(self.per_bin.items(), key=lambda kv: float(kv[0].split("-")[0].rstrip("+")))}
        return {
            "frames": self.n_frames, "empty_frames": self.n_empty_frames,
            "recall": (self.tp / (self.tp + self.fn)) if (self.tp + self.fn) else None,
            "recall_by_range": rec, "per_bin_counts": self.per_bin,
            "fp_frames": self.fp_frames,
            "fp_frame_rate": (self.fp_frames / self.n_empty_frames) if self.n_empty_frames else None,
            "fp_detections": self.fp_detections,
            "first_detection_distance": self.first_detection,
            "latency_ms_mean": float(np.mean(self.latency_ms)) if self.latency_ms else None,
            "latency_ms_p95": float(np.percentile(self.latency_ms, 95)) if self.latency_ms else None,
        }
