#!/usr/bin/env python3
"""Complete shipping-withdrawal report; f8 is historical comparison, never acceptance control."""
from collections import Counter, defaultdict
import itertools
import json
from pathlib import Path
import re

from frame_diff import changes, normalize, field_group

ROOT = Path(__file__).resolve().parent.parent
COMMIT = "c9aea87cb5322092070158cd8987115ee44833c9"
BASE = ROOT / "baseline-707ea9cda051-20261016T060147Z-68fb3429"
CURRENT = ROOT / "candidate-c9aea87cb532-20261016T101302Z-8a9ae4d1"
HISTORY = ROOT / "candidate-f8c088dc4f32-20261016T073403Z-4b64ec55"
ANALYSIS = ROOT / ("analysis-" + CURRENT.name)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def project(row, index):
    if index >= len(row["raw"]["candidates"]):
        return {"candidate_missing": True}
    candidate = row["raw"]["candidates"][index]
    return {k: v for k, v in candidate.items() if k != "points_idx"}


def main():
    explained = load(ANALYSIS / "explained_frames.json")
    assert explained["controls"]["candidate_commit"] == COMMIT
    counts = Counter(frames=0, changed_frames=0, changed_entries=0)
    fields = Counter()
    groups = defaultdict(lambda: dict(frames=0, entries=0))
    examples, previous_spares, target = [], [], None
    for path in sorted((BASE / "frames").glob("*.jsonl")):
        with path.open() as baseline, (CURRENT / "frames" / path.name).open() as current, (HISTORY / "frames" / path.name).open() as historical:
            for i, triple in enumerate(itertools.zip_longest(baseline, current, historical)):
                if any(value is None for value in triple):
                    raise ValueError("historical/current/control frame count differs")
                base, new, old = map(json.loads, triple)
                assert base["key"] == new["key"] == old["key"]
                counts["frames"] += 1
                a, b = {}, {}
                for rep in ("raw", "serialized"):
                    a[rep], _ = normalize(old[rep])
                    b[rep], _ = normalize(new[rep])
                delta = list(changes(a, b))
                if delta:
                    counts["changed_frames"] += 1
                    frame_groups = set()
                    for field, before, after in delta:
                        counts["changed_entries"] += 1
                        fields[re.sub(r"\[\d+\]", "[]", field)] += 1
                        group = field_group(field)
                        groups[group]["entries"] += 1
                        frame_groups.add(group)
                        examples.append(dict(sequence_file=path.name, row=i, key=new["key"], field=field, historical=before, current=after))
                    for group in frame_groups:
                        groups[group]["frames"] += 1
                for ci, candidate in enumerate(old["raw"]["candidates"]):
                    if candidate.get("spared"):
                        previous_spares.append(dict(sequence_file=path.name, row=i, frame_id=new["key"]["frame_id"], candidate_index=ci,
                            sealed=project(base, ci), historical=project(old, ci), current=project(new, ci)))
                if path.name == "new_data_1.jsonl" and i == 1354:
                    assert new["key"]["frame_id"] == "new_data_54_0009"
                    target = dict(sequence_file=path.name, row=i, frame_id=new["key"]["frame_id"], candidate_index=8,
                        sealed=project(base, 8), historical=project(old, 8), current=project(new, 8),
                        current_obstacle=new["serialized"]["obstacle"], current_warning=new["serialized"]["warning"],
                        current_nearest=new["serialized"]["nearest_distance"], current_clear=new["serialized"]["clear_distance"],
                        current_detections=new["serialized"]["detections"], current_warnings=new["serialized"]["warnings"])
    assert counts["frames"] == 18329 and target is not None
    baseline_candidate = target["sealed"]
    shipping_candidate = {k: v for k, v in target["current"].items() if k not in ("spared", "cut")}
    promotion_gone = baseline_candidate == shipping_candidate and target["current"].get("spared") is False
    metadata = load(ANALYSIS / "evaluation_and_config.json")
    shipping = load(ANALYSIS / "shipping_route.json")
    flags = explained["added_cluster_flags"]
    axis_only = not explained["other_or_unexplained_changes"] and all(
        value == 0 for value in explained["changed_frames_by_explicit_result_group"].values())
    formula_mismatches = {k: v for k, v in explained["exact_checks"].items() if k.endswith("_mismatch") and v}
    report = dict(measured_commit=COMMIT, gate_exit=load(CURRENT / "completion.json")["gate_exit"],
        acceptance_control_commit="707ea9cda051369326fb9407c42488c1033dad76",
        source_sha256=load(CURRENT / "source_after.json")["source_sha256"],
        source_clean_before_after=not load(CURRENT / "source_before.json")["git_status"] and not load(CURRENT / "source_after.json")["git_status"],
        clean_LF=load(CURRENT / "source_before.json")["crlf_files"] == [],
        historical_commit="f8c088dc4f3243fbd15a3aae9be0459e8a0aa941", historical_is_acceptance_control=False,
        shipping_routes=shipping, active_evaluation_inputs_identical=metadata["all_active_evaluator_and_labels_identical"],
        axis_range_and_additive_metadata_only=axis_only and not formula_mismatches,
        previous_H3_promotion_disappeared=promotion_gone, previous_promotion_witness=target,
        previous_spared_candidates=previous_spares,
        current_spared_true=flags["spared"].get("true", 0), current_cut_true=flags["cut"].get("true", 0),
        historical_to_current=dict(counts=dict(counts), fields=dict(fields), groups=dict(groups), all_changes=examples),
        exact_result_checks=explained["changed_frames_by_explicit_result_group"],
        range_checks=explained["exact_checks"], range_formula_mismatches=formula_mismatches,
        common_raw_numeric_comparison=explained["common_captured_raw_numeric_values"],
        metrics_summaries=metadata["metrics_summaries"],
        limits="The plain full gate and every captured frame are measured here. H4 author withdrawal units/probes/dark evidence are separate; no G3 held-out case is run. Equality claims concern captured results, not every unrecorded intermediate or tracker state.")
    write(ANALYSIS / "WITHDRAWN_RESULT.json", report)
    print(json.dumps({k: report[k] for k in ("measured_commit", "gate_exit", "source_sha256", "source_clean_before_after", "clean_LF", "axis_range_and_additive_metadata_only", "previous_H3_promotion_disappeared", "current_spared_true", "current_cut_true", "exact_result_checks", "common_raw_numeric_comparison")}, indent=2))
    print(json.dumps(report["historical_to_current"], indent=2))


if __name__ == "__main__":
    main()
