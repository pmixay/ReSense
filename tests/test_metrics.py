"""Metrics on hand-made status JSON lines (no dataset, no Open3D)."""
import json
from pathlib import Path

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


def test_stride_caveat_applies_the_trackers_time_rule():
    # v0.6.3 defaults: confirm_hits 3, confirm_time_s 0.5 -> 5 frames at 10 Hz; the tracker is
    # given the measured interval, so at every 5th frame 3 hits (1.5 s) confirm, not 5 (2.5 s)
    ev = Evaluation(confirm_hits=5, frame_dt=0.1, min_hits=3, confirm_time_s=0.5)
    for d in _empty_bag_every_5th():
        ev.add_frame(d, [])
    c = ev.summary()["stride_caveat"]
    assert "the 3 consecutive hits" in c and "persist 1.5 s" in c and "instead of 0.5 s" in c
    ev = Evaluation(confirm_hits=5, frame_dt=0.1, min_hits=3, confirm_time_s=0.5)
    for k in range(4):                                      # every 2nd frame: 0.2 s apart
        ev.add_frame(status(frame=2 * k, stamp=0.2 * k), [])
    assert "the 3 consecutive hits" in ev.summary()["stride_caveat"]


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
    assert s["per_class_bin_counts"] == {"box0.5": {"50-100": [2, 2]}}
    assert s["first_detection_distance"] == {"box_a": 50.0}
    assert s["fp_detections"] == 2           # id 4 once, id 3 on the empty frame
    assert s["fp_events"] == 1 and s["alarm_events"] == 2   # only id 4 is an event: id 3 was matched earlier
    assert s["fp_frames"] == 1 and s["empty_frames"] == 1


def test_two_overlapping_objects_use_maximum_matching():
    """The shared detection must go to the object with no other possible match."""
    gts = [GTObstacle(distance=50.0, lateral=0.0, label="left", kind="person"),
           GTObstacle(distance=50.0, lateral=1.5, label="right", kind="person")]
    ev = Evaluation()
    ev.add_frame(status(frame=0, dets=[det(1, 50.0, 0.7), det(2, 50.0, 0.0)]), gts)
    s = ev.summary()
    assert s["recall"] == 1.0 and s["fp_detections"] == 0
    assert s["first_detection_distance"] == {"left": 50.0, "right": 50.0}


def test_track_ids_are_scoped_to_independent_sequences():
    ev = Evaluation()
    gt = [GTObstacle(distance=50.0, lateral=0.0, label="box", kind="box")]
    ev.add_frame(status(frame=0, dets=[det(1, 50.0)], seq=0), gt)
    ev.add_frame(status(frame=1, dets=[det(1, 30.0)], seq=1), [])
    s = ev.summary()
    assert s["alarm_events"] == 2 and s["fp_events"] == 1
    assert s["recall"] == 1.0


def test_independent_sequences_exclude_inter_sequence_time_and_distance():
    ev = Evaluation()
    for i, (stamp, seq) in enumerate(((0.0, 0), (0.1, 0), (10.0, 1), (10.1, 1))):
        ev.add_frame(status(frame=i, stamp=stamp, dets=[det(1, 30.0)], seq=seq),
                     [], speed_mps=10.0)
    s = ev.summary()
    assert s["alarm_events"] == s["fp_events"] == 2
    assert s["bag_time_s"] == pytest.approx(0.2)
    assert s["distance_km"] == pytest.approx(0.002)
    assert s["fp_events_per_hour"] == pytest.approx(2 * 3600 / 0.2)


def test_missing_timestamp_does_not_bridge_scoped_sequence():
    ev = Evaluation()
    ev.add_frame(status(stamp=0.0, seq=0), [])
    ev.add_frame(status(stamp=None, seq=1), [])
    ev.add_frame(status(stamp=10.0, seq=1), [])
    assert ev.summary()["bag_time_s"] == 0.0


def test_missing_timestamp_does_not_bridge_continuous_distance():
    ev = Evaluation()
    for stamp in (0.0, None, 10.0, 10.1):
        ev.add_frame(status(stamp=stamp), [], speed_mps=10.0)
    assert ev.summary()["distance_km"] == pytest.approx(0.001)


def test_unlabelled_positive_bag_does_not_claim_false_alarms(tmp_path, capsys):
    path = tmp_path / "unknown.jsonl"
    path.write_text(json.dumps(status(frame=0, stamp=0.0, dets=[det(1, 50.0)])) + "\n")
    s = run_cli(["summarize", str(path), "--unlabelled", "--json"])
    assert s["alarm_frames"] == 1 and s["alarm_events"] == 1
    assert s["gt_status"] == "unlabelled"
    assert all(s[k] is None for k in ("empty_frames", "fp_frames", "fp_events",
                                      "fp_events_per_hour", "fp_events_per_km", "fp_detections"))
    capsys.readouterr()
    run_cli(["summarize", str(path), "--unlabelled"])
    assert "ground truth is unlabelled" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="cannot be used with --gt"):
        run_cli(["summarize", str(path), "--unlabelled", "--gt", str(tmp_path / "gt.json")])


def test_distance_error_first_alarm_and_speed_sources():
    """Additive summary keys: errors of matched detections, the first alarm frame, the
    ego_speed_source counts and the mean number of merged frames."""
    from resense.metrics import gt_row_speed
    gt = [GTObstacle(distance=50.0, lateral=0.2, size=(0.5, 0.5, 1.7), label="p", kind="person")]
    ev = Evaluation()
    ev.add_frame(status(frame=3, stamp=0.0, ego_speed_source="none", n_accumulated=1), [])
    ev.add_frame(status(frame=4, stamp=0.1, dets=[det(1, 50.4, 0.0)], ego_speed_source="given", n_accumulated=2), gt)
    ev.add_frame(status(frame=5, stamp=0.2, dets=[det(1, 49.8, 0.5)], ego_speed_source="given", n_accumulated=3), gt)
    s = ev.summary()
    assert s["distance_error_mean_abs"] == pytest.approx(0.3) and s["distance_error_max_abs"] == pytest.approx(0.4)
    assert s["distance_error_bias"] == pytest.approx(0.1) and s["lateral_error_mean_abs"] == pytest.approx(0.25)
    assert s["first_alarm_frame"] == 4
    assert s["ego_speed_sources"] == {"given": 2, "none": 1} and s["n_accumulated_mean"] == pytest.approx(2.0)
    assert FROZEN_SUMMARY_KEYS <= set(s)
    # no match, no frame index, no ego keys (a v0.3 JSONL): the keys exist and are empty
    ev = Evaluation()
    ev.add_frame(status(dets=[det(2, 30.0)]), [])
    s = ev.summary()
    assert s["distance_error_mean_abs"] is None and s["first_alarm_frame"] == 0
    assert s["ego_speed_sources"] == {} and s["n_accumulated_mean"] is None
    # the speed a sequence row gives the detector: positive speed_mps only
    assert gt_row_speed([{"speed_mps": 15.0}]) == 15.0
    assert gt_row_speed([{"speed_mps": 0.0}]) is None and gt_row_speed([{"distance": 3.0}]) is None and gt_row_speed([]) is None


def test_summarize_compare_two_files(tmp_path, capsys):
    """`resense summarize --compare before.jsonl after.jsonl` prints the before/after table."""
    before = tmp_path / "before.jsonl"
    after = tmp_path / "after.jsonl"
    with open(before, "w") as fh:
        for d in _empty_bag_every_5th():
            fh.write(json.dumps(d) + "\n")
    with open(after, "w") as fh:
        for d in _empty_bag_every_5th()[:8]:           # the alarm of frame 40 (track 9) is gone
            d = dict(d, ego_speed_source="given", n_accumulated=5)
            fh.write(json.dumps(d) + "\n")
    outs = run_cli(["summarize", "--compare", str(before), str(after)])
    text = capsys.readouterr().out
    assert isinstance(outs, list) and [o["alarm_events"] for o in outs] == [2, 1]
    assert [o["file"] for o in outs] == [str(before), str(after)]
    assert "| metric | before.jsonl | after.jsonl | delta |" in text
    assert "| alarm frames | 4 | 3 | -1 |" in text and "| alarm events | 2 | 1 | -1 |" in text
    assert "| frames | 10 | 8 | -2 |" in text and "| first alarm frame | 10 | 10 | +0 |" in text
    assert "| alarm distance max (m) | 80.0 | 28.0 | -52.0 |" in text
    assert "| frames merged (mean) | n/a | 5.00 |  |" in text and "CAVEAT" in text
    outs = run_cli(["summarize", str(before), str(after), "--json"])
    assert json.loads(capsys.readouterr().out)[1]["alarm_frames"] == 3 and len(outs) == 2
    with pytest.raises(SystemExit):
        run_cli(["summarize"])
    # the same file name in two directories (results/v0.3/bag.jsonl vs results/v0.4/bag.jsonl) stays readable
    from resense.metrics import format_comparison
    a, b = dict(outs[0], file="v0.3/bag.jsonl"), dict(outs[1], file="v0.4/bag.jsonl")
    assert format_comparison([a, b]).splitlines()[0] == "| metric | v0.3/bag.jsonl | v0.4/bag.jsonl | delta |"
    assert "| metric | x.jsonl | y.jsonl | z.jsonl |" in format_comparison([dict(a, file="x.jsonl"), dict(b, file="y.jsonl"),
                                                                           dict(b, file="z.jsonl")])


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


def test_committed_real_labels_use_the_current_envelope():
    path = Path(__file__).resolve().parents[1] / "labels" / "doubleT_obstacle.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["_meta"]["gauge_half_width_m"] == 1.05
    crossing_frames = []
    for key, rows in raw.items():
        if key.startswith("_"):
            continue
        for row in rows:
            if "gauge_margin" in row:
                margin = 1.05 - (abs(row["lateral"]) - row["size"][1] / 2)
                assert row["gauge_margin"] == pytest.approx(margin, abs=0.04)
                assert row["in_gauge"] == (row["gauge_margin"] >= 0)
            if row.get("label") == "person_crossing" and row["in_gauge"]:
                crossing_frames.append(int(key))
    assert crossing_frames == list(range(8, 69))


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
