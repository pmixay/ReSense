"""Reference and source fidelity when evaluating local parts outside the live detector."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest

from resense.config import ClusterConfig, GaugeConfig
from scripts.analyze_fresh_support import (decomposition, episode_count, exact_descriptor, negative_report, positive_report,
                                           runtime_support, validate_descriptor)

DIRECT_CAPTURE_ROOT = Path("C:/Users/alikh/AppData/Local/Temp/opencode")


def component():
    xyz = np.array([[110, 0, .4], [110.1, .2, .4], [110, .4, .8],
                    [110.1, 0, 1.0], [110, .2, 1.3], [110.1, .4, 1.3]], np.float32)
    return {"xyz": xyz.tolist(), "dy": xyz[:, 1].tolist(), "h": (xyz[:, 2] + 1).tolist(),
            "strict": [True] * 6, "rail_strict": [True] * 6, "dy_rail": xyz[:, 1].tolist(),
            "voxel_ids": list(range(6)), "frame_idx": list(range(6)), "intensity": [200.] * 6,
            "ring": None, "dy_alt": None, "cfg": asdict(ClusterConfig()), "gauge": asdict(GaugeConfig()),
            "parameters": dict(factor=1., factor_range=0., axis_valid=200., height_valid=120.,
                               keep_thin=True, weak_from=60.),
            "mask_meaning": "effective_corridor", "historical_points": 0}


def test_actual_height_reference_prevents_geometry_only_false_acceptance():
    support = component()
    ids = np.arange(6)
    assert exact_descriptor(support, ids)["zone"] == "gauge"
    support["parameters"]["height_valid"] = 100.
    actual = exact_descriptor(support, ids)
    assert actual["reason"] == "beyond_height_ref"
    assert actual["gauge_voxels"] == 6 and actual["ring_count"] == 0


def test_overlapping_tracks_do_not_multiply_node_stop_episodes():
    assert episode_count({1, 2, 5, 7, 8}) == 3


def test_recorded_intensity_and_rule_configuration_are_not_replaced_by_a_geometry_proxy():
    support = component()
    support["cfg"]["retro_intensity"] = 100.
    actual = exact_descriptor(support, np.arange(6))
    assert actual["reason"] == "retro"
    assert actual["zone"] == "warning"


def test_low_support_eligibility_cannot_be_relabelled_as_corridor_strict():
    support = component()
    support["mask_meaning"] = "low_stage_eligibility"
    with pytest.raises(ValueError, match="low-stage eligibility"):
        runtime_support(support)


def test_source_descriptor_validation_rejects_both_decision_and_geometry_mismatch():
    actual = exact_descriptor(component(), np.arange(6))
    validate_descriptor(actual, deepcopy(actual))
    for field, value in (("zone", "warning"), ("distance", 80.)):
        wrong = dict(actual, **{field: value})
        with pytest.raises(ValueError, match="replay mismatch"):
            validate_descriptor(actual, wrong)
    with pytest.raises(ValueError, match="no longer rejects"):
        validate_descriptor(actual, None)


def test_local_decomposition_does_not_mutate_exact_inputs_or_use_scoring_labels():
    support = component()
    before = deepcopy(support)
    first = decomposition(support)
    assert support == before
    # Unconsumed evaluation labels cannot change either membership or descriptor results.
    support["target_mask"] = [True, False] * 3
    assert decomposition(support) == first
    assert first["strict"][0]["descriptor"]["ring_count"] == 0


@pytest.mark.realdata(str(DIRECT_CAPTURE_ROOT / "direct-fresh-support-all"))
def test_direct_fresh_selected_events_and_positive_counterexample_when_capture_available():
    root = DIRECT_CAPTURE_ROOT
    trace = root / "direct-fresh-support-all"
    centre = root / "range-shape-centre-direct-fresh.json"
    assert (trace / "summary.json").exists() and centre.exists(), "marked direct-fresh capture is incomplete"
    negatives = negative_report(trace)
    assert negatives["paired_frames"] == 9255
    assert negatives["counts"]["stop_track_frames"] == 133
    assert negatives["counts"]["stop_frames"] == 117
    assert negatives["counts"]["episodes"] == 26
    assert negatives["counts"]["matched_observations"] == 494
    assert negatives["counts"]["transitions"] == 467
    assert negatives["counts"]["validated_corridor_descriptors"] == 439
    assert negatives["counts"]["first_stop_gate_true"] == 27
    assert negatives["counts"]["first_stop_low"] == 9
    events = {e["key"]: e for e in negatives["events"]}
    assert len(events) == 27
    assert events["new_data_6.jsonl:331"]["onset_local_parts"]["strict"][0]["descriptor"]["zone"] == "gauge"
    for name in ("74", "298"):
        parts = events[f"new_data_1.jsonl:{name}"]["onset_local_parts"]
        assert parts["strict"][0]["descriptor"]["reason"] == "beyond_height_ref"

    positives = positive_report(centre)
    person = next(s for s in positives["sequences"] if s["kind"] == "person" and "47_" in s["file0"])
    cable = next(s for s in positives["sequences"] if s["kind"] == "cable" and "47_" in s["file0"])
    assert person["counts"]["strict_complete_recoveries"] == 11
    assert cable["counts"]["strict_complete_recoveries"] == 1
    assert all(case["complete_parts"][0]["descriptor"]["zone"] == "gauge"
               for seq in (person, cable) for case in seq["oracle_cases"] if case["mode"] == "strict")
