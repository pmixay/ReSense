"""Raw annotation geometry must preserve uncertainty and the radial range contract."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

path = Path(__file__).resolve().parents[1] / "scripts" / "annotate_synthetic_tracks.py"
spec = importlib.util.spec_from_file_location("team_annotation_builder", path)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_materialize_keeps_radially_valid_near_pass_and_unknown_gauge(tmp_path):
    # Native Pandar coordinates: the forward distance is 1.9m but radial distance >2.5m.
    native = np.array(
        [[1.7, -1.9, -0.8], [1.7, -1.9, -0.8], [1.7, -1.9, -0.7]], np.float32
    )
    np.savez(tmp_path / "f_00000.npz", xyz=native, inten=np.array([1.0, 1.0, 8.0]))
    (tmp_path / "meta.json").write_text(json.dumps([{"i": 0}, {"i": 1}]))
    reviewed = {
        "total_frames": 2,
        "bag": "test",
        "source_sha256": "fixture",
        "review_method": "fixture",
        "objects": {
            "edge": {
                "kind": "box",
                "gauge_relation": "boundary_uncertain",
                "gauge_basis": "unresolved rail boundary",
            }
        },
        "tracks": {
            "edge": {
                "0": {"lo": [1.89, 1.69, -0.81], "hi": [1.91, 1.71, -0.69], "n": 2}
            }
        },
    }
    labels = builder.materialize(tmp_path, reviewed)
    row = labels["00000"][0]
    assert row["distance"] == pytest.approx(1.9)
    assert row["lateral_sensor"] == pytest.approx(1.7)
    assert row["n_points"] == 2 and row["n_unique_points"] == 1
    assert row["in_gauge"] is None and row["gauge_relation"] == "boundary_uncertain"
    assert labels["00001"] == []
    assert labels["_meta"]["exhaustive_obstacles"] is False


def test_empty_reviewed_volume_is_rejected(tmp_path):
    np.savez(
        tmp_path / "f_00000.npz",
        xyz=np.array([[0.0, -10.0, 0.0]], np.float32),
        inten=np.array([5.0]),
    )
    (tmp_path / "meta.json").write_text(json.dumps([{"i": 0}]))
    reviewed = {
        "total_frames": 1,
        "bag": "test",
        "source_sha256": "fixture",
        "review_method": "fixture",
        "objects": {
            "x": {"kind": "box", "gauge_relation": "inside", "gauge_basis": "fixture"}
        },
        "tracks": {
            "x": {"0": {"lo": [9.0, -1.0, -1.0], "hi": [11.0, 1.0, 1.0], "n": 1}}
        },
    }
    with pytest.raises(ValueError, match="no supporting raw return"):
        builder.materialize(tmp_path, reviewed)
