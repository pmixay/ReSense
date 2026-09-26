#!/usr/bin/env python3
"""Evaluate preregistered M1 as an observer of the unchanged detector, never ship it here."""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from resense import _native  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import frame_from_compact  # noqa: E402
from resense.gauge import point_in_polygon  # noqa: E402
from resense.io import load_cache_stamps  # noqa: E402
from resense.metrics import load_gt  # noqa: E402
from scripts.eval_real import load_cfg  # noqa: E402
from scripts.quality_acceptance import EMPTY, aligned, monitoring_cost  # noqa: E402
from scripts.score_clear_distance import overclaim  # noqa: E402


class MonitoringObserver(Detector):
    def _corridor(self, xyz, intensity):
        result = super()._corridor(xyz, intensity)
        candidates = result[0]
        inside = point_in_polygon(candidates.dy, candidates.h, self.cfg.gauge.profile)
        self.raw_profile_distance = float(candidates.xyz[inside, 0].min()) if inside.any() else None
        return result


def candidate_row(original: dict, distance: float | None) -> dict:
    row = copy.deepcopy(original)
    previous = float(row["clear_distance"])
    cap = min(previous, max(0.0, distance)) if distance is not None else previous
    row["clear_distance"] = round(cap, 1)
    row["health"]["clear_distance"] = row["clear_distance"]
    row["health"]["raw_profile_distance"] = distance
    if previous - cap > 0.5:
        row["health"]["monitoring_status"] = "unresolved_envelope_returns"
        if row["health"]["level"] != "error":
            row["health"]["level"] = "warn"
            row["health"]["decision_level"] = "warn"
        row["health"]["messages"].append("raw envelope returns limit the monitored estimate")
    return row


def invariant(row: dict) -> dict:
    out = copy.deepcopy(row)
    out.pop("timing_ms", None)
    out["health"].pop("latency_p95_ms", None)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    assert _native.enabled(), "Use the same native path as the frozen gate"
    args.out.mkdir(parents=True, exist_ok=True)
    report = {"candidate": "M1", "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "native": _native.status(), "recordings": {}, "parameters_changed": False}
    for name in ("cloud_with_fake_obj", *EMPTY):
        cfg = load_cfg(str(ROOT / "configs/default.yaml"), [])
        det = MonitoringObserver(cfg)
        cache = args.cache / name
        stamps = load_cache_stamps(str(cache))
        files = sorted(cache.glob("*.npy"))
        with gzip.open(args.reference / f"{name}.jsonl.gz", "rt") as f:
            expected = [json.loads(line) for line in f if line.strip()]
        if len(files) != len(expected):
            raise ValueError(f"{name}: cache and frozen capture frame counts differ")
        originals, candidates = [], []
        with (args.out / f"{name}.jsonl").open("w") as stream:
            for index, path in enumerate(files):
                if path.stem not in stamps:
                    raise ValueError(f"Missing stamp: {path.stem}")
                frame = frame_from_compact(np.load(path), cfg.sensor, stamp=stamps[path.stem], frame_id=path.stem)
                row = det.process(frame).to_dict()
                row.update(frame=index, frame_id=path.stem)
                if invariant(row) != invariant(expected[index]):
                    raise ValueError(f"Observer changed frozen output at {name}:{index}")
                candidate = candidate_row(row, det.raw_profile_distance)
                originals.append(row)
                candidates.append(candidate)
                stream.write(json.dumps(candidate) + "\n")
        aligned(originals, candidates)
        entry = {"frames": len(originals), "upstream_identical": True,
                 "monitoring_cost": monitoring_cost(originals, candidates)}
        if name == "cloud_with_fake_obj":
            gt = load_gt(str(ROOT / "labels/cloud_with_fake_obj.json"))
            entry["reference_overclaim"] = overclaim(originals, gt)
            entry["candidate_overclaim"] = overclaim(candidates, gt)
        report["recordings"][name] = entry
        (args.out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
        print(name, json.dumps(entry), flush=True)
    report["empty_cost_passed"] = all(report["recordings"][name]["monitoring_cost"]["passed"] for name in EMPTY)
    report["zero_GO_overclaim_diagnostic_passed"] = (
        report["recordings"]["cloud_with_fake_obj"]["candidate_overclaim"]["totals"]["target_by_decision"].get("GO", 0) == 0)
    report["proceed_to_ride"] = report["empty_cost_passed"] and report["zero_GO_overclaim_diagnostic_passed"]
    (args.out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
