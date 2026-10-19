#!/usr/bin/env python3
"""Compare the detector on the real walk (frames F0..F1 of a full run) with the injected re-enactments.

    walk_compare.py --real <run.jsonl> --inj <run_s0.jsonl> [...] --spec <walk_seed0.json> --out <json>
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from assoc import associate, load, summary  # noqa: E402

BANDS = [(210, 175), (175, 150), (150, 125), (125, 100)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", required=True)
    ap.add_argument("--inj", nargs="+", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text())
    f0, f1 = spec["control"]["real_frames"]
    shift = spec["control"]["shift"]
    path_inj = spec["targets"][0]["path"]
    path_real = [[f + shift, x, lat] for f, x, lat in path_inj]
    tr = spec["track"]
    res = {"real": summary(associate(load(a.real), path_real, tr, range(f0, f1 + 1)), BANDS), "injected": {}}
    for p in a.inj:
        res["injected"][Path(p).stem] = summary(associate(load(p), path_inj, tr, range(f0 - shift, f1 - shift + 1)), BANDS)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
