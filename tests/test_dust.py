import numpy as np
import pytest

from resense.dust import DustSpec, PRESETS, augment_dust, ray_lengths_in_box
from resense.frame import Frame


def example_frame():
    xyz = np.array([[10, 0, 0], [100, 0, 0], [-100, 0, 0], [100, 100, 0]], np.float32)
    return Frame(xyz, np.array([4, 40, 80, 120], np.float32),
                 np.array([3, 7, 3, 7], np.uint16), 2.5, "lidar", {"n_raw": 7, "n_near": 3})


def test_optical_depth_is_actual_segment_box_intersection():
    p = np.array([[10, 0, 0], [100, 0, 0], [-100, 0, 0], [100, 100, 0], [0, 0, 0]])
    np.testing.assert_allclose(ray_lengths_in_box(p, np.array([2.5, -3, -1]), np.array([60, 3, 1])),
                               [7.5, 57.5, 0, np.sqrt(2) * 0.5, 0])
    assert ray_lengths_in_box(np.array([[10, 0, 0]]), np.array([2, 1, -1]), np.array([5, 3, 1]))[0] == 0


def test_clean_identity_and_truth_separation():
    frame = example_frame()
    got, audit, indices = augment_dust(frame, PRESETS["clean"], rail_z=-1)
    np.testing.assert_array_equal(got.xyz, frame.xyz)
    np.testing.assert_array_equal(got.intensity, frame.intensity)
    np.testing.assert_array_equal(got.ring, frame.ring)
    np.testing.assert_array_equal(indices, np.arange(frame.n))
    assert got.meta == frame.meta
    assert audit["added_returns"] == audit["removed_returns"] == 0
    assert "dust" not in got.meta


def test_seeded_reproducible_and_original_labels_stay_addressable():
    source = example_frame()
    before = source.xyz.copy()
    a, info, idx = augment_dust(source, PRESETS["high"], rail_z=-1, seed=8, frame_index=9)
    b, info2, idx2 = augment_dust(source, PRESETS["high"], rail_z=-1, seed=8, frame_index=9)
    np.testing.assert_array_equal(a.xyz, b.xyz)
    np.testing.assert_array_equal(idx, idx2)
    assert info == info2
    np.testing.assert_array_equal(a.xyz[idx >= 0], source.xyz[idx[idx >= 0]])
    np.testing.assert_array_equal(source.xyz, before)
    assert set(np.unique(a.ring)).issubset(set(source.ring))
    assert (a.intensity[idx < 0] <= 5).all()
    assert a.meta["n_raw"] == 7 + info["added_returns"] - info["removed_returns"]
    assert a.meta["n_near"] == 3
    assert a.stamp == source.stamp and a.frame_id == source.frame_id


def test_extinction_preserves_returns_whose_rays_do_not_intersect_cloud():
    f = example_frame()
    _, _, idx = augment_dust(f, DustSpec(extinction=100), rail_z=-1)
    assert 2 in idx and 0 not in idx and 1 not in idx


def test_attenuation_is_monotonic_and_independent_of_generated_count():
    f = example_frame()
    _, _, low = augment_dust(f, DustSpec(extinction=.01), rail_z=-1, seed=1)
    _, _, high = augment_dust(f, DustSpec(extinction=1, density=1), rail_z=-1, seed=1)
    assert set(high[high >= 0]).issubset(set(low))
    _, _, same = augment_dust(f, DustSpec(extinction=.01, density=1), rail_z=-1, seed=1)
    np.testing.assert_array_equal(low, same[same >= 0])


def test_ringless_remains_ringless():
    f = example_frame()
    f.ring = None
    got, _, _ = augment_dust(f, PRESETS["low"], rail_z=-1)
    assert got.ring is None


@pytest.mark.parametrize("kwargs", [{"density": -1}, {"extinction": float("nan")},
                                    {"x_bounds": (2, 1)}, {"density": 1e9},
                                    {"height_bounds": (0, float("inf"))}])
def test_invalid_stress_configuration_rejected(kwargs):
    with pytest.raises(ValueError):
        DustSpec(**kwargs)
