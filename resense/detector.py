"""End-to-end per-frame obstacle detection inside the clearance gauge."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field, fields, replace
from typing import List, Optional

import numpy as np

from resense.accumulate import CandidateBuffer
from resense.calibration import MountCalibrator
from resense.clustering import Cluster, find_clusters, find_hanging
from resense.config import DetectorConfig
from resense.egomotion import EgoSpeedEstimate, EgoSpeedEstimator
from resense.frame import Frame
from resense.gauge import (axis_union_coordinates, axis_union_offset, axis_union_strict, corridor_coordinates,
                           corridor_mask, gauge_core_mask, point_in_polygon, widened_profile)
from resense.health import HealthMonitor
from resense.lowobj import BedTemplate, low_candidates, mark_rail_line
from resense.track import TrackModel, estimate_track, rotate_track_model
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
    reason: str = ""           # v0.5 (additive): why the last cluster of an advisory track was demoted ('' = none); 26.09: 'near_envelope' on an obstacle only by tracking.near_escalate_*
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


@dataclass
class Candidates:
    """The points handed to the clustering: vehicle coordinates, track coordinates (``dy``
    lateral to the axis, ``h`` above the rail head), strict-gauge membership, intensity, the
    index in the frame (``-1``: merged from an earlier frame by the accumulation) and the
    low-object flag (a bump above the track bed, below the envelope floor)."""
    xyz: np.ndarray
    dy: np.ndarray
    h: np.ndarray
    in_gauge: np.ndarray
    intensity: np.ndarray
    idx: np.ndarray
    low: np.ndarray

    def __len__(self) -> int:
        return int(self.idx.size)

    def concat(self, other: "Candidates") -> "Candidates":
        return Candidates(**{f.name: np.concatenate([getattr(self, f.name), getattr(other, f.name)])
                             for f in fields(self)})

    def subset(self, m: np.ndarray) -> "Candidates":
        return Candidates(**{f.name: getattr(self, f.name)[m] for f in fields(self)})


def _clusters_of(c: Candidates, cfg, **kw) -> List[Cluster]:
    return find_clusters(c.xyz, c.intensity, c.dy, c.h, c.in_gauge, cfg, frame_idx=c.idx, **kw)


def _finite_only(frame: Frame) -> Frame:
    """Production guard: a driver that leaves NaN / inf in the cloud must not poison the fits."""
    xyz = frame.xyz
    if not xyz.size or np.isfinite(xyz).all():
        return frame
    ok = np.isfinite(xyz).all(axis=1)
    return Frame(xyz=xyz[ok], intensity=frame.intensity[ok],
                 ring=frame.ring[ok] if frame.ring is not None else None, stamp=frame.stamp,
                 frame_id=frame.frame_id, meta=dict(frame.meta, n_nonfinite=int((~ok).sum())))


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
        self._gaps: deque = deque(maxlen=14)  # the last stamp intervals within [0, stamp_dt_range[1]] (s): the input rate

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
        self._gaps.clear()

    def _frame_dt(self, stamp: float) -> float:
        """Time since the previous frame from the stamps when they are sane, else the nominal
        frame period (cached frames and synthetic tests carry no usable stamp)."""
        dt = self.cfg.tracking.frame_dt
        if self._prev_stamp is not None:
            gap = float(stamp) - self._prev_stamp
            lo, hi = self.cfg.accumulation.stamp_dt_range
            if lo <= gap <= hi:
                dt = gap
            if 0.0 <= gap <= hi:
                self._gaps.append(gap)          # the input rate: in-burst intervals included (_periods)
        self._prev_stamp = float(stamp)
        return dt

    def process(self, frame: Frame, ego_speed: Optional[float] = None) -> FrameResult:
        """Detect obstacles in one frame.

        ``ego_speed`` is the train speed in m/s when the caller knows it (odometry topic or a
        parameter); ``None`` lets the detector estimate it from the tunnel texture. A given
        speed always wins. Without a usable speed no frames are accumulated.

        The stages are the methods below, in this order (docs/ALGORITHM.md has the reasoning):
        ``_fit_track`` (1, 1b), ``_corridor`` (2), ``_low_stage`` (2b), ``_speed`` (3),
        ``_accumulate`` (4), ``_cluster`` (5), ``_hanging`` (5b, 25.09), ``_confirm`` (6).
        """
        cfg = self.cfg
        t0 = time.perf_counter()
        frame = _finite_only(frame)
        dt = self._frame_dt(frame.stamp)
        xyz = self._fit_track(frame.xyz, self._periods())
        t1 = time.perf_counter()
        cand, dy_all, h_all, mask, (valid, axis_valid, floor_valid) = self._corridor(xyz, frame.intensity)
        dy_rail = self._dy_rail          # = dy_all unless gauge.axis_union 2 re-measured the corridor coordinate
        cand, straddle, near = self._low_stage(xyz, frame.intensity, dy_rail, h_all, mask, cand,
                                               min(axis_valid, floor_valid))
        t2 = time.perf_counter()
        speed, source, est = self._speed(xyz, dy_rail, h_all, dt, ego_speed)
        t3 = time.perf_counter()
        merged, n_acc = self._accumulate(cand, speed, dt)
        t4 = time.perf_counter()
        clusters = self._cluster(merged, n_acc, valid, floor_valid, straddle, near)
        if cfg.cluster.far_axis_both_sides == 2:
            valid = self._far_both_sides(clusters, valid, floor_valid)
        if cfg.cluster.hanging_enabled and (not cfg.cluster.hanging_needs_rails or self.track.rail_slabs > 0):
            clusters = self._hanging(xyz, frame.intensity, dy_all, h_all, cand, clusters, min(valid, floor_valid))
        if cfg.lowobj.rail_start_within > 0:
            # 26.09 (P3 rail start): low clusters near the train that are rail geometry; the rail lines
            # are at the axis +- rails_spacing / 2 of the rail coordinate (dy_rail, as the low stage)
            mark_rail_line(clusters, xyz[:, 0], dy_rail, h_all, cfg.lowobj, cfg.track.rails_spacing, cfg.gauge.range_min)
        t5 = time.perf_counter()
        gauge, warn = self._confirm(clusters, speed, dt)
        cap = self._clear_cap(clusters, cand, dy_all, h_all) if cfg.health.clear_cap else None
        t6 = time.perf_counter()
        mount = self.calib.state.to_dict()
        health = self.health.update(xyz, frame.meta, self.track, cfg.gauge, valid, cfg.track.rails_min_score,
                                    (t6 - t0) * 1e3, mount, gauge[0].distance if gauge else None, cap)

        return FrameResult(
            stamp=frame.stamp, obstacle=len(gauge) > 0, warning=len(warn) > 0,
            nearest_distance=gauge[0].distance if gauge else None,
            detections=gauge, warnings=warn, candidates=clusters, track=self.track,
            corridor_idx=cand.idx, n_points=frame.n,
            timing_ms={"track": (t1 - t0) * 1e3, "corridor": (t2 - t1) * 1e3,
                       "egomotion": (t3 - t2) * 1e3, "accumulate": (t4 - t3) * 1e3,
                       "cluster": (t5 - t4) * 1e3, "tracking": (t6 - t5) * 1e3,
                       "total": (t6 - t0) * 1e3},
            ego_speed=speed, ego_speed_source=source, n_accumulated=n_acc,
            ego_speed_estimate=None if est is None else est.speed,
            ego_speed_confidence=0.0 if est is None else est.confidence,
            health=health, mount=mount, clear_distance=health["clear_distance"], xyz=xyz,
        )

    def _periods(self) -> int:
        """Nominal frame periods (``tracking.frame_dt``) per processed frame at the current input
        rate: the mean of the last 14 stamp intervals between 0 and the upper end of
        ``accumulation.stamp_dt_range`` (= (t_last - t_first) / (n - 1) over the last 15 stamps of
        a run without a pause or a step back), rounded, clamped to 1-5 (1 on the first frame). 1 at
        10 Hz, 2 at 5 Hz. Recorded receive stamps come in bursts (0.2-0.45 s, then 0.02 s: the
        ride): a single interval is not used, and since 26.09 (safety review) the short in-burst
        intervals are counted too - the median of the last 9 without the ones under 0.02 s made
        alternating 0.19 / 0.01 s stamps 2 periods and 0.29 / 0.005 / 0.005 s 3. (Over 10 stamps
        one ride frame, after a run of late receive stamps with a mean of 0.151 s, became 2
        periods; over 15 every 10 Hz frame of the seven recordings and the ride is 1, as before.)
        The track model (``rates_per_period``,
        ``walls_smoothing_per_period``) and the mount calibration (``time_cadence``) count these
        instead of frames when enabled."""
        nominal = self.cfg.tracking.frame_dt
        if not self._gaps or nominal <= 0:
            return 1
        return min(5, max(1, int(round(float(np.mean(self._gaps)) / nominal))))

    # -- 1, 1b ---------------------------------------------------------------------------------
    def _fit_track(self, xyz_cfg: np.ndarray, periods: int = 1) -> np.ndarray:
        """Track model (bed profile, rail-head level, axis) and the mount calibration (first
        frames, then a drift check every few seconds). Returns the cloud in the corrected frame."""
        cfg = self.cfg
        xyz = self.calib.apply(xyz_cfg)
        self.track = estimate_track(xyz, cfg.track, prev=self.track, periods=periods)
        R_old = self.calib.R.copy()
        if self.calib.update(xyz_cfg, xyz, self.track, periods=periods):
            xyz = self.calib.apply(xyz_cfg)
            dR = self.calib.R @ R_old.T                                 # p_new = dR @ p_old
            change, orient = self.calib.last_change_deg, self.calib.last_change_orientation
            keep = cfg.calibration.reseed_keep_max_deg
            hold = cfg.tracking.reseed_hold
            if keep > 0 and not orient and change <= keep:
                # 26.09 (safety review): a sub-degree change keeps the model, rotated into the
                # corrected frame (bed, rail head, axis, age, the floor-shadow reference); the
                # accumulation buffer is in track coordinates, which the rotation leaves as they are
                self.track = rotate_track_model(self.track, dR)
            else:
                self.track = estimate_track(xyz, cfg.track, prev=None)  # re-seed in the corrected frame
                self.buffer.clear()                                     # merged clouds are in the old frame
                # re-review 26.09: the hold window covers at least the frames the re-seeded model
                # has no floor-shadow reference (this one, then until its age reaches
                # axis_warmup_frames: 6 frames at 10 Hz, 4 at 5 Hz)
                k = max(1, int(periods)) if cfg.track.rates_per_period else 1
                hold = max(hold, 1 + -(-int(cfg.track.axis_warmup_frames) // k))
            if cfg.tracking.reseed_hold > 0 and not orient:
                # 26.09: the tracks follow the rotation; a STOP is held through the re-seed and, above
                # 1 deg, only STOPs are kept (the others' zone votes were taken in the old frame)
                self.tracker.reseed(dR, hold, keep_unreported=change <= 1.0)
            elif orient or change > 1.0:                                # a new orientation or a large tilt:
                self.tracker.reset()                                    # the tracks' positions are meaningless
        return xyz

    # -- 2 -------------------------------------------------------------------------------------
    def _corridor(self, xyz: np.ndarray, intensity: np.ndarray):
        """Clearance-gauge corridor (warning zone) and strict gauge membership. The corridor
        coordinates of the whole frame are computed once and shared with the later stages.

        Returns the corridor candidates, ``dy`` / ``h`` of every point, the corridor mask and
        ``(valid, axis_valid, floor_valid)``: the corridor is trusted up to the axis range and the
        height-reference range; between the two (v0.6) only tall clusters count
        (``clustering.find_clusters``, ``far_min_height``)."""
        cfg = self.cfg
        dy_all, h_all = corridor_coordinates(xyz, self.track)
        self._dy_rail = dy_all
        if cfg.gauge.axis_union == 2:
            # 26.09 (candidate B, off by default): the corridor coordinate re-measured so that the strict
            # envelope is the union of the rail and the sensor-axis envelopes (near field, straight
            # track); the bed, low-object and ego-speed stages keep the rail coordinate (self._dy_rail)
            dy_all = axis_union_coordinates(xyz[:, 0], dy_all, self.track, cfg.gauge)
        mask, strict = corridor_mask(xyz, self.track, cfg.gauge, dy_all, h_all)
        idx = np.flatnonzero(mask)
        cand = Candidates(xyz=xyz[idx], dy=dy_all[idx], h=h_all[idx], in_gauge=strict[idx],
                          intensity=intensity[idx], idx=idx, low=np.zeros(idx.size, dtype=bool))
        if cfg.gauge.edge_margin > 0 or cfg.gauge.edge_margin_per_100m > 0:
            cand.in_gauge = cand.in_gauge & gauge_core_mask(cand.dy, cand.h, cand.xyz[:, 0], cfg.gauge)
        if cfg.gauge.axis_union in (1, 3):
            # 26.09 (candidates A and B2, off by default): also inside when inside the envelope measured
            # from the sensor axis (near field, straight track, the two axes within axis_union_max_offset)
            ax = axis_union_strict(cand.xyz[:, 0], cand.dy, cand.h, self.track, cfg.gauge)
            if ax is not None:
                cand.in_gauge = cand.in_gauge | ax
        floor_valid = max(self.track.floor_range[1] + cfg.track.floor_valid_margin, self.track.floor_verified)
        axis_valid = min(self.track.axis_valid, cfg.gauge.range_max)
        valid = min(axis_valid, floor_valid) if cfg.cluster.far_min_height <= 0 else axis_valid
        if cfg.cluster.far_axis_both_sides == 1:
            # 25.09 (far_switch), opt-in, mode 1: beyond the height reference only as far as both
            # tunnel boundaries support the axis (a hall wall seen to 76 m bent the corridor by
            # 1.4-3.4 m at the 147.5 m switch parts); inside the height reference nothing changes
            valid = min(valid, max(min(self.track.axis_valid_both, cfg.gauge.range_max), floor_valid))
        if cfg.gauge.no_rail_range > 0 and self.track.rail_slabs == 0:
            # v0.6.2: no rail pair in the near range (station, switch cavern): the axis rests on
            # the walls alone, so far clusters are advisory (the tracker's zone vote smooths it)
            valid = min(valid, cfg.gauge.no_rail_range)
        return cand, dy_all, h_all, mask, (valid, axis_valid, floor_valid)

    # -- 2b ------------------------------------------------------------------------------------
    def _low_stage(self, xyz, intensity, dy_all, h_all, mask, cand: Candidates, bed_valid: float):
        """Low objects on the track bed (v0.6): bumps above the learned bed cross-section, below
        the polygon bottom, where the bed is observed (``resense/lowobj.py``); they are appended
        to the candidates with ``low`` set. Also returns the v0.6.2 straddle candidates (every
        bed anomaly plus the corridor points just above the envelope floor, so that an object
        lying across a rail is clustered whole), and the central near-bed candidates."""
        cfg = self.cfg
        self.low_range = 0.0
        if not cfg.lowobj.enabled:
            return cand, None, None
        X_all = xyz[:, 0]
        if self.track.rail_score >= cfg.track.rails_min_score:
            self.bed.update(X_all, dy_all, h_all)
        h_bottom = float(np.asarray(cfg.gauge.profile, dtype=np.float64)[:, 1].min())
        lidx, self.low_range, lall, nidx = low_candidates(X_all, dy_all, h_all, self.bed, cfg.lowobj,
                                                          cfg.gauge.range_min, bed_valid, h_bottom,
                                                          with_all=True, with_near=True)
        lidx = lidx[~mask[lidx]] if lidx.size else lidx
        straddle = None
        if cfg.lowobj.straddle_enabled and lall.size:
            idx = cand.idx
            band = ((h_all[idx] < h_bottom + cfg.lowobj.straddle_band) & (X_all[idx] < self.low_range)
                    & (np.abs(dy_all[idx]) <= cfg.lowobj.half_width))
            si = np.unique(np.concatenate([lall[~mask[lall]], idx[band]]))
            if si.size >= 3:
                ones = np.ones(si.size, dtype=bool)
                straddle = Candidates(xyz=xyz[si], dy=dy_all[si], h=h_all[si], in_gauge=ones,
                                      intensity=intensity[si], idx=si, low=ones)
        if lidx.size:
            ones = np.ones(lidx.size, dtype=bool)
            cand = cand.concat(Candidates(xyz=xyz[lidx], dy=dy_all[lidx], h=h_all[lidx], in_gauge=ones,
                                           intensity=intensity[lidx], idx=lidx, low=ones))
        near = None
        if nidx.size and self.track.rail_score >= cfg.track.rails_min_score:
            nidx = nidx[~mask[nidx]]
            ones = np.ones(nidx.size, dtype=bool)
            near = Candidates(xyz=xyz[nidx], dy=dy_all[nidx], h=h_all[nidx], in_gauge=ones,
                              intensity=intensity[nidx], idx=nidx, low=ones)
        return cand, straddle, near

    # -- 3 -------------------------------------------------------------------------------------
    def _speed(self, xyz, dy_all, h_all, dt: float, ego_speed: Optional[float]):
        """Ego speed: given > estimated > unknown. The estimator costs 7-12 ms on real frames
        (review 21.09): it is skipped when the caller already knows the speed."""
        est: Optional[EgoSpeedEstimate] = None
        if self.cfg.accumulation.estimate_speed and ego_speed is None:
            est = self.ego.estimate(xyz, self.track, dt, self.tracker.tracks, dy_all, h_all)
        if ego_speed is not None:
            return float(ego_speed), "given", est
        if est is not None and est.speed is not None:
            return float(est.speed), "estimated", est
        return None, "none", est

    # -- 4 -------------------------------------------------------------------------------------
    def _accumulate(self, cand: Candidates, speed: Optional[float], dt: float):
        """Multi-frame accumulation of the far corridor candidates (track coordinates, shifted
        by v*dt). Returns the candidates to cluster and the number of frames merged into them."""
        acc = self.cfg.accumulation
        if not (acc.enabled and acc.n_frames > 1):
            return cand, 1
        if speed is None or abs(speed) < acc.min_speed:
            self.buffer.clear()                 # unknown motion (merging would smear) or a stopped train (nothing to gain)
            return cand, 1
        merged, n_acc = cand, 1
        self.buffer.shift(speed * dt)
        old = self.buffer.merged(acc.min_range)
        if old is not None:
            Xo, dyo, ho, io, go = old
            Xo64 = Xo.astype(np.float64)
            xyz_o = np.stack([Xo64, self.track.center_y(Xo64) + dyo, self.track.rail_z(Xo64) + ho],
                             axis=1).astype(np.float32)
            merged = cand.concat(Candidates(xyz=xyz_o, dy=dyo, h=ho, in_gauge=go, intensity=io,
                                            idx=np.full(Xo.size, -1, dtype=cand.idx.dtype),
                                            low=np.zeros(Xo.size, dtype=bool)))
            n_acc = 1 + len(self.buffer)
        far = (cand.xyz[:, 0] >= acc.min_range) & ~cand.low
        self.buffer.push(cand.xyz[far, 0], cand.dy[far], cand.h[far], cand.intensity[far], cand.in_gauge[far])
        return merged, n_acc

    # -- 5 -------------------------------------------------------------------------------------
    def _cluster(self, cand: Candidates, n_acc: int, valid: float, floor_valid: float,
                 straddle: Optional[Candidates], near: Optional[Candidates] = None) -> List[Cluster]:
        """Voxelise, cluster, describe and filter: the corridor candidates (count thresholds
        scaled for merged frames), the low candidates on their own with a tighter radius, the
        straddle candidates; then the low clusters that are the foot or the lower part of a
        corridor object are dropped."""
        cfg = self.cfg
        acc = cfg.accumulation
        factor = max(1.0, n_acc * acc.min_points_scale) if n_acc > 1 else 1.0
        corr = cand.subset(~cand.low)
        dy_alt = None
        if cfg.gauge.axis_union == 3:
            # 26.09 (candidate B2, off by default): the lateral from the sensor axis for the shape rules
            reg = axis_union_offset(corr.xyz[:, 0], self.track, cfg.gauge)
            if reg is not None:
                dy_alt = corr.dy + reg[1]
        clusters = _clusters_of(corr, cfg.cluster, axis_valid=valid,
                                height_valid=floor_valid if cfg.cluster.far_min_height > 0 else None,
                                min_points_factor=factor, factor_range=acc.min_range,
                                smear_max_length=acc.smear_max_length if n_acc > 1 else 0.0,
                                smear_max_width=acc.smear_max_width if n_acc > 1 else 0.0, gauge=cfg.gauge,
                                dy_alt=dy_alt)
        lows: List[Cluster] = []
        straddling: List[Cluster] = []
        lcfg = replace(cfg.cluster, eps=cfg.lowobj.eps)
        if cand.low.any():
            # low candidates are clustered on their own with a tighter radius: at 50 m the corridor
            # radius (0.8 m) merges a 30 cm object with the bed fixtures around it (v0.6 review)
            low = cand.subset(cand.low)
            lows = _clusters_of(low, lcfg, axis_valid=valid, low=low.low, low_cfg=cfg.lowobj)
        if straddle is not None:
            scfg = replace(cfg.lowobj, min_top=cfg.lowobj.straddle_min_top,
                           min_width=cfg.lowobj.straddle_min_width, max_length=cfg.lowobj.straddle_max_length)
            straddling = _clusters_of(straddle, lcfg, axis_valid=valid, low=straddle.low, low_cfg=scfg)
            # a straddling cluster is the whole of what the point-wise low stage saw a slice of
            lows = [c for c in lows if not any(_overlap(c, k) for k in straddling)] + straddling
        if near is not None and len(near):
            ncfg = replace(cfg.lowobj, min_top=-1.0, min_width=cfg.lowobj.near_min_width,
                           max_width=cfg.lowobj.near_max_width, min_length=cfg.lowobj.near_min_length,
                           min_height=cfg.lowobj.near_min_height,
                           min_points=cfg.lowobj.near_min_points, max_length=cfg.lowobj.near_max_length)
            central = _clusters_of(near, lcfg, axis_valid=min(valid, cfg.lowobj.near_range),
                                   low=near.low, low_cfg=ncfg)
            # Candidates are restricted to the inner band before clustering; avoid a
            # second track for anything already accepted by the rail/straddle policies.
            central = [c for c in central if not any(_overlap(c, k) for k in lows)]
            lows += central
        if lows:
            keep = self._not_part_of_corridor_objects(lows, straddling, clusters, corr)
            clusters = sorted(clusters + keep, key=lambda c: c.distance)
        return clusters

    def _far_both_sides(self, clusters: List[Cluster], valid: float, floor_valid: float) -> float:
        """``cluster.far_axis_both_sides`` 2 (25.09, far_switch, opt-in): on a bent axis (no
        straight bonus) fitted to two boundaries, a corridor obstacle beyond the height reference
        and beyond the shorter boundary's range (+ ``axis_valid_margin``) is demoted to advisory
        ``beyond_axis``: the curvature that puts it in the corridor is not supported that far on
        both sides. Other clusters keep their reasons (a column stays a column hit). Returns the
        range the corridor is verified to (for the verified-clear distance)."""
        limit = max(min(self.track.axis_valid_bent, self.cfg.gauge.range_max), floor_valid)
        if limit >= valid:
            return valid
        for c in clusters:
            if c.kind == "" and c.zone == "gauge" and not c.reason and c.distance > limit:
                c.zone, c.reason = "warning", "beyond_axis"
        return limit

    def _hanging(self, xyz, intensity, dy_all, h_all, cand: Candidates, clusters: List[Cluster],
                 valid: float) -> List[Cluster]:
        """5b (``cluster.hanging_enabled``, on since 25.09): thin objects hanging from above into
        the envelope near the axis (``clustering.find_hanging``), from the current frame's points
        within ``hanging_max_distance`` and where the corridor's axis and height reference are
        trusted. Strict-envelope membership is the corridor's (edge margin included). A hanging
        cluster that overlaps a cluster of the other stages is dropped: those stages decide.
        With ``cluster.hanging_needs_rails`` the stage is skipped on a frame without the rail
        pair in the near range (``track.rail_slabs == 0``: stations, switch caverns). With
        ``cluster.hanging_yield_gauge_only`` (26.09) only an overlapping obstacle (zone ``gauge``,
        no demotion reason) takes the object over; an advisory cluster there does not."""
        cfg = self.cfg
        top = float(np.asarray(cfg.gauge.profile, dtype=np.float64)[:, 1].max())
        hang = find_hanging(xyz, intensity, dy_all, h_all, cfg.cluster, top, cfg.gauge.range_min,
                            min(cfg.cluster.hanging_max_distance, valid), cand.idx[cand.in_gauge & (cand.idx >= 0)])
        if cfg.cluster.hanging_yield_gauge_only:
            # 26.09 (safety review): only an obstacle of the other stages takes the object over; an
            # advisory cluster there (a cable demoted as floating) must not remove the hanging one
            others = [k for k in clusters if k.zone == "gauge" and not k.reason]
        else:
            others = clusters
        keep = [c for c in hang if not any(_overlap(c, k) for k in others)]
        return sorted(clusters + keep, key=lambda c: c.distance) if keep else clusters

    def _not_part_of_corridor_objects(self, lows: List[Cluster], straddling: List[Cluster],
                                      clusters: List[Cluster], corr: Candidates) -> List[Cluster]:
        """The foot of something taller (a sign, a column, a person) belongs to the corridor
        stage, which may have demoted it: drop low clusters with corridor points high above
        them; and the lower part of an object the corridor stage already reports is one
        detection, not two (a straddling cluster yields only to a corridor cluster that is
        itself reported)."""
        tall = corr.h > self.cfg.lowobj.foot_max_top
        Xc, dyc = corr.xyz[tall, 0], corr.dy[tall]
        keep = []
        for c in lows:
            m = ((Xc > c.bbox_min[0] - 0.3) & (Xc < c.bbox_max[0] + 0.3)
                 & (np.abs(dyc - c.lateral) < 0.5 * float(c.size[1]) + 0.3))
            if int(m.sum()) >= 3:
                continue
            strad = any(c is k for k in straddling)
            dup = any(_overlap(c, k) for k in clusters
                      if not strad or (k.zone == "gauge" and not k.reason))
            if not dup:
                keep.append(c)
        return keep

    # -- 6 -------------------------------------------------------------------------------------
    def _confirm(self, clusters: List[Cluster], speed: Optional[float], dt: float):
        """Temporal persistence (in seconds: the tracker gets the measured frame interval).
        Returns the confirmed detections in the strict gauge and in the advisory zone."""
        low = self.cfg.lowobj
        low_ok = low.min_model_age <= 0 or self.track.age >= low.min_model_age
        self.tracker.update(clusters, ego_shift=(speed or 0.0) * dt, frame_dt=dt, low_ok=low_ok,
                            rail_within=low.rail_start_within)
        pending = low.pending_advisory and self.calib.state.status == "pending"
        dets: List[Detection] = []
        for t in self.tracker.confirmed():
            if t.last is None:
                continue
            # a track held over a missed frame is reported where it is predicted, not where it was
            shift = float(t.centroid[0] - t.last.centroid[0]) if t.misses else 0.0
            dets.append(Detection(
                id=t.id, distance=t.last.distance + shift, lateral=t.last.lateral,
                center=t.centroid if t.misses else t.last.centroid,
                size=t.last.size, n_points=t.last.n, confidence=t.confidence, age=t.age,
                zone=t.zone, height_min=t.last.height_min, intensity=t.last.intensity,
                reason="near_envelope" if t.escalated else t.last.reason, kind=t.last.kind,
            ))
            d = dets[-1]
            if pending and d.kind == "low" and d.zone == "gauge" and d.distance > low.pending_advisory_within:
                # 26.09 (P3 start-up, candidate a, off): a low track is advisory while the calibration is pending
                d.zone, d.reason = "warning", "calibration_pending"
        dets.sort(key=lambda d: d.distance)
        return [d for d in dets if d.zone == "gauge"], [d for d in dets if d.zone != "gauge"]

    # -- 6b ------------------------------------------------------------------------------------
    def _clear_cap(self, clusters: List[Cluster], cand: Candidates, dy_all: np.ndarray,
                   h_all: np.ndarray) -> Optional[float]:
        """``health.clear_cap`` (25.09): the distance the verified-clear distance is capped at
        (None = no cap), see :func:`clear_cap_distance`. Runs after the tracker and changes
        nothing it or the decision reads."""
        return clear_cap_distance(clusters, self.tracker.tracks, cand, dy_all, h_all, self.cfg.gauge, self.cfg.health)


def clear_cap_distance(clusters: List[Cluster], tracks, cand: Candidates, dy_all: np.ndarray,
                       h_all: np.ndarray, gauge_cfg, hcfg) -> Optional[float]:
    """The nearest thing in the envelope that is not a confirmed obstacle (``health.clear_cap``,
    25.09; docs/evidence/results/p3_clear_distance_2026-09-25.json): the distance of the nearest
    cluster of this frame that touches the strict envelope (``clear_cap_min_gauge`` voxels of
    ``Cluster.n_gauge``, or with ``clear_cap_margin`` >= 0 a point of this frame inside the
    envelope widened by it) and whose track has been matched in ``clear_cap_min_hits`` frames,
    unconfirmed or advisory alike; with ``clear_cap_points`` = k > 0 also the X of the k-th
    nearest strict-envelope corridor return. The cluster of a confirmed in-envelope obstacle is
    skipped: its distance is the obstacle's (``Detection.distance``), whatever rule sets it; with
    ``clear_cap_skip_columns`` so is a column (``reason == 'column'`` or a track held advisory by
    ``tracking.column_hold``): the column row of a double-track tunnel is known infrastructure.
    With ``clear_cap_lost`` (26.09) also the predicted distance of a track that was reported when
    it was last matched and missed this frame (its last cluster touching the envelope, columns
    skipped as above), until the tracker drops it: a STOP lost for a few frames does not turn
    into a verified-clear distance beyond the object."""
    owner = {id(t.last): t for t in tracks if t.last is not None and t.misses == 0}
    poly = widened_profile(gauge_cfg, hcfg.clear_cap_margin) if hcfg.clear_cap_margin >= 0 else None
    best: Optional[float] = None
    for c in clusters:
        if best is not None and c.distance >= best:
            continue
        t = owner.get(id(c))
        if t is not None and t.reported and t.zone == "gauge":
            continue
        if (t.hits if t is not None else 1) < hcfg.clear_cap_min_hits:
            continue
        if hcfg.clear_cap_skip_columns and (c.reason == "column" or (
                t is not None and t.column_hold > 0 and sum(t.column_hist) >= t.column_hold)):
            continue
        touch = c.n_gauge >= hcfg.clear_cap_min_gauge
        if not touch and poly is not None and c.points_idx.size:
            pi = c.points_idx
            touch = bool(point_in_polygon(dy_all[pi], h_all[pi], poly).any())
        if touch:
            best = float(c.distance)
    if getattr(hcfg, "clear_cap_lost", False):
        # 26.09 (safety review): a track that was reported when last matched and missed this frame
        # (not reported any more, or held) caps at its predicted distance while the tracker keeps it
        for t in tracks:
            if t.misses == 0 or not t.seen_reported or t.last is None:
                continue
            if t.last.n_gauge < hcfg.clear_cap_min_gauge:
                continue
            if hcfg.clear_cap_skip_columns and (t.last.reason == "column" or (
                    t.column_hold > 0 and sum(t.column_hist) >= t.column_hold)):
                continue
            d = float(t.last.distance + (t.centroid[0] - t.last.centroid[0]))
            best = d if best is None else min(best, d)
    k = int(hcfg.clear_cap_points)
    if k > 0:
        X = cand.xyz[cand.in_gauge & ~cand.low, 0]
        if X.size >= k:
            xk = float(np.partition(X, k - 1)[k - 1])
            best = xk if best is None else min(best, xk)
    return best
