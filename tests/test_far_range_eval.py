"""Checks for the set F placement protocol that do not need the organizer bags."""

import importlib.util
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest

from resense.config import DetectorConfig
from resense.frame import Frame
from resense.synthetic import ObstacleSpec, place_on_bed
from resense.track import TrackModel

# CI also runs from / inside the image; load the script by path, not the current directory.
_script = Path(__file__).resolve().parents[1] / "scripts" / "far_range_eval.py"
_spec = importlib.util.spec_from_file_location("resense_near_anchor_eval", _script)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
near_anchor_placements = _module.near_anchor_placements
run_sequence = _module.run_sequence
consecutive_files = _module.consecutive_files


def model(center=0.0, slope=0.0, curvature=0.0, rail_score=0.1):
    return TrackModel(floor_coef=np.array([0.0, 0.0, -0.35]), floor_range=(4.0, 60.0),
                      center=center, yaw=np.arctan(slope), curvature=curvature,
                      rail_offset=0.35, rail_score=rail_score)


def test_approach_does_not_jump_to_a_different_split_or_skip_a_frame():
    files = [f"new_data_{split}_{frame:04d}.npy" for split, frame in
             ((46, 49), (46, 50), (47, 0), (47, 1), (127, 0))]
    assert consecutive_files(files, 0, 220) == files[:4]
    assert consecutive_files(files, 2, 220) == files[2:4]
    assert consecutive_files([files[0], files[2]], 0, 10) == files[:1]
    with pytest.raises(ValueError, match="expected split frame"):
        consecutive_files(["other_0000.npy"], 0, 10)


def test_near_anchor_recovers_a_known_frame_transform():
    # f_previous(x+2) - f_next(x) = 0.15 + 0.01*x in the shared near segment.
    previous = model(center=-0.07, slope=0.11)
    following = model(slope=0.1)
    positions, anchor = near_anchor_placements([previous, following], [32.0, 30.0], 0.5)
    assert anchor == 1
    assert positions[1] == pytest.approx([30.0, 3.5])
    rot = np.array([[np.cos(0.01), -np.sin(0.01)], [np.sin(0.01), np.cos(0.01)]])
    assert positions[0] == pytest.approx(rot @ positions[1] + [2.0, 0.15], abs=1e-6)


def test_far_placement_is_not_taken_from_the_far_axis():
    distances = [108.0 - 2.0 * i for i in range(40)]
    models = [model(curvature=0.0005)] + [model() for _ in distances[1:]]
    positions, anchor = near_anchor_placements(models, distances, 0.5)
    assert anchor == len(distances) - 1
    assert positions[anchor][1] == pytest.approx(0.5)
    assert abs(positions[0][1] - (models[0].center_y(distances[0]) + 0.5)) > 1.0


def test_near_anchor_rejects_missing_reference_and_recording_hole():
    with pytest.raises(ValueError, match="no rail-supported"):
        near_anchor_placements([model(), model(rail_score=0.01)], [32.0, 30.0], 0.0, min_rail_score=0.05)
    with pytest.raises(ValueError, match="no reliable near-track overlap"):
        near_anchor_placements([model(), model()], [100.0, 30.0], 0.0)


def test_injector_uses_local_bed_then_vault_drift():
    track = model()
    bed = np.array([[20.0, 0.0, -0.30]] * 20)
    near_crown = np.array([[x, 0.0, 4.0] for x in (30.0, 40.0, 50.0) for _ in range(20)])
    far_crown = np.array([[x, 0.0, 4.0 + 0.01 * (x - 40.0)]
                          for x in range(70, 190, 10) for _ in range(10)])
    xyz = np.vstack([bed, near_crown, far_crown]).astype(np.float32)
    frame = Frame(xyz=xyz, intensity=np.ones(len(xyz), np.float32))
    specs = [ObstacleSpec(distance=19.75, size=(0.5, 0.5, 0.5)),
             ObstacleSpec(distance=149.75, size=(0.5, 0.5, 0.5))]
    near, far = place_on_bed(frame, track, specs)
    assert near.base_z == pytest.approx(-0.30)
    assert far.base_z > float(track.rail_z(150.0)) + 0.3


def test_anchored_set_f_path_runs_on_cached_synthetic_frames(synth_npy_dir):
    files = sorted(str(path) for path in synth_npy_dir.glob("*.npy"))
    stamps = {path.rsplit("/", 1)[-1][:-4]: i * 0.1 for i, path in enumerate(files)}
    job = (files, stamps, [1.0, 1.0], "person", 30.0, 0.2, 59.8, 4,
           asdict(DetectorConfig()), None, False, "bed", "anchored", None, 0.0, 0.0)
    result = run_sequence(job)
    assert "skipped" not in result
    assert result["placement_mode"] == "anchored" and len(result["rows"]) == 2
    assert result["anchor_frame"] is not None
    assert all("axis_error_m" in row and "path_d" in row for row in result["rows"])


def test_anchored_set_f_rejects_missing_or_invalid_timestamps(synth_npy_dir):
    files = sorted(str(path) for path in synth_npy_dir.glob("*.npy"))
    stem0 = files[0].rsplit("/", 1)[-1][:-4]
    stem1 = files[1].rsplit("/", 1)[-1][:-4]
    job = (files, {}, [1.0, 1.0], "person", 30.0, 0.2, 59.8, 4,
           asdict(DetectorConfig()), None, False, "bed", "anchored", None, 0.0, 0.0)
    assert "missing timestamp" in run_sequence(job)["skipped"]
    job = (files, {stem0: 0.1, stem1: 20.1}, *job[2:])
    assert "invalid timestamp step" in run_sequence(job)["skipped"]
