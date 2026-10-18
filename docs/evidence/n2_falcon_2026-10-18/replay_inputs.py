"""Replay N2 input variants against an explicit immutable source tree.

Cached inputs retain original frame order; no sampling or output-derived labels.
Timings on a shared host are diagnostic, not an isolated performance acceptance.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(variable, "1")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--suite",
        choices=("baseline", "orientation", "fields", "proxy", "falcon"),
        required=True,
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--compact-split", type=int,
                        help="read one complete ride split directly from the compact gate cache")
    parser.add_argument(
        "--upright-only",
        action="store_true",
        help="run the supported 8 auto-search mappings",
    )
    parser.add_argument("--replay-frames", type=int, default=0, help="explicit default-off startup replay candidate")
    args = parser.parse_args()
    os.environ["RESENSE_REPO"] = str(args.source)
    sys.path[:0] = [str(args.source), str(args.source / "ros2_ws/src/resense_ros")]
    import numpy as np

    from resense.calibration import orientation_candidates
    from resense.frame import Frame
    from resense_ros import fastcloud

    judge = load_module(
        "n2_judge",
        args.source / "docs/evidence/judgement_2026-10-13/scripts/judge_runner.py",
    )
    variants = load_module(
        "n2_variants",
        Path(__file__).resolve().parents[3] / "scripts/lidar_input_variants.py",
    )
    compact_paths = None
    input_hashes = {}
    if args.compact_split is None:
        metadata = json.loads((args.cache / "meta.json").read_text())
        metadata_hash = sha(args.cache / "meta.json")
    else:
        cache_io = load_module("n2_cache_io", Path(__file__).resolve().parents[3] / "scripts/cache_io.py")
        cache_io.validate_extended_ride_cache(str(args.cache), [args.compact_split], load_arrays=True)
        prefix = f"new_data_{args.compact_split}_"
        compact_paths = [Path(p) for p in cache_io.cache_files(str(args.cache)) if Path(p).name.startswith(prefix)]
        stamps = cache_io.load_cache_stamps(str(args.cache))
        metadata = [{"stamp": stamps[cache_io.cache_file_stem(p)],
                     "bag_t": stamps[cache_io.cache_file_stem(p)],
                     "topic": "/sensing/lidar/hesai128/pointcloud", "frame_id": "ride_compact",
                     "has_ring": True} for p in compact_paths]
        metadata_hash = sha(args.cache / f"new_data_{args.compact_split}_stamps.json")
        input_hashes = {p.name: sha(p) for p in compact_paths}
    if args.limit:
        metadata = metadata[: args.limit]
    args.out.mkdir(parents=True, exist_ok=True)
    cases = [{"name": "baseline", "kind": "baseline", "overrides": {}}]
    if args.suite == "orientation":
        for i, rotation in enumerate(orientation_candidates(False)):
            upright = bool(abs(rotation[2, 2]) == 1)
            if args.upright_only and not upright:
                continue
            cases.append(
                {
                    "name": f"auto_{i:02d}",
                    "kind": "orientation",
                    "rotation": rotation,
                    "supported_8": upright,
                    "overrides": {"calibration.keep_up_axis": upright},
                }
            )
    elif args.suite == "fields":
        for kind in (
            "no_ring",
            "single_return",
            "half_channels",
            "intensity_unit",
            "intensity_u8",
            "float64_padded",
            "float32_padded",
            "new_identity",
        ):
            cases.append({"name": kind, "kind": kind, "overrides": {}})
    elif args.suite == "proxy":
        cases.append({"name": "falcon_proxy", "kind": "falcon_proxy", "overrides": {}})
    elif args.suite == "falcon":
        cases.append(
            {
                "name": "explicit_ros",
                "kind": "baseline",
                "overrides": {
                    "sensor.forward": "+x",
                    "sensor.left": "+y",
                    "sensor.up": "+z",
                },
            }
        )
        cases.append(
            {
                "name": "native_explicit",
                "kind": "falcon_native",
                "overrides": {
                    "sensor.forward": "+z",
                    "sensor.left": "-y",
                    "sensor.up": "+x",
                },
            }
        )
    for case in cases:
        if args.replay_frames:
            case["overrides"]["calibration.orientation_replay_frames"] = args.replay_frames
        case["replica"] = judge.NodeReplica(
            config=str(args.source / "configs/default.yaml"),
            overrides=case["overrides"],
        )
        case["stream"] = (args.out / (case["name"] + ".jsonl")).open("w")
        case["rows"] = []
    started, cpu = time.monotonic(), time.process_time()
    explicit_equivalence = [True] * 24
    for i, meta in enumerate(metadata):
        if compact_paths is None:
            with np.load(args.cache / f"f_{i:05d}.npz") as data:
                original_xyz, original_intensity = data["xyz"], data["inten"]
                original_ring = data["ring"] if meta["has_ring"] else None
        else:
            from resense.pointcloud import compact_to_xyz, expand_compact16
            compact = expand_compact16(cache_io.load_cache_array(compact_paths[i]))
            xyz = compact_to_xyz(compact)
            radial = np.linalg.norm(xyz, axis=1)
            finite = np.isfinite(radial)
            keep = finite & (radial >= 2.5) & (radial <= 250)
            original_xyz = xyz[keep]
            original_intensity, original_ring = compact["intensity"][keep].astype(np.float32), compact["ring"][keep]
            meta.update(n_raw=int(finite.sum()), n_near=int((finite & (radial < 2.5)).sum()))
        if args.suite == "orientation":
            base_axes = cases[0]["replica"].R_vs
            expected = original_xyz @ base_axes.T
            for k, rotation in enumerate(orientation_candidates(False)):
                transformed = original_xyz @ rotation.T.astype(np.float32)
                resolved_axes = base_axes @ rotation.T.astype(np.float32)
                explicit_equivalence[k] &= bool(
                    np.array_equal(transformed @ resolved_axes.T, expected)
                )
        for case in cases:
            xyz, intensity, ring = original_xyz, original_intensity, original_ring
            rep, kind = case["replica"], case["kind"]
            frame_meta = dict(meta)
            if kind == "orientation":
                xyz = (
                    (xyz @ rep.R_vs.T) @ case["rotation"].T.astype(np.float32)
                ) @ rep.R_vs
            elif kind == "falcon_native":
                # Actual recording is ROS FLU; encode manufacturer's native (up, right, forward).
                xyz = xyz[:, [2, 1, 0]] * np.array([1, -1, 1], dtype=np.float32)
            elif kind == "no_ring":
                ring = None
            elif kind == "single_return":
                _, chosen = np.unique(xyz, axis=0, return_index=True)
                chosen.sort()
                xyz, intensity = xyz[chosen], intensity[chosen]
                ring = None if ring is None else ring[chosen]
            elif kind == "half_channels":
                chosen = np.arange(len(xyz)) % 2 == 0 if ring is None else ring % 2 == 0
                xyz, intensity = xyz[chosen], intensity[chosen]
                ring = None if ring is None else ring[chosen]
            elif kind == "intensity_unit":
                intensity = intensity / 255.0
            elif kind in ("intensity_u8", "float64_padded", "float32_padded"):
                message = variants.field_message(
                    xyz,
                    intensity,
                    ring,
                    coordinate_dtype="f8" if kind == "float64_padded" else "f4",
                    intensity_dtype="u1" if kind == "intensity_u8" else "f4",
                    padded=kind.endswith("padded"),
                )
                xyz, intensity, decoded_ring, _, _ = fastcloud.decode(
                    fastcloud.packed(message), 2.5, 250.0
                )
                ring = decoded_ring if ring is not None else None
            elif kind == "new_identity":
                frame_meta.update(topic="/new_lidar/points", frame_id="new_lidar_frame")
            elif kind == "falcon_proxy":
                chosen = variants.falcon_proxy_indices(xyz @ rep.R_vs.T)
                xyz, intensity, ring = xyz[chosen], intensity[chosen], None
            rep.continuity(
                frame_meta["topic"], frame_meta["frame_id"], frame_meta["stamp"], i
            )
            frame = Frame(
                xyz=(xyz @ rep.R_vs.T).astype(np.float32),
                intensity=intensity,
                ring=ring,
                stamp=frame_meta["stamp"],
                frame_id=frame_meta["frame_id"],
                meta={"n_raw": frame_meta["n_raw"], "n_near": frame_meta["n_near"]},
            )
            start = time.perf_counter()
            result = rep.detector.process(frame, ego_speed=None)
            elapsed = (time.perf_counter() - start) * 1000
            row = judge.record(
                i,
                frame_meta["bag_t"],
                frame_meta["stamp"],
                result,
                0,
                elapsed,
                frame_meta["frame_id"],
                frame_meta["topic"],
            )
            cal = rep.detector.calib
            row.update(
                mount_detail=result.mount,
                track_detail=result.track.to_dict(),
                orientation_confirmed=bool(cal._config_passed),
                input_points=len(xyz),
                mount_rotation=np.asarray(rep.detector.mount_rotation).tolist(),
            )
            if kind == "orientation":
                row["correct_orientation"] = bool(
                    np.allclose(cal._R_orient @ case["rotation"], np.eye(3))
                )
            case["stream"].write(json.dumps(row, allow_nan=False) + "\n")
            case["rows"].append(row)
        if i % 100 == 0:
            print(
                f"{args.cache.name} {args.suite}: {i + 1}/{len(metadata)}, {time.monotonic() - started:.1f}s",
                flush=True,
            )
    reports = []
    baseline = cases[0]["rows"]
    for case in cases:
        case["stream"].close()
        rows = case["rows"]
        correct = [
            r["i"]
            for r in rows
            if r.get("correct_orientation", r["orientation_confirmed"])
        ]
        first = correct[0] if correct else None
        counts = dict(Counter(r["decision"] for r in rows))
        report = {
            key: value
            for key, value in case.items()
            if key not in ("replica", "stream", "rows", "rotation")
        }
        report.update(
            frames=len(rows),
            decisions=counts,
            first_correct_orientation=first,
            unconfirmed_go=[
                r["i"]
                for r in rows
                if not r["orientation_confirmed"] and r["decision"] == "GO"
            ],
            wrong_orientation_go=[
                r["i"]
                for r in rows
                if r.get("correct_orientation") is False and r["decision"] == "GO"
            ],
            decision_mismatch=[
                r["i"] for r, b in zip(rows, baseline) if r["decision"] != b["decision"]
            ],
            lost_baseline_stop=[
                r["i"]
                for r, b in zip(rows, baseline)
                if b["decision"] == "STOP" and r["decision"] != "STOP"
            ],
            first_stop=next((r["i"] for r in rows if r["decision"] == "STOP"), None),
            detect_ms_quantiles=np.percentile(
                [r["detect_ms"] for r in rows], [50, 95, 99]
            ).tolist(),
            output_sha256=sha(args.out / (case["name"] + ".jsonl")),
        )
        if "rotation" in case:
            report["rotation"] = case["rotation"].tolist()
            report["post_adoption_mismatch"] = [
                r["i"]
                for r, b in zip(rows, baseline)
                if first is not None
                and r["i"] >= first
                and r["decision"] != b["decision"]
            ]
        reports.append(report)
    sources = {
        str(path.relative_to(args.source)): sha(path)
        for folder in ("resense", "configs")
        for path in sorted((args.source / folder).rglob("*"))
        if path.is_file() and path.suffix in (".py", ".so", ".yaml")
    }
    summary = {
        "source": str(args.source),
        "source_hashes": sources,
        "cache": str(args.cache),
        "cache_meta_sha256": metadata_hash,
        "selected_input_sha256": input_hashes,
        "timestamp_source": "bag receive stamps, preserved" if compact_paths is not None else "decoded original header stamps",
        "suite": args.suite,
        "cases": reports,
        "wall_s": time.monotonic() - started,
        "cpu_s": time.process_time() - cpu,
        "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "timing_is_shared_host_diagnostic": True,
    }
    if args.suite == "orientation":
        summary["explicit_24_exact_vehicle_point_equivalence_all_frames"] = (
            explicit_equivalence
        )
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        json.dumps(
            {"frames": len(metadata), "cases": len(cases), "wall_s": summary["wall_s"]}
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
