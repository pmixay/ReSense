"""Persistence on stored raycasts plus independent checks of the evaluation metrics.

These tests need no Open3D or organizer recordings. They use the shipped defaults and
assert useful behavior without requiring the known two-frame dropout to stay broken.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from resense import Detector, DetectorConfig
from resense.frame import frame_from_compact

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("synthetic_sensitivity", ROOT / "scripts/synthetic_sensitivity.py")
evaluation = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evaluation)
PROTOCOL = json.loads(evaluation.PROTOCOL.read_text())


@pytest.fixture(scope="module")
def replay():
    cfg = DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml"))
    results = {}

    def run(name, gap=0):
        key = name, gap
        if key not in results:
            detector = Detector(cfg)
            results[key] = [(index, returns, detector.process(frame_from_compact(raw, cfg.sensor, stamp=index * 0.1)))
                            for index, raw, returns in evaluation.fixture_sequence(name, gap)]
        return results[key]
    return run


@pytest.mark.parametrize("name", ["clear", "transient"])
def test_clear_and_single_return_transient_do_not_confirm(replay, name):
    rows = replay(name)
    assert sum(returns > 0 for _, returns, _ in rows) == (1 if name == "transient" else 0)
    assert not any(result.obstacle for _, _, result in rows)


def test_visible_rail_object_has_sustained_matched_stop(replay):
    rows = replay("gap", 0)
    case = evaluation.sequence_cases(PROTOCOL, "development")[0]
    assert all(returns > 0 for _, returns, _ in rows)
    # Allow up to the first six frames for calibration/confirmation, then demand every frame.
    for _, _, result in rows[6:]:
        assert result.obstacle
        assert any(evaluation.target_matches(d, case, PROTOCOL["matching"]) for d in result.detections)
    assert len({d.id for _, _, r in rows[6:] for d in r.detections}) == 1


def test_saved_observation_can_recompute_the_physical_match(replay):
    index, returns, result = replay("gap", 0)[5]
    case = evaluation.sequence_cases(PROTOCOL, "development")[0]
    saved = evaluation.observation(result, case, returns, index, index * 0.1, PROTOCOL["matching"])
    saved = json.loads(json.dumps(saved))
    matches = [evaluation.target_matches(SimpleNamespace(**d), case, PROTOCOL["matching"])
               for d in saved["detections"]]
    assert saved["matched_stop"] == any(matches)
    assert saved["matched_ids"] == [d["id"] for d, matched in zip(saved["detections"], matches) if matched]
    assert saved["health"]["level"] in ("ok", "warn", "error")
    assert saved["decision"] == "STOP"


def test_confirmed_stop_survives_one_missing_target_return_frame(replay):
    rows = replay("gap", 1)
    assert rows[6][1] == 0
    assert all(result.obstacle for _, _, result in rows[5:])


@pytest.mark.parametrize("gap", [2, 3])
def test_longer_gaps_recover_without_spurious_target_changes(replay, gap):
    rows = replay("gap", gap)
    before = rows[5][2].detections[0]
    assert all(returns == 0 for _, returns, _ in rows[6:6 + gap])
    recovered = rows[6 + gap:]
    assert all(result.obstacle for _, _, result in recovered)
    assert all(any(d.id == before.id and abs(d.distance - 24.0) < 0.5 for d in result.detections)
               for _, _, result in recovered)


def test_removed_obstacle_releases_and_does_not_return_on_clear_scans(replay):
    rows = replay("removal")
    assert all(result.obstacle for _, _, result in rows[4:6])
    assert all(returns == 0 for _, returns, _ in rows[6:])
    # A bounded hold may cover short dropouts, but a removed object must release by 0.3 s.
    assert not any(result.obstacle for _, _, result in rows[9:])


def row(index, hit=False, visible=True, false=False):
    return {"frame": index, "matched_stop": hit, "visible": visible,
            "stop": hit or false, "unmatched_stop": false,
            "clear_overclaim": visible and not hit, "target_distance_m": 50.0}


def test_metrics_do_not_turn_one_hit_into_sustained_detection():
    rows = [row(i, hit=i == 7) for i in range(16)]
    metrics = evaluation.sequence_metrics(rows, PROTOCOL["metrics"])
    assert metrics["matched_stop_frames"] == 1
    assert metrics["visible_recall"] == pytest.approx(1 / 16)
    assert metrics["steady_visible_recall"] == pytest.approx(1 / 10)
    assert metrics["first_stop_frame"] == 7
    assert metrics["longest_visible_miss_after_stop"] == 8
    assert not metrics["sustained"]


def test_metrics_separate_invisible_gaps_from_visible_misses_and_false_episodes():
    rows = [row(i, hit=i in (2, 3, 6, 7, 8), visible=i != 4, false=i in (0, 1, 9)) for i in range(10)]
    metrics = evaluation.sequence_metrics(rows, {**PROTOCOL["metrics"], "steady_start_frame": 2})
    assert metrics["visible_frames"] == 9
    assert metrics["visible_matched_stop_frames"] == 5
    assert metrics["longest_visible_miss_after_stop"] == 1
    assert metrics["stop_episodes"] == 2
    assert metrics["unmatched_stop_frames"] == 3
    assert metrics["unmatched_stop_episodes"] == 2


def test_unseen_returns_remain_in_report_without_inventing_recall():
    metrics = evaluation.sequence_metrics([row(i, visible=False) for i in range(16)], PROTOCOL["metrics"])
    assert metrics["visible_frames"] == 0 and metrics["visible_recall"] is None
    assert metrics["first_stop_frame"] is None and not metrics["sustained"]


def test_matching_requires_physical_target_location_not_any_stop():
    case = evaluation.sequence_cases(PROTOCOL, "development")[0]
    detection = SimpleNamespace(distance=24.0, center=np.array([24.2, 1.05, -1.35]))
    assert evaluation.target_matches(detection, case, PROTOCOL["matching"])
    detection.center = np.array([24.2, -1.5, -1.35])
    assert not evaluation.target_matches(detection, case, PROTOCOL["matching"])
    detection.center = np.array([24.2, 1.05, 2.0])
    assert not evaluation.target_matches(detection, case, PROTOCOL["matching"])


def report(positive=True):
    metrics = evaluation.sequence_metrics([row(i, hit=i >= 4) for i in range(16)], PROTOCOL["metrics"])
    return {"protocol_sha256": "fixed", "split": "development", "complete_split": True,
            "expected_cases": ["example"], "cases": [
        {"case": {"name": "example", "positive": positive}, "input_sha256": "same",
         "encodings": {name: {"metrics": deepcopy(metrics)} for name in ("float32", "compact16")}}]}


@pytest.mark.parametrize("metric,value", [("matched_stop_frames", 11), ("first_stop_frame", 5),
                                         ("longest_visible_miss_after_stop", 1), ("sustained", False),
                                         ("unmatched_stop_frames", 1), ("unmatched_stop_episodes", 1)])
def test_comparison_rejects_each_preregistered_regression(metric, value):
    baseline = report()
    current = deepcopy(baseline)
    current["cases"][0]["encodings"]["compact16"]["metrics"][metric] = value
    result = evaluation.compare_reports(baseline, current)
    assert not result["passed"] and result["regressions"][0]["metric"] == metric


def test_comparison_rejects_changed_clouds_and_missing_cases():
    baseline = report()
    current = deepcopy(baseline)
    current["cases"][0]["input_sha256"] = "different"
    with pytest.raises(ValueError, match="input changed"):
        evaluation.compare_reports(baseline, current)
    current["cases"] = []
    with pytest.raises(ValueError, match="different case sets"):
        evaluation.compare_reports(baseline, current)


@pytest.mark.parametrize("claimed_complete", [True, False])
def test_comparison_never_passes_identical_incomplete_case_sets(claimed_complete):
    baseline = report()
    baseline["complete_split"] = claimed_complete
    baseline["expected_cases"].append("missing_case")
    result = evaluation.compare_reports(baseline, deepcopy(baseline))
    assert not result["passed"] and not result["detector_gain"]
    assert result["incomplete_split"] == ["baseline", "current"]


def freeze_document():
    return {role: {"commit": value * 40, "detector_source_sha256": value * 64,
                   "config_sha256": value * 64}
            for role, value in (("baseline", "a"), ("candidate", "b"))}


def test_reserved_execution_requires_an_exact_frozen_source_and_config_pair(tmp_path):
    path = tmp_path / "freeze.json"
    path.write_text(json.dumps(freeze_document()))
    frozen = evaluation.candidate_freeze(path, "evaluation")
    assert evaluation.frozen_role(frozen, {"detector_source_sha256": "a" * 64}, "a" * 64) == "baseline"
    assert evaluation.frozen_role(frozen, {"detector_source_sha256": "b" * 64}, "b" * 64) == "candidate"
    for source, config in (("a", "b"), ("b", "a"), ("c", "b")):
        with pytest.raises(ValueError, match="does not match frozen"):
            evaluation.frozen_role(frozen, {"detector_source_sha256": source * 64}, config * 64)
    incomplete = freeze_document()
    del incomplete["baseline"]
    path.write_text(json.dumps(incomplete))
    with pytest.raises(ValueError, match="baseline.commit"):
        evaluation.candidate_freeze(path, "evaluation")


def test_evaluator_rejects_mutated_reserved_candidate_before_processing(tmp_path, monkeypatch):
    path = tmp_path / "freeze.json"
    path.write_text(json.dumps(freeze_document()))
    frozen = evaluation.candidate_freeze(path, "evaluation")
    manifest = {"protocol_sha256": evaluation.file_hash(evaluation.PROTOCOL), "split": "evaluation",
                "candidate_freeze": frozen, "protocol": PROTOCOL, "cases": []}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(evaluation, "source_identity", lambda _: {"detector_source_sha256": "c" * 64})
    monkeypatch.setattr(evaluation, "Detector", lambda _: pytest.fail("detector ran before freeze validation"))
    args = SimpleNamespace(cache=tmp_path, protocol=evaluation.PROTOCOL, candidate_freeze=path,
                           config=ROOT / "configs/default.yaml", source_commit=None)
    with pytest.raises(ValueError, match="does not match frozen"):
        evaluation.evaluate(args)


def test_reserved_seeds_and_geometry_are_distinct_and_evaluation_requires_freeze():
    dev = evaluation.sequence_cases(PROTOCOL, "development")
    held = evaluation.sequence_cases(PROTOCOL, "evaluation")
    assert len(dev) == len(held) == 35
    dev_seeds = {c["seed"] + frame for c in dev for frame in range(PROTOCOL["frame_count"])}
    held_seeds = {c["seed"] + frame for c in held for frame in range(PROTOCOL["frame_count"])}
    assert dev_seeds.isdisjoint(held_seeds)
    assert PROTOCOL["splits"]["development"]["geometry"] != PROTOCOL["splits"]["evaluation"]["geometry"]
    with pytest.raises(ValueError, match="candidate-freeze"):
        evaluation.candidate_freeze(None, "evaluation")
