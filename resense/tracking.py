"""Temporal persistence: a light multi-object tracker in the vehicle frame.

Without odometry a static obstacle moves towards the vehicle by v*dt per frame, so the
association gate is widened by ``ego_speed_max * frame_dt`` along X. Confidence grows
with consecutive hits and decays with misses; only confirmed tracks are reported.

Persistence (v0.5) is measured in *time*, not only in processed frames: a track is
confirmed when it has ``confirm_hits`` hits, it has been observed for at least
``confirm_time_s`` of sensor time (frames x the frame interval the caller passes to
:meth:`Tracker.update`, the first frame included, so 0.3 s = 3 frames at 10 Hz and 3 frames
at any lower rate too; a caller that never passes an interval gets hit counting only), it
was matched in at least ``min_hit_fraction`` of its last ``hit_window`` frames, and it is
matched now. Its zone is 'gauge' when at least ``zone_min_fraction`` of its last
``zone_window`` hits were inside the strict gauge, so a corridor-edge structure that
flickers into the gauge every other frame is advisory (docs/EXPERIMENTS.md section 1b), and
fewer than ``column_hold`` (2 since 25.09) of those hits were demoted as a column: a column far
away shows more than ``column_min_height`` of itself in some frames only (EXPERIMENTS.md 3a).
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
    zone_hist: List[bool] = field(default_factory=list)   # last zone_window hits: inside strict gauge?
    hit_hist: List[bool] = field(default_factory=list)    # last hit_window frames: matched?
    span_s: float = 0.0             # seconds of sensor time the track has been observed (frames x interval, first frame included)
    zone_min_fraction: float = 0.5  # share of zone_hist that must be inside the gauge
    reported: bool = False          # reported as an obstacle / advisory after the last update
    column_hist: List[bool] = field(default_factory=list)  # last zone_window hits: demoted as a column?
    column_hold: int = 0            # this many column hits in column_hist keep the track advisory (0 = off)
    hold: int = 0                   # 26.09: frames left of a calibration re-seed hold (Tracker.reseed)
    seen_reported: bool = False     # 26.09: reported in the frame of its last match (health.clear_cap_lost)

    @property
    def zone(self) -> str:
        if not self.zone_hist:
            return "warning"
        if self.column_hold > 0 and sum(self.column_hist) >= self.column_hold:
            return "warning"
        return "gauge" if sum(self.zone_hist) >= self.zone_min_fraction * len(self.zone_hist) - 1e-9 else "warning"

    @property
    def hit_fraction(self) -> float:
        return (sum(self.hit_hist) / len(self.hit_hist)) if self.hit_hist else 1.0


class Tracker:
    def __init__(self, cfg: TrackingConfig):
        self.cfg = cfg
        self.tracks: List[Track] = []
        self._next_id = 1
        self._timed = False          # a frame interval was supplied at least once

    def reset(self) -> None:
        self.tracks.clear()
        self._next_id = 1
        self._timed = False

    def reseed(self, dR: np.ndarray, hold: int, keep_unreported: bool = True) -> None:
        """A mount-calibration change rotated the cloud by ``dR`` (``p_new = dR @ p_old``; 26.09,
        ``tracking.reseed_hold``): every track's position and velocity are rotated with it, the
        tracks not reported now are dropped unless ``keep_unreported`` (a large tilt change: their
        history was taken in a wrong frame, as the reset did before), and a reported track stays
        reported without a match until ``hold`` frames after its last match: its misses there
        neither decay its confidence nor enter its hit history, and it is reported at its
        predicted position. Repeated re-seeds do not extend that. The re-seeded geometry (a fresh
        track model has no floor-shadow reference for its warm-up) must not drop a confirmed STOP."""
        dR = np.asarray(dR, dtype=np.float64)
        if not keep_unreported:
            self.tracks = [t for t in self.tracks if t.reported]
        for t in self.tracks:
            t.centroid = dR @ t.centroid
            t.velocity = dR @ t.velocity
            if t.reported:
                t.hold = max(t.hold, int(hold) - t.misses)

    def _gate(self, distance: float) -> float:
        c = self.cfg
        return c.gate_base + c.gate_per_m * max(distance, 0.0)

    def update(self, clusters: List[Cluster], ego_shift: float = 0.0,
               frame_dt: Optional[float] = None) -> List[Track]:
        """Associate ``clusters`` with the tracks. ``ego_shift`` (m) is the distance the
        vehicle travelled since the previous frame when it is known: a track seen once has no
        velocity yet and is then predicted as a static object approaching by that much.
        ``frame_dt`` (s) is the interval since the previous frame; it accumulates each track's
        observed time for the ``confirm_time_s`` rule (without it persistence counts hits only)."""
        c = self.cfg
        # widen the gate by the distance a static object travels in the *measured* interval, so a
        # dropped frame (0.2-0.3 s gap in the node) does not throw a 17 m/s approach out of the gate
        step = c.ego_speed_max * (float(frame_dt) if frame_dt is not None and frame_dt > 0 else c.frame_dt)
        if frame_dt is not None:
            self._timed = True
        dt = float(frame_dt) if frame_dt is not None else 0.0
        n_t, n_c = len(self.tracks), len(clusters)
        matched_t = np.zeros(n_t, dtype=bool)
        matched_c = np.zeros(n_c, dtype=bool)
        zw, hw = max(1, int(c.zone_window)), max(1, int(c.hit_window))
        if n_t and n_c:
            # greedy nearest-neighbour association on predicted positions
            static = np.array([-float(ego_shift), 0.0, 0.0])
            pred = np.stack([t.centroid + (t.velocity if t.hits > 1 else static) for t in self.tracks])
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
                t.span_s += dt
                t.confidence = min(1.0, t.confidence + c.conf_gain * cl.score)
                t.last = cl
                t.gauge_hits += int(cl.zone == "gauge")
                t.zone_hist = (t.zone_hist + [cl.zone == "gauge"])[-zw:]
                t.column_hist = (t.column_hist + [cl.reason == "column"])[-zw:]
                t.hit_hist = (t.hit_hist + [True])[-hw:]
                t.history.append(cl.distance)
                t.hold = 0
                matched_t[i] = matched_c[j] = True
                d[i, :] = np.inf
                d[:, j] = np.inf
        # unmatched tracks
        for i, t in enumerate(self.tracks):
            if not matched_t[i]:
                t.misses += 1
                t.age += 1
                t.span_s += dt
                t.centroid = t.centroid + t.velocity
                if t.hold > 0:              # a calibration re-seed hold: this miss does not count
                    continue
                t.confidence = max(0.0, t.confidence - c.conf_decay)
                t.hit_hist = (t.hit_hist + [False])[-hw:]
        self.tracks = [t for t in self.tracks if t.misses <= c.max_misses or (t.hold > 0 and t.reported)]
        # new tracks
        for j, cl in enumerate(clusters):
            if not matched_c[j]:
                self.tracks.append(Track(
                    id=self._next_id, centroid=cl.centroid, velocity=np.zeros(3),
                    confidence=c.conf_gain * cl.score, last=cl, history=[cl.distance],
                    gauge_hits=int(cl.zone == "gauge"), zone_hist=[cl.zone == "gauge"], hit_hist=[True],
                    span_s=dt, zone_min_fraction=c.zone_min_fraction,
                    column_hist=[cl.reason == "column"], column_hold=int(c.column_hold),
                ))
                self._next_id += 1
        # reported: confirmed now, or reported in the previous frame and missed for at most
        # hold_misses frames (a single missed frame does not drop a STOP; review 23.09)
        for t in self.tracks:
            t.reported = (self._qualifies(t) or (t.reported and 0 < t.misses <= c.hold_misses)
                          or (t.reported and t.misses > 0 and t.hold > 0))
            if t.misses == 0:
                t.seen_reported = t.reported
            elif t.hold > 0:
                t.hold -= 1
        return self.tracks

    def _qualifies(self, t: Track) -> bool:
        c = self.cfg
        need_span = c.confirm_time_s if (self._timed and c.confirm_time_s > 0) else 0.0
        return (t.hits >= (c.low_confirm_hits if (t.last is not None and t.last.kind == "low") else c.confirm_hits)
                and t.confidence >= c.conf_threshold and t.misses == 0
                and t.span_s >= need_span - 1e-9
                and (c.min_hit_fraction <= 0 or t.hit_fraction >= c.min_hit_fraction - 1e-9))

    def confirmed(self) -> List[Track]:
        """The tracks reported after the last ``update``: confirmed in this frame, or held over
        ``hold_misses`` missed frames after being reported (their cluster is the last matched one)."""
        return [t for t in self.tracks if t.reported]
