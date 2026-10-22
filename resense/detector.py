"""End-to-end per-frame obstacle detection inside the clearance gauge."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field, fields, replace
from typing import List, Optional

import numpy as np

from resense.accumulate import CandidateBuffer
from resense.calibration import MountCalibrator, OrientationReplayBuffer
from resense.clustering import Cluster, find_clusters, find_hanging
from resense.config import DetectorConfig
from resense.dust_guard import DustGuard, degraded_health
from resense.egomotion import EgoSpeedEstimate, EgoSpeedEstimator
from resense.evidence import PersistentEvidence
from resense.farline import FarAxisTracker, FarConfirm
from resense.farrails import ring_index
from resense.frame import Frame
from resense.gauge import (has_edge_margin, axis_union_coordinates, axis_union_offset, axis_union_strict, corridor_coordinates,
                           corridor_mask, gauge_core_mask, point_in_polygon, reference_offset, union_shift,
                           widened_profile)
from resense.health import HealthMonitor, bed_off_mount_plane
from resense.lowobj import (BedTemplate, low_candidates, low_free_mask, mark_rail_line, no_rail_advisory,
                            rail_reference_check)
from resense.opinion import observation
from resense.track import TrackModel, estimate_track, rotate_track_model
from resense.tracking import Tracker


def _overlap(a: Cluster, b: Cluster, margin: float = 0.3) -> bool:
    """Two clusters of the same object: their along-track extents and lateral widths overlap."""
    return (b.bbox_min[0] - margin < a.bbox_max[0] and b.bbox_max[0] + margin > a.bbox_min[0]
            and abs(b.lateral - a.lateral) < 0.5 * float(a.size[1] + b.size[1]) + margin)


def _overlap_xy(a: Cluster, b: Cluster, margin: float = 0.3) -> bool:
    """21.10 (K2 union): :func:`_overlap` in the vehicle frame (the boxes' X and Y extents), for clusters whose
    laterals are measured from different axes."""
    return (b.bbox_min[0] - margin < a.bbox_max[0] and b.bbox_max[0] + margin > a.bbox_min[0]
            and b.bbox_min[1] - margin < a.bbox_max[1] and b.bbox_max[1] + margin > a.bbox_min[1])


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
    reason: str = ""           # v0.5 (additive): why the last cluster of an advisory track was demoted ('' = none); 26.09: 'near_envelope' on an obstacle only by tracking.near_escalate_*, 'stop_hold' on an obstacle kept by tracking.stop_keep_* (its last cluster was demoted by a signature or a scan line)
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
    clear_distance: float = 0.0            # m: estimated monitored range capped by obstacle/candidate evidence; missed objects may remain
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
    low-object flag (a bump above the track bed, below the envelope floor). ``in_rail`` (26.09):
    the strict membership measured from the rails only, when ``gauge.axis_union`` made
    ``in_gauge`` the union with the envelope measured from the sensor axis; ``None`` = ``in_gauge``.
    ``ring`` holds decoded elevation channels; ``None`` or negative entries mean unknown. The
    accumulation buffer does not preserve channels: old points receive -1 when concatenated."""
    xyz: np.ndarray
    dy: np.ndarray
    h: np.ndarray
    in_gauge: np.ndarray
    intensity: np.ndarray
    idx: np.ndarray
    low: np.ndarray
    in_rail: Optional[np.ndarray] = None
    dy_rail: Optional[np.ndarray] = None
    ring: Optional[np.ndarray] = None

    def __len__(self) -> int:
        return int(self.idx.size)

    def rail(self) -> np.ndarray:
        return self.in_gauge if self.in_rail is None else self.in_rail

    def lateral_rail(self) -> np.ndarray:
        """The lateral from the rail axis (27.09): ``dy`` unless ``gauge.reference`` measured it from
        the sensor axis."""
        return self.dy if self.dy_rail is None else self.dy_rail

    def concat(self, other: "Candidates") -> "Candidates":
        out = {f.name: np.concatenate([getattr(self, f.name), getattr(other, f.name)])
               for f in fields(self) if f.name not in ("in_rail", "dy_rail", "ring")}
        if self.in_rail is not None or other.in_rail is not None:
            out["in_rail"] = np.concatenate([self.rail(), other.rail()])
        if self.dy_rail is not None or other.dy_rail is not None:
            out["dy_rail"] = np.concatenate([self.lateral_rail(), other.lateral_rail()])
        if self.ring is not None or other.ring is not None:
            a = self.ring if self.ring is not None else np.full(len(self), -1, dtype=np.int64)
            b = other.ring if other.ring is not None else np.full(len(other), -1, dtype=np.int64)
            out["ring"] = np.concatenate([a, b])
        return Candidates(**out)

    def subset(self, m: np.ndarray) -> "Candidates":
        return Candidates(**{f.name: (None if getattr(self, f.name) is None else getattr(self, f.name)[m])
                             for f in fields(self)})


def _clusters_of(c: Candidates, cfg, **kw) -> List[Cluster]:
    return find_clusters(c.xyz, c.intensity, c.dy, c.h, c.in_gauge, cfg, frame_idx=c.idx, in_rail=c.in_rail,
                         dy_report=c.dy_rail, ring=c.ring, **kw)


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
        self.evidence = PersistentEvidence(self.cfg.health, self.cfg.gauge, self.cfg.tracking.frame_dt)  # health.clear_cap_persist
        self.bed = BedTemplate(self.cfg.lowobj)
        self.low_range = 0.0            # m, how far the bed was observed for the low-object stage (last frame)
        self._thin: List[Cluster] = []  # 26.09 (tracking.stop_keep_thin): this frame's corridor clusters flatter than min_height
        self._frame_ring: Optional[np.ndarray] = None
        self._frame_xyz: Optional[np.ndarray] = None  # 13.10: this frame's cloud for the column free-top test (cluster.column_free_max_top)
        self._frame_hd: Optional[tuple] = None  # 15.10: its heights above the rail head and laterals (dy_all, h_all) for that test
        self._low_height: List[Cluster] = []  # current straddle evidence just below its clean top-height threshold
        self._prev_stamp: Optional[float] = None
        self._previous_latency_ms: Optional[float] = None  # previous completed process interval
        self._low_frame_dt: Optional[float] = None  # actual positive stamp interval for the bounded low continuation
        self._evidence_dt: Optional[float] = None  # validated sensor interval for sparse clear-distance evidence
        self._gaps: deque = deque(maxlen=14)  # the last stamp intervals within [0, stamp_dt_range[1]] (s): the input rate
        self._orientation_replay = OrientationReplayBuffer(self.cfg.calibration.orientation_replay_frames)
        # 19.10 (farrange, Falcon profiles only): the far straight axis beyond farrange.axis_join
        fr = self.cfg.farrange
        self.far = FarAxisTracker(fr) if fr.enabled and fr.axis_enabled else None
        self._far_axis = None
        self._union_shift = None        # 21.10 (farrange.axis_union_beyond): this frame's lateral shift of the points the union took
        self._far_report_cap: Optional[float] = None    # 21.10 (A7): where the reported range ends beyond the far line
        self._far_valid_hist: deque = deque(maxlen=max(int(fr.axis_report_lag_frames), 1))  # 21.10 (A10): recent trusted ranges
        self.far_confirm = FarConfirm(fr) if fr.enabled and fr.confirm_enabled else None
        self.dust_guard = DustGuard(self.cfg.dust) if self.cfg.dust.enabled else None  # 19.10 N3, off by default

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
        self.evidence.reset()
        self.bed.reset()
        self._thin = []
        self._frame_ring = None
        self._frame_xyz = None
        self._frame_hd = None
        self._low_height = []
        self._prev_stamp = None
        self._previous_latency_ms = None
        self._low_frame_dt = None
        self._evidence_dt = None
        self._gaps.clear()
        self._orientation_replay.stop("scene_reset")
        if self.far is not None:
            self.far.reset()
        self._far_axis = None
        self._far_valid_hist.clear()
        if self.far_confirm is not None:
            self.far_confirm.reset()
        if self.dust_guard is not None:
            self.dust_guard.reset()

    def _frame_dt(self, stamp: float) -> float:
        """Time since the previous frame from the stamps when they are sane, else the nominal
        frame period (cached frames and synthetic tests carry no usable stamp)."""
        dt = self.cfg.tracking.frame_dt
        self._low_frame_dt = dt
        self._evidence_dt = None
        if self._prev_stamp is not None:
            gap = float(stamp) - self._prev_stamp
            # The existing motion/fit timing clips long gaps below. They still consume
            # their real elapsed time from the independent low-evidence continuation cap.
            self._low_frame_dt = gap if gap > 0 else dt
            if np.isfinite(gap) and gap > 0:
                self._evidence_dt = gap
            lo, hi = self.cfg.accumulation.stamp_dt_range
            if lo <= gap <= hi:
                dt = gap
            if 0.0 <= gap <= hi:
                self._gaps.append(gap)          # the input rate: in-burst intervals included (_periods)
        self._prev_stamp = float(stamp)
        return dt

    def process(self, frame: Frame, ego_speed: Optional[float] = None) -> FrameResult:
        """Process one current input; optional bounded startup replay never publishes old inputs."""
        if (type(self) is Detector and self.cfg.calibration.orientation_replay_frames == 0
                and self._orientation_replay.reason == "disabled"
                and self.calib.directional_startup_history(frame.xyz, frame.ring)):
            # A newly recoverable ring-free side mapping has no valid prior
            # model in the old coordinates. Rebuild only this startup; existing
            # supported mappings retain their default-off history semantics.
            self._orientation_replay = OrientationReplayBuffer(4)
            self.calib._canonical_axes = True
        pending = self._orientation_replay
        directional_history = self.cfg.calibration.orientation_replay_frames == 0 and pending.max_frames > 0
        if pending.finished or not self.cfg.calibration.enabled or self.calib._config_passed:
            return self._process_once(frame, ego_speed)
        wall_start, cpu_start = time.perf_counter(), time.process_time()
        if type(self) is not Detector:
            pending.stop("unsupported_subclass")
        else:
            pending.capture(frame, ego_speed)
        result = self._process_once(frame, ego_speed)
        event = None
        if self.calib.last_change_orientation and pending.frames and not pending.finished:
            # Only the validated discrete orientation is installed. The correct initial
            # observations rebuild tilt, tracking, accumulation and health in original
            # order; no synthetic confirmations or history in the old axes survive.
            rotation = self.calib._R_orient.copy()
            orientation = self.calib.state.orientation
            replay_start = time.perf_counter()
            fresh = Detector(self.cfg)
            fresh._orientation_replay.stop("replay_complete")
            fresh.calib._R_orient = rotation.copy()
            fresh.calib.state.R = rotation.copy()
            fresh.calib.state.orientation = orientation
            fresh.calib.state.orientation_confirmed = True
            fresh.calib._config_passed = True
            fresh.calib._canonical_axes = directional_history
            fresh.calib.state.message = f"sensor orientation found from the data: {orientation}"
            for saved, speed in pending.frames:
                replayed = fresh._process_once(saved, speed)
            # Health latency describes physical calls. During this <=4-call startup
            # no latency warning is eligible (10 samples required); retain that history
            # and put the complete current replay cost into the next physical sample.
            fresh.health._lat = self.health._lat.copy()
            replayed.health["latency_p95_ms"] = result.health["latency_p95_ms"]
            replayed.health["latency_sample_age_frames"] = result.health["latency_sample_age_frames"]
            event = {"status": "replayed", "frames": len(pending.frames), "bytes": pending.used_bytes,
                     "first_stamp": pending.frames[0][0].stamp, "published_stamp": frame.stamp,
                     "replay_ms": (time.perf_counter() - replay_start) * 1000}
            pending.stop("replay_complete")
            self.__dict__.update(fresh.__dict__)
            result = replayed
        elif pending.finished:
            event = {"status": "skipped", "reason": pending.reason, "peak_bytes": pending.peak_bytes}
        elif self.calib._config_passed:
            pending.stop("configured_mapping")
        elapsed = (time.perf_counter() - wall_start) * 1000
        self._previous_latency_ms = elapsed
        result.timing_ms["total"] = elapsed
        if event is not None:
            if directional_history:
                event["trigger"] = "directional_up_axis"
            event["physical_call_ms"] = elapsed
            event["physical_cpu_ms"] = (time.process_time() - cpu_start) * 1000
            result.mount["orientation_replay"] = event
        return result

    def _process_once(self, frame: Frame, ego_speed: Optional[float] = None) -> FrameResult:
        """Detect obstacles in one frame.

        ``ego_speed`` is the train speed in m/s when the caller knows it (odometry topic or a
        parameter); ``None`` lets the detector estimate it from the tunnel texture. A given
        speed always wins. Without a usable speed no frames are accumulated.

        The stages are the methods below, in this order (docs/ALGORITHM.md has the reasoning):
        ``_fit_track`` (1, 1b), ``_corridor`` (2), ``_low_stage`` (2b), ``_speed`` (3),
        ``_accumulate`` (4), ``_cluster`` (5), ``_hanging`` (5b, 25.09), ``_confirm`` (6).

        ``timing_ms.total`` runs from entry through health and result construction;
        ``stages`` preserves the old total through tracking. The final timing writes and
        return are outside the measured interval. Health uses the previous completed
        call's total (one frame of delay); the first call/reset has no latency sample.
        """
        t0 = time.perf_counter()
        cfg = self.cfg
        previous_latency_ms = self._previous_latency_ms
        self._previous_latency_ms = None  # a failed call must not leave an older pending sample
        frame = _finite_only(frame)
        self._frame_ring = frame.ring
        dt = self._frame_dt(frame.stamp)
        self._travel_m = self._travel(dt)        # 19.10 (K1): read by _fit_track; None unless walls_smoothing_distance > 0
        xyz = self._fit_track(frame.xyz, self._periods())
        if self.far is not None:
            prev = self._far_axis
            self._far_axis = self.far.update(xyz, self.track, cfg.gauge.range_max, dt=dt)
            # buffered corridor points carry laterals from the axis of their frame: when the far axis
            # appears, disappears or moves (0.2 m at the far end), the buffer is not comparable
            if (prev is None) != (self._far_axis is None) or (
                    prev is not None and abs((self._far_axis.y_join + self._far_axis.slope * (cfg.gauge.range_max - self._far_axis.join))
                                             - (prev.y_join + prev.slope * (cfg.gauge.range_max - prev.join))) > 0.2):
                self.buffer.clear()
        self._frame_xyz = xyz
        t1 = time.perf_counter()
        cand, dy_all, h_all, mask, (valid, axis_valid, floor_valid) = self._corridor(xyz, frame.intensity)
        self._frame_hd = (dy_all, h_all)
        if cfg.track.axis_joint_union and self.track.curve is not None:
            # K2 union (revision 2): the returns the base gauge holds inside its strict envelope, read by _curve_clusters
            self._base_in = np.zeros(len(xyz), dtype=bool)
            self._base_in[cand.idx[cand.in_gauge & (cand.idx >= 0)]] = True
        trust = min(valid, floor_valid)  # the trusted range before the clustering (health.clear_cap_thin)
        dy_rail = self._dy_rail          # = dy_all unless gauge.axis_union 2 re-measured the corridor coordinate
        # Paired rails support lateral axis placement, not a farther bed-anomaly
        # model. Preserve low/straddle/near candidate admission and its history at
        # the pre-extension range; N6 extends only the above-rail corridor.
        low_axis_valid = (min(axis_valid, self.track.axis_valid_without_rails)
                          if self.track.rail_axis_support > 0 else axis_valid)
        cand, straddle, near = self._low_stage(xyz, frame.intensity, dy_rail, h_all, mask, cand,
                                               min(low_axis_valid, floor_valid))
        dust_removed = None
        if self.dust_guard is not None:
            cand, straddle, near, dust_removed = self._dust_qualify(xyz, dy_rail, h_all, cand, straddle, near)
        t2 = time.perf_counter()
        speed, source, est = self._speed(xyz, dy_rail, h_all, dt, ego_speed)
        if cfg.tracking.ego_veto_min_speed > 0 and est is None and ego_speed is None:
            # 29.09 (tracking.ego_veto_*): the LiDAR speed estimate for the veto only; accumulation
            # keeps its own switch (accumulation.estimate_speed)
            est = self.ego.estimate(xyz, self.track, dt, self.tracker.tracks, dy_rail, h_all)
        self._odo_speed = (float(ego_speed) if ego_speed is not None
                           else (float(est.speed) if est is not None and est.speed is not None else None))
        self._ego_last = est                     # 19.10 (K1): read by _travel on the next frame
        t3 = time.perf_counter()
        merged, n_acc = self._accumulate(cand, speed, dt)
        t4 = time.perf_counter()
        clusters = self._cluster(merged, n_acc, valid, floor_valid, straddle, near)
        if cfg.track.axis_joint_union and self.track.curve is not None:
            clusters = self._curve_clusters(xyz, frame.intensity, clusters, valid)
        if cfg.track.axis_joint_reach_dual > 0:
            self._dual_zone(clusters)
        if cfg.cluster.far_axis_both_sides == 2:
            valid = self._far_both_sides(clusters, valid, floor_valid)
        if cfg.cluster.hanging_enabled and (not cfg.cluster.hanging_needs_rails or self.track.rail_slabs > 0):
            clusters = self._hanging(xyz, frame.intensity, dy_all, h_all, cand, clusters, min(valid, floor_valid))
        if cfg.cluster.shell_min_top > 0:
            self._shell(clusters, xyz, dy_all, h_all)
        if cfg.lowobj.rail_start_within > 0:
            # 26.09 (P3 rail start): low clusters near the train that are rail geometry; the rail lines
            # are at the axis +- rails_spacing / 2 of the rail coordinate (dy_rail, as the low stage)
            mark_rail_line(clusters + self._low_height, xyz[:, 0], dy_rail, h_all, cfg.lowobj,
                           cfg.track.rails_spacing, cfg.gauge.range_min)
        if cfg.lowobj.local_rail_margin > 0 or cfg.lowobj.rail_band_range > 0:
            clusters = self._rail_reference(clusters, xyz, dy_rail, h_all)
        if cfg.lowobj.no_rail_low_within > 0 and self.track.rail_slabs == 0:
            # 19.10 (F1 c, off by default): without the rail pair in the near range a low cluster beyond
            # no_rail_low_within is advisory; a signature, so an earned STOP is kept by the stop-keep rule
            no_rail_advisory(clusters, cfg.lowobj.no_rail_low_within)
        if cfg.cluster.mount_cross_tol > 0:
            self._mount_cross_check(clusters, xyz)
        t5 = time.perf_counter()
        gauge, warn = self._confirm(clusters, speed, dt)
        cap = self._clear_cap(clusters, cand, dy_all, h_all, trust, n_acc) if cfg.health.clear_cap else None
        t6 = time.perf_counter()
        mount = self.calib.state.to_dict()
        drift = self.track.wall_drift
        bed_conflict = False
        if cfg.health.clear_lost_bed:       # amendment 1 of falcon_clear_distance_2026-10-21: the bed against the mount plane
            st = self.calib.state
            if st.height is not None and st.status in ("ok", "identity") and np.isfinite(st.height):
                bed_conflict = bed_off_mount_plane(self.track, -float(st.height), cfg.cluster.mount_cross_tol,
                                                   cfg.cluster.mount_cross_grade, cfg.cluster.mount_cross_range)
        if self._far_report_cap is not None:
            drift = min(drift, self._far_report_cap)      # 21.10 (A7): see _corridor
        if self.far is not None and cfg.farrange.axis_stable and cfg.farrange.axis_report_lag_frames > 0:
            # 21.10 (A9 / A10): the reported range grows only as far as the trusted range reached in each of the last
            # frames (an object entering a newly trusted stretch gets those frames to be seen before it is reported
            # clear); the Falcon profiles only; detection and trust are unchanged
            self._far_valid_hist.append(float(min(valid, drift)))
            drift = min(drift, min(self._far_valid_hist))
        health = self.health.update(xyz, frame.meta, self.track, cfg.gauge, valid, cfg.track.rails_min_score,
                                    previous_latency_ms, mount, gauge[0].distance if gauge else None, cap,
                                    wall_drift=drift if drift < 1e9 else None, bed_conflict=bed_conflict)
        health["latency_basis"] = "previous_complete_process"
        health["latency_sample_age_frames"] = 1 if previous_latency_ms is not None else None
        if dust_removed is not None:
            health = degraded_health(health, self.dust_guard.last, dust_removed)
        t7 = time.perf_counter()

        result = FrameResult(
            stamp=frame.stamp, obstacle=len(gauge) > 0, warning=len(warn) > 0,
            nearest_distance=gauge[0].distance if gauge else None,
            detections=gauge, warnings=warn, candidates=clusters, track=self._published_track(),
            corridor_idx=cand.idx, n_points=frame.n,
            timing_ms={"track": (t1 - t0) * 1e3, "corridor": (t2 - t1) * 1e3,
                       "egomotion": (t3 - t2) * 1e3, "accumulate": (t4 - t3) * 1e3,
                       "cluster": (t5 - t4) * 1e3, "tracking": (t6 - t5) * 1e3,
                       "stages": (t6 - t0) * 1e3, "health": (t7 - t6) * 1e3},
            ego_speed=speed, ego_speed_source=source, n_accumulated=n_acc,
            ego_speed_estimate=None if est is None else est.speed,
            ego_speed_confidence=0.0 if est is None else est.confidence,
            health=health, mount=mount, clear_distance=health["clear_distance"], xyz=xyz,
        )
        t8 = time.perf_counter()
        result.timing_ms["result"] = (t8 - t7) * 1e3
        result.timing_ms["total"] = self._previous_latency_ms = (t8 - t0) * 1e3
        return result

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
    def _travel(self, dt: float) -> Optional[float]:
        """Metres travelled since the previous frame from that frame's speed (given or the LiDAR estimate), for
        the per-distance axis smoothing (19.10, ``track.walls_smoothing_distance``); None when it is off or the speed
        is unknown."""
        tc = self.cfg.track
        if tc.walls_smoothing_distance <= 0 or self.track is None:
            return None
        v = getattr(self, "_odo_speed", None)
        est = getattr(self, "_ego_last", None)
        still = (v is None and est is not None and est.speed is None and est.speed_profile == 0.0 and est.corr == 0.0
                 and self.ego.last_speed is not None and self.ego.last_speed <= tc.walls_smoothing_standstill_speed)
        # the texture profile saw no change at all (zero energy) after the last confident speed was a crawl:
        # standing (squareT_platform frames 320-690: 0.0, then no estimate); at most walls_smoothing_standstill_max
        # seconds in a row (no texture can also mean a featureless tunnel)
        self._still_s = (getattr(self, "_still_s", 0.0) + float(dt)) if still else 0.0
        if still and self._still_s <= tc.walls_smoothing_standstill_max:
            v = 0.0
        return None if v is None else abs(float(v)) * float(dt)

    def _fit_track(self, xyz_cfg: np.ndarray, periods: int = 1) -> np.ndarray:
        """Track model (bed profile, rail-head level, axis) and the mount calibration (first
        frames, then a drift check every few seconds). Returns the cloud in the corrected frame."""
        cfg = self.cfg
        xyz = self.calib.apply(xyz_cfg)
        # ring identity is a property of the uncorrected frame: after the mount correction a ring is no
        # longer a constant elevation (resense/farrails.py); only the opt-in far rail evidence needs it
        ring = (ring_index(xyz_cfg, band=(cfg.track.rails_range[1] - 10.0, 100.0, 6.0, 0.5))
                if cfg.track.rails_far_check_enabled and cfg.track.rails_far_rings else None)
        # N6 uses supplied scan-line IDs only, never a Pandar table inferred for an
        # unknown sensor. Keep the older experimental curvature-refit path separate.
        rail_args = {"axis_ring": self._frame_ring} if cfg.track.rails_axis_extension else {}
        fit_xyz = xyz
        guard = self.dust_guard
        if guard is not None and (guard.active or guard.light) and cfg.dust.track_filter:
            # 19.10 N3 (dust.track_filter): diffuse returns must not move the bed / rail / axis fits
            keep = guard.track_input(xyz, self.track)
            if not keep.all():
                fit_xyz = xyz[keep]
                ring = None if ring is None else ring[keep]
                if rail_args.get("axis_ring") is not None:
                    rail_args = {"axis_ring": rail_args["axis_ring"][keep]}
        self.track = estimate_track(fit_xyz, cfg.track, prev=self.track, periods=periods, ring=ring,
                                    travel=getattr(self, "_travel_m", None), **rail_args)
        R_old = self.calib.R.copy()
        if self.calib.update(xyz_cfg, xyz, self.track, periods=periods, ring=self._frame_ring):
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
                self.track = estimate_track(xyz, cfg.track, prev=None, ring=ring)  # re-seed in the corrected frame
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
        far = self._far_axis
        if far is not None:
            # 19.10 (farrange): beyond the join the lateral is measured from the far straight axis
            dy_all = dy_all - far.offset(xyz[:, 0], self.track)
        self._dy_rail = dy_all
        self._union_shift = None
        self._far_report_cap = None
        if far is not None and cfg.farrange.axis_stable and cfg.farrange.axis_report_tolerance > 0:
            # 21.10 (A7, review F1): beyond the far line's trusted end the near model's corridor is not where the
            # track is once its centre leaves the continued far line by more than the tolerance: the reported
            # monitored / clear range ends there (as health's wall_drift cap); detection is unchanged
            top = max(min(self.track.axis_valid, cfg.gauge.range_max), far.valid)
            if top > far.valid:
                Xg = np.arange(far.valid, top + 1e-6, 1.0)
                off = np.abs(far.line_offset(Xg, self.track))
                bad = np.flatnonzero(off > cfg.farrange.axis_report_tolerance)
                if bad.size:
                    cap = float(Xg[bad[0]])
                    self._far_report_cap = cap if self._far_report_cap is None else min(self._far_report_cap, cap)
        if far is not None and cfg.farrange.axis_stable and cfg.farrange.axis_union_beyond:
            # 21.10 (farrange.axis_union_beyond, review F1): between the far line's trusted end and the near model's
            # own trusted range the corridor is the union of both hypotheses, the near model's lateral (v1.2.0's
            # corridor) and the far line continued straight, whichever is nearer the centre: a point is never
            # removed from v1.2.0's corridor, and a clear range there means both are empty
            X = xyz[:, 0]
            hi = max(min(self.track.axis_valid, cfg.gauge.range_max), far.valid)
            beyond = (X > far.valid) & (X <= hi)
            if beyond.any():
                alt = dy_all[beyond] - far.line_offset(X[beyond], self.track)
                take = np.abs(alt) < np.abs(dy_all[beyond])
                if take.any():
                    shift = np.zeros(X.size, dtype=dy_all.dtype)
                    sub = np.flatnonzero(beyond)[take]
                    shift[sub] = alt[take] - dy_all[sub]
                    dy_all = dy_all + shift
                    self._union_shift = shift
        if cfg.gauge.axis_union == 2:
            # 26.09 (candidate B, off by default): the corridor coordinate re-measured so that the strict
            # envelope is the union of the rail and the sensor-axis envelopes (near field, straight
            # track); the bed, low-object and ego-speed stages keep the rail coordinate (self._dy_rail)
            dy_all = axis_union_coordinates(xyz[:, 0], dy_all, self.track, cfg.gauge)
        mask, strict = corridor_mask(xyz, self.track, cfg.gauge, dy_all, h_all)
        idx = np.flatnonzero(mask)
        cand = Candidates(xyz=xyz[idx], dy=dy_all[idx], h=h_all[idx], in_gauge=strict[idx],
                          intensity=intensity[idx], idx=idx, low=np.zeros(idx.size, dtype=bool),
                          ring=None if self._frame_ring is None else self._frame_ring[idx])
        ref = reference_offset(cand.xyz[:, 0], self.track, cfg.gauge) if cfg.gauge.reference > 0 else None
        if ref is not None:
            # 27.09 (gauge.reference 1 / 2 / 3, 3 on): the envelope measured from the sensor axis where
            # it agrees with the rails (near field, straight track). The candidate set (the advisory
            # corridor), the reported lateral (dy_rail), the gauge-distance reach and the frame-wide stages
            # (bed, low objects, rail start, ego speed, hanging search, clear cap: dy_all) keep the rails;
            # the hanging stage reads the strict membership from here. The corridor coordinate of the
            # candidates (strict membership, shape rules, accumulation) is the lateral from the sensor axis (mode 3: only
            # where that is nearer the centre, the union below; modes 1 / 2 everywhere in the near field). The
            # rails' own strict membership is kept (in_rail, as for gauge.axis_union): an oversize cluster
            # whose part inside the reference envelope took in an edge line falls back to it (the safety
            # review's scene of 26.09), and the wall keep counts it
            in_rail = cand.in_gauge
            if has_edge_margin(cfg.gauge):
                in_rail = in_rail & gauge_core_mask(cand.dy, cand.h, cand.xyz[:, 0], cfg.gauge)
            cand.in_rail = in_rail
            cand.dy_rail = cand.dy
            # 27.09 (gauge.reference 3): the union - a point takes the sensor-axis lateral only where it is
            # nearer the centre there, so neither side of the rails' envelope is narrowed
            cand.dy = cand.dy + (union_shift(cand.dy, ref[1]) if cfg.gauge.reference == 3 else ref[1])
            cand.in_gauge = point_in_polygon(cand.dy, cand.h, cfg.gauge.profile)
        if has_edge_margin(cfg.gauge):
            core = gauge_core_mask(cand.dy, cand.h, cand.xyz[:, 0], cfg.gauge)
            if ref is not None and cfg.gauge.reference_edge_margin != 1.0:
                # 27.09 (gauge.reference_edge_margin): the margin models the fitted rail axis' uncertainty;
                # where the envelope is measured from the sensor axis it is scaled (0 = none)
                s = max(float(cfg.gauge.reference_edge_margin), 0.0)
                ok = ref[0]
                if ok.any():
                    g = replace(cfg.gauge, edge_margin=cfg.gauge.edge_margin * s,
                                edge_margin_per_100m=cfg.gauge.edge_margin_per_100m * s,
                                edge_margin_per_100m2=cfg.gauge.edge_margin_per_100m2 * s)
                    core[ok] = gauge_core_mask(cand.dy[ok], cand.h[ok], cand.xyz[ok, 0], g)
            cand.in_gauge = cand.in_gauge & core
        if far is not None and cfg.farrange.axis_core_margin:
            # 19.10 (farrange): the strict gauge shrinks by the far axis' lateral uncertainty
            half = float(np.max(np.abs(np.asarray(cfg.gauge.profile, dtype=np.float64)[:, 0])))
            cand.in_gauge = cand.in_gauge & (np.abs(cand.dy) <= half - far.sigma(cand.xyz[:, 0]))
        if cfg.gauge.axis_union in (1, 3):
            # 26.09 (candidates A and B2, off by default): also inside when inside the envelope measured
            # from the sensor axis (near field, straight track, the two axes within axis_union_max_offset)
            ax = axis_union_strict(cand.xyz[:, 0], cand.dy, cand.h, self.track, cfg.gauge)
            if ax is not None:
                cand.in_rail = cand.in_gauge            # the rails' own envelope (safety review of 26.09)
                cand.in_gauge = cand.in_gauge | ax
        floor_valid = max(self.track.floor_range[1] + cfg.track.floor_valid_margin, self.track.floor_verified)
        axis_valid = min(self.track.axis_valid, cfg.gauge.range_max)
        if far is not None:
            # never below the near model's trust (review R3). Beyond the far line's end the near model gives the
            # laterals as before: extending the far line with its growing sigma there emptied the strict gauge
            # and lost baseline STOPs at 80-90 m (re-review R2 is a measured residual, see the report)
            axis_valid = max(axis_valid, min(far.valid, cfg.gauge.range_max))
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
                                      intensity=intensity[si], idx=si, low=ones,
                                      ring=None if self._frame_ring is None else self._frame_ring[si])
        if lidx.size:
            ones = np.ones(lidx.size, dtype=bool)
            cand = cand.concat(Candidates(xyz=xyz[lidx], dy=dy_all[lidx], h=h_all[lidx], in_gauge=ones,
                                           intensity=intensity[lidx], idx=lidx, low=ones,
                                           ring=None if self._frame_ring is None else self._frame_ring[lidx]))
        near = None
        if nidx.size and self.track.rail_score >= cfg.track.rails_min_score:
            nidx = nidx[~mask[nidx]]
            ones = np.ones(nidx.size, dtype=bool)
            near = Candidates(xyz=xyz[nidx], dy=dy_all[nidx], h=h_all[nidx], in_gauge=ones,
                              intensity=intensity[nidx], idx=nidx, low=ones,
                              ring=None if self._frame_ring is None else self._frame_ring[nidx])
        return cand, straddle, near

    # -- 2c ------------------------------------------------------------------------------------
    def _dust_qualify(self, xyz, dy_all, h_all, cand: Candidates, straddle: Optional[Candidates],
                      near: Optional[Candidates]):
        """19.10 N3 (``dust.enabled``, off by default; resense/dust_guard.py): while diffuse volumetric
        returns are observed in the gauge interior, keep only locally supported returns as obstacle
        candidates (corridor, low, straddle, near). Returns the sets and the number of candidate
        returns kept out, or ``None`` for that number when the guard is inactive (nothing changes)."""
        guard = self.dust_guard
        guard.assess(xyz, dy_all, h_all)
        if not guard.active:
            return cand, straddle, near, None
        removed = 0
        out = []
        for c in (cand, straddle, near):
            if c is None or not len(c):
                out.append(c)
                continue
            keep = guard.supported(xyz, c.idx, dy_all, h_all)
            if c is cand:
                removed = int((~keep).sum())
            out.append(c if keep.all() else c.subset(keep))
        straddle = out[1] if out[1] is None or len(out[1]) >= 3 else None
        return out[0], straddle, out[2], removed

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
            dro = None
            if self.cfg.gauge.reference > 0:
                # 27.09 (gauge.reference 1): the buffer holds the corridor coordinate, measured from the
                # sensor axis where the reference applies (its offset at the shifted X, this frame's model)
                ref = reference_offset(Xo64, self.track, self.cfg.gauge)
                if ref is None:
                    dro = dyo
                elif self.cfg.gauge.reference == 3:
                    # the union shifted a point only towards the centre: undo it where that is consistent
                    dro = np.where(np.abs(dyo + ref[1]) >= np.abs(dyo), dyo, dyo - ref[1])
                else:
                    dro = dyo - ref[1]
            yo = self.track.center_y(Xo64) + (dyo if dro is None else dro)
            if self._far_axis is not None:
                yo = yo + self._far_axis.offset(Xo64, self.track)       # 19.10 (farrange)
            xyz_o = np.stack([Xo64, yo, self.track.rail_z(Xo64) + ho], axis=1).astype(np.float32)
            merged = cand.concat(Candidates(xyz=xyz_o, dy=dyo, h=ho, in_gauge=go, intensity=io,
                                            idx=np.full(Xo.size, -1, dtype=cand.idx.dtype),
                                            low=np.zeros(Xo.size, dtype=bool),
                                            in_rail=self.buffer.merged_rail(acc.min_range), dy_rail=dro))
            n_acc = 1 + len(self.buffer)
        far = (cand.xyz[:, 0] >= acc.min_range) & ~cand.low
        dy_push = cand.dy
        if self._union_shift is not None:
            # 21.10 (axis_union_beyond): the buffer is rebuilt with the near model and the far line's trusted part
            # only, so a point taken by the union is stored with its near lateral (its strict flag is kept)
            ok = cand.idx >= 0
            dy_push = cand.dy.copy()
            dy_push[ok] = dy_push[ok] - self._union_shift[cand.idx[ok]]
        self.buffer.push(cand.xyz[far, 0], dy_push[far], cand.h[far], cand.intensity[far], cand.in_gauge[far],
                         in_rail=None if cand.in_rail is None else cand.in_rail[far])
        return merged, n_acc

    # -- 5 -------------------------------------------------------------------------------------
    def _corridor_clusters(self, corr: Candidates, valid: float, floor_valid: float, factor: float, dy_alt,
                           keep_thin: bool, hd, n_acc: int) -> List[Cluster]:
        """The corridor clustering of ``_cluster`` for one candidate group (21.10, A8: split by hypothesis)."""
        cfg = self.cfg
        acc = cfg.accumulation
        return _clusters_of(corr, cfg.cluster, axis_valid=valid,
                            height_valid=floor_valid if cfg.cluster.far_min_height > 0 else None,
                                min_points_factor=factor, factor_range=acc.min_range,
                                smear_max_length=acc.smear_max_length if n_acc > 1 else 0.0,
                                smear_max_width=acc.smear_max_width if n_acc > 1 else 0.0, gauge=cfg.gauge,
                                dy_alt=dy_alt, keep_thin=keep_thin,
                                weak_from=cfg.tracking.thin_far_min_distance
                                if cfg.cluster.weak_min_points > 0 or cfg.cluster.weak_min_rings > 0 else 0.0,
                                frame_xyz=self._frame_xyz if cfg.cluster.column_free_max_top > 0
                                or cfg.cluster.column_core_margin > 0 else None,
                                 frame_ring=self._frame_ring, frame_dy=hd[0], frame_h=hd[1],
                                 frame_track=self.track, frame_track_cfg=cfg.track)

    def _cluster(self, cand: Candidates, n_acc: int, valid: float, floor_valid: float,
                 straddle: Optional[Candidates], near: Optional[Candidates] = None) -> List[Cluster]:
        """Voxelise, cluster, describe and filter: the corridor candidates (count thresholds
        scaled for merged frames), the low candidates on their own with a tighter radius, the
        straddle candidates; then the low clusters that are the foot or the lower part of a
        corridor object are dropped. The corridor clustering gets this frame's cloud for the column
        signature's free-top test (13.10, ``cluster.column_free_max_top``)."""
        cfg = self.cfg
        acc = cfg.accumulation
        self._low_height = []
        self._near_low = []                     # 19.10: the opt-in near-bed path's clusters (exempt from F1a)
        factor = max(1.0, n_acc * acc.min_points_scale) if n_acc > 1 else 1.0
        corr = cand.subset(~cand.low)
        dy_alt = None
        if cfg.gauge.axis_union == 3:
            # 26.09 (candidate B2, off by default): the lateral from the sensor axis for the shape rules
            reg = axis_union_offset(corr.xyz[:, 0], self.track, cfg.gauge)
            if reg is not None:
                dy_alt = corr.dy + reg[1]
        keep_thin = cfg.tracking.stop_keep_thin > 0 or cfg.tracking.thin_far_min_distance > 0
        hd = self._frame_hd or (None, None)
        groups = [corr]
        far = self._far_axis
        if (far is not None and self._union_shift is not None and cfg.farrange.axis_union_separate
                and dy_alt is None and len(corr)):
            # 21.10 (A8): beyond far.valid the points that kept the near model's lateral are clustered on their own;
            # up to far.valid and the points the union gave the far line are clustered together as before
            ok = corr.idx >= 0
            took = np.zeros(len(corr), dtype=bool)
            took[ok] = self._union_shift[corr.idx[ok]] != 0
            near_hyp = (corr.xyz[:, 0] > far.valid) & ~took & ok
            if near_hyp.any() and not near_hyp.all():
                groups = [corr.subset(~near_hyp), corr.subset(near_hyp)]
        clusters = []
        for grp in groups:
            clusters += self._corridor_clusters(grp, valid, floor_valid, factor, dy_alt, keep_thin, hd, n_acc)
        clusters.sort(key=lambda c: c.distance)
        if keep_thin:
            # 26.09 (tracking.stop_keep_thin, on since 26.09): the clusters flatter than min_height go
            # to the tracker only, to continue a track (Tracker._continue_thin); no other stage sees them
            # (27.09: also tracking.thin_far_min_distance, Detector._far_thin)
            self._thin = [c for c in clusters if c.thin or c.weak]
            clusters = [c for c in clusters if not (c.thin or c.weak)]
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
            margin = cfg.lowobj.straddle_keep_height_margin if cfg.tracking.stop_keep_low_s > 0 else 0.0
            straddling = _clusters_of(straddle, lcfg, axis_valid=valid, low=straddle.low, low_cfg=scfg,
                                     low_height_margin=margin)
            self._low_height = [c for c in straddling if c.low_height_weak]
            straddling = [c for c in straddling if not c.low_height_weak]
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
            self._near_low = central
        if lows:
            keep = self._not_part_of_corridor_objects(lows, straddling, clusters, corr)
            clusters = sorted(clusters + keep, key=lambda c: c.distance)
        if self._low_height:
            # The same foot and duplicate rules apply to continuation evidence. It never
            # enters the normal candidate list or supersedes a clean low/corridor cluster.
            self._low_height = self._not_part_of_corridor_objects(
                self._low_height, self._low_height, clusters, corr)
        return clusters

    def _dual_zone(self, clusters: List[Cluster]) -> None:
        """20.10 (v5c, ``track.axis_joint_reach_dual``): on a frame whose trusted range the K2 reach cap shortened
        (``track.joint_reach`` > 0), the range goes on beyond the cap (``track._joint_output``), where the walls no
        longer confirm the joint shape. An obstacle there whose nearest point lies beyond the cap stays one only
        when its lateral extent also reaches into the strict gauge measured from the base axis, which the
        estimator without K2 trusts that far; otherwise it is advisory ``beyond_axis``, as with the cap alone
        (v5b). A cluster that starts before the cap is left as it is, so nothing v5b keeps is demoted. The
        extent is the cluster's box (accumulated points included) at its centroid's distance."""
        tr, g = self.track, self.cfg.gauge
        if tr is None or tr.joint_reach <= 0 or tr.base is None:
            return
        prof = np.asarray(g.profile, dtype=np.float64)
        hlo, hhi = float(prof[:, 1].min()), float(prof[:, 1].max())
        for c in clusters:
            if c.zone != "gauge" or c.reason or float(c.bbox_min[0]) <= tr.joint_reach:
                continue
            x = float(c.centroid[0])
            yb = float(tr.base.center_y(np.array([x]))[0])
            lo, hi = float(c.bbox_min[1]) - yb, float(c.bbox_max[1]) - yb
            near = 0.0 if lo <= 0.0 <= hi else (lo if lo > 0.0 else hi)   # its point nearest the base axis
            h = float(np.clip(0.5 * (c.height_min + c.height_max), hlo + 0.01, hhi - 0.01))
            dy, hh, xx = np.array([near]), np.array([h]), np.array([x])
            inside = gauge_core_mask(dy, hh, xx, g) if has_edge_margin(g) else point_in_polygon(dy, hh, g.profile)
            if not bool(inside[0]):
                c.zone, c.reason = "warning", "beyond_axis"

    def _published_track(self) -> TrackModel:
        """The model in the result (display, records): the track model, or with ``track.axis_joint_union`` on a curve
        frame its copy with the curve's shape and trusted range (``joint_used`` true), so the drawn gauge follows the
        curve as far as the walls confirm it. The detector itself keeps reading the track model."""
        tr = self.track
        cv = tr.curve if self.cfg.track.axis_joint_union else None
        if cv is None:
            return tr
        return replace(tr, center=cv.center, yaw=cv.yaw, curvature=cv.curvature, curv_step=cv.curv_step,
                       curv_knot=cv.curv_knot, axis_valid=cv.axis_valid, joint_used=True)

    def _curve_clusters(self, xyz: np.ndarray, intensity: np.ndarray, clusters: List[Cluster],
                        base_valid: float = 0.0) -> List[Cluster]:
        """21.10 (K2 union, ``track.axis_joint_union``): on a curve frame the joint shape (``track.curve``, trusted as far
        as a tunnel boundary follows it) is a second gauge. The corridor and the clustering of the above-rail candidates
        run again in its coordinates, on this frame's points alone (no accumulation, no low stage); each of its
        obstacles (zone ``gauge``, no reason) that overlaps no obstacle of the base gauge is added, in place of the base
        gauge's advisory clusters it overlaps. Nothing the base gauge reports as an obstacle is changed, and the bed,
        low-object, ego-speed, mount and clear-distance stages keep the base model. Revision 2: only beyond the
        farthest X to which a boundary still follows the base axis (``curve.curve_from``), and only objects the base
        gauge did not judge: none of their returns inside its strict envelope within its trusted range ``base_valid``."""
        saved = (self.track, self._far_axis, getattr(self, "_dy_rail", None), self._frame_hd, self._thin,
                 getattr(self, "_low_height", []), getattr(self, "_near_low", []))
        try:
            self.track, self._far_axis = self.track.curve, None
            cand, dy_k, h_k, _, (valid, _, floor_valid) = self._corridor(xyz, intensity)
            self._frame_hd = (dy_k, h_k)
            extra = self._cluster(cand, 1, valid, floor_valid, None, None) if len(cand) else []
        finally:
            (self.track, self._far_axis, self._dy_rail, self._frame_hd, self._thin, self._low_height,
             self._near_low) = saved
        obstacles = [c for c in clusters if c.zone == "gauge" and not c.reason]
        start = float(saved[0].curve.curve_from)
        base_in = getattr(self, "_base_in", None)

        def judged(k: Cluster) -> bool:
            # revision 2: an object with returns inside the base strict envelope within the base's trusted range was
            # judged by the base gauge (its advisory reasons stand); the curve adds only what the base cannot see
            own = k.points_idx[k.points_idx >= 0]
            return (base_in is not None and float(k.distance) <= base_valid and own.size > 0
                    and bool(base_in[own[own < base_in.size]].any()))
        add = [k for k in extra if k.zone == "gauge" and not k.reason and float(k.distance) > start
               and not judged(k) and not any(_overlap_xy(k, c) for c in obstacles)]
        self._curve_added, self._curve_seen = len(add), extra      # read by evidence traces only
        if not add:
            return clusters
        dy_base = saved[2]
        for k in add:
            # the tracker's record (track opinion) and the reported lateral stay in the base coordinates, as the
            # base advisory cluster it replaces would have given them (a curve lateral mixed into a track's history
            # reads as a lateral jump to the opinion: marked platform object 23 was withheld 7 frames, revision 1)
            over = [c for c in clusters if _overlap_xy(c, k)]
            if over:
                b = min(over, key=lambda c: float(np.linalg.norm(c.centroid - k.centroid)))
                k.lateral, k.obs_as = b.lateral, observation(b)
            else:
                own = k.points_idx[k.points_idx >= 0]
                if dy_base is not None and own.size:
                    k.lateral = float(np.mean(dy_base[own]))
                k.obs_as = observation(k)
            k.curve = True
        keep = [c for c in clusters if not any(_overlap_xy(c, k) for k in add)]
        return sorted(keep + add, key=lambda c: c.distance)

    def _far_both_sides(self, clusters: List[Cluster], valid: float, floor_valid: float) -> float:
        """``cluster.far_axis_both_sides`` 2 (25.09, far_switch, opt-in): on a bent axis (no
        straight bonus) fitted to two boundaries, a corridor obstacle beyond the height reference
        and beyond the shorter boundary's range (+ ``axis_valid_margin``) is demoted to advisory
        ``beyond_axis``: the curvature that puts it in the corridor is not supported that far on
        both sides. Other clusters keep their reasons (a column stays a column hit). Returns the
        range supported by the corridor model (for the monitored-range estimate)."""
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
            # 26.09 (safety review): a blob kept only by the wall keep that another rule demoted is not
            # an object the other stages decided on
            others = [k for k in clusters if not (k.wall_kept and k.reason)]
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
        Xc, dyc = corr.xyz[tall, 0], corr.lateral_rail()[tall]
        keep = []
        for c in lows:
            m = ((Xc > c.bbox_min[0] - 0.3) & (Xc < c.bbox_max[0] + 0.3)
                 & (np.abs(dyc - c.lateral) < 0.5 * float(c.size[1]) + 0.3))
            if int(m.sum()) >= 3:
                continue
            strad = any(c is k for k in straddling)
            # 26.09 (safety review): a blob kept only by the wall keep (cluster.wall_keep_gauge_voxels)
            # counts only as an obstacle, as for a straddling cluster: demoted (a column), it must not
            # remove a low object beside it
            # 14.10 (review): so does a part the structure cut carved out of an oversize cluster
            # (Cluster.cut): the sealed detector dropped that cluster whole, it removed nothing
            dup = any(_overlap(c, k) for k in clusters
                      if not (strad or k.wall_kept or k.cut) or (k.zone == "gauge" and not k.reason))
            if not dup:
                keep.append(c)
        return keep

    def _shell(self, clusters: List[Cluster], xyz: np.ndarray, dy_all: np.ndarray, h_all: np.ndarray) -> None:
        """29.09 (cluster.shell_*, after TunnelGuard ``_shell_points``): a far gauge cluster standing on
        the floor and reaching the upper envelope is infrastructure when the tunnel lining continues
        right above it (a column, a post, a mast): demoted with reason 'shell' (a shape signature,
        so an earned STOP is kept by the stop-keep rule and near escalation still wins)."""
        c = self.cfg.cluster
        cand = [cl for cl in clusters if cl.zone == "gauge" and not cl.reason and cl.kind != "low"
                and cl.distance >= c.shell_min_distance and cl.height_max >= c.shell_min_top
                and cl.height_min < c.shell_max_bottom and cl.points_idx.size]
        if not cand:
            return
        X = xyz[:, 0]
        for cl in cand:
            idx = cl.points_idx
            x0, x1 = float(cl.bbox_min[0]), float(cl.bbox_max[0])
            ds = 1.0 + 0.01 * x0
            d0, d1 = float(dy_all[idx].min()) - c.shell_lateral, float(dy_all[idx].max()) + c.shell_lateral
            top = float(cl.height_max)
            m = ((X > x0 - ds) & (X < x1 + ds) & (h_all > top) & (h_all < top + c.shell_gap)
                 & (dy_all > d0) & (dy_all < d1))
            if int(np.count_nonzero(m)) < c.shell_min_points:
                continue
            touch = max(c.shell_touch_min, c.shell_touch_beams * 0.00218 * x0)
            if float(h_all[m].min()) - top <= touch:
                cl.reason, cl.zone, cl.demoted = "shell", "warning", True

    def _rail_reference(self, clusters: List[Cluster], xyz: np.ndarray, dy_rail: np.ndarray,
                        h_all: np.ndarray) -> List[Cluster]:
        """19.10 (F1 a/b; ``lowobj.local_rail_margin`` / ``rail_band_range`` > 0): low clusters that do not rise
        above the frame's own rail returns around them (``lowobj.rail_reference_check``; with
        ``local_rail_exclude_low`` both original and independent low-free references must reject the cluster,
        preventing fragmented objects from supplying their own reference; the opt-in near-bed clusters, which report
        objects below the rail head by design, are exempt) are advisory, reason ``below_rail_ref`` (a
        signature: an earned STOP is kept by the stop-keep rule) with ``local_rail_advisory``, or else weak low
        evidence handed to the tracker separately (it may continue a reported low STOP, never start one).
        Returns the clusters to confirm."""
        low = self.cfg.lowobj
        free = (low_free_mask(xyz.shape[0], clusters + self._low_height, xyz[:, 0], dy_rail)
                if low.local_rail_exclude_low else None)
        # the opt-in near-bed path (lowobj.near_enabled) reports objects below the rail head by design: exempt
        near = getattr(self, "_near_low", [])
        check = [c for c in clusters if not any(c is k for k in near)] if near else clusters
        weak = rail_reference_check(check, xyz[:, 0], dy_rail, h_all, low, self.cfg.track.rails_spacing, free)
        if not weak:
            return clusters
        if low.local_rail_advisory:
            for c in weak:
                c.zone, c.reason, c.demoted = "warning", "below_rail_ref", True
            return clusters
        for c in weak:
            c.low_height_weak = True
        self._low_height = self._low_height + weak
        return [c for c in clusters if not c.low_height_weak]

    def _mount_cross_check(self, clusters: List[Cluster], xyz: np.ndarray) -> None:
        """19.10 (``cluster.mount_cross_tol`` > 0, off by default; F1 lane, Falcon frame 4394): a second
        height reference in the near field. The calibrated mount puts the rail-head plane at
        ``z = -height`` (``MountCalibration.height``, frozen with the final tilt). Where the track model's
        rail head at a gauge cluster's distance X differs from it by more than ``mount_cross_tol`` +
        ``mount_cross_grade`` * X (a model that lost the bed: the Falcon floor fit that climbed to the
        ceiling behind a near person), the cluster stays an obstacle only if the mount reference also puts
        some of its points inside the envelope's height band (0 .. the profile top above the rail head);
        otherwise it is advisory, reason ``height_conflict`` (a signature: an earned STOP is kept by the
        stop-keep rule; never near-escalated). Only within ``mount_cross_range`` and once the mount
        calibration is final; corridor and low clusters alike."""
        cc = self.cfg.cluster
        st = self.calib.state
        if st.height is None or st.status not in ("ok", "identity") or not np.isfinite(st.height):
            return
        plane = -float(st.height)
        top = float(np.asarray(self.cfg.gauge.profile, dtype=np.float64)[:, 1].max())
        for cl in clusters:
            if (cl.zone != "gauge" or cl.reason or cl.distance > cc.mount_cross_range
                    or not cl.points_idx.size):
                continue
            x = float(cl.distance)
            if abs(float(self.track.rail_z(x)) - plane) <= cc.mount_cross_tol + cc.mount_cross_grade * x:
                continue
            hm = xyz[cl.points_idx, 2].astype(np.float64) - plane
            if np.all(hm > top) if cc.mount_cross_above_only else not np.any((hm >= 0.0) & (hm <= top)):
                cl.reason, cl.zone, cl.demoted = "height_conflict", "warning", True

    # -- 6 -------------------------------------------------------------------------------------
    def _confirm(self, clusters: List[Cluster], speed: Optional[float], dt: float):
        """Temporal persistence (in seconds: the tracker gets the measured frame interval).
        Returns the confirmed detections in the strict gauge and in the advisory zone."""
        low = self.cfg.lowobj
        low_ok = low.min_model_age <= 0 or self.track.age >= low.min_model_age
        self.tracker.update(clusters, ego_shift=(speed or 0.0) * dt, frame_dt=dt, low_ok=low_ok,
                            odo_speed=getattr(self, "_odo_speed", None),
                            rail_within=low.rail_start_within,
                            thin=self._thin if self.cfg.tracking.stop_keep_thin > 0 else None,
                            low_height=self._low_height,
                            low_frame_dt=self._low_frame_dt,
                            far_thin=self._far_thin(clusters) if self.cfg.tracking.thin_far_min_distance > 0 else None)
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
                reason=("doubt" if t.withheld else "near_envelope" if t.escalated
                        else "low_height_hold" if t.last.low_height_weak else "stop_hold" if (t.kept and t.zone == "gauge")
                        else t.last.reason), kind=t.last.kind,
            ))
            d = dets[-1]
            if pending and d.kind == "low" and d.zone == "gauge" and d.distance > low.pending_advisory_within:
                # 26.09 (P3 start-up, candidate a, off): a low track is advisory while the calibration is pending
                d.zone, d.reason = "warning", "calibration_pending"
        if self.far_confirm is not None:
            # 19.10 (farrange.confirm_*): far STOPs need range-consistent evidence over frames
            self.far_confirm.update(self.tracker.tracks)
            for d in dets:
                if d.zone == "gauge" and d.distance > self.cfg.farrange.confirm_from and not self.far_confirm.ok(d.id):
                    d.zone, d.reason = "warning", "far_unconfirmed"
        dets.sort(key=lambda d: d.distance)
        return [d for d in dets if d.zone == "gauge"], [d for d in dets if d.zone != "gauge"]

    def _far_thin(self, clusters: List[Cluster]) -> List[Cluster]:
        """27.09 (``tracking.thin_far_min_distance`` > 0, on): this frame's scan lines
        (corridor clusters flatter than ``cluster.min_height``) that the tracker may use as far
        evidence: at least that far, inside the strict gauge (zone ``gauge``: no far-field, overhead
        or signature demotion) with ``thin_far_min_voxels`` strict voxels, and overlapping no other
        cluster of the frame (the lower edge of an object another cluster already describes). With
        ``cluster.weak_min_points`` also the clusters under the point-count bar (``Cluster.weak``)
        that far and in zone ``gauge`` (``cluster.gauge_min_points`` strict voxels). Experimental
        ``far_min_ring_count`` filters known single-channel evidence only here; unknown channels
        retain the usual path, and ``self._thin`` still supports continuation of existing STOPs."""
        tc = self.cfg.tracking
        min_rings = tc.far_min_ring_count
        return [c for c in self._thin
                if c.distance >= tc.thin_far_min_distance and c.zone == "gauge"
                and (c.n_gauge >= tc.thin_far_min_voxels or not c.thin)
                and (min_rings <= 0 or c.ring_count <= 0 or c.ring_count >= min_rings)
                and not any(_overlap(c, k) for k in clusters)]

    # -- 6b ------------------------------------------------------------------------------------
    def _clear_cap(self, clusters: List[Cluster], cand: Candidates, dy_all: np.ndarray,
                   h_all: np.ndarray, trust: float = np.inf, n_acc: int = 1) -> Optional[float]:
        """``health.clear_cap`` (25.09): the cap on the monitored-range estimate
        (None = no cap), see :func:`clear_cap_distance`. Runs after the tracker and changes
        nothing it or the decision reads. 27.09: with ``clear_cap_thin`` also the nearest
        scan-line cluster of this frame inside the strict envelope (:func:`thin_cap_distance`),
        with ``clear_cap_persist`` the nearest persistent sparse envelope blob
        (:class:`resense.evidence.PersistentEvidence`, updated every frame while it is on)."""
        hcfg = self.cfg.health
        best = clear_cap_distance(clusters, self.tracker.tracks, cand, dy_all, h_all, self.cfg.gauge, hcfg)
        extra = []
        if hcfg.clear_cap_thin and self.cfg.tracking.stop_keep_thin > 0:
            extra.append(thin_cap_distance(self._thin, self.cfg.cluster.gauge_min_points, trust, n_acc))
        if hcfg.clear_cap_persist > 0:
            extra.append(self.evidence.update(cand.xyz[:, 0], cand.dy, cand.h, cand.low, self._evidence_dt))
        for d in extra:
            if d is not None:
                best = d if best is None else min(best, d)
        return best


def thin_cap_distance(thin: List[Cluster], min_gauge: int, trust: float, n_acc: int = 1) -> Optional[float]:
    """``health.clear_cap_thin`` (27.09; the predicate of the M2 observer of 26.09,
    scripts/evaluate_thin_monitoring.py, without its CAUTION): the distance of the nearest scan-line
    cluster of this frame (flatter than ``cluster.min_height``; kept only for
    ``tracking.stop_keep_thin``) inside the strict envelope (``zone`` gauge, at least ``min_gauge``
    strict voxels), not demoted by any rule (``reason`` empty), a corridor cluster (``kind`` empty),
    within the trusted range ``trust`` (axis and height reference), in a frame without merged
    frames (``n_acc`` 1). The row of returns an object leaves at the envelope top or on the bed at
    range (set O: the box above the envelope, the plank) caps the estimate although it cannot start
    a track. A cluster under the point-count bar kept only as far evidence for an approaching track
    (``Cluster.weak``, ``cluster.weak_min_points``) does not cap: it is not a scan line of the kind
    this predicate was validated on."""
    best: Optional[float] = None
    if n_acc != 1:
        return None
    for c in thin:
        if not c.thin or c.weak or c.kind or c.reason or c.zone != "gauge" or c.n_gauge < min_gauge:
            continue
        d = float(c.distance)
        if np.isfinite(d) and 0.0 <= d <= trust and (best is None or d < best):
            best = d
    return best


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
    into an uncapped monitored-range estimate beyond that tracked object. Other objects can
    still be missed."""
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
        if hcfg.clear_cap_skip_columns and (c.reason == "column" or (t is not None and t.column_held)):
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
            if hcfg.clear_cap_skip_columns and (t.last.reason == "column" or t.column_held):
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
