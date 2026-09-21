"""Metrics on hand-made status JSON lines (no dataset, no Open3D)."""
import json

import pytest

from resense.cli import run_cli
from resense.metrics import Evaluation, GTObstacle, frame_stride, gt_key, gt_objects, load_gt

FROZEN_SUMMARY_KEYS = {"frames", "empty_frames", "recall", "recall_by_range", "per_bin_counts", "fp_frames",
                       "fp_frame_rate", "fp_detections", "first_detection_distance", "latency_ms_mean",
                       "latency_ms_p95"}


def det(id_, distance, lateral=0.0, zone="gauge"):
    return {"id": id_, "zone": zone, "distance": distance, "lateral": lateral, "center": [distance, lateral, 0.0],
            "size": [0.5, 0.5, 0.5], "n_points": 20, "confidence": 1.0, "age": 3, "height_min": 0.2, "intensity": 30.0}


def status(frame=None, stamp=None, dets=(), warning=False, total_ms=50.0, **extra):
    """One line as ``resense run --out`` writes it (FrameResult.to_dict() + frame)."""
    dets = list(dets)
    d = {"stamp": stamp, "obstacle": bool(dets), "warning": warning,
         "nearest_distance": min(x["distance"] for x in dets) if dets else None,
         "detections": dets, "warnings": [], "n_candidates": len(dets), "n_points": 1000, "n_corridor": 10,
         "track": {}, "timing_ms": {"total": total_ms}}
    if frame is not None:
        d["frame"] = frame
    d.update(extra)
    return d


def _empty_bag_every_5th():
    """10 frames of an empty bag, every 5th frame, 0.5 s apart: track 7 alarms in three
    consecutive frames, track 9 in one; two advisory-only frames."""
    lines = []
    for k in range(10):
        dets = [det(7, 30.0 - k)] if k in (2, 3, 4) else ([det(9, 80.0)] if k == 8 else [])
        lines.append(status(frame=5 * k, stamp=100.0 + 0.5 * k, dets=dets, warning=k in (0, 1), total_ms=40.0 + k))
    return lines


def test_fp_events_vs_fp_frames_and_rates():
    ev = Evaluation()
    for d in _empty_bag_every_5th():
        ev.add_frame(d, [], speed_mps=10.0)
    s = ev.summary()
    assert s["frames"] == 10 and s["empty_frames"] == 10
    assert s["fp_frames"] == 4 and s["alarm_frames"] == 4
    assert s["fp_events"] == 2 and s["alarm_events"] == 2          # ids 7 and 9, not 4 frames
    assert s["fp_detections"] == 4
    assert s["advisory_frames"] == 2 and s["advisory_frame_rate"] == pytest.approx(0.2)
    assert s["bag_time_s"] == pytest.approx(4.5)
    assert s["fp_events_per_hour"] == pytest.approx(2 / (4.5 / 3600))
    assert s["distance_km"] == pytest.approx(0.045)
    assert s["fp_events_per_km"] == pytest.approx(2 / 0.045)
    assert s["alarm_distance_min"] == pytest.approx(26.0) and s["alarm_distance_max"] == pytest.approx(80.0)
    assert s["latency_ms_mean"] == pytest.approx(44.5) and s["latency_ms_max"] == pytest.approx(49.0)
    assert s["frame_stride"] == 5
    assert "every 5th" in s["stride_caveat"] and "1.5 s" in s["stride_caveat"] and "0.3 s" in s["stride_caveat"]
    assert FROZEN_SUMMARY_KEYS <= set(s)


def test_no_speed_and_no_stride_information():
    ev = Evaluation()
    for k in range(3):
        ev.add_frame(status(stamp=None, dets=[det(1, 20.0)]), [])
    s = ev.summary()
    assert s["fp_events"] == 1 and s["fp_frames"] == 3
    assert s["bag_time_s"] == 0.0 and s["fp_events_per_hour"] is None
    assert s["distance_km"] is None and s["fp_events_per_km"] is None
    assert s["frame_stride"] is None and s["stride_caveat"] is None


def test_per_frame_ego_speed_integrates_distance():
    ev = Evaluation()
    ev.add_frame(status(frame=0, stamp=0.0, ego_speed_mps=10.0), [])
    ev.add_frame(status(frame=1, stamp=0.1, ego_speed_mps=20.0), [])   # 20 m/s over 0.1 s
    ev.add_frame(status(frame=2, stamp=0.2, ego_speed_mps=20.0), [])
    s = ev.summary()
    assert s["distance_km"] == pytest.approx(0.004)
    assert s["frame_stride"] == 1 and s["stride_caveat"] is None


def test_matched_track_is_not_a_false_alarm_event():
    gt = [GTObstacle(distance=50.0, lateral=0.0, size=(0.5, 0.5, 0.5), label="box_a", kind="box0.5")]
    ev = Evaluation()
    ev.add_frame(status(frame=0, stamp=0.0, dets=[det(3, 50.4), det(4, 120.0)]), gt)   # 3 matches, 4 does not
    ev.add_frame(status(frame=1, stamp=0.1, dets=[det(3, 50.2)]), gt)
    ev.add_frame(status(frame=2, stamp=0.2, dets=[det(3, 50.1)]), [])                  # id 3 unmatched once, on an empty frame
    s = ev.summary()
    assert s["recall"] == 1.0
    assert s["recall_by_range"] == {"50-100": 1.0}
    assert s["recall_by_class"] == {"box0.5": 1.0} and s["per_class_counts"] == {"box0.5": [2, 2]}
    assert s["first_detection_distance"] == {"box_a": 50.0}
    assert s["fp_detections"] == 2           # id 4 once, id 3 on the empty frame
    assert s["fp_events"] == 1 and s["alarm_events"] == 2   # only id 4 is an event: id 3 was matched earlier
    assert s["fp_frames"] == 1 and s["empty_frames"] == 1


def test_frame_stride_detection():
    assert frame_stride([0, 1, 2, 3]) == 1
    assert frame_stride([0, 10, 20, 30]) == 10
    assert frame_stride([0, 5, 10, 11, 15, 20]) == 5     # one irregular step does not change the mode
    assert frame_stride([3]) is None and frame_stride([]) is None
    assert gt_key(42) == "00042" and gt_key("7") == "00007"


def test_gt_row_from_bbox_and_meta(tmp_path):
    g = GTObstacle.from_dict({"bbox": [[54.8, -0.4, -1.3], [55.3, 0.2, 0.4]], "label": "p", "name": "person"})
    assert g.distance == pytest.approx(54.8) and g.lateral == pytest.approx(-0.1)
    assert g.size == pytest.approx((0.5, 0.6, 1.7)) and g.kind == "person"
    f = tmp_path / "gt.json"
    f.write_text(json.dumps({"_meta": {"bag": "x"}, "00042": [{"kind": "box", "size": [0.5, 0.5, 0.5], "distance": 40,
                                                                "lateral": 0.0, "n_points": 0},
                                                               {"kind": "person", "distance": 60, "lateral": 0.3}]}))
    gt = load_gt(str(f))
    assert list(gt) == ["00042"]
    objs = gt_objects(gt["00042"])
    assert [o.kind for o in objs] == ["person"]             # the occluded row (n_points == 0) is dropped
    assert len(gt_objects(gt["00042"], skip_occluded=False)) == 2


def test_summarize_cli(tmp_path, capsys):
    path = tmp_path / "results.jsonl"
    with open(path, "w") as fh:
        for d in _empty_bag_every_5th():
            fh.write(json.dumps(d) + "\n")
        fh.write("---\nnot json\n")            # a status capture has separators and noise
    out = run_cli(["summarize", str(path), "--speed-mps", "10", "--json"])
    printed = json.loads(capsys.readouterr().out)
    assert printed["fp_events"] == out["fp_events"] == 2
    assert printed["fp_events_per_km"] == pytest.approx(2 / 0.045)
    assert printed["unparsed_lines"] == 1
    run_cli(["summarize", str(path)])
    text = capsys.readouterr().out
    assert "alarm events (distinct confirmed ids): 2" in text and "CAVEAT" in text and "every 5th" in text


def test_summarize_cli_with_labels(tmp_path, capsys):
    path = tmp_path / "results.jsonl"
    gt = {"_meta": {"source": "test"},
          "00010": [{"kind": "box", "size": [0.5, 0.5, 0.5], "distance": 28.0, "lateral": 0.0, "label": "b"}],
          "00015": [], "00020": []}
    (tmp_path / "gt.json").write_text(json.dumps(gt))
    with open(path, "w") as fh:
        for d in _empty_bag_every_5th():
            fh.write(json.dumps(d) + "\n")
    out = run_cli(["summarize", str(path), "--gt", str(tmp_path / "gt.json"), "--json"])
    assert out["recall"] == 1.0 and out["frames"] == 10 and out["empty_frames"] == 9
    assert out["fp_events"] == 1                      # id 7 matched the box at frame 10, id 9 remains
    out = run_cli(["summarize", str(path), "--gt", str(tmp_path / "gt.json"), "--labelled-only", "--json"])
    assert out["frames"] == 3 and out["fp_frames"] == 2 and out["fp_events"] == 0   # frames 15 and 20 alarm with id 7
    capsys.readouterr()
