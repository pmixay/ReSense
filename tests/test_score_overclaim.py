"""Acceptance cannot pass on missing/truncated evidence or changed score definitions."""
import gzip
import json

import pytest

from scripts.score_overclaim import build_report, main, read_results, reconstructed_judge_score, score_rows
from scripts.score_clear_distance import overclaim


def frame(index=0, **kwargs):
    return {"frame": index, "obstacle": False, "warning": False, "warnings": [],
            "clear_distance": 100.0, "health": {"level": "ok", "monitored_range": 120.0}, **kwargs}


def label(name="box", **kwargs):
    return {"label": name, "in_gauge": True, "plausible": True, "n_points": 10,
            "n_in_envelope": 10, "distance": 40.0, **kwargs}


def test_explicit_score_retains_legacy_definition_and_does_not_hide_outside_diagnostic():
    rows = [frame(), frame(1, warning=True, warnings=[{"distance": 40., "reason": ""}])]
    gt = {"00000": [label(), label("outside", in_gauge=False), label("invisible", n_points=0)],
          "00001": [label("second"), label("implausible", plausible=False)]}
    report = score_rows(rows, gt)
    assert report["totals"] == overclaim(rows, gt)["totals"]
    assert report["totals"]["target_by_decision"] == {"GO": 1, "CAUTION": 1}
    assert report["all_measured_diagnostic"]["overclaims_by_decision"] == {"CAUTION": 1, "GO": 2}
    assert len(report["residual_target_object_frames"]) == 2


def test_tolerance_is_strict_and_does_not_mask_nonfinite_distance():
    assert score_rows([frame(clear_distance=40.5)], {"00000": [label()]})["totals"]["target"] == 0
    assert score_rows([frame(clear_distance=40.501)], {"00000": [label()]})["totals"]["target"] == 1
    with pytest.raises(ValueError):
        score_rows([frame()], {"00000": [label(distance=float("nan"))]})


def test_reconstructed_judge_score_counts_unique_scan_frames_not_each_object():
    rows = [frame(), frame(1, clear_distance=42.0)]
    gt = {"00000": [label("first"), label("second", distance=80.)], "00001": [label()]}
    result = reconstructed_judge_score(rows, gt)
    assert result["eligible_scan_frames"] == 2 and result["eligible_object_frames"] == 3
    assert result["overclaim_frames"] == 1 and result["overclaim_frames_by_decision"] == {"GO": 1}


def test_truncated_matching_result_and_label_file_cannot_claim_complete_set_o():
    report = build_report([frame()], {"00000": [label()]}, {}, apply_cap=True, sensor_model="pandar128")
    assert report["checks"]["complete_set_O"] == "fail"
    assert report["checks"]["go_target_overclaims_le_5"] == "not_measured"
    assert report["checks"]["complete_five_empty_recordings"] == "not_measured"
    assert report["numerical_screen"] == "fail"


def test_full_blank_labels_and_large_tolerance_cannot_remove_acceptance_targets():
    rows = [frame(i) for i in range(1510)]
    empty_labels = {f"{i:05d}": [] for i in range(1510)}
    report = build_report(rows, empty_labels, {}, tol=1e6)
    assert report["checks"]["canonical_set_O_labels"] == "fail"
    assert report["checks"]["complete_set_O"] == "fail"
    assert report["checks"]["original_tolerance_0_5m"] == "fail"
    assert report["numerical_screen"] == "fail"


def test_approved_retention_profile_is_explicit_and_requires_measured_sensor_cap():
    rows, gt = [frame()], {"00000": [label()]}
    original = build_report(rows, gt, {})
    approved = build_report(rows, gt, {}, acceptance_profile="conservative_2026_10_17")
    assert original["minimum_empty_median_retention"] == .9
    assert approved["minimum_empty_median_retention"] == .65
    assert approved["checks"]["qualified_pandar_cap_with_measured_threshold"] == "fail"
    assert approved["numerical_screen"] == "fail"  # approval does not waive missing evidence
    with pytest.raises(ValueError):
        build_report(rows, gt, {}, acceptance_profile="permissive")


def test_advisory_cap_removes_caution_overclaim_but_does_not_fake_go_improvement():
    rows = [frame(), frame(1, warning=True, warnings=[{"distance": 40., "reason": ""}])]
    report = build_report(rows, {"00000": [label()], "00001": [label()]}, {}, apply_cap=True)
    assert report["set_O"]["before"]["totals"]["target_by_decision"] == {"GO": 1, "CAUTION": 1}
    assert report["set_O"]["after"]["totals"]["target_by_decision"] == {"GO": 1}
    assert report["set_O"]["stats"]["decision_rows_unchanged"]


def test_judge_and_full_rows_normalize_identically_with_gzip(tmp_path):
    judge = {"i": 0, "obstacle": False, "warning": True, "clear": 100., "monitored": 120.,
             "level": "ok", "dlevel": "ok", "warns": [{"d": 40., "reason": ""}]}
    path = tmp_path / "judge.jsonl.gz"
    with gzip.open(path, "wt") as output:
        output.write(json.dumps(judge) + "\n")
    normalized = read_results(path)[0]
    assert normalized["frame"] == 0 and normalized["clear_distance"] == 100.
    assert normalized["health"]["monitored_range"] == 120.
    assert normalized["warnings"][0]["distance"] == 40.


@pytest.mark.parametrize("rows", [[frame(), frame()], [frame(1), frame(0)],
                                  [frame(clear_distance=float("nan"))], [frame(clear_distance=None)],
                                  [frame(warning="false")],
                                  [frame(health={"level": "bad", "monitored_range": 120.0})],
                                  [frame(health={"monitored_range": 120.0})], []])
def test_missing_invalid_or_duplicate_evidence_is_rejected(tmp_path, rows):
    path = tmp_path / "invalid.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(ValueError):
        read_results(path)


def test_cli_acceptance_cannot_raise_tolerance_to_hide_overclaims(tmp_path):
    with pytest.raises(SystemExit) as error:
        main([str(tmp_path / "unused.jsonl"), "--require-c2", "--tol", "1000000"])
    assert error.value.code == 2


def test_cli_never_overwrites_its_input_evidence(tmp_path):
    path = tmp_path / "results.jsonl"
    original = json.dumps(frame()) + "\n"
    path.write_text(original)
    with pytest.raises(SystemExit) as error:
        main([str(path), "--out", str(path)])
    assert error.value.code == 2 and path.read_text() == original
