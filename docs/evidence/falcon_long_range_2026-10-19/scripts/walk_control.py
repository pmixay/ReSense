#!/usr/bin/env python3
"""Positive control 2 (detector behaviour): the real person's reviewed walk, frames F0..F1 of the
recording, re-enacted by the person-like target on the empty frames F0-SHIFT.. (same along/lateral
path from the anchors, same timing). Writes the injection specs; ``walk_compare.py`` compares the
detector's person outputs (first warning, first STOP, STOP fraction per band) with the real run.

    walk_control.py <out_dir> [--f0 2290 --f1 3200 --shift 1990 --seeds 3]
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
import os  # noqa: E402
REPO = Path(os.environ.get("RESENSE_REPO", HERE.parents[3]))


def walk_path(f0, f1):
    cal = json.loads((HERE.parent / "person_calibration.json").read_text())
    rows = sorted((r for r in cal["rows"] if r["episode"].startswith("main")), key=lambda r: r["frame"])
    return [[r["frame"], r["x"], r["lat"]] for r in rows if f0 - 25 <= r["frame"] <= f1 + 25]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--f0", type=int, default=2290)
    ap.add_argument("--f1", type=int, default=3200)
    ap.add_argument("--shift", type=int, default=1990)
    ap.add_argument("--seeds", type=int, default=3)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cal = json.loads((HERE.parent / "person_calibration.json").read_text())
    person = json.loads((HERE.parent / "person_model.json").read_text())
    path = [[f - a.shift, x, lat] for f, x, lat in walk_path(a.f0, a.f1)]
    for s in range(a.seeds):
        tgt = {k: person[k] for k in ("size", "bottom", "fill", "rho", "intensity")}
        tgt.update({"from": a.f0 - a.shift, "to": a.f1 - a.shift + 1, "path": path})
        spec = {"track": cal["track"], "seed": 7000 + s, "targets": [tgt],
                "control": {"real_frames": [a.f0, a.f1], "shift": a.shift}}
        (out / f"walk_seed{s}.json").write_text(json.dumps(spec, indent=1))
    print(out)


if __name__ == "__main__":
    main()
