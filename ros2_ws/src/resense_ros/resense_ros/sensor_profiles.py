"""Explicit lidar coordinate profiles shared by launch and between-bag resets.

The Falcon recording uses ROS axes. The manufacturer's native x-up convention is
a separate explicit profile: a topic or frame name alone does not establish which
coordinate convention a driver publishes. Profiles never infer a Pandar density
model for Falcon. Runtime callers must reset their detector and pending input when
installing a newly resolved profile; this module only produces configuration.
"""

from __future__ import annotations

from copy import deepcopy

PROFILE_NAMES = ("manual", "pandar128", "falcon_ros", "falcon_native")
_PROFILES = {
    "pandar128": (("-y", "+x", "+z"), "pandar128"),
    "falcon_ros": (("+x", "+y", "+z"), "falcon_prime"),
    "falcon_native": (("+z", "-y", "+x"), "falcon_prime"),
}


def apply_sensor_profile(cfg, profile: str):
    """Return ``(independent_config, range_model)`` for an explicit profile.

    ``manual`` preserves every setting and returns ``None`` for the range model,
    meaning the caller keeps its explicit existing selection. Named profiles set
    the three axes and enable mount calibration with the upright/inverted search.
    With correct axes, native Falcon does not require the wider, wall-prone search
    over all 24 orientations. Deliberate 24-orientation recovery is a separate
    explicit calibration option exercised by the N2 battery.
    """
    if profile not in PROFILE_NAMES:
        raise ValueError(
            f"unknown sensor profile {profile!r}; choose one of {PROFILE_NAMES}"
        )
    resolved = deepcopy(cfg)
    if profile == "manual":
        return resolved, None
    axes, range_model = _PROFILES[profile]
    resolved.sensor.forward, resolved.sensor.left, resolved.sensor.up = axes
    resolved.sensor.roll_deg = resolved.sensor.pitch_deg = resolved.sensor.yaw_deg = 0.0
    resolved.calibration.enabled = True
    resolved.calibration.keep_up_axis = True
    far = getattr(resolved, "farrange", None)
    if range_model == "falcon_prime" and far is not None and far.with_falcon_profile:
        # 19.10 (Falcon long range): the far straight axis and the range crop beyond 250 m
        far.enabled = True
        resolved.sensor.max_range = far.max_range
        resolved.gauge.range_max = far.max_range
        resolved.track.floor_verify_max_range = far.max_range
    return resolved, range_model
