#!/usr/bin/env python3
"""Frozen, paired transplantation of organizer points onto seen empty backgrounds.

This measures sensitivity to novel combinations, not real hold-out recall. Coordinates,
range sampling and heights come from the source sensor; rail membership and background
motion are not surveyed. No detector track fit supplies placement or matching labels.

  python scripts/novel_placement_eval.py extract --bag DATA/cloud_with_fake_obj --out DATA/objects
  python scripts/novel_placement_eval.py plan --source DATA/objects --cache DATA/cache --out plan.json
  python scripts/novel_placement_eval.py run --plan plan.json --out results.json

Commit the plan before running. It pins detector/config, evaluator, source arrays, background
frame bytes and timestamps. Missing data or changed inputs fail closed. Do not tune on results.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from resense.config import DetectorConfig, SensorConfig  # noqa: E402
from resense.frame import Frame, frame_from_compact, sensor_to_vehicle  # noqa: E402
from resense.io import _natural_key, load_cache_stamps  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OBJECTS = ("small_center", "small_on_rail", "big_above", "thin_hanging")
BACKGROUNDS = ("doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
               "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch", "new_data")
OFFSETS = (-0.65, 0.0, 0.65)
WARMUP = 30
LIMITATIONS = [
    "Novel synthetic combinations on backgrounds and organizer object shapes already inspected.",
    "Fixed sensor-axis placement: no independent surveyed rail-envelope ground truth.",
    "Source approach and target background motion differ; this is a sensitivity experiment.",
    "Original X/Z and point counts are retained before angular occlusion; no scaling or densification.",
    "Lateral-only shifts do not recast the object on the destination sensor ray grid.",
    "A 0.1-degree angular-cell z-buffer approximates occlusion; it is not a calibrated ray caster.",
    "Source heights may not rest on the destination bed; no real material or long-range recall claim.",
]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def code_hashes():
    paths = sorted((ROOT / "resense").glob("*.py")) + [
        ROOT / "native/resense_native.cpp", Path(__file__).resolve()]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def extract(bag, out):
    # The zero delimiter is absent from quantized frame caches: extraction needs the raw bag.
    from rosbags.rosbag2 import Reader
    from rosbags.typesys import Stores, get_typestore
    from label_fake_objects import OBJECTS as organizer_objects, group_frame, link_tracks
    from resense.pointcloud import pointcloud2_to_structured

    per_frame, groups, stamps = {}, {}, {}
    ts = get_typestore(Stores.ROS2_HUMBLE)
    with Reader(Path(bag)) as reader:
        conns = [c for c in reader.connections if c.msgtype == "sensor_msgs/msg/PointCloud2"]
        for k, (conn, stamp, raw) in enumerate(reader.messages(connections=conns)):
            arr = pointcloud2_to_structured(ts.deserialize_cdr(raw, conn.msgtype))
            xyz = np.column_stack([arr[n].ravel() for n in ("x", "y", "z")])
            zero = np.flatnonzero((xyz == 0).all(axis=1))
            if not len(zero):
                raise ValueError(f"frame {k}: missing organizer zero delimiter")
            start = int(zero[-1]) + 1
            xyz = sensor_to_vehicle(xyz[start:], SensorConfig())
            intensity = arr["intensity"].ravel()[start:]
            r = np.linalg.norm(xyz, axis=1)
            keep = np.isfinite(xyz).all(axis=1) & (r >= 2.5) & (r <= 250)
            xyz, intensity = xyz[keep], intensity[keep]
            per_frame[k] = np.column_stack([xyz, intensity]).astype(np.float32)
            groups[k] = [(float(xyz[g, 0].min()), g) for g in group_frame(xyz, 8.0)]
            stamps[k] = stamp / 1e9
            if k % 200 == 0:
                print(f"extracted source frame {k}", flush=True)
    tracks = sorted((t for t in link_tracks(groups) if len(t) >= 5), key=lambda t: t[-1][0])
    if len(tracks) != len(organizer_objects):
        raise ValueError(f"expected ten organizer objects, got {len(tracks)}")
    arrays, manifest = {}, {}
    for spec, track in zip(organizer_objects, tracks):
        label = spec[0]
        if label not in OBJECTS:
            continue
        chosen = [(k, gi) for k, gi, d in track if 15.0 <= d <= 80.0]
        if len(chosen) < 3:
            raise ValueError(f"{label}: fewer than three source frames at 15–80 m")
        by_frame = dict(chosen)
        ids = list(range(chosen[0][0], chosen[-1][0] + 1))
        for k in ids:
            arrays[f"{label}_{k}"] = (per_frame[k][groups[k][by_frame[k]][1]] if k in by_frame
                                        else np.zeros((0, 4), dtype=np.float32))
        manifest[label] = {"frames": ids, "stamps": [stamps[k] for k in ids], "size": spec[2]}
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "points.npz", **arrays)
    write_json(out / "manifest.json", {"objects": manifest, "source_bag": str(Path(bag).resolve()),
               "raw_hashes": {p.name: sha(p) for p in sorted(Path(bag).glob("*.db3"))},
               "points_sha256": sha(out / "points.npz"), "coordinates": "fixed sensor axis -y,+x,+z"})


def make_plan(source, cache, out, config=None):
    source, cache = Path(source).resolve(), Path(cache).resolve()
    manifest = json.loads((source / "manifest.json").read_text())
    cfg = DetectorConfig.from_yaml(config) if config else DetectorConfig()
    # Extraction's sensor coordinate convention must remain fixed.
    if asdict(cfg.sensor) != asdict(SensorConfig()):
        raise ValueError("this protocol requires the default fixed sensor-axis convention")
    cases, inputs = [], {}
    for bag in BACKGROUNDS:
        files = sorted((cache / bag).glob("*.npy"), key=lambda p: _natural_key(str(p)))
        stamps = load_cache_stamps(str(cache / bag))
        for oi, label in enumerate(OBJECTS):
            ids = manifest["objects"][label]["frames"]
            start = (2040 if bag == "new_data" else 40) + oi * 11
            chosen = files[start:start + WARMUP + len(ids)]
            if len(chosen) != WARMUP + len(ids):
                raise ValueError(f"{bag}: incomplete background window for {label}")
            times = [stamps.get(p.stem) for p in chosen]
            if any(t is None for t in times) or any(not 0 < b - a < 0.5 for a, b in zip(times, times[1:])):
                raise ValueError(f"{bag}: missing or discontinuous background timestamps")
            # All frame identities and bytes are committed before detector evaluation.
            for p, stamp in zip(chosen, times):
                if str(p) not in inputs:
                    inputs[str(p)] = {"sha256": sha(p), "stamp": stamp}
            for lateral in OFFSETS:
                cases.append({"bag": bag, "object": label, "lateral_m": lateral,
                              "background": [str(p) for p in chosen], "source_frames": ids})
    plan = {"protocol": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
            "limitations": LIMITATIONS, "config": asdict(cfg),
            "code_sha256": code_hashes(), "source": str(source),
            "source_manifest_sha256": sha(source / "manifest.json"),
            "source_points_sha256": sha(source / "points.npz"), "inputs": inputs,
            "warmup_frames": WARMUP, "angular_cell_deg": 0.1, "cases": cases,
            "policy": "One frozen run. Keep every case. No score threshold, exclusions, or tuning after inspection."}
    write_json(out, plan)
    return plan


def transplant(background, source, lateral, angular_cell_deg=0.1):
    """Rigid lateral move, retaining X/Z and intensity; remove occluded returns on both sides."""
    pts = source[:, :3].copy()
    if not len(pts):
        return background, pts
    pts[:, 1] += lateral - 0.5 * (pts[:, 1].min() + pts[:, 1].max())
    xyz = np.concatenate([background.xyz, pts])
    r = np.linalg.norm(xyz, axis=1)
    angles = np.degrees(np.column_stack([np.arctan2(xyz[:, 1], xyz[:, 0]),
                                         np.arctan2(xyz[:, 2], np.hypot(xyz[:, 0], xyz[:, 1]))]))
    cells = np.rint(angles / angular_cell_deg).astype(np.int64)
    n = background.n
    # Only cells in the object's angular bounding box can occlude either side.
    near = np.flatnonzero(((cells[:n] >= cells[n:].min(axis=0)) &
                           (cells[:n] <= cells[n:].max(axis=0))).all(axis=1))
    _, inv = np.unique(np.concatenate([cells[near], cells[n:]]), axis=0, return_inverse=True)
    bg_min, obj_min = np.full(inv.max() + 1, np.inf), np.full(inv.max() + 1, np.inf)
    m = len(near)
    np.minimum.at(bg_min, inv[:m], r[near])
    np.minimum.at(obj_min, inv[m:], r[n:])
    keep_bg = np.ones(n, dtype=bool)
    keep_bg[near] = r[near] <= obj_min[inv[:m]]
    keep_obj = r[n:] <= bg_min[inv[m:]]
    frame = Frame(np.concatenate([background.xyz[keep_bg], pts[keep_obj]]),
                  np.concatenate([background.intensity[keep_bg], source[keep_obj, 3]]),
                  stamp=background.stamp, frame_id=background.frame_id, meta=dict(background.meta))
    return frame, pts[keep_obj]


def target_match(detections, xyz):
    """Match physical coordinates, independent of detector lateral/rail coordinates."""
    if not len(xyz):
        return False
    lo, hi = xyz.min(axis=0), xyz.max(axis=0)
    distance = float(lo[0])
    tol = max(2.0, 0.03 * distance) + 0.5 * float(hi[0] - lo[0])
    for d in detections:
        center = np.asarray(d["center"])
        if (abs(d["distance"] - distance) <= tol and
                lo[1] - 0.5 <= center[1] <= hi[1] + 0.5 and
                lo[2] - 0.5 <= center[2] <= hi[2] + 0.5):
            return True
    return False


def validate_plan(plan):
    if plan["code_sha256"] != code_hashes():
        raise ValueError("detector or evaluator changed after preregistration; keep the original plan and explain a new one")
    source = Path(plan["source"])
    for name, key in (("manifest.json", "source_manifest_sha256"), ("points.npz", "source_points_sha256")):
        if sha(source / name) != plan[key]:
            raise ValueError(f"source changed: {name}")
    for path, spec in plan["inputs"].items():
        if sha(path) != spec["sha256"]:
            raise ValueError(f"background changed: {path}")


def run(plan_path, out):
    from resense.detector import Detector
    plan = json.loads(Path(plan_path).read_text())
    validate_plan(plan)
    points = np.load(Path(plan["source"]) / "points.npz")
    cfg = DetectorConfig.from_dict(plan["config"])
    cases = []
    for ci, case in enumerate(plan["cases"]):
        control, injected = Detector(cfg), Detector(cfg)
        rows = []
        for k, path in enumerate(case["background"]):
            frame = frame_from_compact(np.load(path), cfg.sensor, stamp=plan["inputs"][path]["stamp"])
            base = control.process(frame).to_dict()
            j = k - plan["warmup_frames"]
            source = (points[f"{case['object']}_{case['source_frames'][j]}"] if j >= 0
                      else np.zeros((0, 4), dtype=np.float32))
            augmented, visible = transplant(frame, source, case["lateral_m"], plan["angular_cell_deg"])
            result = injected.process(augmented).to_dict()
            if j < 0:
                continue
            hit = target_match(result["detections"], injected.calib.apply(visible))
            base_hit = target_match(base["detections"], control.calib.apply(visible))
            rows.append({"frame": Path(path).name, "source_frame": case["source_frames"][j],
                         "source_points": len(source), "visible_points": len(visible),
                         "nearest_sensor_x_m": float(visible[:, 0].min()) if len(visible) else None,
                         "target_matched": hit, "control_target_matched": base_hit,
                         "injected_stop": result["obstacle"], "control_stop": base["obstacle"]})
        record = {k: case[k] for k in ("bag", "object", "lateral_m")}
        record.update(visible_frames=sum(r["visible_points"] > 0 for r in rows),
                      target_matched_frames=sum(r["target_matched"] for r in rows),
                      injected_only_matched_frames=sum(r["target_matched"] and not r["control_target_matched"] for r in rows),
                      control_matched_frames=sum(r["control_target_matched"] for r in rows), rows=rows)
        record["first_matched_sensor_x_m"] = max(
            (r["nearest_sensor_x_m"] for r in rows if r["target_matched"]), default=None)
        cases.append(record)
        print(f"case {ci + 1}/{len(plan['cases'])}: {case['bag']} {case['object']} {case['lateral_m']}", flush=True)
    summary = {key: sum(c[key] for c in cases) for key in
               ("visible_frames", "target_matched_frames", "injected_only_matched_frames", "control_matched_frames")}
    summary["cases_with_target_match"] = sum(c["target_matched_frames"] > 0 for c in cases)
    summary["cases"] = len(cases)
    write_json(out, {"plan_sha256": sha(plan_path), "limitations": plan["limitations"],
                     "summary": summary, "cases": cases})


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("extract")
    p.add_argument("--bag", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--source", required=True)
    p.add_argument("--cache", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--config")
    p = sub.add_parser("run")
    p.add_argument("--plan", required=True)
    p.add_argument("--out", required=True)
    args = parser.parse_args()
    if args.command == "extract":
        extract(args.bag, args.out)
    elif args.command == "plan":
        make_plan(args.source, args.cache, args.out, args.config)
    else:
        run(args.plan, args.out)


if __name__ == "__main__":
    main()
