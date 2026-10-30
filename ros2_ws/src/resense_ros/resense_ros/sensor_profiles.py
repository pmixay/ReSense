"""Explicit lidar coordinate profiles shared by launch and between-bag resets.

The Falcon recording uses ROS axes. The manufacturer's native x-up convention is
a separate explicit profile: a topic or frame name alone does not establish which
coordinate convention a driver publishes. Profiles never infer a Pandar density
model for Falcon. Runtime callers must reset their detector and pending input when
installing a newly resolved profile; this module only produces configuration.
"""

from __future__ import annotations

from copy import deepcopy

import numpy as np

PROFILE_NAMES = ("manual", "pandar128", "falcon_ros", "falcon_native")
# the Falcon Prime's own point fields (docs/evidence/extended_data_2026-10-17, field table); it has no ``ring``
FALCON_FIELDS = frozenset({"scan_id", "scan_idx", "elongation"})
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
    if range_model == "falcon_prime" and not getattr(resolved.tracking, "doubt_falcon", True):
        # 21.10 (G2, track opinion 1.3): the learned opinion is trained on Pandar tracks only
        resolved.tracking.doubt_model = ""
        resolved.tracking.doubt_extra_hits = 0
    far = getattr(resolved, "farrange", None)
    if range_model == "falcon_prime" and far is not None and far.with_falcon_profile:
        # 19.10 (Falcon long range): the far straight axis and the range crop beyond 250 m
        far.enabled = True
        resolved.sensor.max_range = far.max_range
        resolved.gauge.range_max = far.max_range
        resolved.track.floor_verify_max_range = far.max_range
        resolved.cluster.far_min_height = far.far_min_height
        resolved.cluster.far_max_length = far.far_max_length
    return resolved, range_model


def detect_range_model(field_names, ring=None):
    """The range-density model the cloud's own point layout identifies, or ``None`` (22.10, 1.3).

    Only the reported range's density prior is chosen here; axes, calibration and the detector's
    profile stay explicit (see the module note: a topic or frame name proves nothing). Falcon Prime
    declares ``scan_id``, ``scan_idx`` and ``elongation`` and no ``ring``; Pandar128 declares ``ring``
    with channels 0-127, at least 64 of them present in the frame. Anything else (a cloud without
    ``ring``, a constant ``ring``, more than 128 channels) is ``None``: no model is inferred.
    """
    names = set(field_names)
    if FALCON_FIELDS <= names and "ring" not in names:
        return "falcon_prime"
    if "ring" in names and ring is not None and np.size(ring):
        counts = np.bincount(np.asarray(ring, dtype=np.int64))
        if counts.size <= 128 and np.count_nonzero(counts) >= 64:
            return "pandar128"
    return None
