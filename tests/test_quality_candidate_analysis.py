import copy
import hashlib
import json

import pytest

from scripts import analyze_quality_candidates as analysis


def row(i=0, stop=False):
    return {"frame": i, "frame_id": f"new_data_{i:04d}", "stamp": float(i),
            "obstacle": stop, "warning": False, "nearest_distance": 30.0 if stop else None,
            "detections": [{"id": 1, "distance": 30.0, "lateral": 0.0}] if stop else [],
            "warnings": [], "clear_distance": 30.0 if stop else 100.0,
            "timing_ms": {"total": 20.0},
            "health": {"level": "ok", "decision_level": "ok", "monitored_range": 150.0,
                       "latency_p95_ms": 20.0, "messages": []}}


def expected(rows):
    return [{"name": r["frame_id"] + ".npy", "stamp": r["stamp"]} for r in rows]


def test_episodes_reset_at_boundaries_and_events_are_not_episodes():
    first = [row(0, True), row(1, True), row(2), row(3, True)]
    first[0]["detections"].append({"id": 2, "distance": 40.0, "lateral": 0.0})
    result = analysis.event_stats({"new_data_0": first, "new_data_1": [row(0, True)]})
    assert result == {"frames": 5, "alarm_frames": 4, "stop_episodes": 3,
                      "alarm_events": 3, "track_alarm_frames": 5}


def test_timing_only_is_parity_but_clear_range_ids_and_faults_are_not():
    before = row(0, True)
    after = copy.deepcopy(before)
    after["timing_ms"]["total"] = 300.0
    after["health"].update(level="warn", latency_p95_ms=300.0,
                           messages=["latency p95 300 ms over the 100 ms budget"])
    assert analysis.semantic(before) == analysis.semantic(after)
    for change in (lambda r: r.update(clear_distance=20.0),
                   lambda r: r["detections"][0].update(id=9),
                   lambda r: r["health"].update(monitored_range=90.0),
                   lambda r: r["health"].update(level="error"),
                   lambda r: r["health"].update(decision_level="warn"),
                   lambda r: r["health"].update(messages=["view blocked"])):
        changed = copy.deepcopy(before)
        change(changed)
        assert analysis.semantic(before) != analysis.semantic(changed)


@pytest.mark.parametrize("change", [
    lambda rows: rows.pop(),
    lambda rows: rows.reverse(),
    lambda rows: rows.__setitem__(1, copy.deepcopy(rows[0])),
    lambda rows: rows[0].update(stamp=0.01),
    lambda rows: rows[0].update(frame_id="wrong_0000"),
    lambda rows: rows[0].update(obstacle=True),
    lambda rows: rows[0].pop("warnings"),
    lambda rows: rows[0]["health"].update(monitored_range=float("nan")),
    lambda rows: rows[0]["timing_ms"].update(total=-1),
])
def test_corrupt_or_misaligned_rows_fail(change):
    rows = [row(0), row(1)]
    manifest = expected(rows)
    change(rows)
    with pytest.raises((ValueError, KeyError)):
        analysis.validate_piece("new_data_0", rows, manifest)


def write_run(path, pieces):
    path.mkdir()
    for name, rows in pieces.items():
        (path / (name + ".jsonl")).write_text("".join(json.dumps(r) + "\n" for r in rows))
    bags = {}
    for bag in analysis.COUNTS:
        subset = {k: v for k, v in pieces.items() if k == bag or k.startswith(bag + "_")}
        bags[bag] = analysis.event_stats(subset)
    (path / "summary.json").write_text(json.dumps({"bags": bags}))
    (path / "config.yaml").write_text("resense: {}\n")


@pytest.fixture
def paired_runs(tmp_path, monkeypatch):
    # Keep eight boundaries but shrink each piece to one frame for integration tests.
    monkeypatch.setattr(analysis, "COUNTS", {"new_data": 8, "cloud_with_fake_obj": 2})
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    audit, pieces = {}, {}
    for bag, count in analysis.COUNTS.items():
        rows = [dict(row(i), frame_id=f"{bag}_{i:04d}") for i in range(count)]
        raw = json.dumps(expected(rows)).encode()
        (audit_dir / f"{bag}_cache_manifest.json").write_bytes(raw)
        audit[bag] = {"frames": count, "cache_manifest_sha256": hashlib.sha256(raw).hexdigest()}
        if bag == "new_data":
            for i, r in enumerate(rows):
                pieces[f"new_data_{i}"] = [dict(r, frame=0)]
        else:
            pieces[bag] = rows
    (audit_dir / "audit.json").write_text(json.dumps(audit))
    ref, cand = tmp_path / "ref", tmp_path / "cand"
    write_run(ref, pieces)
    write_run(cand, pieces)
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps({"00000": [{"label": "target", "in_gauge": True,
                                          "distance": 30.0, "lateral": 0.0}]}))
    return ref, cand, audit_dir, labels


def test_valid_report_reuses_object_and_overclaim_scores(paired_runs):
    report = analysis.analyze(*paired_runs)
    assert report["input_validation_passed"] and report["semantic_parity_passed"]
    assert report["full_acceptance_asserted"] is False
    target = report["candidate"]["set_O"]["objects"]["target"]
    assert target["alarm_frames"] == 0 and target["first_alarm_m"] is None
    assert target["missed_intervals"][0]["frames"] == 1
    assert report["candidate"]["set_O"]["overclaim"]["totals"]["target_by_decision"] == {"GO": 1}


@pytest.mark.parametrize("corruption", ["missing", "extra", "summary", "audit", "compressed_duplicate"])
def test_incomplete_or_ambiguous_artifacts_fail(paired_runs, corruption):
    ref, cand, audit_dir, labels = paired_runs
    path = cand / "new_data_0.jsonl"
    if corruption == "missing":
        path.unlink()
    elif corruption == "extra":
        (cand / "new_data.jsonl").write_bytes(path.read_bytes())
    elif corruption == "summary":
        summary = json.loads((cand / "summary.json").read_text())
        summary["bags"]["new_data"]["alarm_events"] = 99
        (cand / "summary.json").write_text(json.dumps(summary))
    elif corruption == "audit":
        (audit_dir / "new_data_cache_manifest.json").write_text("[]")
    else:
        import gzip
        (cand / "new_data_0.jsonl.gz").write_bytes(gzip.compress(path.read_bytes()))
    with pytest.raises(ValueError):
        analysis.analyze(ref, cand, audit_dir, labels)


def test_cli_parity_exit_and_report_agree(paired_runs, tmp_path):
    ref, cand, audit_dir, labels = paired_runs
    path = cand / "new_data_0.jsonl"
    changed = json.loads(path.read_text())
    changed["clear_distance"] = 10.0
    path.write_text(json.dumps(changed) + "\n")
    out = tmp_path / "report.json"
    args = ["--reference", str(ref), "--candidate", str(cand), "--audit-dir", str(audit_dir),
            "--labels", str(labels), "--out", str(out), "--require-parity"]
    assert analysis.main(args) == 1
    report = json.loads(out.read_text())
    assert not report["semantic_parity_passed"]
    assert report["semantic_difference_frames"]["new_data_0"] == ["new_data_0000"]
    assert not report["monitoring_cost_by_piece"]["new_data_0"]["passed"]
