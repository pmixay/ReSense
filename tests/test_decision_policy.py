"""Policy behavior on production object/JSON shapes and source/installed consumers."""
from copy import deepcopy
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest

from resense.detector import Detection, FrameResult
from resense.track import TrackModel

try:
    from resense_ros.decision_policy import DecisionPolicy, decision, evaluate_decision
except ModuleNotFoundError:
    from ros2_ws.src.resense_ros.resense_ros.decision_policy import DecisionPolicy, decision, evaluate_decision

ROOT = Path(__file__).resolve().parents[1]


def frame(reason="", distance=40., size=(.5, .5, 1.), **changes):
    warning = Detection(1, distance, .9, np.array([distance, .9, .5]), np.array(size),
                        10, .8, 10, "warning", 0., 30., reason=reason)
    result = FrameResult(1., False, True, None, [], [warning], [],
                         TrackModel(np.array([0., 0., -1.]), (3., 100.), 0., 0., 0.),
                         np.array([], dtype=int), 100, health={"level": "ok"})
    for key, value in changes.items():
        setattr(result, key, value)
    return result


def both_shapes(result, policy):
    obj = evaluate_decision(result, policy)
    encoded = json.loads(json.dumps(result.to_dict()))
    assert evaluate_decision(encoded, policy) == obj
    return obj


def test_v1_reproduces_original_precedence_for_all_valid_health_combinations():
    for obstacle, warning, level, dl in itertools.product(
            (False, True), (False, True), ("ok", "warn", "error"), (None, "ok", "warn")):
        health = {"level": level}
        if dl is not None:
            health["decision_level"] = dl
        result = frame(obstacle=obstacle, warning=warning, health=health)
        expected = ("STOP" if obstacle else "FAULT" if level == "error" else
                    "CAUTION" if warning or (dl or level) == "warn" else "GO")
        assert both_shapes(result, "v1").decision == expected
        assert decision(result) == expected
    assert decision({}) == "GO"  # old web/offline rows may omit additive fields
    assert decision({"health": None}) == "GO"


@pytest.mark.parametrize("reason,distance,size,expected,code", [
    ("column", 20, (.3, .3, 2.8), "GO", None),
    ("", 80, (.5, .5, 1), "CAUTION", "margin_object"),
    ("", 81, (.5, .5, 1), "GO", None),
    ("beyond_axis", 150, (3, .5, 1), "CAUTION", "compact_range_object"),
    ("beyond_height_ref", 150, (.5, .5, 3.01), "GO", None),
    ("beyond_axis", 40, (3.01, .5, 1), "GO", None),
    ("doubt", 200, (20, 20, 20), "CAUTION", "doubt"),
    ("floating", 200, (20, 20, 20), "CAUTION", "advisory_object"),
    ("future_reason", 200, (.5, .5, 1), "CAUTION", "advisory_object"),
])
def test_v2_reason_distance_and_compactness_contract(reason, distance, size, expected, code):
    result = frame(reason, distance, size)
    assert both_shapes(result, "v1").decision == "CAUTION"
    evaluated = both_shapes(result, "v2")
    assert evaluated.decision == expected
    assert evaluated.caution_reason == ((code,) if code else ())


def test_runtime_parameters_are_explicit_and_do_not_change_default_v1():
    result = frame(distance=70)
    assert decision(result, DecisionPolicy("v2", caution_distance_m=60)) == "GO"
    assert decision(result, "v2") == "CAUTION"
    assert decision(result) == "CAUTION"
    result = frame("beyond_axis", size=(2.1, .5, 1))
    assert decision(result, DecisionPolicy("v2", compact_max_size_m=2)) == "GO"
    assert decision(result, "v2") == "CAUTION"


@pytest.mark.parametrize("params", [{"version": "v3"}, {"caution_distance_m": 0},
                                    {"caution_distance_m": float("inf")},
                                    {"compact_max_size_m": float("nan")},
                                    {"compact_max_size_m": -1}, {"caution_distance_m": True},
                                    {"caution_distance_m": 10 ** 1000}])
def test_invalid_runtime_configuration_is_rejected(params):
    with pytest.raises(ValueError):
        DecisionPolicy(**params)


@pytest.mark.parametrize("row", [None, [], "row", {"obstacle": "false"}, {"warning": 1},
                                 {"health": []}, {"health": {"level": "OK"}},
                                 {"health": {"level": np.array(["ok", "warn"])}},
                                 {"health": {"decision_level": None}},
                                 {"health": {"decision_level": "error"}}])
def test_untrustworthy_input_is_fault(row):
    for version in ("v1", "v2"):
        assert decision(row, version) == "FAULT"


@pytest.mark.parametrize("warnings", [None, [], "warnings", [None], [{}], [{"reason": None}],
    [{"reason": "", "distance": float("nan")}], [{"reason": "", "distance": -1}],
    [{"reason": "beyond_axis", "size": [1, 1]}],
    [{"reason": "beyond_axis", "size": [1, 0, 1]}],
    [{"reason": "beyond_axis", "size": [1, 1, float("inf")]}]])
def test_missing_or_invalid_suppression_evidence_retains_caution(warnings):
    answer = evaluate_decision({"warning": True, "warnings": warnings}, "v2")
    assert answer.decision == "CAUTION"
    assert answer.caution_reason == ("incomplete_advisory",)


def test_stop_health_and_doubt_survive_suppressed_advisories_and_invalid_details():
    result = frame("column", health={"level": "warn", "decision_level": "warn"})
    assert both_shapes(result, "v2").caution_reason == ("health_warning",)
    result.warnings.append(frame("doubt").warnings[0])
    assert both_shapes(result, "v2").caution_reason == ("doubt", "health_warning")
    result.health["level"] = "error"
    assert both_shapes(result, "v2").decision == "FAULT"
    # A held STOP can have no current boxes and malformed health; base policy cannot release it.
    result.obstacle, result.warnings, result.health = True, [], None
    assert both_shapes(result, "v2").decision == "STOP"
    assert decision({"obstacle": True, "warning": "broken", "health": []}, "v2") == "STOP"
    assert decision(frame("column", health={"level": "warn", "decision_level": "ok"}), "v2") == "GO"


def test_additive_status_contract_is_deterministic_and_input_is_not_mutated():
    row = frame("doubt", health={"level": "warn"}).to_dict()
    row["warnings"] *= 2
    before = deepcopy(row)
    answer = evaluate_decision(row, "v2")
    assert answer.to_dict() == {"decision": "CAUTION", "decision_policy": "v2",
                                "caution_reason": ["doubt", "health_warning"]}
    assert json.loads(json.dumps(answer.to_dict())) == answer.to_dict()
    assert row == before
    for word, row in (("GO", {}), ("FAULT", {"health": {"level": "error"}}), ("STOP", {"obstacle": True})):
        assert evaluate_decision(row).to_dict() == {"decision": word, "decision_policy": "v1", "caution_reason": []}


def test_saved_status_is_not_a_freshness_or_latch_evaluator():
    row = {"decision": "STOP", "stop_held": True, "freshness": {"valid": False},
           "warning": False, "obstacle": False}
    assert decision(row) == "GO"  # caller must project its health and held obstacle before evaluating


def test_all_consumers_share_the_same_callable_and_cross_ring_keeps_geometry(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "webapp/backend"))
    from resense_web.decision import decision_of
    from scripts import analyze_cross_ring_measurement as cross
    from scripts import hero_view, score_clear_distance, synthetic_sensitivity

    assert decision_of is score_clear_distance.decision is hero_view.decision is synthetic_sensitivity.decision
    assert cross.decision_word is decision_of
    a = {"health": {"level": "ok"}, "detections": [{"id": 1, "age": 4, "distance": 10}]}
    b = deepcopy(a)
    b["health"]["level"] = "warn"
    assert len(cross.compare([a], [b])["decision_differences"]) == 1
    b = deepcopy(a)
    b["detections"][0]["distance"] = 11
    assert len(cross.compare([a], [b])["decision_differences"]) == 1


@pytest.mark.parametrize("installed", [False, True])
def test_pure_policy_import_and_consumers_in_both_layouts(tmp_path, installed):
    env = {**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    env.pop("RESENSE_DETECTOR_ROOT", None)
    if installed:
        package = tmp_path / "resense_ros"
        package.mkdir()
        for name in ("__init__.py", "decision_policy.py"):
            shutil.copyfile(ROOT / "ros2_ws/src/resense_ros/resense_ros" / name, package / name)
        env["PYTHONPATH"] = str(tmp_path)
        module = "resense_ros.decision_policy"
    else:
        env["PYTHONPATH"] = str(ROOT)
        module = "ros2_ws.src.resense_ros.resense_ros.decision_policy"
    code = (f"from {module} import decision; import sys; "
            "assert 'rclpy' not in sys.modules and 'numpy' not in sys.modules; "
            "assert decision({'warning': True}) == 'CAUTION'; "
            f"sys.path.insert(0, {str(ROOT / 'webapp/backend')!r}); "
            "from resense_web.decision import decision_of; assert decision_of is decision; "
            f"import runpy; ns = runpy.run_path({str(ROOT / 'scripts/score_clear_distance.py')!r}); "
            "assert ns['decision'] is decision")
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
