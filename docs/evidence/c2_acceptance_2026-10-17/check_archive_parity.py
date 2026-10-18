#!/usr/bin/env python3
"""Project every archived 1.1.0 JSONL through the approved range policy, including X3."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.score_overclaim import compare_rows, read_results  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, required=True)
    args = parser.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    archive = ROOT / "docs/evidence/p4_eval_1.1.0_2026-10-16/raw/p4_raw_2026-10-16.tar.xz"
    cases = []
    scratch = args.scratch / "current_parity_input.jsonl"
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            if not (member.isfile() and "1.1.0" in member.name and member.name.endswith(".jsonl")):
                continue
            raw = source.extractfile(member).read()
            scratch.write_bytes(raw)
            rows = read_results(scratch)
            after, stats = compare_rows(rows, apply_cap=True, cap_small_target=True,
                                        sensor_model="pandar128", acceptance_profile="conservative_2026_10_17")
            cases.append({"member": member.name, "sha256": hashlib.sha256(raw).hexdigest(), "frames": len(rows),
                          "decision_rows_unchanged": stats["decision_rows_unchanged"],
                          "detections_and_warnings_unchanged": stats["detections_and_warnings_unchanged"],
                          "clear_never_lengthens": all(b["clear_distance"] <= a["clear_distance"]
                                                       for a, b in zip(rows, after))})
    passed = bool(cases) and all(c["decision_rows_unchanged"] and c["detections_and_warnings_unchanged"]
                                and c["clear_never_lengthens"] for c in cases)
    report = {"scope": "all 1.1.0-named archived JSONL, including X3 and superseded attribution captures; no new detector gate",
              "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
              "reporting_profile": "conservative_2026_10_17", "captures": len(cases),
              "frames": sum(c["frames"] for c in cases), "passed": passed, "cases": cases}
    (Path(__file__).parent / "archive_parity.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}, indent=2))
    return int(not passed)


if __name__ == "__main__":
    raise SystemExit(main())
