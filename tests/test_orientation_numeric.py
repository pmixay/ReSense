"""Proper signed-axis remapping must not perturb the canonical float32 cloud."""
import numpy as np
import pytest

from resense.calibration import MountCalibrator, orientation_candidates, rot_x, rot_y, rot_z
from resense.config import DetectorConfig


@pytest.mark.parametrize('rotation', orientation_candidates())
def test_new_directional_mode_preserves_canonical_float32_geometry(rotation):
    rng = np.random.default_rng(12)
    xyz = rng.uniform([3, -6, -3], [200, 6, 4], (4000, 3)).astype(np.float32)
    cfg = DetectorConfig()
    cal = MountCalibrator(cfg.calibration, cfg.track)
    cal._R_orient = rotation.T.copy()
    cal._canonical_axes = True
    roll, pitch, yaw = np.radians([3., -2.4, 1.])
    cal._set_tilt(roll, pitch, yaw)
    tilt = rot_z(yaw) @ rot_y(pitch) @ rot_x(roll)
    expected = xyz @ tilt.T.astype(np.float32)
    seen = xyz @ rotation.T.astype(np.float32)
    np.testing.assert_array_equal(cal.apply(seen), expected)
    np.testing.assert_allclose(cal.R @ rotation, tilt, atol=1e-15)
