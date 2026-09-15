"""Temporal persistence: a light multi-object tracker in the vehicle frame.

Without odometry a static obstacle moves towards the vehicle by v*dt per frame, so the
association gate is widened by ``ego_speed_max * frame_dt`` along X. Confidence grows
with consecutive hits and decays with misses; only confirmed tracks are reported.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from resense.clustering import Cluster
from resense.config import TrackingConfig


@dataclass
class Track:
    id: int
    centroid: np.ndarray
    velocity: np.ndarray            # (3,) m/frame, estimated from consecutive matches
    hits: int = 1
    misses: int = 0
    age: int = 1
    confidence: float = 0.0
    last: Optional[Cluster] = None
    history: List[float] = field(default_factory=list)  # distances

    gauge_hits: int = 0             # frames in which the cluster was inside the strict gauge
    zone_hist: List[bool] = field(default_factory=list)   # last 5 hits: inside strict gauge?

    @property
    def zone(self) -> str:
        if not self.zone_hist:
            return "warning"
        return "gauge" if sum(self.zone_hist) * 2 >= len(self.zone_hist) else "warning"


class Tracker:
    def __init__(self, cfg: TrackingConfig):
        self.cfg = cfg
        self.tracks: List[Track] = []
        self._next_id = 1

    def reset(self) -> None:
        self.tracks.clear()
        self._next_id = 1

    def _gate(self, distance: float) -> float:
        c = self.cfg
        return c.gate_base + c.gate_per_m * max(distance, 0.0)

    def update(self, clusters: List[Cluster]) -> List[Track]:
        c = self.cfg
        step = c.ego_speed_max * c.frame_dt
        n_t, n_c = len(self.tracks), len(clusters)
        matched_t = np.zeros(n_t, dtype=bool)
        matched_c = np.zeros(n_c, dtype=bool)
        if n_t and n_c:
            # greedy nearest-neighbour association on predicted positions
            pred = np.stack([t.centroid + t.velocity for t in self.tracks])
            cen = np.stack([cl.centroid for cl in clusters])
            d = np.linalg.norm(pred[:, None, :] - cen[None, :, :], axis=2)
            # along-track motion towards the vehicle is allowed up to ``step`` extra
            dx = cen[None, :, 0] - pred[:, 0][:, None]   # <0: cluster is closer than predicted
            allowed = np.array([self._gate(t.centroid[0]) for t in self.tracks])[:, None] + np.where(dx < 0, step, 0.0)
            d = np.where(d <= allowed, d, np.inf)
            while True:
                if not np.isfinite(d).any():
                    break
                i, j = np.unravel_index(np.argmin(d), d.shape)
                t, cl = self.tracks[i], clusters[j]
                t.velocity = 0.5 * t.velocity + 0.5 * (cl.centroid - t.centroid) if t.hits > 1 else (cl.centroid - t.centroid)
                t.centroid = cl.centroid
                t.hits += 1
                t.misses = 0
                t.age += 1
                t.confidence = min(1.0, t.confidence + c.conf_gain * cl.score)
                t.last = cl
                t.gauge_hits += int(cl.zone == "gauge")
                t.zone_hist = (t.zone_hist + [cl.zone == "gauge"])[-5:]
                t.history.append(cl.distance)
                matched_t[i] = matched_c[j] = True
                d[i, :] = np.inf
                d[:, j] = np.inf
        # unmatched tracks
        for i, t in enumerate(self.tracks):
            if not matched_t[i]:
                t.misses += 1
                t.age += 1
                t.centroid = t.centroid + t.velocity
                t.confidence = max(0.0, t.confidence - c.conf_decay)
        self.tracks = [t for t in self.tracks if t.misses <= c.max_misses]
        # new tracks
        for j, cl in enumerate(clusters):
            if not matched_c[j]:
                self.tracks.append(Track(
                    id=self._next_id, centroid=cl.centroid, velocity=np.zeros(3),
                    confidence=c.conf_gain * cl.score, last=cl, history=[cl.distance],
                    gauge_hits=int(cl.zone == "gauge"), zone_hist=[cl.zone == "gauge"],
                ))
                self._next_id += 1
        return self.tracks

    def confirmed(self) -> List[Track]:
        c = self.cfg
        return [t for t in self.tracks
                if t.hits >= c.confirm_hits and t.confidence >= c.conf_threshold and t.misses == 0]
