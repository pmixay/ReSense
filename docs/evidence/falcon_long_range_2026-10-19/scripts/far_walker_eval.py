#!/usr/bin/env python3
"""Detector outputs on the real far walker (far_walker_labels.json): per 10 m band, the fraction of
covered frames with an associated STOP / any output, and first STOP. ``assoc.py`` association
(2.5 m along, 1.0 m lateral of the labelled path).

    far_walker_eval.py <run.jsonl> [...] --out <json>
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from assoc import associate, load  # noqa: E402

EV = HERE.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lab = json.loads((EV / "far_walker_labels.json").read_text())
    tr = lab["track_reference"]
    res = {}
    for p in a.runs:
        rows = load(p)
        out = {}
        for ep, v in lab["episodes"].items():
            path = v["path"]
            frames = [f for f, _, _ in path]
            A = associate(rows, path, tr, frames)
            bands = {}
            for lo in range(240, 310, 10):
                b = [x for x in A if lo <= x["x"] < lo + 10]
                if b:
                    bands[f"{lo}-{lo + 10}"] = {"frames": len(b), "stop": round(sum(x["stop"] for x in b) / len(b), 3),
                                                "output": round(sum(x["stop"] or x["warn"] for x in b) / len(b), 3)}
            fs = next((x for x in A if x["stop"]), None)
            out[ep] = {"frames": len(A), "stop_frames": sum(x["stop"] for x in A),
                       "output_frames": sum(x["stop"] or x["warn"] for x in A),
                       "first_stop": None if fs is None else [fs["i"], round(fs["x"], 1)], "bands": bands}
        res[Path(p).stem] = out
    Path(a.out).write_text(json.dumps(res, indent=1))
    for k, v in res.items():
        print(k, {ep: (e["stop_frames"], e["output_frames"], e["frames"], {b: (x["stop"], x["output"]) for b, x in e["bands"].items()}) for ep, e in v.items()})


if __name__ == "__main__":
    main()
