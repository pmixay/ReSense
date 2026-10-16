"""Classify remaining serialized differences without changing the retained comparison."""
from collections import Counter
import json
from pathlib import Path

P = Path(__file__).resolve().parent
S = Path(r"C:\Users\alikh\AppData\Local\Temp\opencode\resense-h4-columns-author-20261016")
R = Path(r"C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-h4-safety-20261016\run-001\replay-sealed-all")


def diff(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for k in sorted(a.keys() | b.keys()) for d in diff(a.get(k), b.get(k), path + "/" + k)]
    return [] if a == b else [dict(path=path, sealed=a, candidate=b)]


result = {}
for bag in ["roundT_doubleT", "squareT_platform_squareT_switch", "ride_1", "ride_3"]:
    counts, examples = Counter(), []
    with (R / (bag + ".jsonl")).open() as rf, (S / "attempt-08-normal/results" / (bag + ".jsonl")).open() as gf:
        for r, g in zip(map(json.loads, rf), map(json.loads, gf), strict=True):
            assert r["frame_id"] == g["frame_id"]
            ds = diff(r["serialized"], g["serialized"])
            counts.update(d["path"] for d in ds)
            if ds and len(examples) < 2:
                examples.append(dict(frame=r["frame_id"], differences=ds))
    result[bag] = dict(paths=dict(counts), examples=examples)
out = P / "normal_diff_details.json"
assert not out.exists()
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
