#!/usr/bin/env python3
"""P4 capped-top physical counterexample and controls, with raw per-frame outputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
import raycast as rc


def scene(raise_, distance, top):
    rr = lambda x: np.where((x >= 32) & (x <= 70), raise_, 0.0)  # noqa: E731
    head = rc.FLOOR + 0.18 + raise_
    boxes = [] if top is None else [(distance, distance + 0.3, rc.AY - 0.15, rc.AY + 0.15,
                                    rc.FLOOR, head + top)]
    return rc.frame(rail_raise=rr, boxes=boxes), head


def run(raise_, top, margin, moving=False):
    cfg = DetectorConfig()
    cfg.lowobj.local_rail_margin = margin
    det = Detector(cfg)
    rows = []
    fixed, head = scene(raise_, 40.0, top)
    for k in range(45 if moving else 12):
        distance = 58.0 - 0.8 * k if moving else 40.0
        fr, head = scene(raise_, distance, top) if moving else (fixed, head)
        res = det.process(Frame(xyz=fr.xyz, intensity=fr.intensity, stamp=0.1 * k))
        matched = [d for d in res.detections if abs(d.distance - distance) < 1.0 and abs(d.center[1] - rc.AY) < 0.5]
        rows.append({"frame": k, "true_distance": distance, "matched_stop": bool(matched),
                     "rail_model_error": float(det.track.rail_z(distance)) - head,
                     "result": res.to_dict()})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    out = {}
    for raise_ in (0.0, 0.18, 0.20):
        for top in (None, 0.12, 0.17, 0.20, 0.25):
            for margin in (0.0, 0.01):
                key = f"stationary/raise{raise_}/top{top}/margin{margin}"
                out[key] = run(raise_, top, margin)
                print(key, sum(r["matched_stop"] for r in out[key]), flush=True)
    for margin in (0.0, 0.01):
        key = f"moving/raise0.18/top0.17/margin{margin}"
        out[key] = run(0.18, 0.17, margin, moving=True)
        print(key, [r["true_distance"] for r in out[key] if r["matched_stop"]], flush=True)
    a.out.write_text(json.dumps(out) + "\n")


if __name__ == "__main__":
    main()
