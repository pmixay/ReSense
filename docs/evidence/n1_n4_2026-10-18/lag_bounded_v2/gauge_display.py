"""Display-only gauge state. Never feeds the detector, its tracks or decisions.

The trusted box describes supported rail geometry, not an obstacle-free path.
A stale/held outline is visibly grey and has zero solid range. Distance-weighted
smoothing uses declared/measured speed; without it a stated temporal fallback
avoids inventing odometry. Raw geometry and smoothing lag remain observable.
"""
from __future__ import annotations

import math
import time
import numpy as np


class GaugeDisplay:
    def __init__(self, range_min=3.0, range_max=250.0, smoothing_distance=6.0,
                 fallback_tau=0.8, growth_per_frame=5.0, hold_frames=3,
                 hold_seconds=0.5, max_lateral_lag=0.25, clock=time.monotonic):
        self.range_min, self.range_max = float(range_min), float(range_max)
        self.smoothing_distance, self.fallback_tau = smoothing_distance, fallback_tau
        self.growth_per_frame, self.hold_frames = growth_per_frame, hold_frames
        self.hold_seconds, self.max_lateral_lag, self.clock = hold_seconds, max_lateral_lag, clock
        self.x = np.arange(0.0, self.range_max + 1.0, 1.0)
        self.reset()

    def reset(self):
        self.center = self.rail = None
        self.stamp = None
        self.extent = self.previous_target = 0.0
        self.missing = 0
        self.last_good_clock = None
        self.expired = False
        self.last_status = self._status(False, "unavailable", 0.0, None, "unavailable")

    def _status(self, valid, reason, axis_valid, lag, smoothing):
        return {"valid": bool(valid), "held": self.center is not None and not valid,
                "reason": reason, "drawn_range_m": float(self.extent),
                "solid_range_m": float(self.extent) if valid else 0.0,
                "axis_valid_m": float(axis_valid), "missing_frames": self.missing,
                "hold_expired": self.expired,
                "max_lateral_lag_m": lag, "smoothing": smoothing,
                "meaning": "supported gauge geometry; clear_distance is separate"}

    def invalidate(self, reason="input_invalid"):
        self.missing += 1
        self.expired = (self.missing > self.hold_frames or (self.last_good_clock is not None
                        and self.clock() - self.last_good_clock >= self.hold_seconds))
        if self.expired:
            self.center = self.rail = None
            self.extent = self.previous_target = 0.0
            self.stamp = None
        self.last_status = self._status(False, reason, 0.0, None, "held")
        return dict(self.last_status)

    def update(self, track, stamp, health, speed=None):
        try:
            axis_valid = float(track.axis_valid)
            monitored = float(health.get("monitored_range", 0.0))
            target = min(axis_valid, monitored, self.range_max)
            y = np.broadcast_to(np.asarray(track.center_y(self.x), dtype=float), self.x.shape).copy()
            z = np.broadcast_to(np.asarray(track.rail_z(self.x), dtype=float), self.x.shape).copy()
            good = (math.isfinite(target) and target > self.range_min
                    and np.isfinite(y).all() and np.isfinite(z).all()
                    and health.get("freshness_valid", True) is not False
                    and health.get("level", "error") in ("ok", "warn")
                    and health.get("decision_level", "ok") in ("ok", "warn"))
        except (AttributeError, TypeError, ValueError):
            return self.invalidate("fit_unavailable")
        if not good:
            # A falling support range takes effect immediately, even on an invalid frame.
            if math.isfinite(target):
                self.extent = min(self.extent, max(0.0, target)) if target > 0 else self.extent
            return self.invalidate("input_or_fit_invalid")
        dt = max(0.0, min(1.0, float(stamp) - self.stamp)) if self.stamp is not None else 0.1
        known_speed = speed is not None and math.isfinite(float(speed))
        if known_speed:
            # At standstill still let the finite observation settle; no fake travelled distance.
            alpha = max(1 - math.exp(-abs(float(speed)) * dt / self.smoothing_distance),
                        1 - math.exp(-dt / (2 * self.fallback_tau)))
            smoothing = "distance_with_stationary_settling"
        else:
            alpha = 1 - math.exp(-dt / self.fallback_tau)
            smoothing = "time_fallback_no_odometry"
        if self.center is None:
            self.center, self.rail = y, z
            self.extent = min(target, self.range_min + self.growth_per_frame)
            self.previous_target = self.extent
        else:
            self.center += alpha * (y - self.center)
            self.rail += alpha * (z - self.rail)
        # A smoothed edge can lag a bending/new fit. Only draw the contiguous part
        # within 25 cm of the current fitted axis; do not hide metres of lag in a
        # stable-looking green box. Near-field discontinuities start a new display.
        support_target = target
        bad = np.flatnonzero((self.x >= self.range_min) & (self.x <= target)
                             & (np.abs(y - self.center) > self.max_lateral_lag))
        reason = "supported"
        if bad.size:
            agreement = float(self.x[bad[0]] - 1.0)
            if agreement <= self.range_min:
                self.center, self.rail = y, z
                self.extent = min(target, self.range_min + self.growth_per_frame)
                self.previous_target = self.extent
                reason = "reseeded_near_axis_change"
            else:
                target = min(target, agreement)
                reason = "range_limited_by_display_lag"
        # Require a positive range change to persist for two frames, then grow gradually.
        accepted_target = min(target, self.previous_target) if self.previous_target else self.range_min
        self.extent = min(target, max(self.range_min, min(accepted_target, self.extent + self.growth_per_frame)))
        self.previous_target, self.stamp, self.missing = target, float(stamp), 0
        self.last_good_clock, self.expired = self.clock(), False
        selected = (self.x >= self.range_min) & (self.x <= self.extent)
        lag = float(np.max(np.abs(y[selected] - self.center[selected]))) if selected.any() else 0.0
        self.last_status = self._status(True, reason, axis_valid, round(lag, 4), smoothing)
        self.last_status.update(support_range_m=support_target, agreement_range_m=target,
                                max_allowed_lateral_lag_m=self.max_lateral_lag)
        return dict(self.last_status)

    def outline(self, profile):
        """Four longitudinal edges and two end rings for the configured cross-section."""
        if self.center is None or self.extent <= self.range_min:
            return []
        xs = np.unique(np.r_[self.range_min, self.x[(self.x > self.range_min) & (self.x < self.extent)], self.extent])
        axis = np.column_stack((xs, np.interp(xs, self.x, self.center), np.interp(xs, self.x, self.rail)))
        polygon = np.asarray(profile, dtype=float)
        edges = [axis + [0.0, y, z] for y, z in polygon]
        for i in (0, -1):
            edges.append(np.vstack([axis[i] + [0.0, y, z] for y, z in np.vstack((polygon, polygon[0]))]))
        return edges
