"""History acceptance must preserve identities and reject gains hidden by aggregate totals."""
import gzip
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load("history_stress")
comparison = load("compare_history_stress")


def frames(stops):
    return [{"frame": k, "frame_id": f"frame_{k}", "stamp": 100 + k * 0.1,
             "obstacle": bool(detections), "detections": detections} for k, detections in enumerate(stops)]


def detection(ident=1, distance=30.0, lateral=0.0):
    return {"id": ident, "distance": distance, "lateral": lateral, "kind": "low"}


def test_same_totals_cannot_hide_a_new_stop_frame():
    result = comparison.compare_rows(frames([[detection()], []]), frames([[], [detection()]]))
    assert result["baseline_stop_frames"] == result["candidate_stop_frames"] == 1
    assert result["new_stop_frames"] == [1] and not result["passed"]


def test_same_frame_and_event_totals_cannot_hide_a_new_physical_event():
    result = comparison.compare_rows(frames([[detection()]]), frames([[detection(distance=40)]]))
    assert not result["new_stop_frames"]
    assert len(result["new_stop_events"]) == 1 and not result["passed"]


def test_track_id_changes_match_when_frame_and_position_agree():
    result = comparison.compare_rows(frames([[detection(1)]]), frames([[detection(20, 30.1, 0.1)]]))
    assert result["passed"] and result["matched_events"] == [{"baseline_id": 1, "candidate_id": 20}]
    assert len(result["detection_payload_changes"]) == 1
    assert result["detection_payload_changes"][0]["candidate"][0]["distance"] == 30.1


def test_one_baseline_event_cannot_hide_two_candidate_events():
    result = comparison.compare_rows(frames([[detection()], [detection()]]),
                                     frames([[detection(2)], [detection(3)]]))
    assert not result["new_stop_frames"] and len(result["new_stop_events"]) == 1
    assert not result["passed"]


def test_event_assignment_finds_a_full_matching_when_a_greedy_choice_would_fail():
    before = comparison.event_map(frames([[detection(1, 30), detection(2, 30.6)]]))
    after = comparison.event_map(frames([[detection(3, 30.3), detection(4, 29.6)]]))
    assert len(comparison.event_pairs(before, after)) == 2


@pytest.mark.parametrize("change", ["timestamp", "frame", "missing", "order"])
def test_different_input_sequences_fail_closed(change):
    before, after = frames([[], []]), frames([[], []])
    if change == "timestamp":
        after[0]["stamp"] += 0.01
    elif change == "frame":
        after[0]["frame"] = 2
    elif change == "missing":
        after.pop()
    else:
        after.reverse()
    with pytest.raises(ValueError, match="input identity"):
        comparison.compare_rows(before, after)


def report_inventory():
    return {"schema": "resense-history-stress-v2", "totals": {"histories": 33},
            "rows": [{"source": k[0], "bag": k[1], "history": k[2], "seed": k[3]}
                     for k in sorted(comparison.EXPECTED)]}


def test_all_33_histories_are_required_including_raw_histories():
    report = report_inventory()
    assert len(comparison.inventory(report)) == 33
    report["rows"] = [r for r in report["rows"] if r["source"] != "capture"]
    with pytest.raises(ValueError, match="expected all 33"):
        comparison.inventory(report)


def test_duplicate_histories_cannot_replace_missing_histories():
    report = report_inventory()
    report["rows"][-1] = report["rows"][0]
    with pytest.raises(ValueError, match="duplicated history"):
        comparison.inventory(report)


def test_missing_original_bag_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="original bag is required"):
        runner.preflight(tmp_path, runner.EMPTY, tmp_path / "missing")


def test_missing_raw_history_is_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "CAPTURES", tmp_path)
    with pytest.raises(ValueError, match="missing expected raw history"):
        runner.capture_nodes("failed_clear")


def test_missing_raw_frame_is_an_error():
    with pytest.raises(ValueError, match="did not replay every requested frame"):
        runner.verify_capture_frames("old_pass", [10, 10.1, 10.2], [10, 10.2])


def test_missing_cache_frame_named_by_timestamp_sidecar_is_an_error(tmp_path, monkeypatch):
    bag = tmp_path / "raw"
    bag.mkdir()
    (bag / "bag.db3").write_bytes(b"hash-only fixture")
    captures = tmp_path / "captures"
    captures.mkdir()
    monkeypatch.setattr(runner, "CAPTURES", captures)
    for name in runner.CAPTURE_NAMES:
        row = {"stamp": 10, "obstacle": False, "node": {"recording": 1}}
        (captures / (name + ".jsonl.gz")).write_bytes(gzip.compress((json.dumps(row) + "\n").encode()))
    directory = tmp_path / "cache" / "roundT_doubleT"
    directory.mkdir(parents=True)
    (directory / "roundT_doubleT_0000.npy").write_bytes(b"not loaded")
    (directory / "roundT_doubleT_stamps.json").write_text(json.dumps(
        {"bag": "roundT_doubleT", "stamps": {"0000": 10, "0001": 10.1}}))
    with pytest.raises(ValueError, match="missing_frames"):
        runner.preflight(tmp_path / "cache", ["roundT_doubleT"], bag)


def test_source_root_import_trap_is_detected(tmp_path):
    import resense.detector
    actual_root = Path(resense.detector.__file__).resolve().parents[1]
    assert runner.verify_import_root(actual_root).endswith("resense/detector.py")
    with pytest.raises(ValueError, match="wrong detector imported"):
        runner.verify_import_root(tmp_path)


def identity(config, files):
    return {"config": config, "source_files": files,
            "config_sha256": comparison.digest_json(config),
            "source_sha256": comparison.digest_json(files)}


@pytest.mark.parametrize("field", ["config", "source_files"])
def test_wrong_frozen_variant_cannot_pass_as_candidate(field):
    baseline = identity({"keep": 0.0}, {"detector.py": "a" * 64})
    candidate = identity({"keep": 0.3}, {"detector.py": "b" * 64})
    comparison.verify_identity(candidate, candidate, "candidate")
    wrong = dict(candidate)
    wrong[field] = baseline[field]
    hash_field = "config_sha256" if field == "config" else "source_sha256"
    wrong[hash_field] = baseline[hash_field]
    with pytest.raises(ValueError, match="expected frozen identity"):
        comparison.verify_identity(wrong, candidate, "candidate")


@pytest.mark.parametrize("field", ["config", "source_files"])
def test_declared_hash_cannot_hide_changed_identity_contents(field):
    expected = identity({"keep": 0.3}, {"detector.py": "b" * 64})
    changed = {**expected, field: {"modified": True}}
    with pytest.raises(ValueError, match="report contents"):
        comparison.verify_identity(changed, expected, "candidate")


def test_gz_capture_hash_and_summary_are_validated(tmp_path):
    rows = frames([[detection()], []])
    row = runner.finish_history("cache", "roundT_doubleT", "every", 0, rows, tmp_path)
    report = {"capture_directory": "."}
    report_path = tmp_path / "report.json"
    assert comparison.load_capture(report_path, report, row) == rows
    row["stop_events"] = 2
    with pytest.raises(ValueError, match="event summary"):
        comparison.load_capture(report_path, report, row)
    row["stop_events"] = 1
    (tmp_path / row["capture"]["file"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        comparison.load_capture(report_path, report, row)
