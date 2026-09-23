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
   returns ahead than behind). Then the axis-aligned proper rotations are tried - the 8 that
   keep the configured up axis vertical (upright or inverted: a spinning LiDAR's spin axis is
   vertical in any real mount) or, with ``keep_up_axis: false``, all 24 - and each
   is scored by the rail pair it reveals: two parallel ridges 1.59 m apart, 0.08-0.5 m above a
   bed that lies below the sensor, running along +X, with the tunnel visible ahead. Nothing
   but a correctly oriented cloud shows that pattern. A new orientation is adopted only when
   the same candidate wins on ``orientation_votes`` frames and the configured one never
   passed, so a platform or a switch (no rails) cannot flip the mount. (The sideways
   candidates are off by default because a flat side wall of a square tunnel with two cable
   trays on it passes for a bed with a rail pair: measured on ``roundT_squareT_pressureGate_squareT``.
   For the same reason a sensor that *is* mounted on its side must be described by
   ``sensor.forward/left/up``: the geometry alone cannot tell such a wall from the bed.)
2. **Roll** from the rail pair: the two rail heads are at the same height in the track's own
   cross-section, so their height difference over the rail spacing is the sensor roll
   relative to the rail plane (which is what the clearance gauge is defined in).
3. **Pitch** from the slope of the bed fit at the vehicle (``floor_coef`` linear term): the
   train body rides on the track, so the bed slope at X = 0 in the sensor frame is the mount
   pitch whatever the grade of the line.
4. **Yaw** from the rail-slab tangent (``RailsFit.tan_yaw``) - only when its median exceeds
   ``min_yaw_deg`` (a big mount yaw); the per-frame track model follows small and dynamic
   yaw (curves) itself.

The tilt is measured in two stages, because on a moving train the per-frame roll swings by
+-1 deg with the cant transitions and the body's lean (the 20-minute ride: median -0.1 deg,
10-90 % range -1.0 ... +0.7 deg, EXPERIMENTS.md section 6), and neighbouring frames see the same
stretch of rail: a median of 5 consecutive frames is off by up to 1.6-2.2 deg there. A
**provisional** correction from the first ``provisional_frames`` observations is applied only
for a clearly tilted rig (``provisional_min_deg``, e.g. the ~3 deg of the ``doubleT_obstacle``
rig); the **final** one is the median of ``frames`` observations taken every ``obs_spacing``
frames (20 s at the defaults: p90 error 0.5 deg on the ride), applied above ``apply_min_deg``,
and then frozen; the track model is re-seeded after every change. Afterwards the same
measurements continue every ``monitor_period`` frames on the corrected cloud: when the median
of the last ``drift_window`` checks leaves ``drift_warn_deg`` (a mount knocked loose - a
lasting change, not a curve) it is reported through the health status, never silently
re-applied.
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


def orientation_candidates(keep_up_axis: bool = False) -> List[np.ndarray]:
    """The 24 proper rotations that map sensor axes onto signed vehicle axes (identity first);
    with ``keep_up_axis`` only the 8 whose up row is the configured up axis (either sign)."""
    out = [np.eye(3)]
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1.0, -1.0), repeat=3):
            R = np.zeros((3, 3))
            for row, (col, s) in enumerate(zip(perm, signs)):
                R[row, col] = s
            if abs(np.linalg.det(R) - 1.0) < 1e-9 and not np.allclose(R, np.eye(3)):
                if keep_up_axis and abs(R[2, 2]) != 1.0:
                    continue
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
    status: str = "pending"         # pending | provisional | ok | identity | fallback | disabled
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
        self._obs: List[tuple] = []      # spaced observations for the final tilt: (roll, pitch, yaw, height, lateral)
        self._recent: List[tuple] = []   # the first observations, for the provisional tilt
        self._provisional_done = False
        self._since_obs = 0
        self._applied = (0.0, 0.0, 0.0)  # rad: the tilt part of the current correction (roll, pitch, yaw)
        self._checks: List[tuple] = []   # drift monitor: residual (roll, pitch) of the last checks
        self.last_change_deg = 0.0       # how far the last correction change rotated the cloud
        self._frames = 0
        self._frozen = not cfg.enabled
        self._since_check = 0
        self._candidates = orientation_candidates(getattr(cfg, "keep_up_axis", True))

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

    def _set_tilt(self, roll: float, pitch: float, yaw: float) -> bool:
        """Compose the orientation with a tilt (rad); True when the correction changed."""
        R = rot_z(yaw) @ rot_y(pitch) @ rot_x(roll) @ self._R_orient
        d = R @ self.state.R.T
        self.last_change_deg = float(np.degrees(np.arccos(np.clip((np.trace(d) - 1.0) / 2.0, -1.0, 1.0))))
        self.state.R = R
        self._applied = (roll, pitch, yaw)
        self.state.roll_deg, self.state.pitch_deg, self.state.yaw_deg = (float(np.degrees(v)) for v in (roll, pitch, yaw))
        return self.last_change_deg > 1e-6

    @staticmethod
    def _medians(obs: List[tuple]):
        a = np.asarray(obs, dtype=np.float64)
        yaws = a[:, 2][np.isfinite(a[:, 2])]
        return (float(np.median(a[:, 0])), float(np.median(a[:, 1])), float(np.median(yaws)) if yaws.size else 0.0,
                float(np.median(a[:, 3])), float(np.median(a[:, 4])))

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
                        self._checks = (self._checks + [(ob.roll, ob.pitch)])[-max(cfg.drift_window, 1):]
                        c = np.asarray(self._checks)
                        self.state.drift_deg = float(np.degrees(np.max(np.abs(np.median(c, axis=0)))))
                        drifting = len(self._checks) >= max(cfg.drift_window // 2, 1) and self.state.drift_deg > cfg.drift_warn_deg
                        if drifting:
                            self.state.message = (f"mount drift: residual tilt {self.state.drift_deg:.1f} deg "
                                                  f"(> {cfg.drift_warn_deg}, median of the last {len(self._checks)} checks) "
                                                  f"since calibration")
                        elif self.state.message.startswith("mount drift"):
                            self.state.message = "drift back within bounds"
            return False

        spacing = max(cfg.obs_spacing, 1)
        if self._provisional_done and self._config_passed and self._obs and self._since_obs + 1 < spacing:
            # between two spaced observations the frame is not needed: observing every frame cost
            # 10-15 ms for the first ~20 s of every recording (review 23.09). The spacing counts
            # frames; the observation is taken on the first frame with a rail pair after it.
            self._since_obs += 1
            return self._finish(False)
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
                    self.last_change_deg = 90.0
                    self._obs.clear()
                    self._recent.clear()
                    self._since_obs = 0
                    self._config_passed = True          # stop searching
                    return True
        if ob.ok:
            self._config_passed = True
            # absolute estimate = the tilt already applied + the residual seen through it (small angles)
            a_r, a_p, a_y = self._applied
            est = (ob.roll + a_r, ob.pitch + a_p, (ob.yaw + a_y) if np.isfinite(ob.yaw) else float("nan"),
                   ob.height, ob.lateral)
            if not self._provisional_done:
                self._recent.append(est)
            self._since_obs += 1
            if not self._obs or self._since_obs >= max(cfg.obs_spacing, 1):
                self._obs.append(est)
                self._since_obs = 0
        return self._finish(changed)

    def _finish(self, changed: bool) -> bool:
        """The provisional tilt, the final tilt and the no-rail fallback, once the frame's
        observation (if any) is recorded."""
        cfg = self.cfg
        max_t = np.radians(cfg.max_tilt_deg)
        # --- 2a. provisional tilt: only a clearly tilted rig is corrected before the final window
        if not self._provisional_done and len(self._recent) >= cfg.provisional_frames:
            self._provisional_done = True
            roll, pitch, yaw, _, _ = self._medians(self._recent)
            if (np.degrees(max(abs(roll), abs(pitch))) >= cfg.provisional_min_deg
                    and abs(roll) <= max_t and abs(pitch) <= max_t):
                yaw = yaw if abs(yaw) >= np.radians(cfg.min_yaw_deg) else 0.0
                changed = self._set_tilt(roll, pitch, yaw)
                self.state.status = "provisional"
                self.state.message = (f"provisional tilt: roll {self.state.roll_deg:+.2f}, pitch {self.state.pitch_deg:+.2f} deg "
                                      f"(final after {cfg.frames} observations)")
        # --- 2b. final tilt: medians over spaced frames with a rail pair
        if len(self._obs) >= cfg.frames:
            roll, pitch, yaw, height, lateral = self._medians(self._obs)
            if abs(roll) > max_t or abs(pitch) > max_t:
                self.state.status = "fallback"
                self.state.message = (f"implausible tilt (roll {np.degrees(roll):.1f}, pitch "
                                      f"{np.degrees(pitch):.1f} deg): configured mapping kept")
                self._frozen = True
                return self._set_tilt(0.0, 0.0, 0.0) or changed     # drop a provisional tilt too
            if abs(roll) < np.radians(cfg.apply_min_deg):
                roll = 0.0
            if abs(pitch) < np.radians(cfg.apply_min_deg):
                pitch = 0.0
            if abs(yaw) < np.radians(cfg.min_yaw_deg):
                yaw = 0.0
            changed = self._set_tilt(roll, pitch, yaw) or changed
            self.state.height, self.state.lateral = height, lateral
            self.state.frames_used = len(self._obs)
            identity = np.allclose(self.state.R, np.eye(3), atol=1e-9)
            self.state.status = "identity" if identity else "ok"
            if not self.state.message or self.state.message.startswith("provisional"):
                self.state.message = ("configured mapping confirmed" if identity else
                                      f"tilt corrected: roll {self.state.roll_deg:+.2f}, pitch {self.state.pitch_deg:+.2f}, "
                                      f"yaw {self.state.yaw_deg:+.2f} deg")
            self._frozen = True
        elif self._frames >= cfg.max_frames:
            kept = "provisional correction kept" if self.state.status == "provisional" else "configured mapping kept"
            self.state.status = "fallback"
            self.state.message = (f"no rail pair in {self._frames} frames: {kept}"
                                  if not self._obs else f"only {len(self._obs)} observations with a rail pair: {kept}")
            self._frozen = True
        return changed
