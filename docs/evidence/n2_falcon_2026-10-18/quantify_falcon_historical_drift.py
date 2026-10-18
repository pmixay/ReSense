"""Record exact historical numerical differences without declaring them equal."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [HERE / "falcon_full/baseline.jsonl", HERE / "falcon_default_off/baseline.jsonl"]
    before, after = ([json.loads(line) for line in path.read_text().splitlines()] for path in paths)
    assert len(before) == len(after) == 4443
    fields = [("curv",), ("track_detail", "curvature"),
              ("track_detail", "yaw"), ("track_detail", "floor_coef")]
    output = {}
    for field in fields:
        changed, maximum, maximum_frame, example = 0, 0.0, None, None
        for index, (left, right) in enumerate(zip(before, after)):
            a, b = left, right
            for key in field:
                a, b = a[key], b[key]
            if a != b:
                changed += 1
                delta = max(abs(x - y) for x, y in zip(a, b)) if isinstance(a, list) else abs(a - b)
                if delta > maximum:
                    maximum, maximum_frame, example = delta, index, [a, b]
        output[".".join(field)] = {"changed_frames": changed, "max_absolute_difference": maximum,
                                   "maximum_frame": maximum_frame, "example_old_new": example}
    operational = ("decision", "obstacle", "warning", "nearest", "clear", "monitored", "dlevel",
                   "dets", "warns", "n_points", "rail_lock", "track_center", "ego", "mount_rotation")
    equal = {field: all(a[field] == b[field] for a, b in zip(before, after)) for field in operational}
    receipt = {"status": "HISTORICAL_EXACT_FIELD_MISMATCH_QUANTIFIED_NOT_WAIVED", "frames": 4443,
               "operational_fields_exact": equal, "numerical_differences": output,
               "hypothesis": "The new wrapper explicitly forces Haswell BLAS dispatch; historical full-Falcon execution did not record its dispatch. A fresh immutable9b control with matching explicit environment is required to attribute these differences.",
               "acceptance": "No numerical tolerance was applied. The historical exact-field FAIL remains retained separately.",
               "input_sha256": {str(path): sha(path) for path in [Path(__file__), *paths]}}
    target = HERE / "falcon_default_off/historical_numeric_differences.json"
    target.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"operational_fields_exact": all(equal.values()), "fields": output}))


if __name__ == "__main__":
    main()
