"""End-to-end per-frame obstacle detection inside the clearance gauge."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from resense.clustering import Cluster, find_clusters
from resense.config import DetectorConfig
from resense.frame import Frame
from resense.gauge import corridor_coordinates, corridor_mask
from resense.track import TrackModel, estimate_track
from resense.tracking import Tracker


@dataclass
class Detection:
    id: int
    distance: float            # m along the track to the nearest point
    lateral: float             # m, + left of the track axis
    center: np.ndarray         # (3,) vehicle frame
    size: np.ndarray           # (3,) bbox size
    n_points: int              # occupied voxels (~ distinct rays)
    confidence: float
    age: int                   # frames since first seen
    zone: str                  # 'gauge' or 'warning'
    height_min: float          # lowest point above the rail head
    intensity: float

    def to_dict(self) -> dict:
        return {
            "id": int(self.id), "zone": self.zone, "distance": round(float(self.distance), 2),
            "lateral": round(float(self.lateral), 2),
            "center": [round(float(v), 2) for v in self.center],
            "size": [round(float(v), 2) for v in self.size],
            "n_points": int(self.n_points), "confidence": round(float(self.confidence), 3),
            "age": int(self.age), "height_min": round(float(self.height_min), 2),
            "intensity": round(float(self.intensity), 1),
        }


@dataclass
class FrameResult:
    stamp: float
    obstacle: bool                         # confirmed object inside the strict gauge
    warning: bool                          # confirmed object in the advisory zone only
    nearest_distance: Optional[float]      # nearest confirmed gauge obstacle (m)
    detections: List[Detection]            # confirmed, zone == 'gauge'
    warnings: List[Detection]              # confirmed, zone == 'warning'
    candidates: List[Cluster]              # all single-frame clusters (before persistence)
    track: TrackModel
    corridor_idx: np.ndarray               # indices of corridor points in the frame
    n_points: int
    timing_ms: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "stamp": self.stamp, "obstacle": bool(self.obstacle), "warning": bool(self.warning),
            "nearest_distance": None if self.nearest_distance is None else round(float(self.nearest_distance), 2),
            "detections": [d.to_dict() for d in self.detections],
            "warnings": [d.to_dict() for d in self.warnings],
            "n_candidates": len(self.candidates), "n_points": int(self.n_points),
            "n_corridor": int(self.corridor_idx.size), "track": self.track.to_dict(),
            "timing_ms": {k: round(v, 2) for k, v in self.timing_ms.items()},
        }


class Detector:
    """Stateful detector: keeps the smoothed track model and the tracker between frames."""

    def __init__(self, cfg: Optional[DetectorConfig] = None):
        self.cfg = cfg or DetectorConfig()
        self.track: Optional[TrackModel] = None
        self.tracker = Tracker(self.cfg.tracking)

    def reset(self) -> None:
        self.track = None
        self.tracker.reset()

    def process(self, frame: Frame) -> FrameResult:
        cfg = self.cfg
        t0 = time.perf_counter()
        xyz = frame.xyz

        # 1. track model: bed profile, rail head level, track axis
        self.track = estimate_track(xyz, cfg.track, prev=self.track)
        t1 = time.perf_counter()

        # 2. clearance gauge corridor (warning zone) and strict gauge membership
        mask, strict = corridor_mask(xyz, self.track, cfg.gauge)
        idx = np.flatnonzero(mask)
        cand = xyz[idx]
        dy, h = corridor_coordinates(cand, self.track)
        t2 = time.perf_counter()

        # 3. voxelise + cluster + describe + filter
        valid = min(self.track.axis_valid, self.track.floor_range[1] + cfg.track.floor_valid_margin)
        clusters = find_clusters(cand, frame.intensity[idx], dy, h, strict[idx], cfg.cluster, frame_idx=idx,
                                 axis_valid=valid)
        t3 = time.perf_counter()

        # 4. temporal persistence
        self.tracker.update(clusters)
        dets: List[Detection] = []
        for t in self.tracker.confirmed():
            if t.last is None:
                continue
            dets.append(Detection(
                id=t.id, distance=t.last.distance, lateral=t.last.lateral, center=t.last.centroid,
                size=t.last.size, n_points=t.last.n, confidence=t.confidence, age=t.age,
                zone=t.zone, height_min=t.last.height_min, intensity=t.last.intensity,
            ))
        dets.sort(key=lambda d: d.distance)
        gauge = [d for d in dets if d.zone == "gauge"]
        warn = [d for d in dets if d.zone != "gauge"]
        t4 = time.perf_counter()

        return FrameResult(
            stamp=frame.stamp, obstacle=len(gauge) > 0, warning=len(warn) > 0,
            nearest_distance=gauge[0].distance if gauge else None,
            detections=gauge, warnings=warn, candidates=clusters, track=self.track,
            corridor_idx=idx, n_points=frame.n,
            timing_ms={"track": (t1 - t0) * 1e3, "corridor": (t2 - t1) * 1e3,
                       "cluster": (t3 - t2) * 1e3, "tracking": (t4 - t3) * 1e3,
                       "total": (t4 - t0) * 1e3},
        )
