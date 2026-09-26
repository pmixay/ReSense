"""Production guards (v0.6): is the detector's answer trustworthy right now?

A safety function must say not only "obstacle at X m" / "clear", but also *how far the path
was actually checked* and whether the input can be trusted. :class:`HealthMonitor` computes,
per frame and without touching any detection:

* ``points`` - valid returns; a frame far below ``min_points`` (a dead or blinded sensor, a
  truncated message) is a fault, one below ``low_points_fraction`` of the running median a
  warning;
* ``near_fraction`` - returns closer than ``near_range``: a dirty or blocked window, spray;
* ``blocked_sectors`` - 10 deg azimuth sectors of the central +-30 deg without returns
  (something in front of the sensor);
* ``visibility`` - how far along the track the tunnel is seen (the 20th farthest return within
  3 m of the track axis): the sightline in a curve, the end of the tunnel, fog;
* ``rail_lock`` - share of the recent frames in which the rail pair was found (the track model
  runs on its prior without it: stations, switches, a covered bed);
* ``latency_p95_ms`` against the frame budget;
* the mount calibration status and drift (``resense/calibration.py``);
* ``floor_shadow_frames`` / ``floor_held_frames`` / ``floor_released_frames`` (review 25.09) -
  since the start (or a reset), the frames in which the floor-shadow rule of the track model
  (``track.floor_shadow_height``) found the shadow of a large near object, held the previous bed,
  or was released after ``track.floor_shadow_max_hold`` held frames in a row: counters only;
* ``monitored_range`` - the distance up to which the corridor was checked this frame:
  ``min(visibility, trusted axis range, trusted height-reference range, gauge range)``; and
  ``clear_distance`` - the nearest confirmed obstacle, or ``monitored_range`` when there is
  none; with ``clear_cap`` (on since 25.09, round 2) also no farther than the nearest unconfirmed
  or advisory candidate touching the envelope (``candidate_distance``, from the detector). A
  consumer that brakes on ``clear_distance < stopping distance`` gets the fail-safe
  behaviour for free: a blinded sensor, a lost track model or a stale input shrink it.

``level`` is ``ok`` / ``warn`` / ``error`` with human-readable ``messages``; the ROS node
publishes it as ``diagnostic_msgs/DiagnosticArray`` and adds the input-staleness watchdog.
``decision_level`` (26.09) is the level the node's decision reads (``DetectorNode.decision``: a
``warn`` there is ``CAUTION``): ``level`` without the latency warning unless
``health.latency_affects_decision``. Latency over the budget is the machine being slow, not the
path being unsafe; it stays in ``level``, ``messages`` and ``latency_p95_ms``.
"""
from __future__ import annotations

from collections import deque
from typing import Optional

import numpy as np

from resense import _native
from resense.config import GaugeConfig, HealthConfig

LEVELS = ("ok", "warn", "error")


def visibility_along_track(xyz: np.ndarray, center_y, band: float = 3.0, k: int = 20) -> float:
    """X of the ``k``-th farthest return within ``band`` metres of the track axis (m)."""
    model = getattr(center_y, "__self__", None)       # TrackModel.center_y: one native pass
    if _native.enabled() and hasattr(model, "center_coefs"):
        v = _native.visibility(xyz, *model.center_coefs(), band, k)
        if v is not None:
            return v
    X = xyz[:, 0]
    fwd = X > 0.0
    if not fwd.any():
        return 0.0
    Xf = X[fwd].astype(np.float64)
    sel = np.abs(xyz[fwd, 1] - center_y(Xf)) < band
    Xs = Xf[sel]
    if Xs.size == 0:
        return 0.0
    if Xs.size <= k:
        return float(Xs.min())
    return float(np.partition(Xs, Xs.size - k)[Xs.size - k])


class HealthMonitor:
    def __init__(self, cfg: HealthConfig):
        self.cfg = cfg
        self._points = deque(maxlen=200)
        self._lock = deque(maxlen=max(1, int(cfg.lock_window)))
        self._lat = deque(maxlen=max(1, int(cfg.latency_window)))
        self._shadow = [0, 0, 0]            # floor-shadow frames: found, held, released

    def reset(self) -> None:
        self._points.clear()
        self._lock.clear()
        self._lat.clear()
        self._shadow = [0, 0, 0]

    def update(self, xyz: np.ndarray, meta: dict, track, gauge: GaugeConfig, trusted_range: float,
               rails_min_score: float, latency_ms: float, calibration: Optional[dict] = None,
               obstacle_distance: Optional[float] = None, candidate_distance: Optional[float] = None) -> dict:
        cfg = self.cfg
        msgs, level, dlevel = [], 0, 0

        def flag(lv: int, text: str, decision: bool = True):
            nonlocal level, dlevel
            level = max(level, lv)
            if decision:
                dlevel = max(dlevel, lv)
            msgs.append(text)

        n = int(xyz.shape[0])
        n_raw = int(meta.get("n_raw", n))
        n_near = int(meta.get("n_near", 0))
        med = float(np.median(self._points)) if self._points else float(n)
        self._points.append(n)
        if n < cfg.min_points:
            flag(2, f"only {n} valid returns (< {cfg.min_points}): sensor blinded or message truncated")
        elif self._points and n < cfg.low_points_fraction * med:
            flag(1, f"{n} valid returns, {n / max(med, 1):.0%} of the running median")
        near_frac = n_near / max(n_raw, 1)
        if near_frac > cfg.max_near_fraction:
            flag(1, f"{near_frac:.0%} of the returns closer than {cfg.near_range} m: dirty or blocked window")

        # blocked sectors in the central +-30 deg
        blocked = 0
        if n:
            az = np.degrees(np.arctan2(xyz[:, 1], xyz[:, 0]))
            edges = np.arange(-30.0, 30.0 + 1e-6, cfg.sector_deg)
            counts = np.histogram(az, bins=edges)[0]
            ref = float(np.median(counts)) if counts.size else 0.0
            blocked = int((counts < 0.05 * max(ref, 1.0)).sum()) if ref > 0 else int(counts.size)
            if blocked:
                flag(2 if blocked >= counts.size // 2 else 1,
                     f"{blocked} of {counts.size} central {cfg.sector_deg:.0f} deg sectors without returns: view blocked")

        vis = visibility_along_track(xyz, track.center_y) if n else 0.0
        if vis < cfg.min_visibility:
            flag(1, f"track visible to {vis:.0f} m only (< {cfg.min_visibility:.0f} m)")

        self._lock.append(bool(track.rail_score >= rails_min_score))
        lock = sum(self._lock) / len(self._lock)
        if len(self._lock) >= min(5, self._lock.maxlen) and lock < cfg.min_lock_rate:
            flag(1, f"rail pair found in {lock:.0%} of the last {len(self._lock)} frames: track model on its prior")

        if getattr(track, "floor_shadow", 0.0) > 0:
            self._shadow[0] += 1
            if track.floor_held:
                self._shadow[1] += 1
            elif getattr(track, "floor_hold_run", 0) > 0:
                self._shadow[2] += 1

        self._lat.append(float(latency_ms))
        p95 = float(np.percentile(self._lat, 95))
        if len(self._lat) >= 10 and p95 > cfg.latency_budget_ms:
            flag(1, f"latency p95 {p95:.0f} ms over the {cfg.latency_budget_ms:.0f} ms budget",
                 decision=cfg.latency_affects_decision)

        if calibration:
            st = calibration.get("status")
            if st == "fallback":
                flag(1, "mount calibration: " + calibration.get("message", "fallback"))
            if calibration.get("drift_deg", 0.0) > 0 and "drift" in calibration.get("message", ""):
                flag(1, calibration["message"])

        monitored = float(max(0.0, min(vis, trusted_range, gauge.range_max)))
        if level >= 2:
            monitored = 0.0                     # an input fault: nothing is verified
        clear = monitored if obstacle_distance is None else float(min(obstacle_distance, monitored))
        if candidate_distance is not None:     # clear_cap (25.09): an unconfirmed / advisory object in the envelope
            clear = float(max(0.0, min(clear, candidate_distance)))
        out = {
            "level": LEVELS[level], "decision_level": LEVELS[dlevel], "messages": msgs,
            "points": n, "near_fraction": round(near_frac, 3), "blocked_sectors": blocked,
            "visibility": round(vis, 1), "rail_lock": round(lock, 2), "latency_p95_ms": round(p95, 1),
            "monitored_range": round(monitored, 1), "clear_distance": round(clear, 1),
            "floor_shadow_frames": self._shadow[0], "floor_held_frames": self._shadow[1],
            "floor_released_frames": self._shadow[2],
        }
        if cfg.clear_cap:
            out["candidate_distance"] = None if candidate_distance is None else round(float(candidate_distance), 1)
        return out
