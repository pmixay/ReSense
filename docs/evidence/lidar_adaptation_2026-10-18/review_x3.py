"""Independently revalidate the complete X3 raw evidence and compare every output row."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def semantic(row):
    result = {key: value for key, value in row.items()
              if key not in ("decode_ms", "detect_ms", "total_ms")}
    # Health latency depends on concurrent work. Preserve decision health and
    # every other diagnostic; do not discard orientation or range changes.
    result["msgs"] = [m for m in row["msgs"] if not m.startswith("latency p95 ")]
    if any(m.startswith("latency p95 ") for m in row["msgs"]) and row["level"] == "warn":
        result["level"] = row["dlevel"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--reference-raw-root", type=Path,
                        help="Relocate raw paths in memory to ROOT/<bag>/<variant>/probe.jsonl")
    parser.add_argument("--candidate-raw-root", type=Path,
                        help="Relocate raw paths in memory to ROOT/<bag>/<variant>/probe.jsonl")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    reference, candidate = (json.loads(p.read_text()) for p in (args.reference, args.candidate))
    spec = importlib.util.spec_from_file_location("x3_review_driver", ROOT / "scripts/robustness_battery.py")
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    for report, root in ((reference, args.reference_raw_root), (candidate, args.candidate_raw_root)):
        if root is not None:
            for key, entry in report["entries"].items():
                if len(Path(key).parts) != 2 or any(p in (".", "..") for p in Path(key).parts):
                    raise ValueError("invalid case path")
                entry["raw_path"] = str(root / key / "probe.jsonl")
    for report in (reference, candidate):
        if report["protocol"] != driver.protocol():
            raise ValueError("report differs from the registered driver protocol")
        if set(report["sources"]) != set(driver.BAGS):
            raise ValueError("source inventory differs from the registered X3 membership")
        label_names = {"doubleT_obstacle", "cloud_with_fake_obj"}
        if set(report["labels"]) != label_names or any(
                report["labels"][name] != sha(ROOT / f"labels/{name}.json") for name in label_names):
            raise ValueError("label inventory or actual label bytes differ")
        driver.validated_entries(report, args.cache, ROOT)
        if len(report["entries"]) != 40 or sum(
                e["metrics"]["frames"] for e in report["entries"].values()) != 29765:
            raise ValueError("registered 40-case/29765-row coverage differs")
        if "judge_reproduction" in report and report["judge_reproduction"] != driver.judge_comparison(report["entries"]):
            raise ValueError("judge reproduction summary disagrees with revalidated metrics")
    source_equal = all({k: v for k, v in reference["sources"][name].items() if k != "path"}
                       == {k: v for k, v in candidate["sources"][name].items() if k != "path"}
                       for name in reference["sources"])
    if (not source_equal or reference["protocol"] != candidate["protocol"]
            or reference["labels"] != candidate["labels"]):
        raise ValueError("reference/candidate source, protocol or label identity differs")
    comparisons = {key: driver.compare_metrics(reference["entries"][key]["metrics"], e["metrics"])
                   for key, e in candidate["entries"].items()}
    comparison = {"passed": all(row["passed"] for rows in comparisons.values() for row in rows),
                  "cases": comparisons}
    expected_pass = comparison["passed"] and candidate.get("judge_reproduction", {"passed": True})["passed"]
    expected_status = "PASS" if expected_pass else "FAIL"
    if candidate["comparison"] != comparison or candidate["status"] != expected_status:
        raise ValueError("candidate comparison/status disagrees with directional metric reconstruction")
    results = {}
    for key, old in reference["entries"].items():
        new = candidate["entries"][key]
        a, b = ([json.loads(line) for line in Path(entry["raw_path"]).read_text().splitlines()]
                for entry in (old, new))
        if len(a) != len(b):
            raise ValueError(f"raw length mismatch: {key}")
        differences = {}
        for left, right in zip(a, b):
            if left["i"] != right["i"]:
                raise ValueError(f"frame alignment mismatch: {key}")
            ls, rs = semantic(left), semantic(right)
            for field in ls.keys() | rs.keys():
                if field not in ls or field not in rs or ls[field] != rs[field]:
                    differences.setdefault(field, []).append(left["i"])
        results[key] = {"frames": len(a), "changed_fields": differences,
                        "lost_stop_frames": [left["i"] for left, right in zip(a, b)
                                             if left["obstacle"] and not right["obstacle"]],
                        "added_stop_frames": [left["i"] for left, right in zip(a, b)
                                              if not left["obstacle"] and right["obstacle"]],
                        "reference_first_stop": next((r["i"] for r in a if r["obstacle"]), None),
                        "candidate_first_stop": next((r["i"] for r in b if r["obstacle"]), None),
                        "metrics_identical": old["metrics"] == new["metrics"],
                        "reference_raw_sha256": old["raw_sha256"],
                        "candidate_raw_sha256": new["raw_sha256"]}
    report = {"status": "RAW_EVIDENCE_REVALIDATED", "cases": results,
              "case_count": len(results), "rows_compared": sum(v["frames"] for v in results.values()),
              "all_metrics_identical": all(v["metrics_identical"] for v in results.values()),
              "all_non_timing_fields_identical": all(not v["changed_fields"] for v in results.values()),
              "source_protocol_labels_identical": source_equal,
              "candidate_gate_status": expected_status,
              "comparison_recomputed": comparison,
              "raw_path_relocations": {"reference": str(args.reference_raw_root) if args.reference_raw_root else None,
                                       "candidate": str(args.candidate_raw_root) if args.candidate_raw_root else None},
              "scope": "Both reports' raw SHA, completion identities, input stamps, frame counts and recomputed metrics validated before exact row comparison",
              "excluded": "decode/detect/total timing and latency-only health warning promotion/text",
              "input_sha256": {str(p): sha(p) for p in (args.reference, args.candidate, Path(__file__),
                                                          ROOT / "scripts/robustness_battery.py")}}
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}))


if __name__ == "__main__":
    main()
