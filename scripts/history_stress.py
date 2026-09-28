#!/usr/bin/env python3
"""False STOPs on five clear recordings under six histories plus three raw node histories.

Every history starts a fresh detector with calibration enabled. Captures retain source frame
indices, timestamps, and every STOP detection. Missing recordings, timestamp sidecars, captured
histories, or requested raw frames are errors. Run the same runner against another checkout with
--source-root; imported detector modules are verified against that root.
"""
from __future__ import annotations

import os

if __name__ == "__main__":
    for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
import gzip  # noqa: E402
import hashlib  # noqa: E402
import importlib.metadata  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402

RUNNER = Path(__file__).resolve()
_bootstrap = argparse.ArgumentParser(add_help=False)
_bootstrap.add_argument("--source-root", default=str(RUNNER.parents[1]))
ROOT = Path(_bootstrap.parse_known_args()[0].source_root).resolve()
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
CAPTURES = ROOT / "docs/evidence/results/quality_cycle_2026-09-26_clear_failure/captures"
EMPTY = ("roundT_doubleT", "doubleT_platform", "roundT_pressureGate_roundT",
         "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch")
HISTORIES = (("every", "every", 0.0), ("drop20", "drop", 0.2), ("drop40", "drop", 0.4),
             ("catchup", "catchup", 80), ("offset", "offset", 0), ("dither5", "dither", 5.0))
CAPTURE_NAMES = ("failed_clear", "old_stock", "old_pass")


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_import_root(root=ROOT):
    import resense.detector
    actual = Path(resense.detector.__file__).resolve()
    expected = Path(root).resolve() / "resense/detector.py"
    if actual != expected:
        raise ValueError(f"wrong detector imported: {actual}; expected {expected}")
    return str(actual)


def _history(kind: str, param, n: int, rng) -> np.ndarray:
    if n <= 0:
        raise ValueError("cannot construct a history from an empty recording")
    if kind == "drop":
        keep = rng.random(n) >= param
        keep[0] = True
        return np.flatnonzero(keep)
    if kind == "catchup":
        return np.concatenate([np.arange(0, min(n, int(param)), 2), np.arange(min(n, int(param)), n)])
    if kind == "offset":
        return np.arange(int(rng.integers(5, max(6, n // 4))), n)
    return np.arange(n)


def capture_nodes(name):
    from check_dry_run import load as load_status
    path = CAPTURES / (name + ".jsonl.gz")
    if not path.is_file():
        raise ValueError(f"missing expected raw history: {path}")
    node = [f for f in load_status(path)[0] if f.get("node", {}).get("recording") == 1]
    stamps = [float(f["stamp"]) for f in node]
    if not stamps or any(not np.isfinite(s) for s in stamps) or any(b <= a for a, b in zip(stamps, stamps[1:])):
        raise ValueError(f"raw history {name} has empty, non-finite, duplicated or unordered timestamps")
    if len({round(s, 6) for s in stamps}) != len(stamps):
        raise ValueError(f"raw history {name} repeats a timestamp at replay precision")
    return node


def verify_capture_frames(name, expected, observed):
    wanted = [round(float(s), 6) for s in expected]
    actual = [round(float(s), 6) for s in observed]
    if wanted != actual:
        raise ValueError(f"raw history {name} did not replay every requested frame in order: "
                         f"expected={len(wanted)} observed={len(actual)} "
                         f"missing={sorted(set(wanted) - set(actual))[:5]}")


def preflight(cache, bags, bag):
    from scripts.cache_io import cache_file_stem, cache_files, load_cache_stamps
    if not bag or not Path(bag).is_dir() or not list(Path(bag).glob("*.db3")):
        raise ValueError(f"original bag is required for all three captured histories: {bag}")
    sources = {"raw_bag": {p.name: sha(p) for p in sorted(Path(bag).iterdir()) if p.is_file()},
               "captures": {}, "cache": {}}
    for name in CAPTURE_NAMES:
        node = capture_nodes(name)
        sources["captures"][name] = {"sha256": sha(CAPTURES / (name + ".jsonl.gz")), "frames": len(node)}
    for name in bags:
        directory = Path(cache) / name
        files = cache_files(directory)
        if not files:
            raise ValueError(f"missing or empty expected cache: {directory}")
        stamps = load_cache_stamps(directory)
        stems = [cache_file_stem(p) for p in files]
        if set(stems) != set(stamps):
            raise ValueError(f"cache/timestamp inventory differs for {name}: "
                             f"missing_stamps={sorted(set(stems)-set(stamps))[:5]} "
                             f"missing_frames={sorted(set(stamps)-set(stems))[:5]}")
        sequence = [float(stamps[stem]) for stem in stems]
        if any(not np.isfinite(s) for s in sequence) or any(b <= a for a, b in zip(sequence, sequence[1:])):
            raise ValueError(f"non-finite, repeated or unordered cache timestamps: {name}")
        inventory = [{"stem": stem, "sha256": sha(path), "stamp": stamps[stem]}
                     for stem, path in zip(stems, files)]
        sources["cache"][name] = {"frames": len(files), "inventory_sha256": digest_json(inventory)}
    return sources


def frame_record(index, frame, result):
    return {"frame": int(index), "frame_id": frame.frame_id, "stamp": float(frame.stamp),
            "obstacle": bool(result.obstacle), "detections": [d.to_dict() for d in result.detections]}


def events_of(rows):
    events = {}
    for row in rows:
        for detection in row["detections"]:
            event = events.setdefault(int(detection["id"]), {"id": int(detection["id"]), "frames": [], "distances": []})
            event["frames"].append(row["frame"])
            event["distances"].append(float(detection["distance"]))
    return [{"id": ident, "first_frame": e["frames"][0], "last_frame": e["frames"][-1],
             "stop_frames": len(e["frames"]), "distance_min": min(e["distances"]),
             "distance_max": max(e["distances"])} for ident, e in sorted(events.items())]


def finish_history(source, bag, name, seed, rows, capture_dir):
    if not rows:
        raise ValueError(f"history contains no frames: {source}/{bag}/{name}/{seed}")
    events = events_of(rows)
    distances = [round(float(d["distance"]), 1) for r in rows for d in r["detections"]]
    tag = f"{source}__{bag}__{name}__{seed}.jsonl.gz"
    path = Path(capture_dir) / tag
    payload = "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows).encode()
    path.write_bytes(gzip.compress(payload, mtime=0))
    return {"source": source, "bag": bag, "history": name, "seed": seed, "frames": len(rows),
            "stop_frames": sum(r["obstacle"] for r in rows), "stop_events": len(events),
            "stop_distances": sorted(set(distances)), "events": events,
            "stop_frame_ids": [r["frame"] for r in rows if r["obstacle"]],
            "capture": {"file": tag, "sha256": sha(path)}}


def run_cache(job):
    bag, name, kind, param, seed, cache, cfg_dict, capture_dir = job
    verify_import_root()
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    from scripts.cache_io import cache_file_stem, cache_files, load_cache_array, load_cache_stamps
    from resense.pointcloud import COMPACT_DTYPE, compact_to_xyz, expand_compact16
    cfg = DetectorConfig.from_dict(cfg_dict)
    files = cache_files(Path(cache) / bag)
    stamps = load_cache_stamps(Path(cache) / bag)
    rng, det, rows = np.random.default_rng(seed), Detector(cfg), []
    for i in _history(kind, param, len(files), rng):
        path = files[i]
        stem = cache_file_stem(path)
        arr = load_cache_array(path)
        if kind == "dither":
            arr = expand_compact16(arr)
            xyz = compact_to_xyz(arr) + rng.uniform(-param, param, (arr.size, 3)).astype(np.float32) * 1e-3
            out = np.zeros(arr.size, dtype=COMPACT_DTYPE)
            out["x"], out["y"], out["z"] = xyz.T
            out["intensity"], out["ring"] = arr["intensity"], arr["ring"]
            arr = out
        frame = frame_from_compact(arr, cfg.sensor, stamp=stamps[stem], frame_id=stem)
        rows.append(frame_record(int(stem.rsplit("_", 1)[1]), frame, det.process(frame)))
    return finish_history("cache", bag, name, seed, rows, capture_dir)


def run_capture(job):
    name, bag, cfg_dict, capture_dir = job
    verify_import_root()
    from replay_node_frames import bag_frames
    from resense.config import DetectorConfig
    from resense.detector import Detector
    cfg = DetectorConfig.from_dict(cfg_dict)
    node = capture_nodes(name)
    stamps = [f["stamp"] for f in node]
    det, rows = Detector(cfg), []
    for index, frame in bag_frames(bag, cfg, node[0]["node"].get("input_topic"), stamps, False):
        rows.append(frame_record(index, frame, det.process(frame, ego_speed=None)))
    verify_capture_frames(name, stamps, [r["stamp"] for r in rows])
    return finish_history("capture", "roundT_doubleT", name, 0, rows, capture_dir)


def main(argv=None) -> int:
    import eval_real
    from detector_freeze import source_digest, source_hashes
    from resense.config import DetectorConfig
    from resense import _native
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", default=str(ROOT))
    parser.add_argument("--cache", default="/data/cache")
    parser.add_argument("--bag", required=True, help="original roundT_doubleT; all three captured histories are required")
    parser.add_argument("--config", default=str(ROOT / "configs/default.yaml"))
    parser.add_argument("--set", action="append", default=[])
    parser.add_argument("--bags", default=",".join(EMPTY))
    parser.add_argument("--seeds", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if Path(args.source_root).resolve() != ROOT:
        raise ValueError("--source-root must be selected at process startup")
    if args.jobs < 1 or args.seeds < 1:
        raise ValueError("jobs and seeds must be positive")
    bags = args.bags.split(",")
    if len(set(bags)) != len(bags) or any(b not in EMPTY for b in bags):
        raise ValueError("--bags must be unique known obstacle-free recordings")
    imported = verify_import_root()
    cfg = DetectorConfig.from_dict(eval_real.load_cfg_dict(args.config, args.set))
    cfg.calibration.enabled = True
    cfg_dict = cfg.to_dict()
    source_files = source_hashes(ROOT)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    capture_dir = args.out.with_suffix("").with_name(args.out.stem + "_frames")
    capture_dir.mkdir(parents=True, exist_ok=True)
    print("preflight: verifying all captured histories, original bag, cache frames and timestamps", flush=True)
    sources = preflight(args.cache, bags, args.bag)
    jobs = [(bag, name, kind, param, seed, args.cache, cfg_dict, str(capture_dir))
            for bag in bags for name, kind, param in HISTORIES
            for seed in (range(args.seeds) if kind in ("drop", "offset", "dither") else [0])]
    cap_jobs = [(name, args.bag, cfg_dict, str(capture_dir)) for name in CAPTURE_NAMES]
    t0, rows = time.time(), []
    with ProcessPoolExecutor(max_workers=args.jobs) as executor:
        for fn, tasks in ((run_capture, cap_jobs), (run_cache, jobs)):
            for row in executor.map(fn, tasks):
                rows.append(row)
                print(f"{len(rows)}/{len(jobs)+len(cap_jobs)} {row['source']} {row['bag']} {row['history']} "
                      f"seed={row['seed']} frames={row['frames']} STOP={row['stop_frames']} events={row['stop_events']}", flush=True)
    if source_hashes(ROOT) != source_files:
        raise ValueError("detector source changed during history replay")
    totals = {"histories": len(rows), "stop_frames": sum(r["stop_frames"] for r in rows),
              "stop_events": sum(r["stop_events"] for r in rows),
              "histories_with_stop": sum(r["stop_events"] > 0 for r in rows),
              "captures_stop_events": sum(r["stop_events"] for r in rows if r["source"] == "capture"),
              "cache_stop_events": sum(r["stop_events"] for r in rows if r["source"] == "cache")}
    out = {"schema": "resense-history-stress-v2", "created_utc": datetime.now(timezone.utc).isoformat(),
           "runner_sha256": sha(RUNNER), "source_root": str(ROOT), "detector_import": imported,
           "source_commit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
           "source_sha256": source_digest(source_files), "source_files": source_files,
           "config": cfg_dict, "config_sha256": digest_json(cfg_dict), "config_file_sha256": sha(args.config),
           "runtime": {"python": sys.version, "native": _native.LIBRARY,
                       "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "rosbags")}},
           "inputs": sources, "sets": args.set, "wall_s": round(time.time()-t0, 1),
           "capture_directory": capture_dir.name, "totals": totals, "rows": rows,
           "limitations": ["Known clear development recordings, not new holdout data.",
                           "Concurrent run timings are not latency evidence."]}
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print("totals:", json.dumps(totals), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
