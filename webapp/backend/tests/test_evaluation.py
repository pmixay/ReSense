"""Scoring runs against label files (no dataset needed: synthetic frame dicts)."""
from __future__ import annotations

import json
import re

import pytest

from resense.metrics import gt_objects
from resense_web import evaluation

CYRILLIC = re.compile("[а-яА-ЯёЁ]")
DOUBLE_T = "doubleT_obstacle"


def _frame(idx: int, stop: bool, dets=(), stamp=None) -> dict:
    dets = [dict(d, id=d.get("id", 1)) for d in dets]
    return {"frame": idx, "pos": idx, "obstacle": stop, "warning": False, "detections": dets, "warnings": [],
            "nearest_distance": min((d["distance"] for d in dets), default=None),
            "stamp": 0.1 * idx if stamp is None else stamp, "timing_ms": {"total": 40.0},
            "decision": "STOP" if stop else "GO"}


def _write(tmp_path, data: dict, name: str = "gt.json"):
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_find_builtin_labels():
    p = evaluation.find_builtin_labels(DOUBLE_T)
    assert p is not None and p.name == "doubleT_obstacle.json"
    assert evaluation.find_builtin_labels("cloud_with_fake_obj").name == "cloud_with_fake_obj.json"
    assert evaluation.find_builtin_labels("new_data").name == "new_data_objects.json"
    assert evaluation.find_builtin_labels("DoubleT_Obstacle") == p
    for name in ("roundT_doubleT", "demo_approach", "", "doubleT"):
        assert evaluation.find_builtin_labels(name) is None


def test_builtin_files_validate():
    for name in (DOUBLE_T, "cloud_with_fake_obj", "new_data"):
        with open(evaluation.find_builtin_labels(name), encoding="utf-8") as fh:
            evaluation.validate_labels(json.load(fh))


@pytest.mark.parametrize("data", [
    [],
    "labels",
    {},
    {"_meta": {"bag": "x"}},
    {"_meta": [1]},
    {"frame_1": []},
    {"00001": {"distance": 5}},
    {"00001": [5]},
    {"00001": [{"lateral": 0.1}]},
    {"00001": [{"distance": "far"}]},
    {"00001": [{"bbox": [[1, 2, 3]]}]},
    {"00001": [{"distance": 5, "size": [1, 2]}]},
    {"00001": [{"distance": 5, "in_gauge": "yes"}]},
    {"_meta": {"bag": "x"}, "events": {"a": 1}},
])
def test_validate_rejects(data):
    with pytest.raises(ValueError) as e:
        evaluation.validate_labels(data)
    assert CYRILLIC.search(str(e.value))


def test_validate_accepts():
    evaluation.validate_labels({"00000": []})
    evaluation.validate_labels({"_meta": {"bag": "b"}, "00042": [{"distance": 55.6, "lateral": -0.2,
                                                                  "size": [0.4, 0.5, 1.7], "in_gauge": True}]})
    evaluation.validate_labels({"7": [{"bbox": [[10, -1, -1], [11, 1, 1]]}]})
    evaluation.validate_labels({"_meta": {"bag": "ride"}, "events": []})


def test_evaluate_doublet_consistent_with_raw():
    labels = evaluation.find_builtin_labels(DOUBLE_T)
    gt = json.loads(labels.read_text(encoding="utf-8"))
    frames, n_in = [], 0
    for i in range(201):
        objs = gt_objects(gt[f"{i:05d}"])
        person = [g for g in objs if g.label == "person_crossing" and g.in_gauge]
        n_in += any(g.in_gauge for g in objs)
        stop = bool(person) and i % 5 != 0
        dets = [{"distance": person[0].distance, "lateral": person[0].lateral}] if stop else []
        frames.append(_frame(i, stop, dets))
    s = evaluation.evaluate(frames, labels)
    raw = s["raw"]
    json.dumps(s)
    assert s["labels_name"] == "doubleT_obstacle.json"
    assert s["frames_labelled"] == 201 == raw["frames"]
    assert s["frames_with_object_in_gauge"] == n_in == raw["frames"] - raw["empty_frames"]
    assert s["frames_detected"] == sum(f["obstacle"] for f in frames) == raw["alarm_frames"] - raw["fp_frames"]
    assert s["false_stop_frames"] == raw["fp_frames"] == 0 and s["false_stop_episodes"] == 0
    assert s["recall"] == pytest.approx(s["frames_detected"] / n_in)
    assert s["first_detection_distance"] == pytest.approx(max(raw["first_detection_distance"].values()), abs=0.01)
    assert raw["first_detection_distance"]["person_crossing"] > 54
    # the in-gauge flags of the chart agree with the evaluation's denominator
    flags = evaluation.labels_in_gauge(list(range(201)), labels)
    assert sum(flags) == n_in


def test_false_stops_episodes_and_unlabelled_frames(tmp_path):
    rows = [{"distance": 30.0, "lateral": 0.0, "size": [0.5, 0.5, 1.7], "in_gauge": True, "label": "box"}]
    side = [{"distance": 20.0, "lateral": 2.0, "size": [0.5, 0.5, 1.0], "in_gauge": False, "label": "post"}]
    hidden = [dict(rows[0], n_points=0)]
    data = {"_meta": {"bag": "t"}}
    for i in range(10):
        data[f"{i:05d}"] = rows if 3 <= i <= 5 else (side if i in (0, 1) else [])
    data["00006"] = hidden                       # fully occluded: not a frame with an object
    del data["00009"]                            # unlabelled: counts as empty
    p = _write(tmp_path, data)
    det = [{"distance": 30.2, "lateral": 0.1}]
    stops = {0: [], 1: [], 3: det, 4: det, 5: det, 6: det, 7: [], 9: []}
    frames = [_frame(i, i in stops, stops.get(i, [])) for i in range(10)]
    s = evaluation.evaluate(frames, p)
    assert s["frames_labelled"] == 9
    assert s["frames_with_object_in_gauge"] == 3 and s["frames_detected"] == 3 and s["recall"] == 1.0
    # false STOPs: 0-1 (a post beside the track), 6-7 (the object is hidden) and 9 (unlabelled)
    assert s["false_stop_frames"] == 5 == s["raw"]["fp_frames"]
    assert s["false_stop_episodes"] == 3
    assert s["first_detection_distance"] == 30.0
    assert s["raw"]["occluded_gt_skipped"] == 1
    assert evaluation.labels_in_gauge([0, 3, 6, 9, 42], p) == [False, True, False, False, False]


def test_obstacle_free_declaration(tmp_path):
    p = _write(tmp_path, {"_meta": {"bag": "ride"}, "events": [{"id": 3}]})
    frames = [_frame(10 + 2 * i, i in (4, 5, 8)) for i in range(12)]    # every 2nd bag frame
    s = evaluation.evaluate(frames, p)
    assert s["frames_labelled"] == 12 and s["frames_with_object_in_gauge"] == 0
    assert s["recall"] is None and s["first_detection_distance"] is None
    assert s["false_stop_frames"] == 3 and s["false_stop_episodes"] == 2
    assert s["raw"]["frame_stride"] == 2 and s["raw"]["stride_caveat"]
    assert evaluation.labels_in_gauge([10, 12], p) == [False, False]


def test_evaluate_without_detections_key(tmp_path):
    p = _write(tmp_path, {"00000": [], "00001": []})
    frames = [{"frame": 0, "obstacle": False}, {"frame": 1, "obstacle": True}]
    s = evaluation.evaluate(frames, p)
    assert s["false_stop_frames"] == 1 and s["frames_labelled"] == 2
