"""Independent ground truth and fail-closed controls of the novel-placement study."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from resense.frame import Frame


spec = importlib.util.spec_from_file_location(
    "novel_placement_eval", Path(__file__).resolve().parents[1] / "scripts/novel_placement_eval.py")
novel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(novel)


def test_transplant_preserves_scale_range_and_intensity_without_upsampling():
    bg = Frame(np.array([[10, 8, -2]], dtype=np.float32), np.array([12], dtype=np.float32), stamp=3.2)
    obj = np.array([[20, 3, 0, 1], [20.3, 3.3, 0.3, 2]], dtype=np.float32)
    original = obj.copy()
    result, visible = novel.transplant(bg, obj, lateral=-0.65)
    np.testing.assert_array_equal(obj, original)
    np.testing.assert_allclose(visible[:, [0, 2]], original[:, [0, 2]])
    np.testing.assert_allclose(np.ptp(visible, axis=0), np.ptp(original[:, :3], axis=0))
    assert (visible[:, 1].min() + visible[:, 1].max()) / 2 == pytest.approx(-0.65)
    np.testing.assert_array_equal(result.intensity[-2:], original[:, 3])
    assert result.stamp == 3.2 and len(visible) == len(obj)


def test_occlusion_removes_background_behind_target_and_target_behind_foreground():
    # Different angle cells: the first target ray is visible; the second is blocked.
    bg = Frame(np.array([[40, 0, 0], [10, 0.1, 0]], dtype=np.float32), np.ones(2))
    obj = np.array([[20, 0, 0, 1], [20, 0.2, 0, 1]], dtype=np.float32)
    result, visible = novel.transplant(bg, obj, lateral=0.1)
    np.testing.assert_allclose(visible, [[20, 0, 0]], atol=1e-7)
    np.testing.assert_allclose(result.xyz, [[10, 0.1, 0], [20, 0, 0]], atol=1e-7)


def test_matching_uses_physical_target_position_and_rejects_wrong_height():
    xyz = np.array([[40, 0.6, 1.5], [40.3, 0.9, 1.8]])
    det = {"distance": 40.1, "center": [40.1, 0.7, 1.6], "lateral": -100}
    assert novel.target_match([det], xyz)  # detector's rail coordinate cannot move the label
    assert not novel.target_match([{**det, "center": [40.1, 0.7, -1]}], xyz)
    assert not novel.target_match([{**det, "distance": 50}], xyz)
    assert not novel.target_match([det], np.empty((0, 3)))


def test_source_dropout_keeps_background_and_cannot_count_as_hit():
    bg = Frame(np.array([[20, 0, 1]], dtype=np.float32), np.ones(1))
    result, visible = novel.transplant(bg, np.empty((0, 4)), 0)
    assert result is bg and visible.shape == (0, 3)
    assert not novel.target_match([{"distance": 20, "center": [20, 0, 1]}], visible)


def test_changed_background_and_code_fail_before_detector_execution(tmp_path, monkeypatch):
    (tmp_path / "manifest.json").write_text("{}")
    (tmp_path / "points.npz").write_bytes(b"source")
    frame = tmp_path / "frame.npy"
    frame.write_bytes(b"frame")
    monkeypatch.setattr(novel, "code_hashes", lambda: {"detector": "frozen"})
    plan = {"code_sha256": {"detector": "frozen"}, "source": str(tmp_path),
            "source_manifest_sha256": novel.sha(tmp_path / "manifest.json"),
            "source_points_sha256": novel.sha(tmp_path / "points.npz"),
            "inputs": {str(frame): {"sha256": novel.sha(frame)}}}
    novel.validate_plan(plan)
    frame.write_bytes(b"changed")
    with pytest.raises(ValueError, match="background changed"):
        novel.validate_plan(plan)
    plan["code_sha256"] = {"detector": "new"}
    with pytest.raises(ValueError, match="changed after preregistration"):
        novel.validate_plan(plan)


def test_plan_refuses_missing_data_and_nondefault_sensor_coordinates(tmp_path):
    novel.write_json(tmp_path / "manifest.json", {"objects": {
        label: {"frames": [0, 1, 2]} for label in novel.OBJECTS}})
    with pytest.raises(ValueError, match="incomplete background"):
        novel.make_plan(tmp_path, tmp_path, tmp_path / "plan.json")
    config = tmp_path / "config.yaml"
    config.write_text("sensor:\n  pitch_deg: 3\n")
    with pytest.raises(ValueError, match="fixed sensor-axis"):
        novel.make_plan(tmp_path, tmp_path, tmp_path / "plan.json", config)
    assert not (tmp_path / "plan.json").exists()
