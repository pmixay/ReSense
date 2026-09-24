"""Labels and per-object score of the organizers' synthetic-obstacle recording (dataset-free)."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest


def _load(name):
    path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"resense_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


label = _load("label_fake_objects")
score = _load("score_fake_objects")


def _message(real, objects):
    """A PointCloud2 as the organizers wrote it: the organized scan (no-return points are
    zeros), then the object points."""
    pts = np.concatenate([real, objects]) if len(objects) else real
    out = np.zeros(len(pts), dtype=[("x", "f4"), ("y", "f4"), ("z", "f4"), ("intensity", "f4")])
    out["x"], out["y"], out["z"] = pts[:, 0], pts[:, 1], pts[:, 2]
    return out


def test_object_block_is_everything_after_the_last_zero():
    real = np.array([[1.0, -20.0, 0.0], [0.0, 0.0, 0.0], [2.0, -30.0, 1.0], [0.0, 0.0, 0.0]])
    obj = np.array([[0.1, -80.0, 0.5], [0.2, -80.0, 0.6]])
    assert np.allclose(label.split_objects(_message(real, obj)), obj)
    assert label.split_objects(_message(real, obj[:0])).shape == (0, 3)


def test_objects_of_one_frame_split_at_gaps():
    xyz = np.array([[98.0, 0, 0], [98.3, 0, 0], [199.0, 0, 0], [5.0, 0, 0]])
    groups = label.group_frame(xyz, gap=8.0)
    assert [sorted(xyz[g, 0].tolist()) for g in groups] == [[5.0], [98.0, 98.3], [199.0]]
    assert label.group_frame(np.zeros((0, 3)), 8.0) == []


def test_tracks_follow_approaching_objects_and_keep_them_apart():
    # two objects 100 m apart approaching at 1.8 m per frame, one seen only every other frame
    groups = {}
    for k in range(20):
        g = [(100.0 - 1.8 * k, None)]
        if k % 2 == 0:
            g.append((200.0 - 1.8 * k, None))
        groups[k] = g
    tracks = label.link_tracks(groups)
    assert len(tracks) == 2
    assert sorted(len(t) for t in tracks) == [10, 20]
    for t in tracks:
        x = [row[2] for row in t]
        assert all(b < a for a, b in zip(x, x[1:]))


def _row(lab, d, in_gauge=True, lateral=0.0, plausible=True, n_env=1):
    return {"label": lab, "distance": d, "lateral": lateral, "size": [0.3, 0.3, 0.3], "in_gauge": in_gauge,
            "n_points": 5, "n_in_envelope": n_env, "plausible": plausible}


def _det(id_, d, lateral=0.0):
    return {"id": id_, "distance": d, "lateral": lateral}


def test_score_counts_alarms_advisories_and_outside_false_alarms():
    gt, results = {}, []
    for k, d in enumerate([80.0, 70.0, 60.0, 50.0, 40.0]):
        gt[f"{k:05d}"] = [_row("inside", d), _row("outside", d + 100, in_gauge=False, lateral=1.3),
                          _row("far_rock", d + 150, plausible=False)]
        dets = [_det(1, d)] if k >= 2 else []            # the inside object: STOP from 60 m
        warns = [_det(2, d)] if k == 1 else []            # advisory once at 70 m
        if k == 4:
            dets.append(_det(3, d + 100, lateral=1.2))     # an alarm on the outside object
            dets.append(_det(4, 5.0))                       # and one on nothing
        results.append({"frame": k, "obstacle": bool(dets), "detections": dets, "warnings": warns})
    objs, bg = score.score(results, gt)
    assert set(objs) == {"inside", "outside"}            # implausible rows are not graded
    inside = objs["inside"]
    assert inside["alarm_frames"] == 3 and inside["advisory_only_frames"] == 1
    assert inside["first_alarm_m"] == 60.0 and inside["alarm_held_from_m"] == 60.0
    assert inside["first_advisory_or_alarm_m"] == 70.0 and inside["verdict"] == "detected"
    assert objs["outside"]["false_alarm_frames"] == 1 and objs["outside"]["verdict"] == "false alarm"
    assert bg == {"frames": 5, "alarm_frames": 3, "background_alarm_frames": 1, "background_alarm_ids": 1}


def test_held_from_needs_ninety_percent_of_the_closer_frames():
    assert score._held_from([(10.0, True), (20.0, True), (30.0, False), (40.0, True)]) == 20.0
    assert score._held_from([(10.0, False)]) is None
    assert score._held_from([]) is None


@pytest.mark.parametrize("d,key", [(0.0, "0-50"), (99.9, "50-100"), (250.0, "200-300"), (300.0, "300+")])
def test_range_bins(d, key):
    assert score._bin(d) == key
