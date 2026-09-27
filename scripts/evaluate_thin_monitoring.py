#!/usr/bin/env python3
"""Measure preregistered M2 without changing the production detector."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from resense import _native  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import frame_from_compact  # noqa: E402
from resense.io import load_cache_stamps  # noqa: E402
from resense.metrics import load_gt  # noqa: E402
from scripts.eval_real import load_cfg  # noqa: E402
from scripts.evaluate_monitoring_candidate import candidate_row, invariant  # noqa: E402
from scripts.quality_acceptance import EMPTY, aligned, monitoring_cost, read_rows  # noqa: E402
from scripts.score_clear_distance import overclaim  # noqa: E402


def thin_distance(clusters, min_gauge: int, trust_range: float, n_acc: int) -> float | None:
    if n_acc != 1:
        return None
    distances = [float(c.distance) for c in clusters
                 if c.thin and not c.kind and c.zone == "gauge" and not c.reason
                 and c.n_gauge >= min_gauge and math.isfinite(c.distance)
                 and 0 <= c.distance <= trust_range]
    return min(distances, default=None)


class ThinObserver(Detector):
    def _cluster(self, cand, n_acc, valid, floor_valid, straddle, near):
        self.monitoring_trust_range = min(valid, floor_valid)
        return super()._cluster(cand, n_acc, valid, floor_valid, straddle, near)

    def monitoring_distance(self, result):
        return thin_distance(self._thin, self.cfg.cluster.gauge_min_points,
                             self.monitoring_trust_range, result.n_accumulated)


def thin_row(original, distance):
    row = candidate_row(original, distance)
    row["health"]["thin_cluster_distance"] = row["health"].pop("raw_profile_distance")
    if row["health"].get("monitoring_status") == "unresolved_envelope_returns":
        row["health"]["monitoring_status"] = "unresolved_thin_cluster"
        row["health"]["messages"][-1] = "supported thin cluster limits the monitored estimate"
    return row


def evaluate(name, cache_root, reference, out):
    cfg = load_cfg(str(ROOT / "configs/default.yaml"), [])
    det = ThinObserver(cfg)
    cache = cache_root / ("new_data" if name.startswith("new_data_") else name)
    stamps = load_cache_stamps(str(cache))
    expected, receipt = read_rows(reference, name)
    # The frozen capture defines the same ride piece boundaries and frame order.
    originals, candidates = [], []
    with (out / f"{name}.jsonl").open("w") as stream:
        for old in expected:
            frame_id = old["frame_id"]
            if frame_id not in stamps or abs(stamps[frame_id] - old["stamp"]) > 1e-6:
                raise ValueError(f"{name}:{frame_id}: missing or changed input timestamp")
            frame = frame_from_compact(np.load(cache / f"{frame_id}.npy"), cfg.sensor,
                                       stamp=stamps[frame_id], frame_id=frame_id)
            result = det.process(frame)
            row = result.to_dict()
            row.update(frame=old["frame"], frame_id=frame_id)
            if invariant(row) != invariant(old):
                raise ValueError(f"Observer changed frozen output at {name}:{frame_id}")
            candidate = thin_row(row, det.monitoring_distance(result))
            if candidate["clear_distance"] > row["clear_distance"]:
                raise ValueError("M2 increased an estimate; overclaim nonregression violated")
            originals.append(row)
            candidates.append(candidate)
            stream.write(json.dumps(candidate) + "\n")
    aligned(originals, candidates)
    entry = {"frames": len(originals), "upstream_identical": True, "reference": receipt,
             "no_estimate_increased": True, "monitoring_cost": monitoring_cost(originals, candidates)}
    if name == "cloud_with_fake_obj":
        gt = load_gt(str(ROOT / "labels/cloud_with_fake_obj.json"))
        entry["reference_overclaim"] = overclaim(originals, gt)
        entry["candidate_overclaim"] = overclaim(candidates, gt)
    return entry, originals, candidates


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    assert _native.enabled(), "Use the native path of the frozen gate"
    a.out.mkdir(parents=True, exist_ok=True)
    report = {"candidate": "M2", "production_changed": False, "native": _native.status(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "helper_sha256": hashlib.sha256((ROOT / "scripts/evaluate_monitoring_candidate.py").read_bytes()).hexdigest(),
              "recordings": {}}

    def save():
        (a.out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")

    def run(name):
        entry, before, after = evaluate(name, a.cache, a.reference, a.out)
        report["recordings"][name] = entry
        save()
        print(name, json.dumps(entry), flush=True)
        return before, after

    for name in ("cloud_with_fake_obj", *EMPTY):
        run(name)
    cost = all(report["recordings"][n]["monitoring_cost"]["passed"] for n in EMPTY)
    target = report["recordings"]["cloud_with_fake_obj"]["candidate_overclaim"]["totals"]
    benefit = target["target"] < 54 and target["target_by_decision"].get("GO", 0) < 46
    report.update(empty_cost_passed=cost, partial_benefit_passed=benefit,
                  zero_GO_overclaim_diagnostic_passed=target["target_by_decision"].get("GO", 0) == 0,
                  proceed_to_ride=cost and benefit)
    save()
    if not cost or not benefit:
        report["disposition"] = "rejected; registered early gate failed"
        save()
        return
    run("doubleT_obstacle")
    before, after = [], []
    for i in range(8):
        b, c = run(f"new_data_{i}")
        before.extend(b)
        after.extend(c)
    report["ride_monitoring_cost"] = monitoring_cost(before, after)
    report["disposition"] = ("eligible for independent review as partial improvement"
                              if report["ride_monitoring_cost"]["passed"] else "rejected; ride cost failed")
    save()


if __name__ == "__main__":
    main()
