"""Coordinate and source-integrity checks for the offline dust experiment."""
from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from resense.calibration import MountCalibrator, rot_x, rot_y, rot_z
from resense.config import DetectorConfig
from resense.dust import PRESETS, augment_dust
from resense.frame import Frame
from scripts.dust_reference import augment_in_reference, process_clean_reference


def source():
    rng = np.random.default_rng(16)
    return Frame(rng.uniform([3, -4, -2], [90, 4, 3], (300, 3)).astype(np.float32),
                 rng.uniform(0, 100, 300).astype(np.float32),
                 rng.integers(0, 8, 300, dtype=np.uint16), 10.1, "source", {"n_raw": 310, "n_near": 10})


def reference(frame, rotation):
    cfg = DetectorConfig()
    calibrator = MountCalibrator(cfg.calibration, cfg.track)
    calibrator.state.R = rotation
    detector = SimpleNamespace(calib=calibrator)
    def process(frame):
        calibrator.apply(frame.xyz)
        return SimpleNamespace(track=SimpleNamespace(rail_z=lambda x: np.full(len(x), -1.5)))
    detector.process = process
    return process_clean_reference(detector, frame)[1]


@pytest.mark.parametrize("rotation", [np.eye(3), rot_x(.11) @ rot_y(-.09),
                                      rot_y(.09) @ rot_x(-.11) @ rot_z(np.pi / 2)])
def test_cloud_uses_clean_model_axes_and_retains_source_bytes(rotation):
    frame = source()
    frame.xyz = frame.xyz @ rotation.astype(np.float32)
    original = deepcopy(frame)
    ref = reference(frame, rotation)
    result, audit, indices = augment_in_reference(frame, PRESETS["medium"], ref, seed=13, frame_index=7)
    again, audit2, indices2 = augment_in_reference(frame, PRESETS["medium"], ref, seed=13, frame_index=7)
    np.testing.assert_array_equal(result.xyz, again.xyz)
    np.testing.assert_array_equal(indices, indices2)
    assert audit == audit2
    keep, generated = indices >= 0, indices < 0
    assert keep.any() and generated.any() and (~np.isin(np.arange(frame.n), indices)).any()
    for name in ("xyz", "intensity", "ring"):
        assert getattr(result, name)[keep].tobytes() == getattr(frame, name)[indices[keep]].tobytes()
        assert getattr(frame, name).tobytes() == getattr(original, name).tobytes()
    aligned = result.xyz[generated] @ np.asarray(ref["input_to_model_rotation"], np.float32).T
    assert np.all(aligned >= np.array([2.5, -3., -1.4]) - 2e-5)
    assert np.all(aligned <= np.array([60., 3., 2.]) + 2e-5)
    assert result.meta == {"n_raw": 310 + audit["added_returns"] - audit["removed_returns"], "n_near": 10}
    assert result.stamp == frame.stamp and result.frame_id == frame.frame_id
    assert frame.meta == original.meta


def test_identity_reference_matches_original_generator_exactly():
    frame = source()
    ref = reference(frame, np.eye(3))
    old, old_audit, old_indices = augment_dust(frame, PRESETS["high"], rail_z=-1.5, seed=8)
    got, audit, indices = augment_in_reference(frame, PRESETS["high"], ref, seed=8)
    for name in ("xyz", "intensity", "ring"):
        np.testing.assert_array_equal(getattr(got, name), getattr(old, name))
    np.testing.assert_array_equal(indices, old_indices)
    assert {k: v for k, v in audit.items() if k != "placement_reference"} == old_audit


@pytest.mark.parametrize("kind", ["rotation", "height", "source", "intensity", "metadata"])
def test_reference_rejects_changed_geometry_or_input(kind):
    frame = source()
    ref = reference(frame, rot_y(.07))
    if kind == "rotation":
        ref["input_to_model_rotation"][0][0] += .1
    elif kind == "height":
        ref["rail_z_at20"] += 1
    elif kind == "source":
        frame.xyz[0, 0] += 1
    elif kind == "intensity":
        frame.intensity[0] += 1
    else:
        frame.meta["n_raw"] += 1
    with pytest.raises(ValueError):
        augment_in_reference(frame, PRESETS["low"], ref)


def test_clean_and_ringless_sources_are_supported():
    frame = source()
    frame.ring = None
    ref = reference(frame, rot_y(.07) @ rot_x(.13))
    got, audit, indices = augment_in_reference(frame, PRESETS["clean"], ref)
    assert got.ring is None and audit["added_returns"] == audit["removed_returns"] == 0
    assert got.xyz.tobytes() == frame.xyz.tobytes()
    np.testing.assert_array_equal(indices, np.arange(frame.n))
