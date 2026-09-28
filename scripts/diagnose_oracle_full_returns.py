#!/usr/bin/env python3
"""Registered all-return physical translation and held/recomputed strict membership."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from resense.detector import Detector  # noqa: E402
from scripts.diagnose_oracle_accumulation import evaluate, inputs, oracle_speed  # noqa: E402
from scripts.diagnose_range_metric import sha  # noqa: E402


def translate_window(history, displacement, min_range):
    """Translate raw clouds identically, retaining capture flags and source identities."""
    parts = {key: [] for key in ("xyz", "intensity", "target", "all_source", "origins", "strict", "rail")}
    current_frame = history[-1]["frame"]
    for item in history:
        moved = item["xyz"].copy()
        moved[:, 0] -= displacement - item["displacement"]
        keep = np.ones(len(moved), bool) if item["frame"] == current_frame else moved[:, 0] >= min_range
        parts["xyz"].append(moved[keep])
        parts["origins"].append(np.full(int(keep.sum()), item["frame"], np.int64))
        for key in ("intensity", "target", "all_source", "strict", "rail"):
            parts[key].append(item[key][keep])
    return {key: np.concatenate(value) for key, value in parts.items()}


def run(args):
    detector = Detector()
    cfg = detector.cfg
    stamps, positions, history, rows, provenance = [], [], [], [], []
    displacement = 0.
    for item in inputs(args):
        frame, k = item["cloud"], item["frame"]
        stamps.append(frame.stamp)
        positions.append(item["position"])
        speed, raw_speed = oracle_speed(stamps, positions)
        dt = stamps[-1] - stamps[-2] if len(stamps) > 1 else .1
        displacement += (speed or 0.) * dt
        detector.track = item["track"]
        current = detector._corridor(frame.xyz, frame.intensity)[0]
        strict, rail = np.zeros(frame.n, bool), np.zeros(frame.n, bool)
        strict[current.idx], rail[current.idx] = current.in_gauge, current.rail()
        target, all_source = np.zeros(frame.n, bool), np.zeros(frame.n, bool)
        target[item["target"]], all_source[item["all_source"]] = True, True
        history.append({"frame": k, "displacement": displacement, "xyz": frame.xyz,
                        "intensity": frame.intensity, "target": target, "all_source": all_source,
                        "strict": strict, "rail": rail})
        history = history[-3:]
        row = {"frame": k, "source_distance_m": item["position"], "speed_raw_mps": raw_speed,
               "speed_supplied_mps": speed, "dt_s": dt, "variants": []}
        for window in (2, 3):
            selected = history[-window:]
            union = translate_window(selected, displacement, cfg.accumulation.min_range)
            cand, _, _, _, (_, valid, floor_valid) = detector._corridor(union["xyz"], union["intensity"])
            indices = cand.idx.copy()
            source = union["target"][indices]
            origins = union["origins"][indices]
            background = ~union["all_source"][indices]
            cand.idx = np.where(origins == k, indices, -1)
            for flags in ("historical", "recomputed"):
                # subset creates independent arrays so neither flag variant mutates the other.
                variant = cand.subset(np.ones(len(cand), bool))
                if flags == "historical":
                    variant.in_gauge = union["strict"][indices]
                    variant.in_rail = union["rail"][indices]
                for pairing in ("present", "background"):
                    keep = np.ones(len(cand), bool) if pairing == "present" else background
                    record = evaluate(variant.subset(keep), source[keep], origins[keep], cfg,
                                      len(selected), valid, floor_valid, bounded=True)
                    record.update(mode=f"physical_{pairing}_{flags}", window=window, bounded=True,
                                  full_union_source_points=int(union["target"].sum()),
                                  current_corridor_source_points=int(source.sum()),
                                  source_strict_historical=int((source & union["strict"][indices]).sum()),
                                  source_strict_recomputed=int((source & cand.in_gauge).sum()))
                    row["variants"].append(record)
        rows.append(row)
        provenance.append(item["provenance"])
        print(f"full-return frame {k}", flush=True)
    return {"mode": "all_return_oracle_X_translation_historical_geometry_conditional_clustering",
            "protocol_sha256": sha(ROOT / "docs/ORACLE_FULL_RETURN_PROTOCOL_2026-09-28.md"),
            "observer_sha256": sha(__file__),
            "helper_sha256": sha(ROOT / "scripts/diagnose_oracle_accumulation.py"),
            "source_hashes": {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / "resense").glob("*.py"))},
            "limitations": ["Oracle source-relative motion, not vehicle odometry or full rigid pose.",
                            "Rounded historical geometry; no current sequential detector parity.",
                            "Full raw return union includes points omitted by the production candidate buffer.",
                            "No tracker or low-object stage; gauge candidates are not confirmed STOPs.",
                            "Previously inspected organizer synthetic approach; no unseen validation."],
            "inputs": provenance, "rows": rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", required=True)
    p.add_argument("--cache", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    result = run(args)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(result, separators=(",", ":")).encode(), mtime=0))


if __name__ == "__main__":
    main()
