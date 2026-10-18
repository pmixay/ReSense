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
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    reference, candidate = (json.loads(p.read_text()) for p in (args.reference, args.candidate))
    spec = importlib.util.spec_from_file_location("x3_review_driver", ROOT / "scripts/robustness_battery.py")
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    for report in (reference, candidate):
        driver.validated_entries(report, args.cache, ROOT)
    source_equal = all({k: v for k, v in reference["sources"][name].items() if k != "path"}
                       == {k: v for k, v in candidate["sources"][name].items() if k != "path"}
                       for name in reference["sources"])
    if (not source_equal or reference["protocol"] != candidate["protocol"]
            or reference["labels"] != candidate["labels"]):
        raise ValueError("reference/candidate source, protocol or label identity differs")
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
                        "metrics_identical": old["metrics"] == new["metrics"],
                        "reference_raw_sha256": old["raw_sha256"],
                        "candidate_raw_sha256": new["raw_sha256"]}
    report = {"status": "RAW_EVIDENCE_REVALIDATED", "cases": results,
              "case_count": len(results), "rows_compared": sum(v["frames"] for v in results.values()),
              "all_metrics_identical": all(v["metrics_identical"] for v in results.values()),
              "all_non_timing_fields_identical": all(not v["changed_fields"] for v in results.values()),
              "source_protocol_labels_identical": source_equal,
              "candidate_gate_status": candidate["status"],
              "scope": "Both reports' raw SHA, completion identities, input stamps, frame counts and recomputed metrics validated before exact row comparison",
              "excluded": "decode/detect/total timing and latency-only health warning promotion/text",
              "input_sha256": {str(p): sha(p) for p in (args.reference, args.candidate, Path(__file__),
                                                          ROOT / "scripts/robustness_battery.py")}}
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}))


if __name__ == "__main__":
    main()
