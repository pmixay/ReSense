"""Explicit sensor profiles cannot leak calibration or a density model across bags."""

import numpy as np
import pytest

from resense.config import DetectorConfig
from resense.frame import axis_matrix

try:
    from resense_ros.sensor_profiles import apply_sensor_profile
except ModuleNotFoundError:
    from ros2_ws.src.resense_ros.resense_ros.sensor_profiles import apply_sensor_profile


def test_manual_keeps_configuration_and_does_not_invent_a_density_profile():
    cfg = DetectorConfig()
    cfg.sensor.forward, cfg.sensor.left, cfg.sensor.up = "+z", "-y", "+x"
    cfg.calibration.enabled = False
    cfg.calibration.keep_up_axis = False
    result, model = apply_sensor_profile(cfg, "manual")
    assert result == cfg and result is not cfg and result.sensor is not cfg.sensor
    assert model is None
    result.sensor.max_range = 99.0
    assert cfg.sensor.max_range != 99.0


@pytest.mark.parametrize(
    "profile,raw,model",
    [
        ("pandar128", [2.0, -10.0, 3.0], "pandar128"),
        ("falcon_ros", [10.0, 2.0, 3.0], "falcon_prime"),
        ("falcon_native", [3.0, -2.0, 10.0], "falcon_prime"),
    ],
)
def test_profiles_map_the_same_physical_point_and_keep_the_sensor_prior_explicit(
    profile, raw, model
):
    cfg = DetectorConfig()
    cfg.calibration.enabled = False
    cfg.calibration.keep_up_axis = False
    resolved, actual_model = apply_sensor_profile(cfg, profile)
    assert np.allclose(axis_matrix(resolved.sensor) @ raw, [10.0, 2.0, 3.0])
    assert np.isclose(np.linalg.det(axis_matrix(resolved.sensor)), 1.0)
    assert actual_model == model
    assert resolved.calibration.enabled and resolved.calibration.keep_up_axis
    assert cfg.calibration.enabled is False and cfg.calibration.keep_up_axis is False


def test_bag_switch_overwrites_previous_axes_and_sensor_prior_without_mutating_old_config():
    pandar, first_model = apply_sensor_profile(DetectorConfig(), "pandar128")
    pandar.sensor.roll_deg, pandar.sensor.pitch_deg, pandar.sensor.yaw_deg = (
        90.0,
        -2.0,
        5.0,
    )
    falcon, second_model = apply_sensor_profile(pandar, "falcon_ros")
    assert first_model == "pandar128" and second_model == "falcon_prime"
    assert pandar.sensor.forward == "-y" and falcon.sensor.forward == "+x"
    assert pandar.sensor is not falcon.sensor
    assert (falcon.sensor.roll_deg, falcon.sensor.pitch_deg, falcon.sensor.yaw_deg) == (
        0.0,
        0.0,
        0.0,
    )
    assert pandar.sensor.roll_deg == 90.0


def test_unknown_or_misspelled_profile_does_not_fall_back_to_pandar():
    with pytest.raises(ValueError, match="unknown sensor profile"):
        apply_sensor_profile(DetectorConfig(), "falcon")
