"""The N2 battery must change the declared input property without corrupting geometry."""

import numpy as np
import pytest

from resense.pointcloud import pointcloud2_to_arrays
from scripts.lidar_input_variants import falcon_proxy_indices, field_message

try:
    from resense_ros import fastcloud
except ModuleNotFoundError:
    from ros2_ws.src.resense_ros.resense_ros import fastcloud


@pytest.mark.parametrize(
    "coordinate_dtype,intensity_dtype,padded",
    [("f4", "f4", False), ("f4", "u1", True), ("f8", "f4", True), ("f8", "u1", False)],
)
@pytest.mark.parametrize("has_ring", [False, True])
def test_field_encodings_preserve_nonzero_points_and_missing_ring_contract(
    coordinate_dtype, intensity_dtype, padded, has_ring
):
    xyz = np.array([[10, 1, -1], [20, 2, -0.5], [30, -1, 2]], dtype=np.float32)
    intensity = np.array([0, 1, 255], dtype=np.float32)
    ring = np.array([2, 3, 4], dtype=np.uint16) if has_ring else None
    msg = field_message(
        xyz,
        intensity,
        ring,
        coordinate_dtype=coordinate_dtype,
        intensity_dtype=intensity_dtype,
        padded=padded,
    )
    decoded = fastcloud.decode(fastcloud.packed(msg), 2.5, 250)
    reference = pointcloud2_to_arrays(fastcloud.packed(msg), 2.5, 250)
    for a, b in zip(decoded, reference):
        assert np.array_equal(a, b)
    assert np.array_equal(decoded[0], xyz) and np.array_equal(decoded[1], intensity)
    assert fastcloud.has_field(msg, "ring") is has_ring
    assert decoded[3:] == (3, 0)


def test_falcon_proxy_deduplicates_nearest_ray_and_enforces_fov_without_invented_returns():
    xyz = np.array(
        [
            [10.0, 0, 0],
            [10.0, 0, 0],
            [20.0, 0, 0],
            [-10.0, 0, 0],
            [10.0, 30, 0],
            [10.0, 0, 10],
            [10.0, 1, 0],
            [0.5, 0, 0],
        ],
        dtype=np.float32,
    )
    kept = falcon_proxy_indices(xyz)
    assert kept.tolist() == [0, 6]
    assert np.array_equal(kept, falcon_proxy_indices(xyz))
