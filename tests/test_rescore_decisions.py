"""Rescoring must expose alert losses, not hide them behind reduced CAUTION totals."""
import json

import pytest

from scripts.rescore_decisions import DecisionPolicy, main, rescore_file, summarize


def write_rows(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return path


def row(frame, reason="", distance=40, **kw):
    return {"frame": frame, "obstacle": False, "warning": True, "health": {"level": "ok"},
            "warnings": [{"reason": reason, "distance": distance, "size": [1, 1, 1]}], **kw}


def test_in_gauge_losses_count_object_frames_and_unique_frames_without_cancellation(tmp_path):
    path = write_rows(tmp_path / "objects.jsonl", [row(0, "column"), row(1), row(2, obstacle=True)])
    label = {"label": "inside", "in_gauge": True, "n_points": 10, "n_in_envelope": 1}
    gt = {"00000": [label, {**label, "label": "outside", "in_gauge": False}],
          "00001": [label, {**label, "label": "edge", "n_in_envelope": 0}],
          "00002": [label, {**label, "label": "invisible", "n_points": 0},
                    {**label, "label": "implausible", "plausible": False}]}
    result = rescore_file(path, "objects", DecisionPolicy("v2"), gt)
    assert result["v1"]["CAUTION"] == 2 and result["selected"]["CAUTION"] == 1
    assert result["selected"]["STOP"] == 1
    assert result["in_gauge_object_frames"]["frames"] == 4
    assert result["in_gauge_frames"]["frames"] == 3
    assert result["measured_envelope_object_frames"]["frames"] == 3
    assert result["in_gauge_object_frames"]["lost_v1_alerts"] == 1
    assert result["in_gauge_frames"]["v1_alert_retention"] == pytest.approx(2 / 3)
    assert result["loss_examples"][0]["frame"] == 0
    assert set(result["per_label"]) == {"inside", "edge"}
    summary = summarize([result], DecisionPolicy("v2"))
    assert summary["checks"]["in_gauge_object_alert_retention"] == "fail"
    assert summary["checks"]["empty_caution_le_25pct"] == "not_measured"


def test_empty_threshold_range_visibility_and_non_frame_snapshots(tmp_path):
    rows = [row(0, "column"), row(1, distance=100), row(2, "doubt"), row(3, warning=False),
            row(4, snapshot_kind="watchdog")]
    empty = rescore_file(write_rows(tmp_path / "empty.jsonl", rows), "empty", DecisionPolicy("v2"), {})
    assert empty["frames"] == 4 and empty["skipped_snapshots"] == 1
    assert empty["selected_caution_fraction"] == .25
    assert summarize([empty], DecisionPolicy("v2"))["checks"]["empty_caution_le_25pct"] == "pass"
    visible = rescore_file(write_rows(tmp_path / "range.jsonl", [row(0, visible=False, distance=100),
                          row(1, visible=True), row(2, visible=True, distance=100)]),
                          "range", DecisionPolicy("v2"), {})
    assert visible["visible_frames"]["frames"] == 2
    assert visible["visible_frames"]["lost_v1_alerts"] == 1
    assert summarize([visible], DecisionPolicy("v2"))["checks"]["range_visible_alert_retention"] == "fail"


def test_judge_runner_aliases_preserve_health_and_advisory_distance(tmp_path):
    rows = [{"i": 0, "obstacle": False, "warning": True, "level": "warn", "dlevel": "ok",
             "warns": [{"reason": "", "d": 90, "size": [1, 1, 1]}]},
            {"i": 1, "obstacle": False, "warning": False, "level": "warn", "dlevel": "warn", "warns": []},
            {"i": 2, "obstacle": False, "warning": True, "level": "error", "dlevel": "ok", "warns": []}]
    path = write_rows(tmp_path / "judge.jsonl", rows)
    gt = {"00000": [{"label": "inside", "in_gauge": True}]}
    result = rescore_file(path, "objects", DecisionPolicy("v2"), gt)
    assert result["v1"] == {"GO": 0, "CAUTION": 2, "STOP": 0, "FAULT": 1}
    assert result["selected"] == {"GO": 1, "CAUTION": 1, "STOP": 0, "FAULT": 1}
    assert result["in_gauge_frames"]["lost_v1_alerts"] == 1


def test_cli_reports_failures_and_missing_evidence_without_claiming_acceptance(tmp_path, capsys):
    path = write_rows(tmp_path / "roundT_doubleT.jsonl", [row(0, "doubt")])
    output = tmp_path / "score.json"
    assert main([str(path), "--policy", "v2", "--out", str(output), "--require-targets"]) == 1
    result = json.loads(output.read_text())
    assert result["checks"]["empty_caution_le_25pct"] == "fail"
    assert result["checks"]["in_gauge_object_alert_retention"] == "not_measured"
    assert result["acceptance"].startswith("not_accepted")
    assert len(result["sources"][0]["sha256"]) == 64
    capsys.readouterr()
    with pytest.raises(SystemExit):
        main([str(path), str(path)])


@pytest.mark.parametrize("role,rows", [("empty", [{"decision": "CAUTION"}]),
                                       ("objects", [{"obstacle": False, "warning": False}]),
                                       ("range", [row(0)])])
def test_inadequate_saved_outputs_are_rejected_not_inferred(role, rows, tmp_path):
    path = write_rows(tmp_path / "incomplete.jsonl", rows)
    with pytest.raises(ValueError, match=r"incomplete.jsonl:1:"):
        rescore_file(path, role, DecisionPolicy("v2"), {})
