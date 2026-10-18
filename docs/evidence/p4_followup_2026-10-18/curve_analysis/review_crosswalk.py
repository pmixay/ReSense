"""Independent saved-row arithmetic review; no detector, ICP or renderer execution."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    report = json.loads((HERE / "report.json").read_text())
    assert report["script_sha256"] == sha(HERE / "analyze.py")
    assert report["row_archive_sha256"] == sha(HERE / "crosswalk_rows.json.gz")
    rows = json.loads(gzip.decompress((HERE / "crosswalk_rows.json.gz").read_bytes()))
    assert report["B_alignment"]["maximum_raw_axis_sample_delta_m"] == 0
    checks = {}
    for label, data in rows.items():
        expected = report["recordings"][label]
        assert len(data["frames"]) == (252 if label == "B" else 268)
        selected = {
            "raw_axis_error_all_reference_points": data["points"],
            "raw_axis_error_within_axis_range": [p for p in data["points"] if p["within_axis"]],
            "raw_axis_error_within_monitored_v110": [p for p in data["points"] if p["within_monitored_v110"]],
        }
        if label == "B":
            visible = [p for p in data["points"] if p["display_error_signed_m"] is not None]
            selected["same_display_visible_raw_axis_error"] = visible
            selected["same_display_visible_display_error"] = visible
        else:
            assert expected["display_available"] is False
            assert expected["same_display_visible_display_error"] is None
        checks[label] = {}
        for key, points in selected.items():
            field = "display_error_signed_m" if key == "same_display_visible_display_error" else "raw_axis_error_signed_m"
            values = np.abs([p[field] for p in points])
            assert len(values) == expected[key]["n"]
            for q in (50, 90, 99, 100):
                assert float(np.percentile(values, q)) == expected[key][f"p{q}"]
            assert float(np.mean(values > 1.05)) == expected[key]["share_over_1.05m"]
            checks[label][key] = {"n": len(values), "p90": float(np.percentile(values, 90))}
    data = subprocess.check_output(["git", "show", report["N1_evidence_commit"] +
        ":docs/evidence/n1_n4_2026-10-18/final_core_f5ff15f/rows/roundT_doubleT.jsonl.gz"], cwd=ROOT)
    n1 = [json.loads(line) for line in gzip.decompress(data).splitlines()]
    pairs = {}
    for j, distance in enumerate((40, 80, 120)):
        selected, values = [], []
        for i in range(1, len(n1)):
            a, b = n1[i - 1], n1[i]
            if not (a["gauge"]["valid"] and b["gauge"]["valid"] and
                    min(a["gauge"]["solid_range_m"], b["gauge"]["solid_range_m"]) >= distance):
                continue
            selected.append([i - 1, i])
            values.append(float(np.hypot(b["display_y"][j] - a["display_y"][j],
                                         b["display_z"][j] - a["display_z"][j])))
        expected = report["recordings"]["B"]["jitter_metrics_kept_separate"][str(distance)]
        assert selected == expected["same_visible_pairs"]
        assert float(np.percentile(values, 90)) == expected["display_visible_3D_uncompensated_m"]["p90"]
        pairs[str(distance)] = {"pairs": len(selected), "all_pairs": 251, "display_3D_p90_m": float(np.percentile(values, 90))}
    result = {"status": "SAVED_ROW_ARITHMETIC_AND_SCOPE_REVIEW_PASS", "checked_utc": datetime.now(timezone.utc).isoformat(),
              "reviewer": "c2_implementation; independent of crosswalk author",
              "checks": checks, "N1_visible_pairs": pairs,
              "input_sha256": {name: sha(HERE / name) for name in
                  ("analyze.py", "report.json", "crosswalk_rows.json.gz", "README.md", "P3_HANDOFF.md", "review_crosswalk.py")},
              "limits": ["No detector, renderer or ICP was run; no surveyed truth claim.",
                         "Source/matrix/EMA method inspected; saved point arithmetic independently recomputed.",
                         "40m compensated jitter and same-point path error regress; limited far coverage is explicit.",
                         "C display remains missing; N1 uncompensated3D and B6 compensated lateral metrics are distinct."]}
    (HERE / "independent_review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])


if __name__ == "__main__":
    main()
