"""End-to-end per-frame obstacle detection inside the clearance gauge."""
from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import List, Optional

import numpy as np

from resense.accumulate import CandidateBuffer
from resense.calibration import MountCalibrator
from resense.clustering import Cluster, find_clusters
from resense.config import DetectorConfig
from resense.egomotion import EgoSpeedEstimate, EgoSpeedEstimator
from resense.frame import Frame
from resense.gauge import corridor_coordinates, corridor_mask, gauge_core_mask
from resense.health import HealthMonitor
from resense.lowobj import BedTemplate, low_candidates
from resense.track import TrackModel, estimate_track
from resense.tracking import Tracker


def _overlap(a: Cluster, b: Cluster, margin: float = 0.3) -> bool:
    """Two clusters of the same object: their along-track extents and lateral widths overlap."""
    return (b.bbox_min[0] - margin < a.bbox_max[0] and b.bbox_max[0] + margin > a.bbox_min[0]
            and abs(b.lateral - a.lateral) < 0.5 * float(a.size[1] + b.size[1]) + margin)


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
    reason: str = ""           # v0.5 (additive): why the last cluster of an advisory track was demoted ('' = none)
    kind: str = ""             # v0.6 (additive): 'low' = a bump above the track bed, '' = corridor object

    def to_dict(self) -> dict:
        return {
            "id": int(self.id), "zone": self.zone, "distance": round(float(self.distance), 2),
            "lateral": round(float(self.lateral), 2),
            "center": [round(float(v), 2) for v in self.center],
            "size": [round(float(v), 2) for v in self.size],
            "n_points": int(self.n_points), "confidence": round(float(self.confidence), 3),
            "age": int(self.age), "height_min": round(float(self.height_min), 2),
            "intensity": round(float(self.intensity), 1),
            "reason": self.reason, "kind": self.kind,
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
    # --- additive since v0.4: ego motion and multi-frame accumulation ---
    ego_speed: Optional[float] = None      # m/s, the value the accumulation actually used (None = unknown)
    ego_speed_source: str = "none"         # 'given' | 'estimated' | 'none'
    n_accumulated: int = 1                 # frames merged into this result (1 = single frame)
    ego_speed_estimate: Optional[float] = None   # the estimator's own opinion, for diagnostics (None = not run / no estimate)
    ego_speed_confidence: float = 0.0      # confidence of the estimator's opinion, 0..1
    # --- additive since v0.6: production guards and mount calibration ---
    health: dict = field(default_factory=dict)   # resense.health.HealthMonitor.update(): level, messages, monitored range
    mount: dict = field(default_factory=dict)    # resense.calibration.MountCalibration.to_dict()
    clear_distance: float = 0.0            # m: nearest confirmed obstacle, else how far the corridor was verified clear
    xyz: Optional[np.ndarray] = None       # the processed cloud (vehicle frame after the mount correction), not serialised

    def to_dict(self) -> dict:
        return {
            "stamp": self.stamp, "obstacle": bool(self.obstacle), "warning": bool(self.warning),
            "nearest_distance": None if self.nearest_distance is None else round(float(self.nearest_distance), 2),
            "detections": [d.to_dict() for d in self.detections],
            "warnings": [d.to_dict() for d in self.warnings],
            "n_candidates": len(self.candidates), "n_points": int(self.n_points),
            "n_corridor": int(self.corridor_idx.size), "track": self.track.to_dict(),
            "timing_ms": {k: round(v, 2) for k, v in self.timing_ms.items()},
            "ego_speed": None if self.ego_speed is None else round(float(self.ego_speed), 2),
            "ego_speed_source": self.ego_speed_source,
            "n_accumulated": int(self.n_accumulated),
            "ego_speed_estimate": None if self.ego_speed_estimate is None else round(float(self.ego_speed_estimate), 2),
            "ego_speed_confidence": round(float(self.ego_speed_confidence), 3),
            "clear_distance": round(float(self.clear_distance), 1),
            "health": self.health,
            "mount": self.mount,
        }


class Detector:
    """Stateful detector: keeps the smoothed track model, the tracker, the candidate buffer
    of the multi-frame accumulation and the ego-speed estimator between frames."""

    def __init__(self, cfg: Optional[DetectorConfig] = None):
        self.cfg = cfg or DetectorConfig()
        self.track: Optional[TrackModel] = None
        self.tracker = Tracker(self.cfg.tracking)
        acc = self.cfg.accumulation
        self.buffer = CandidateBuffer(acc.n_frames if acc.enabled else 1, acc.max_points_per_frame)
        self.ego = EgoSpeedEstimator(acc)
        self.calib = MountCalibrator(self.cfg.calibration, self.cfg.track)
        self.health = HealthMonitor(self.cfg.health)
        self.bed = BedTemplate(self.cfg.lowobj)
        self.low_range = 0.0            # m, how far the bed was observed for the low-object stage (last frame)
        self._prev_stamp: Optional[float] = None

    @property
    def mount_rotation(self) -> np.ndarray:
        """R with ``p_processed = R @ p_configured_vehicle_frame`` (identity until the mount
        calibration applies a correction); outputs map back with ``R.T``."""
        return self.calib.R

    def reset(self) -> None:
        """Forget the scene (track model, tracks, buffers); the mount calibration is kept."""
        self.track = None
        self.tracker.reset()
        self.buffer.clear()
        self.ego.reset()
        self.health.reset()
        self.bed.reset()
        self._prev_stamp = None

    def _frame_dt(self, stamp: float) -> float:
        """Time since the previous frame from the stamps when they are sane, else the nominal
        frame period (cached frames and synthetic tests carry no usable stamp)."""
        dt = self.cfg.tracking.frame_dt
        if self._prev_stamp is not None:
            gap = float(stamp) - self._prev_stamp
            lo, hi = self.cfg.accumulation.stamp_dt_range
            if lo <= gap <= hi:
                dt = gap
        self._prev_stamp = float(stamp)
        return dt

    def process(self, frame: Frame, ego_speed: Optional[float] = None) -> FrameResult:
        """Detect obstacles in one frame.

        ``ego_speed`` is the train speed in m/s when the caller knows it (odometry topic or a
        parameter); ``None`` lets the detector estimate it from the tunnel texture. A given
        speed always wins. Without a usable speed no frames are accumulated.
        """
        cfg = self.cfg
        acc = cfg.accumulation
        t0 = time.perf_counter()
        xyz_cfg = frame.xyz
        if xyz_cfg.size and not np.isfinite(xyz_cfg).all():
            # production guard: a driver that leaves NaN / inf in the cloud must not poison the fits
            ok = np.isfinite(xyz_cfg).all(axis=1)
            frame = Frame(xyz=xyz_cfg[ok], intensity=frame.intensity[ok],
                          ring=frame.ring[ok] if frame.ring is not None else None, stamp=frame.stamp,
                          frame_id=frame.frame_id, meta=dict(frame.meta, n_nonfinite=int((~ok).sum())))
            xyz_cfg = frame.xyz
        xyz = self.calib.apply(xyz_cfg)

        # 1. track model: bed profile, rail head level, track axis
        self.track = estimate_track(xyz, cfg.track, prev=self.track)
        # 1b. mount calibration (first frames, then a drift check every few seconds)
        if self.calib.update(xyz_cfg, xyz, self.track):
            xyz = self.calib.apply(xyz_cfg)
            self.track = estimate_track(xyz, cfg.track, prev=None)      # re-seed in the corrected frame
            self.buffer.clear()                                         # merged clouds are in the old frame
            if self.calib.last_change_deg > 1.0:                        # a new orientation or a large tilt:
                self.tracker.reset()                                    # the tracks' positions are meaningless
        t1 = time.perf_counter()

        # 2. clearance gauge corridor (warning zone) and strict gauge membership; the corridor
        #    coordinates of the whole frame are computed once and shared with the estimator
        dy_all, h_all = corridor_coordinates(xyz, self.track)
        mask, strict = corridor_mask(xyz, self.track, cfg.gauge, dy_all, h_all)
        idx = np.flatnonzero(mask)
        cand = xyz[idx]
        dy, h = dy_all[idx], h_all[idx]
        in_gauge = strict[idx]
        if cfg.gauge.edge_margin > 0 or cfg.gauge.edge_margin_per_100m > 0:
            in_gauge = in_gauge & gauge_core_mask(dy, h, cand[:, 0], cfg.gauge)
        inten = frame.intensity[idx]
        # the corridor is trusted up to the axis range and the height-reference range; between
        # the two (v0.6) only tall clusters count (clustering.find_clusters, far_min_height)
        floor_valid = max(self.track.floor_range[1] + cfg.track.floor_valid_margin, self.track.floor_verified)
        axis_valid = min(self.track.axis_valid, cfg.gauge.range_max)
        valid = min(axis_valid, floor_valid) if cfg.cluster.far_min_height <= 0 else axis_valid
        if cfg.gauge.no_rail_range > 0 and self.track.rail_slabs == 0:
            # v0.6.2: no rail pair in the near range (station, switch cavern): the axis rests on
            # the walls alone, so far clusters are advisory (the tracker's zone vote smooths it)
            valid = min(valid, cfg.gauge.no_rail_range)

        # 2b. low objects on the track bed (v0.6): bumps above the learned bed cross-section,
        #     below the polygon bottom, where the bed is observed (resense/lowobj.py)
        low_flag = np.zeros(idx.size, dtype=bool)
        self.low_range = 0.0
        straddle_idx = np.zeros(0, dtype=np.int64)
        if cfg.lowobj.enabled:
            X_all = xyz[:, 0]
            if self.track.rail_score >= cfg.track.rails_min_score:
                self.bed.update(X_all, dy_all, h_all)
            h_bottom = float(np.asarray(cfg.gauge.profile, dtype=np.float64)[:, 1].min())
            lidx, self.low_range, lall = low_candidates(X_all, dy_all, h_all, self.bed, cfg.lowobj,
                                                        cfg.gauge.range_min, min(axis_valid, floor_valid),
                                                        h_bottom, with_all=True)
            lidx = lidx[~mask[lidx]] if lidx.size else lidx
            if cfg.lowobj.straddle_enabled and lall.size:
                # (v0.6.2) every bed anomaly plus the corridor points just above the envelope floor,
                # where the bed is observed: an object lying across a rail is clustered whole
                ch = h_all[idx]
                band = ((ch < h_bottom + cfg.lowobj.straddle_band) & (X_all[idx] < self.low_range)
                        & (np.abs(dy_all[idx]) <= cfg.lowobj.half_width))
                straddle_idx = np.unique(np.concatenate([lall[~mask[lall]], idx[band]]))
            if lidx.size:
                idx = np.concatenate([idx, lidx])
                cand = xyz[idx]
                dy, h = dy_all[idx], h_all[idx]
                in_gauge = np.concatenate([in_gauge, np.ones(lidx.size, dtype=bool)])
                inten = frame.intensity[idx]
                low_flag = np.concatenate([low_flag, np.ones(lidx.size, dtype=bool)])
        t2 = time.perf_counter()

        # 3. ego speed: given > estimated > unknown
        dt = self._frame_dt(frame.stamp)
        est: Optional[EgoSpeedEstimate] = None
        # the estimator costs 7-12 ms on real frames (review 21.09): skip it when the caller
        # already knows the speed; `resense run` without a speed still exercises it
        if acc.estimate_speed and ego_speed is None:
            est = self.ego.estimate(xyz, self.track, dt, self.tracker.tracks, dy_all, h_all)
        if ego_speed is not None:
            speed, source = float(ego_speed), "given"
        elif est is not None and est.speed is not None:
            speed, source = float(est.speed), "estimated"
        else:
            speed, source = None, "none"
        t3 = time.perf_counter()

        # 4. multi-frame accumulation of the far candidates (track coordinates, shifted by v*dt)
        n_acc = 1
        xyz_c, dy_c, h_c, g_c, i_c, fidx, low_c = cand, dy, h, in_gauge, inten, idx, low_flag
        if acc.enabled and acc.n_frames > 1:
            if speed is None or abs(speed) < acc.min_speed:
                self.buffer.clear()                     # unknown motion (merging would smear) or a stopped train (nothing to gain)
            else:
                self.buffer.shift(speed * dt)
                old = self.buffer.merged(acc.min_range)
                if old is not None:
                    Xo, dyo, ho, io, go = old
                    Xo64 = Xo.astype(np.float64)
                    xyz_o = np.stack([Xo64, self.track.center_y(Xo64) + dyo, self.track.rail_z(Xo64) + ho],
                                     axis=1).astype(np.float32)
                    xyz_c = np.concatenate([cand, xyz_o])
                    dy_c = np.concatenate([dy, dyo])
                    h_c = np.concatenate([h, ho])
                    g_c = np.concatenate([in_gauge, go])
                    i_c = np.concatenate([inten, io])
                    fidx = np.concatenate([idx, np.full(Xo.size, -1, dtype=idx.dtype)])
                    low_c = np.concatenate([low_flag, np.zeros(Xo.size, dtype=bool)])
                    n_acc = 1 + len(self.buffer)
                far = (cand[:, 0] >= acc.min_range) & ~low_flag
                self.buffer.push(cand[far, 0], dy[far], h[far], inten[far], in_gauge[far])
        t4 = time.perf_counter()

        # 5. voxelise + cluster + describe + filter (count thresholds scaled for the merged frames)
        factor = max(1.0, n_acc * acc.min_points_scale) if n_acc > 1 else 1.0
        corr = ~low_c
        clusters = find_clusters(xyz_c[corr], i_c[corr], dy_c[corr], h_c[corr], g_c[corr], cfg.cluster,
                                 frame_idx=fidx[corr], axis_valid=valid,
                                 height_valid=floor_valid if cfg.cluster.far_min_height > 0 else None,
                                 min_points_factor=factor, factor_range=acc.min_range,
                                 smear_max_length=acc.smear_max_length if n_acc > 1 else 0.0,
                                 smear_max_width=acc.smear_max_width if n_acc > 1 else 0.0)
        lows: List[Cluster] = []
        straddling: List[Cluster] = []
        lcfg = replace(cfg.cluster, eps=cfg.lowobj.eps)
        if low_c.any():
            # low candidates are clustered on their own with a tighter radius: at 50 m the corridor
            # radius (0.8 m) merges a 30 cm object with the bed fixtures around it (v0.6 review)
            lows = find_clusters(xyz_c[low_c], i_c[low_c], dy_c[low_c], h_c[low_c], g_c[low_c], lcfg,
                                 frame_idx=fidx[low_c], axis_valid=valid,
                                 low=np.ones(int(low_c.sum()), dtype=bool), low_cfg=cfg.lowobj)
        if straddle_idx.size >= 3:
            si = straddle_idx
            scfg = replace(cfg.lowobj, min_top=cfg.lowobj.straddle_min_top,
                           min_width=cfg.lowobj.straddle_min_width, max_length=cfg.lowobj.straddle_max_length)
            straddling = find_clusters(xyz[si], frame.intensity[si], dy_all[si], h_all[si],
                                       np.ones(si.size, dtype=bool), lcfg, frame_idx=si, axis_valid=valid,
                                       low=np.ones(si.size, dtype=bool), low_cfg=scfg)
            # a straddling cluster is the whole of what the point-wise low stage saw a slice of
            lows = [c for c in lows if not any(_overlap(c, k) for k in straddling)] + straddling
        if lows:
            # the foot of something taller (a sign, a column, a person) belongs to the corridor stage,
            # which may have demoted it: drop low clusters with corridor points high above them
            Xc, dyc, hc = xyz_c[corr, 0], dy_c[corr], h_c[corr]
            tall = hc > cfg.lowobj.foot_max_top
            Xc, dyc = Xc[tall], dyc[tall]
            keep = []
            for c in lows:
                m = ((Xc > c.bbox_min[0] - 0.3) & (Xc < c.bbox_max[0] + 0.3)
                     & (np.abs(dyc - c.lateral) < 0.5 * float(c.size[1]) + 0.3))
                if int(m.sum()) >= 3:
                    continue
                # the lower part of an object the corridor stage already reports: one detection, not two
                # (a straddling cluster yields only to a corridor cluster that is itself reported)
                strad = any(c is k for k in straddling)
                dup = any(_overlap(c, k) for k in clusters
                          if not strad or (k.zone == "gauge" and not k.reason))
                if not dup:
                    keep.append(c)
            clusters = sorted(clusters + keep, key=lambda c: c.distance)
        t5 = time.perf_counter()

        # 6. temporal persistence (in seconds: the tracker gets the measured frame interval)
        self.tracker.update(clusters, ego_shift=(speed or 0.0) * dt, frame_dt=dt)
        dets: List[Detection] = []
        for t in self.tracker.confirmed():
            if t.last is None:
                continue
            dets.append(Detection(
                id=t.id, distance=t.last.distance, lateral=t.last.lateral, center=t.last.centroid,
                size=t.last.size, n_points=t.last.n, confidence=t.confidence, age=t.age,
                zone=t.zone, height_min=t.last.height_min, intensity=t.last.intensity,
                reason=t.last.reason, kind=t.last.kind,
            ))
        dets.sort(key=lambda d: d.distance)
        gauge = [d for d in dets if d.zone == "gauge"]
        warn = [d for d in dets if d.zone != "gauge"]
        t6 = time.perf_counter()
        mount = self.calib.state.to_dict()
        health = self.health.update(xyz, frame.meta, self.track, cfg.gauge, valid, cfg.track.rails_min_score,
                                    (t6 - t0) * 1e3, mount, gauge[0].distance if gauge else None)

        return FrameResult(
            stamp=frame.stamp, obstacle=len(gauge) > 0, warning=len(warn) > 0,
            nearest_distance=gauge[0].distance if gauge else None,
            detections=gauge, warnings=warn, candidates=clusters, track=self.track,
            corridor_idx=idx, n_points=frame.n,
            timing_ms={"track": (t1 - t0) * 1e3, "corridor": (t2 - t1) * 1e3,
                       "egomotion": (t3 - t2) * 1e3, "accumulate": (t4 - t3) * 1e3,
                       "cluster": (t5 - t4) * 1e3, "tracking": (t6 - t5) * 1e3,
                       "total": (t6 - t0) * 1e3},
            ego_speed=speed, ego_speed_source=source, n_accumulated=n_acc,
            ego_speed_estimate=None if est is None else est.speed,
            ego_speed_confidence=0.0 if est is None else est.confidence,
            health=health, mount=mount, clear_distance=health["clear_distance"], xyz=xyz,
        )
