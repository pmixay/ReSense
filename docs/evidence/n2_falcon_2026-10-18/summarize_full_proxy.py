"""Revalidate the full transformed-input experiment against the same-runtime control.

This reports sensitivity to removed/changed input evidence, not a default detector
acceptance gate or recall on unchanged observable objects.
"""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "proxy", "control-source", "proxy-source", "cache", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--evaluation-input-root", type=Path, default=ROOT,
                        help="Harness checkout supplying labels and Set F speed metadata")
    args = parser.parse_args()
    helper = ROOT / "docs/evidence/lidar_adaptation_2026-10-18/review_gate_frames.py"
    spec = importlib.util.spec_from_file_location("full_proxy_review", helper)
    review = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(review)
    read, sha, gate = review.read, review.sha, review.gate
    old_receipt, receipt = (read(folder / "receipt.json") for folder in (args.control, args.proxy))
    if (old_receipt["status"] != "FINISHED" or not old_receipt["source_unchanged"]
            or not receipt["transformed_input_experiment_not_default_gate"] or receipt["smoke_test_only"]
            or not receipt["source_unchanged"] or not receipt["input_coverage_matches"]
            or not receipt["set_f_hook_activated"] or receipt.get("coverage_error")
            or receipt["expected_processed_source_frames"] != 18329):
        raise ValueError("completed and verified full-input control/experiment required")
    for name, value in old_receipt["source_hashes"].items():
        if name in receipt["source_hashes"] and value != receipt["source_hashes"][name]:
            raise ValueError(f"source differs between control and experiment: {name}")
    native = {Path(name).name: value for name, value in receipt["source_hashes"].items() if name.endswith(".so")}
    if native != old_receipt["native_library_hashes"]:
        raise ValueError("native library differs between control and experiment")
    for name, expected in receipt["hook_hashes"].items():
        if sha(args.proxy / "hook" / name) != expected:
            raise ValueError("retained transform helper/hook differs from the recorded bytes")
    if not receipt["activated_processes"]:
        raise ValueError("missing transform activation records")
    for activation in receipt["activated_processes"]:
        source = Path(receipt["source"])
        if (Path(activation["source"]) != source
                or Path(activation["detector_module"]) != source / "resense/detector.py"
                or activation["helper_sha256"] != receipt["hook_hashes"]["lidar_input_variants.py"]
                or not activation["transformed_input_only"]):
            raise ValueError("activation record differs from the pinned source/transform")
    totals, input_membership = Counter(), Counter()
    if {p.name for p in (args.proxy / "input_receipts").glob("frames_*.jsonl")} != set(receipt["input_workers"]):
        raise ValueError("proxy worker receipt inventory differs")
    for name, expected in receipt["input_workers"].items():
        path = args.proxy / "input_receipts" / name
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        if sha(path) != expected["sha256"] or len(rows) != expected["frames"]:
            raise ValueError("proxy input receipt bytes/coverage differ")
        if [row["__source_frame_index"] for row in rows] != list(range(len(rows))):
            raise ValueError("proxy per-worker source indices are not consecutive")
        for row in rows:
            if not 0 <= row["after_points"] <= row["before_points"]:
                raise ValueError("invalid transformed point count")
            totals.update(processed_source_frames=1, before_points=row["before_points"],
                          after_points=row["after_points"], output_ring_frames=row["output_has_ring"],
                          metadata_changed_frames=not row["metadata_preserved"])
            input_membership[(row["frame_id"], row["stamp"])] += 1
    if (dict(totals) != receipt["input_totals"] or totals["processed_source_frames"] != 18329
            or totals["output_ring_frames"] or totals["metadata_changed_frames"]):
        raise ValueError("transformed input totals/ring/metadata contract differ")
    old, new = (read(folder / "gate.json") for folder in (args.control, args.proxy))
    for report in (old, new):
        if (report["native"]["path"] != "native" or report["run"]["nominal_stamps"] is not False
                or report["ride"]["chunks"] != 8):
            raise ValueError("runtime/stamp/chunk protocol differs")
    # The proxy pins detector modules through sitecustomize; evaluation labels and
    # speed metadata are read by the unmodified harness from its own checkout.
    evaluation_paths = sorted(set(gate.eval_real.LABELS.values()) | {
        gate.SET_O_LABELS, "docs/extended_dataset_intake.json"})
    evaluation_hashes = {}
    for name in evaluation_paths:
        value = sha(args.evaluation_input_root / name)
        if value != sha(args.control_source / name):
            raise ValueError(f"evaluation labels/speed input differs from pinned control: {name}")
        evaluation_hashes[name] = value
    a, ah = review.validate_capture(old, args.control / "work", args.cache, args.control_source)
    b, bh = review.validate_capture(new, args.proxy / "work", args.cache, args.evaluation_input_root)
    cases = {}
    for name in a:
        if len(a[name]) != len(b[name]):
            raise ValueError("ordinary input membership differs")
        changes, lost, added = Counter(), [], []
        for (pi, left), (pj, right) in zip(a[name], b[name]):
            if pi != pj or any(left[k] != right[k] for k in ("frame", "frame_id", "stamp")):
                raise ValueError("ordinary row identity differs")
            identity = [pi, left["frame"], left["frame_id"]]
            changes.update(f"{kind}:{field}" for field, kind in review.changed(review.semantic(left), review.semantic(right)))
            if left["obstacle"] and not right["obstacle"]:
                lost.append(identity)
            if right["obstacle"] and not left["obstacle"]:
                added.append(identity)
        cases[name] = {"frames": len(a[name]), "changed_field_counts": dict(changes),
                       "baseline_stop_frames": sum(row["obstacle"] for _, row in a[name]),
                       "proxy_stop_frames": sum(row["obstacle"] for _, row in b[name]),
                       "lost_stop_rows": lost, "added_stop_rows": added}
    af, bf = (read(folder / "work/setF_straight.json") for folder in (args.control, args.proxy))
    review.validate_set_f(af, old, args.cache, args.control_source)
    review.validate_set_f(bf, new, args.cache, args.evaluation_input_root)
    expected_membership = Counter((row["frame_id"], row["stamp"]) for rows in b.values() for _, row in rows)
    ride_stamps = review.load_cache_stamps(str(args.cache / gate.RIDE))
    expected_membership.update((row["frame"], ride_stamps.get(row["frame"]) or 0.0)
                               for sequence in bf["sequences"] for row in sequence["rows"])
    if input_membership != expected_membership:
        raise ValueError("proxy source identities/stamps/multiplicity differ from ordinary and Set F rows")
    if af["parameters"] != bf["parameters"]:
        raise ValueError("Set F source/configuration/seed/protocol parameters differ")
    sequences = []
    for left, right in zip(af["sequences"], bf["sequences"]):
        if any(left[k] != right[k] for k in ("kind", "file0", "d0", "lateral", "refl")):
            raise ValueError("Set F sequence membership differs")
        if len(left["rows"]) != len(right["rows"]):
            raise ValueError("Set F row coverage differs")
        lost, added, changed_placement = [], [], []
        for lr, rr in zip(left["rows"], right["rows"]):
            if lr["frame"] != rr["frame"]:
                raise ValueError("Set F source frame differs")
            if lr["hit"] and not rr["hit"]:
                lost.append(lr["frame"])
            if rr["hit"] and not lr["hit"]:
                added.append(lr["frame"])
            if lr["gt"] != rr["gt"]:
                changed_placement.append(lr["frame"])
        sequences.append({"kind": left["kind"], "file0": left["file0"], "rows": len(left["rows"]),
                          "baseline_first_m": left["first"], "proxy_first_m": right["first"],
                          "lost_hit_rows": lost, "added_hit_rows": added,
                          "changed_legacy_gt_rows": changed_placement})
    if sum(v["frames"] for v in cases.values()) != 15269 or sum(v["rows"] for v in sequences) != 3060:
        raise ValueError("full membership differs")
    comparison = gate.compare(old, new, [])
    output = {"status": "COMPLETE_TRANSFORMED_INPUT_MEASUREMENT_NOT_DEFAULT_ACCEPTANCE",
              "loaded_detector_source": receipt["source"],
              "loaded_detector_source_hashes": receipt["source_hashes"],
              "gate_orchestration_checkout": new["code"],
              "evaluation_input_root": str(args.evaluation_input_root),
              "evaluation_input_sha256": evaluation_hashes,
              "same_runtime_comparison_passed": not any(row["fails"] for row in comparison),
              "comparison": comparison, "ordinary": cases, "set_F": sequences,
              "ordinary_rows": 15269, "set_F_rows": 3060, "input_totals_recomputed": dict(totals),
              "input_identity_stamp_multiplicity_verified": True,
              "control_raw_sha256": ah, "proxy_raw_sha256": bh,
              "limitations": receipt["limitations"] + [
                  "Overall STOP loss/addition is not a person-specific true/false-positive count.",
                  "Set F stored hit/fp aggregates are reconstructed; complete detections are absent, so assignments cannot be independently rebuilt.",
                  "Input-call receipts validate source identities and point counts, not independently stored transformed point payloads; the transform is identified by retained helper/hook hashes and its tests.",
                  "The gate's code.commit describes the orchestration checkout. Actual loaded detector identity is the pinned baseline source/source_hashes and hook activation detector_module, not that Git stamp.",
                  "Timing is informational under shared load and the recorded priority change."],
              "input_sha256": {str(p): sha(p) for p in (
                  args.control / "receipt.json", args.proxy / "receipt.json", args.control / "gate.json",
                  args.proxy / "gate.json", args.control / "work/setF_straight.json",
                  args.proxy / "work/setF_straight.json", helper, Path(__file__))}}
    args.out.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({key: output[key] for key in ("status", "same_runtime_comparison_passed", "ordinary_rows", "set_F_rows")}))


if __name__ == "__main__":
    main()
