"""Paired set F summaries never mix skipped sequences or mismatched background frames."""

import importlib.util
from pathlib import Path

import pytest


PATH = Path(__file__).resolve().parents[1] / "scripts" / "compare_setf.py"
SPEC = importlib.util.spec_from_file_location("resense_compare_setf", PATH)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def report(mode):
    return {"schema": "setF-placement-v1", "source": "synthetic objects on real empty ride frames",
            "parameters": {"placement_mode": mode, "seed": 1, "files": "46,127", "frames": 2,
                           "kinds": "person", "cache_files": ["new_data_46_0000.npy"],
                           "config_sha256": "abc", "speeds_sha256": "def", "selected_stamps_sha256": "ghi"},
            "sequences": [{"file0": "new_data_46_0000.npy", "kind": "person", "d0": 50,
                           "lateral": 0.1, "refl": 40., "first": 49.,
                           "rows": [{"frame": "new_data_46_0000", "d": 49., "n": 2, "hit": True, "gt_vehicle_y_m": 0.1},
                                    {"frame": "new_data_46_0001", "d": 48., "n": 0, "hit": False, "gt_vehicle_y_m": 0.2}]},
                          {"file0": "new_data_127_0000.npy", "kind": "person", "d0": 50,
                           "lateral": 0.1, "refl": 40., "first": 49.,
                           "rows": [{"frame": "new_data_127_0000", "d": 49., "n": 2, "hit": True, "gt_vehicle_y_m": 0.1}]}]}


def test_skipped_sequence_is_excluded_from_both_modes():
    old, new = report("legacy"), report("anchored")
    new["sequences"][0]["rows"][0]["hit"] = False
    new["sequences"][0]["rows"][0]["gt_vehicle_y_m"] = 0.7
    new["sequences"][1].update(skipped="no near reference", rows=[], first=None)
    s = module.compare(old, new)
    summary = s["per_kind"]["person"]
    assert {k: v for k, v in summary.items() if k != "recall_by_bin"} == {
        "paired_sequences": 1, "skipped": 1, "visible": {"legacy": 1, "anchored": 1},
        "visible_hits": {"legacy": 1, "anchored": 0},
        "first_median": {"legacy": 49., "anchored": 49.}}
    assert summary["recall_by_bin"]["legacy"]["0-50"] == [1, 1]
    assert summary["recall_by_bin"]["anchored"]["0-50"] == [0, 1]
    assert s["sequences"][0]["max_axis_delta_m"] == 0.6
    assert s["sequences"][1]["skipped"]["anchored"] == "no near reference"


@pytest.mark.parametrize("mutate, message", [
    (lambda r: r["parameters"].update(seed=2), "different seed"),
    (lambda r: r["parameters"].update(config_sha256="other"), "different config_sha256"),
    (lambda r: r["sequences"][0].update(lateral=0.2), "different sampled lateral"),
    (lambda r: r["sequences"][0]["rows"][0].update(frame="other"), "different frame selection"),
])
def test_comparison_rejects_nonpaired_inputs(mutate, message):
    old, new = report("legacy"), report("anchored")
    mutate(new)
    with pytest.raises(ValueError, match=message):
        module.compare(old, new)
