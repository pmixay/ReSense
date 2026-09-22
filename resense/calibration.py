"""Automatic LiDAR mount calibration (v0.6): which way the sensor looks, and how it is tilted.

The detector works in the vehicle frame (X forward, Y left, Z up). ``sensor.forward/left/up``
maps the raw sensor axes onto it for the hackathon mount (``-y/+x/+z``); the track model then
re-estimates the sensor height, the lateral offset and the yaw of the track every frame. What
the per-frame model cannot absorb is a *different mount*: a unit bolted on with another axis
forward (``+x`` is the ROS convention and what most drivers publish), upside down, or rolled
or pitched by a few degrees. A roll of 3 deg tilts the gauge polygon by 7 cm at its sides and
18 cm at its top corners; a wrong forward axis makes the detector blind. This module finds the
mount from the data during the first frames and hands the detector a correction rotation
``R`` (``p_vehicle = R @ p_configured``), so a new train needs no hand calibration.

What is measured, and from what:

1. **Orientation** (which signed sensor axis points forward / up): only when the configured
   mapping fails a sanity check on a frame (no rail pair in the near range, or fewer far
   returns ahead than behind). Then all 24 axis-aligned proper rotations are tried and each
   is scored by the rail pair it reveals: two parallel ridges 1.59 m apart, 0.08-0.5 m above a
   bed that lies below the sensor, running along +X, with the tunnel visible ahead. Nothing
   but a correctly oriented cloud shows that pattern. A new orientation is adopted only when
   the same candidate wins on ``orientation_votes`` frames and the configured one never
   passed, so a platform or a switch (no rails) cannot flip the mount.
2. **Roll** from the rail pair: the two rail heads are at the same height in the track's own
   cross-section, so their height difference over the rail spacing is the sensor roll
   relative to the rail plane (which is what the clearance gauge is defined in).
3. **Pitch** from the slope of the bed fit at the vehicle (``floor_coef`` linear term): the
   train body rides on the track, so the bed slope at X = 0 in the sensor frame is the mount
   pitch whatever the grade of the line.
4. **Yaw** from the rail-slab tangent (``RailsFit.tan_yaw``) - only when its median exceeds
   ``min_yaw_deg`` (a big mount yaw); the per-frame track model follows small and dynamic
   yaw (curves) itself.

Medians over ``frames`` frames with a rail pair are composed into ``R`` once and frozen;
the track model is then re-seeded. Afterwards the same measurements continue every
``monitor_period`` frames on the corrected cloud: a residual beyond ``drift_warn_deg`` (a
mount knocked loose) is reported through the health status, never silently re-applied.
Implausible estimates (tilt > ``max_tilt_deg``) are rejected and reported; with no rail pair
in ``max_frames`` frames the calibrator gives up and keeps the configured mapping
(``status = 'fallback'``).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from resense.config import CalibrationConfig, TrackConfig
from resense.track import TrackModel, _fit_floor, default_track_model, estimate_rails


def orientation_candidates() -> List[np.ndarray]:
    """The 24 proper rotations that map sensor axes onto signed vehicle axes (identity first)."""
    out = [np.eye(3)]
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1.0, -1.0), repeat=3):
            R = np.zeros((3, 3))
            for row, (col, s) in enumerate(zip(perm, signs)):
                R[row, col] = s
            if abs(np.linalg.det(R) - 1.0) < 1e-9 and not np.allclose(R, np.eye(3)):
                out.append(R)
    return out


def rot_x(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def axis_label(R: np.ndarray) -> str:
    """'forward=-y left=+x up=+z' for an axis-aligned rotation (rows = vehicle axes)."""
    names = "xyz"
    parts = []
    for row, veh in zip(R, ("forward", "left", "up")):
        j = int(np.argmax(np.abs(row)))
        parts.append(f"{veh}={'+' if row[j] > 0 else '-'}{names[j]}")
    return " ".join(parts)


@dataclass
class MountObservation:
    """What one frame says about the mount (in the currently corrected cloud)."""
    ok: bool                        # a plausible rail pair ahead, bed below, tunnel ahead
    rail_score: float = -1.0
    roll: float = float("nan")      # rad, correction about X that levels the rail heads
    pitch: float = float("nan")     # rad, correction about Y that levels the bed at the vehicle
    yaw: float = float("nan")       # rad, correction about Z that aligns X with the rails
    height: float = float("nan")    # m, sensor above the rail head at X = 0
    lateral: float = float("nan")   # m, track axis at X = 0 (+ left of the sensor)
    forward_ratio: float = 0.0      # far returns ahead / behind


def observe_mount(xyz: np.ndarray, tcfg: TrackConfig, prior: Optional[TrackModel] = None,
                  min_rail_score: float = 0.05, max_points: int = 60000) -> MountObservation:
    """Measure rails, bed slope and tunnel direction of one cloud (vehicle frame under the
    current correction). Cheap: the near range only, strided to ``max_points``."""
    X = xyz[:, 0]
    ax = np.abs(X)
    lat = np.hypot(xyz[:, 1], xyz[:, 2])
    fwd = int(((X > 15.0) & (lat < 0.35 * ax)).sum())
    rear = int(((X < -15.0) & (lat < 0.35 * ax)).sum())
    ratio = fwd / (rear + 1.0)
    near = (X > 2.0) & (X < 45.0) & (np.abs(xyz[:, 1]) < 4.0)
    P = xyz[near]
    if P.shape[0] > max_points:
        P = P[:: int(np.ceil(P.shape[0] / max_points))]
    if P.shape[0] < 500 or fwd < 200 or ratio < 1.5:
        return MountObservation(ok=False, forward_ratio=ratio)
    base = prior if prior is not None else default_track_model(tcfg)
    base = TrackModel(floor_coef=np.array(base.floor_coef, dtype=np.float64), floor_range=base.floor_range,
                      center=base.center, yaw=0.0 if prior is None else base.yaw,
                      curvature=0.0 if prior is None else base.curvature, rail_offset=base.rail_offset)
    fit = _fit_floor(P, tcfg, base)
    if fit is None:
        return MountObservation(ok=False, forward_ratio=ratio)
    coef, frange, _, _ = fit
    model = TrackModel(floor_coef=coef, floor_range=frange, center=base.center, yaw=base.yaw,
                       curvature=base.curvature, rail_offset=base.rail_offset)
    if float(model.floor_z(0.0)) > -0.3:
        return MountObservation(ok=False, forward_ratio=ratio)       # the "bed" is not below the sensor
    rails = estimate_rails(P, model, tcfg, base.center, prior)
    if rails.score < min_rail_score or not np.isfinite(rails.cant):
        return MountObservation(ok=False, rail_score=rails.score, forward_ratio=ratio)
    roll = -np.arctan2(rails.cant, tcfg.rails_spacing)
    slope = float(coef[-2])                                          # dz/dX of the bed at X = 0
    pitch = float(np.arctan(slope))
    yaw = -float(np.arctan(rails.tan_yaw)) if rails.tan_yaw is not None else float("nan")
    height = -float(model.floor_z(0.0) + rails.rail_offset)
    return MountObservation(ok=True, rail_score=float(rails.score), roll=float(roll), pitch=pitch, yaw=yaw,
                            height=height, lateral=float(rails.center), forward_ratio=ratio)


@dataclass
class MountCalibration:
    """Current state of the calibration, as reported in the status JSON (``mount``)."""
    R: np.ndarray = field(default_factory=lambda: np.eye(3))
    status: str = "pending"         # pending | ok | identity | fallback | disabled
    orientation: str = "configured"  # 'configured' or the adopted axis mapping, e.g. 'forward=+x left=+y up=+z'
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    height: Optional[float] = None
    lateral: Optional[float] = None
    frames_used: int = 0
    drift_deg: float = 0.0          # residual tilt seen by the monitor after freezing
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "status": self.status, "orientation": self.orientation,
            "roll_deg": round(self.roll_deg, 2), "pitch_deg": round(self.pitch_deg, 2),
            "yaw_deg": round(self.yaw_deg, 2),
            "height": None if self.height is None else round(self.height, 2),
            "lateral": None if self.lateral is None else round(self.lateral, 2),
            "frames_used": int(self.frames_used), "drift_deg": round(self.drift_deg, 2),
            "message": self.message,
        }


class MountCalibrator:
    """Online mount calibration: observe the first frames, freeze a correction, monitor drift."""

    def __init__(self, cfg: CalibrationConfig, tcfg: TrackConfig):
        self.cfg = cfg
        self.tcfg = tcfg
        self.state = MountCalibration(status="pending" if cfg.enabled else "disabled")
        self._R_orient = np.eye(3)
        self._orient_votes: dict = {}
        self._config_passed = False
        self._obs: List[MountObservation] = []
        self._frames = 0
        self._frozen = not cfg.enabled
        self._since_check = 0
        self._candidates = orientation_candidates()

    # ------------------------------------------------------------------
    @property
    def R(self) -> np.ndarray:
        return self.state.R

    @property
    def frozen(self) -> bool:
        return self._frozen

    def apply(self, xyz: np.ndarray) -> np.ndarray:
        """The cloud in the corrected vehicle frame (the same array when the correction is the identity)."""
        R = self.state.R
        if np.allclose(R, np.eye(3), atol=1e-9):
            return xyz
        return (xyz @ R.T.astype(np.float32)).astype(np.float32, copy=False)

    # ------------------------------------------------------------------
    def _search_orientation(self, xyz_cfg: np.ndarray) -> Optional[int]:
        """Index of the best passing candidate orientation for a cloud in the configured frame."""
        best, best_score = None, 0.0
        for k, Rc in enumerate(self._candidates):
            if k == 0:
                continue
            ob = observe_mount(xyz_cfg @ Rc.T, self.tcfg, None, self.cfg.min_rail_score)
            if ob.ok and ob.rail_score > best_score:
                best, best_score = k, ob.rail_score
        return best

    def update(self, xyz_cfg: np.ndarray, xyz_cur: np.ndarray, track: Optional[TrackModel]) -> bool:
        """Feed one frame (``xyz_cfg``: the configured vehicle frame; ``xyz_cur``: the same cloud
        under the current correction; ``track``: the detector's current model). Returns True
        when the correction changed (the caller re-seeds its track model)."""
        cfg = self.cfg
        if not cfg.enabled:
            return False
        self._frames += 1
        if self._frozen:
            if cfg.monitor_period > 0:
                self._since_check += 1
                if self._since_check >= cfg.monitor_period:
                    self._since_check = 0
                    ob = observe_mount(xyz_cur, self.tcfg, track, cfg.min_rail_score)
                    if ob.ok:
                        tilt = np.degrees(max(abs(ob.roll), abs(ob.pitch)))
                        a = cfg.drift_smoothing
                        self.state.drift_deg = float(a * self.state.drift_deg + (1 - a) * tilt)
                        if self.state.drift_deg > cfg.drift_warn_deg:
                            self.state.message = (f"mount drift: residual tilt {self.state.drift_deg:.1f} deg "
                                                  f"(> {cfg.drift_warn_deg}) since calibration")
            return False

        ob = observe_mount(xyz_cur, self.tcfg, track, cfg.min_rail_score)
        changed = False
        # --- 1. orientation: only if the current mapping fails and another one passes repeatedly
        if not ob.ok and cfg.search_orientations and not self._config_passed:
            k = self._search_orientation(xyz_cfg)
            if k is not None:
                self._orient_votes[k] = self._orient_votes.get(k, 0) + 1
                if self._orient_votes[k] >= cfg.orientation_votes:
                    self._R_orient = self._candidates[k]
                    self.state.R = self._R_orient.copy()
                    self.state.orientation = axis_label(self._R_orient)
                    self.state.message = f"sensor orientation found from the data: {self.state.orientation}"
                    self._obs.clear()
                    self._config_passed = True          # stop searching
                    return True
        if ob.ok:
            self._config_passed = True
            self._obs.append(ob)
        # --- 2. tilt: medians over the frames with a rail pair
        if len(self._obs) >= cfg.frames:
            roll = float(np.median([o.roll for o in self._obs]))
            pitch = float(np.median([o.pitch for o in self._obs]))
            yaws = [o.yaw for o in self._obs if np.isfinite(o.yaw)]
            yaw = float(np.median(yaws)) if yaws else 0.0
            height = float(np.median([o.height for o in self._obs]))
            lateral = float(np.median([o.lateral for o in self._obs]))
            max_t = np.radians(cfg.max_tilt_deg)
            if abs(roll) > max_t or abs(pitch) > max_t:
                self.state.status = "fallback"
                self.state.message = (f"implausible tilt (roll {np.degrees(roll):.1f}, pitch "
                                      f"{np.degrees(pitch):.1f} deg): configured mapping kept")
                self._frozen = True
                return False
            if abs(roll) < np.radians(cfg.apply_min_deg):
                roll = 0.0
            if abs(pitch) < np.radians(cfg.apply_min_deg):
                pitch = 0.0
            if abs(yaw) < np.radians(cfg.min_yaw_deg):
                yaw = 0.0
            R = rot_z(yaw) @ rot_y(pitch) @ rot_x(roll) @ self._R_orient
            self.state.R = R
            self.state.roll_deg, self.state.pitch_deg, self.state.yaw_deg = (float(np.degrees(v)) for v in (roll, pitch, yaw))
            self.state.height, self.state.lateral = height, lateral
            self.state.frames_used = len(self._obs)
            identity = np.allclose(R, np.eye(3), atol=1e-9)
            self.state.status = "identity" if identity else "ok"
            if not self.state.message:
                self.state.message = ("configured mapping confirmed" if identity else
                                      f"tilt corrected: roll {self.state.roll_deg:+.2f}, pitch {self.state.pitch_deg:+.2f}, "
                                      f"yaw {self.state.yaw_deg:+.2f} deg")
            self._frozen = True
            changed = not identity
        elif self._frames >= cfg.max_frames:
            self.state.status = "fallback"
            self.state.message = (f"no rail pair in {self._frames} frames: configured mapping kept"
                                  if not self._obs else f"only {len(self._obs)} frames with a rail pair: configured mapping kept")
            self._frozen = True
        return changed
