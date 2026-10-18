"""Registered, bounded L16 explicit-mapping experiment; never edits detector code."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
COMMIT = "e9d8fc649f2dd51dd5cd1e4b04ac8c306cc02569"
REMOTE = "1b880168ce2dbeec2071838892ac05eed5a9166a"
SOURCE = Path("/home/resense/data/version_1_2_0_candidate")
CACHES = Path("/home/resense/data/decoded")
BAGS = {"roundT_squareT_pressureGate_squareT": 545, "doubleT_obstacle": 201}
NATIVE = "511f7766639f0ddab471a77263f7a343de19d0a8217dd7cd3a11635c8a7db2c8"


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def source_identity():
    freeze = load_module("l16_freeze", ROOT / "scripts/detector_freeze.py")
    files = freeze.source_hashes(SOURCE)
    for name, value in files.items():
        blob = subprocess.check_output(["git", "show", f"{COMMIT}:{name}"], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == value, name
    native = {str(p.relative_to(SOURCE)): sha(p) for p in SOURCE.rglob("_resense_native*.so")}
    assert len(native) == 1 and list(native.values()) == [NATIVE], native
    return {"commit": COMMIT, "root": str(SOURCE), "files": files,
            "source_sha256": freeze.source_digest(files), "native": native}


def register():
    destination = HERE / "registration.json"
    assert not destination.exists(), "Registration is immutable; do not overwrite"
    snapshots = HERE / "p4_inputs"
    snapshots.mkdir(exist_ok=True)
    remote_files = [
        "docs/evidence/p1_branch_check_2026-10-18/README.md",
        "docs/evidence/p1_branch_check_2026-10-18/ana_p1_doubleT_obstacle.json",
        "docs/evidence/p1_branch_check_2026-10-18/ana_p1_roundT_squareT_pressureGate_squareT.json",
        "docs/evidence/orientation_2026-10-18/README.md",
        "scripts/orientation_battery.py",
    ]
    evidence = {}
    for index, name in enumerate(remote_files):
        data = subprocess.check_output(["git", "show", f"{REMOTE}:{name}"], cwd=ROOT)
        path = snapshots / f"{index}_{Path(name).name}"
        path.write_bytes(data)
        evidence[name] = {"snapshot": str(path.relative_to(HERE)), "sha256": sha(path)}
    inputs = {}
    for bag, count in BAGS.items():
        cache = CACHES / bag
        metadata = json.loads((cache / "meta.json").read_text())
        files = sorted(cache.glob("f_*.npz"))
        assert len(metadata) == len(files) == count
        assert [p.name for p in files] == [f"f_{i:05d}.npz" for i in range(count)]
        inputs[bag] = {"frames": count, "meta_sha256": sha(cache / "meta.json"),
                       "files": {p.name: sha(p) for p in files}}
    save(destination, {"registered_utc": now(), "source": source_identity(),
                       "protocol_sha256": sha(HERE / "PROTOCOL.md"),
                       "harness_sha256": sha(Path(__file__)), "remote_commit": REMOTE,
                       "p4_evidence": evidence, "inputs": inputs, "maximum_rows": 2984,
                       "variants": ["upright", "case04_explicit", "case05_explicit", "case05_wrong"]})
    print(f"Registered {destination}", flush=True)


def normalize(row):
    value = deepcopy(row)
    for key in ("decode_ms", "detect_ms", "total_ms"):
        value.pop(key)
    for holder, messages, level, decision in (
        (value, "msgs", "level", "dlevel"),
        (value["health_detail"], "messages", "level", "decision_level"),
    ):
        filtered = [m for m in holder[messages] if not m.startswith("latency p95 ")]
        if filtered != holder[messages] and holder[level] == "warn":
            holder[level] = holder[decision]
        holder[messages] = filtered
    value["health_detail"].pop("latency_p95_ms")
    return value


def intervals(rows):
    out = []
    previous = False
    for row in rows:
        if row["decision"] == "STOP":
            if previous:
                out[-1][1] = row["i"]
            else:
                out.append([row["i"], row["i"]])
        previous = row["decision"] == "STOP"
    return out


def run():
    registration = json.loads((HERE / "registration.json").read_text())
    assert source_identity() == registration["source"]
    assert sha(Path(__file__)) == registration["harness_sha256"]
    assert sha(HERE / "PROTOCOL.md") == registration["protocol_sha256"]
    assert not (HERE / "summary.json").exists()
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        assert os.environ.get(name) == "1", name
    assert os.environ.get("OPENBLAS_CORETYPE") == "Haswell"
    os.environ["RESENSE_REPO"] = str(SOURCE)
    sys.path[:0] = [str(SOURCE), str(SOURCE / "ros2_ws/src/resense_ros")]
    import numpy as np
    from resense.calibration import axis_label, orientation_candidates
    from resense.frame import Frame
    judge = load_module("l16_judge", SOURCE / "docs/evidence/judgement_2026-10-13/scripts/judge_runner.py")
    base = judge.NodeReplica().R_vs.astype(np.float64)
    rots = orientation_candidates(False)
    cases = [("upright", 0, False), ("case04_explicit", 4, True),
             ("case05_explicit", 5, True), ("case05_wrong", 5, False)]
    raw = HERE / "raw"
    raw.mkdir(exist_ok=True)
    started, cpu = time.monotonic(), time.process_time()
    report = {"started_utc": now(), "registration_sha256": sha(HERE / "registration.json"),
              "source": registration["source"], "environment": {key: os.environ[key] for key in
              ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_CORETYPE")},
              "affinity": sorted(os.sched_getaffinity(0)), "bags": {}}
    for bag, count in BAGS.items():
        cache = CACHES / bag
        registered = registration["inputs"][bag]
        assert sha(cache / "meta.json") == registered["meta_sha256"]
        metadata = json.loads((cache / "meta.json").read_text())
        workers = []
        for name, index, explicit in cases:
            expected = rots[index].T @ base if explicit else base
            axes = dict(part.split("=") for part in axis_label(expected).split())
            overrides = {f"sensor.{key}": value for key, value in axes.items()} if explicit else {}
            rep = judge.NodeReplica(overrides=overrides)
            assert np.array_equal(rep.R_vs, expected)
            assert rep.cfg.calibration.orientation_replay_frames == 0
            assert rep.cfg.calibration.keep_up_axis and rep.cfg.calibration.enabled
            path = raw / f"{bag}__{name}.jsonl"
            workers.append({"name": name, "index": index, "explicit": explicit, "rep": rep,
                            "rows": [], "path": path, "stream": path.open("x"),
                            "overrides": overrides, "axes": axes, "exact_input_frames": 0,
                            "cone_equal_frames": 0})
        for i, meta in enumerate(metadata):
            path = cache / f"f_{i:05d}.npz"
            assert sha(path) == registered["files"][path.name]
            with np.load(path) as data:
                xyz, inten = data["xyz"], data["inten"]
                ring = data["ring"] if meta["has_ring"] else None
            original_vehicle = (xyz @ base.T.astype(np.float32)).astype(np.float32)
            def cone(points):
                x = points[:, 0]
                narrow = np.hypot(points[:, 1], points[:, 2]) < .35 * np.abs(x)
                return [int(((x > 15) & narrow).sum()), int(((x < -15) & narrow).sum())]
            original_cone = cone(original_vehicle)
            for worker in workers:
                rotation = rots[worker["index"]]
                transformed = xyz if worker["index"] == 0 else (
                    (xyz.astype(np.float64) @ base.T @ rotation.T) @ base).astype(np.float32)
                uncorrected_vehicle = transformed @ base.T.astype(np.float32)
                cone_same = cone(uncorrected_vehicle) == original_cone
                assert cone_same, "Selected rotations must preserve the forward/rear cone exactly"
                worker["cone_equal_frames"] += 1
                rep = worker["rep"]
                vehicle = (transformed @ rep.R_vs.T).astype(np.float32)
                equal = vehicle.tobytes() == original_vehicle.tobytes()
                worker["exact_input_frames"] += int(equal)
                if worker["explicit"] or worker["index"] == 0:
                    assert equal, (bag, i, worker["name"])
                rep.continuity(meta["topic"], meta["frame_id"], meta["stamp"], i)
                frame = Frame(vehicle, inten, ring, stamp=meta["stamp"], frame_id=meta["frame_id"],
                              meta={"n_raw": meta["n_raw"], "n_near": meta["n_near"]})
                begin = time.perf_counter()
                result = rep.detector.process(frame, ego_speed=None)
                elapsed = 1000 * (time.perf_counter() - begin)
                row = judge.record(i, meta["bag_t"], meta["stamp"], result, 0, elapsed,
                                   meta["frame_id"], meta["topic"])
                row.update(mount_detail=result.mount, track_detail=result.track.to_dict(),
                           health_detail=result.health, mount_rotation=rep.detector.mount_rotation.tolist())
                worker["stream"].write(json.dumps(row, allow_nan=False) + "\n")
                worker["rows"].append(row)
            if i % 100 == 0:
                print(f"{bag}: {i + 1}/{count}, elapsed {time.monotonic()-started:.1f}s", flush=True)
        baseline = workers[0]["rows"]
        assert sum(r["decision"] == "STOP" for r in baseline) == (193 if count == 201 else 0)
        reports = []
        for worker in workers:
            worker["stream"].close()
            rows = worker["rows"]
            assert len(rows) == count
            pairs = [(normalize(a), normalize(b)) for a, b in zip(baseline, rows)]
            changed = [i for i, (a, b) in enumerate(pairs) if a != b]
            differences = Counter(key for a, b in pairs for key in a if a[key] != b[key])
            stop = [r["i"] for r in rows if r["decision"] == "STOP"]
            baseline_stop = [r["i"] for r in baseline if r["decision"] == "STOP"]
            item = {"name": worker["name"], "p4_index": worker["index"], "frames": count,
                    "rotation": rots[worker["index"]].astype(int).tolist(),
                    "axes": worker["axes"], "overrides": worker["overrides"],
                    "decisions": dict(Counter(r["decision"] for r in rows)),
                    "statuses": dict(Counter(r["mount_detail"]["status"] for r in rows)),
                    "first_orientation_confirmed": next((r["i"] for r in rows
                        if r["mount_detail"]["orientation_confirmed"]), None),
                    "stop_while_confirmed": [r["i"] for r in rows if r["decision"] == "STOP"
                        and r["mount_detail"]["orientation_confirmed"]],
                    "stop_after_status_ok": [r["i"] for r in rows if r["decision"] == "STOP"
                        and r["mount_detail"]["status"] == "ok"],
                    "stop_indices": stop, "stop_intervals": intervals(rows),
                    "lost_stop": sorted(set(baseline_stop) - set(stop)),
                    "added_stop": sorted(set(stop) - set(baseline_stop)),
                    "changed_non_timing_rows": changed, "changed_fields": dict(differences),
                    "exact_vehicle_input_frames": worker["exact_input_frames"],
                    "forward_cone_equal_frames": worker["cone_equal_frames"],
                    "resets": worker["rep"].resets, "raw": str(worker["path"].relative_to(HERE)),
                    "raw_sha256": sha(worker["path"])}
            item["explicit_mapping_pass"] = not changed if worker["explicit"] else None
            reports.append(item)
        report["bags"][bag] = reports
    assert source_identity() == registration["source"]
    assert sha(Path(__file__)) == registration["harness_sha256"]
    report.update(completed_utc=now(), rows=sum(sum(c["frames"] for c in cases) for cases in report["bags"].values()),
                  wall_s=time.monotonic()-started, cpu_s=time.process_time()-cpu,
                  peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                  source_unchanged=True, harness_unchanged=True)
    assert report["rows"] == 2984
    report["explicit_mapping_pass"] = all(c["explicit_mapping_pass"] for cases in report["bags"].values()
                                          for c in cases if c["explicit_mapping_pass"] is not None)
    save(HERE / "summary.json", report)
    print(json.dumps({"rows": report["rows"], "explicit_mapping_pass": report["explicit_mapping_pass"]}), flush=True)
    return 0 if report["explicit_mapping_pass"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("register", "run"))
    args = parser.parse_args()
    if args.action == "register":
        register()
    else:
        raise SystemExit(run())
