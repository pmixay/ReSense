#!/usr/bin/env python3
"""Run clean/dust paired measurements on complete node-decoded recordings.

Each level gets a fresh detector and every source frame. The clean rail reference
places the simulation; no augmentation truth enters runtime health/decisions.
Use --detector-root for an immutable baseline export. Raw results are gzip JSONL.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
EMPTY = ["doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
         "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--detector-root", type=Path, default=ROOT)
    p.add_argument("--bags", default=",".join(EMPTY + ["doubleT_obstacle", "cloud_with_fake_obj"]))
    p.add_argument("--levels", default="clean,low,medium,high")
    p.add_argument("--seed", type=int, default=20261018)
    p.add_argument("--set", action="append", default=[])
    a = p.parse_args()
    if not a.levels.startswith("clean"):
        p.error("clean must be first to provide the unchanged placement reference")
    for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[k] = "1"
    sys.path.insert(0, str(a.detector_root.resolve()))
    import numpy as np
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import Frame, axis_matrix
    from resense.metrics import _assign_detections, gt_objects, load_gt
    import yaml
    spec = importlib.util.spec_from_file_location("dust_stress_module", ROOT / "resense/dust.py")
    dust = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = dust
    spec.loader.exec_module(dust)
    a.out.mkdir(parents=True, exist_ok=True)
    sources = {str(f.relative_to(a.detector_root)): hashlib.sha256(f.read_bytes()).hexdigest()
               for f in sorted((a.detector_root / "resense").glob("*.py"))}
    report = {"schema": "dust-battery-v1", "seed": a.seed, "detector_root": str(a.detector_root),
              "source_hashes": sources, "config_overrides": a.set,
              "generator_sha256": hashlib.sha256((ROOT / "resense/dust.py").read_bytes()).hexdigest(),
              "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "cpu_affinity": sorted(os.sched_getaffinity(0)), "recordings": {}}
    for bag in a.bags.split(","):
        folder = a.cache / bag
        meta_path = folder / "meta.json"
        meta = json.loads(meta_path.read_text())
        paths = sorted(folder.glob("f_*.npz"))
        if len(paths) != len(meta) or any(f.name != f"f_{i:05d}.npz" for i, f in enumerate(paths)):
            raise ValueError(f"{bag}: incomplete/misaligned cache")
        labels_path = ROOT / "labels" / f"{bag}.json"
        labels = load_gt(str(labels_path)) if labels_path.exists() else {}
        source_hash = hashlib.sha256(meta_path.read_bytes())
        for path in paths:
            source_hash.update(path.name.encode())
            source_hash.update(hashlib.sha256(path.read_bytes()).digest())
        bag_report = {"cache_sha256": source_hash.hexdigest(), "frames": len(paths), "levels": {}}
        report["recordings"][bag] = bag_report
        clean_rail = []
        for level in a.levels.split(","):
            cfg = DetectorConfig.from_yaml(str(a.detector_root / "configs/default.yaml"))
            cfg.calibration.enabled = True
            for override in a.set:
                key, val = override.split("=", 1)
                section, key = key.split(".", 1)
                setattr(getattr(cfg, section), key, yaml.safe_load(val))
            detector = Detector(cfg)
            rotation = axis_matrix(cfg.sensor).astype(np.float32)
            counts, objects = Counter(), defaultdict(lambda: {"visible_inside_frames": 0, "stop_frames": [],
                                                               "first_stop_frame": None, "first_stop_m": None})
            last_stop = False
            elapsed, rails, last_stamp = [], [], None
            output = a.out / f"{bag}_{level}.jsonl.gz"
            started = time.perf_counter()
            with gzip.open(output, "wt", encoding="utf-8") as fh:
                for i, (path, m) in enumerate(zip(paths, meta)):
                    with np.load(path) as d:
                        fr = Frame(d["xyz"] @ rotation.T, d["inten"],
                                   d["ring"] if m["has_ring"] else None, m["stamp"], m["frame_id"],
                                   {"n_raw": m["n_raw"], "n_near": m["n_near"]})
                    if last_stamp is not None:
                        gap = fr.stamp - last_stamp
                        if gap < -.5 or gap > 30:
                            detector = Detector(cfg)
                        elif gap > 1:
                            detector.reset()
                    last_stamp = fr.stamp
                    audit = None
                    if level != "clean":
                        fr, audit, _ = dust.augment_dust(fr, dust.PRESETS[level], rail_z=clean_rail[i],
                                                       seed=a.seed, frame_index=i)
                        counts["injected_returns"] += audit["added_returns"]
                        counts["attenuated_returns"] += audit["removed_returns"]
                    t0 = time.perf_counter()
                    result = detector.process(fr)
                    elapsed.append((time.perf_counter() - t0) * 1000)
                    row = result.to_dict()
                    row["frame"] = i
                    health = row.get("health") or {}
                    decision = ("STOP" if result.obstacle else "FAULT" if health.get("level") == "error"
                                else "CAUTION" if result.warning or health.get("decision_level", health.get("level")) == "warn"
                                else "GO")
                    row["decision"] = decision
                    row["augmentation"] = audit
                    counts[decision] += 1
                    counts["stop_episodes"] += int(decision == "STOP" and not last_stop)
                    counts["degraded_frames"] += int(health.get("decision_level", health.get("level")) in ("warn", "error"))
                    last_stop = decision == "STOP"
                    rail = float(result.track.rail_z(np.array([20.]))[0])
                    rails.append(rail)
                    visible = [r for r in labels.get(f"{i:05d}", []) if r.get("n_points", 1) > 0 and r.get("plausible", True)]
                    gt = gt_objects(visible)
                    assignment = _assign_detections(row.get("detections", []), gt)
                    row["matched_labels"] = [visible[k].get("label", "obstacle") for k in assignment]
                    for gi, label in enumerate(visible):
                        if not label.get("in_gauge", True):
                            continue
                        obj = objects[label.get("label", "obstacle")]
                        obj["visible_inside_frames"] += 1
                        if gi in assignment:
                            obj["stop_frames"].append(i)
                            if obj["first_stop_frame"] is None:
                                obj["first_stop_frame"] = i
                                obj["first_stop_m"] = float(label["distance"])
                    fh.write(json.dumps(row, separators=(",", ":")) + "\n")
            if level == "clean":
                clean_rail = rails
            measurement = {**dict(counts), "objects": dict(objects), "frames": len(paths),
                           "timing_ms": {"median": float(np.median(elapsed)), "p95": float(np.percentile(elapsed, 95))},
                           "wall_seconds": time.perf_counter() - started,
                           "raw_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
            if level != "clean":
                clean = bag_report["levels"]["clean"]
                measurement["extra_stop_episodes"] = counts["stop_episodes"] - clean.get("stop_episodes", 0)
                if bag in EMPTY:
                    measurement["empty_episode_acceptance"] = measurement["extra_stop_episodes"] <= 1
                for name, obj in objects.items():
                    base = clean["objects"].get(name, {})
                    obj["lost_clean_stop_frames"] = sorted(set(base.get("stop_frames", [])) - set(obj["stop_frames"]))
                    old = base.get("first_stop_m")
                    obj["first_stop_ratio"] = obj["first_stop_m"] / old if old and obj["first_stop_m"] is not None else None
            bag_report["levels"][level] = measurement
            (a.out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
            print(f"{bag}/{level}: {dict(counts)} p95={measurement['timing_ms']['p95']:.1f}ms", flush=True)


if __name__ == "__main__":
    main()
