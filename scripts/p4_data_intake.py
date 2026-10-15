#!/usr/bin/env python3
"""H0 local inventory: complete gate stamps, raw headers, float32 node caches.

Run with PYTHONPATH and RESENSE_REPO pinned to the detector checkout. Reuses
cache_decoded.py verbatim for missing bags; never overwrites a partial cache.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from robustness_battery import (cache_meta, environment, git, identity, read_json,
                                sha256, source_info, write_new)

COUNTS = {"doubleT_obstacle": 201, "doubleT_platform": 345, "roundT_doubleT": 252,
          "roundT_pressureGate_roundT": 268, "roundT_squareT_pressureGate_squareT": 545,
          "squareT_platform_squareT_switch": 877, "cloud_with_fake_obj": 1510, "new_data": 11271}


def raw_headers(path):
    from judge_runner import db3_files
    from resense_ros.fastcloud import _Reader

    out = []
    for db in db3_files(str(path)):
        with sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True) as con:
            topics = dict(con.execute("SELECT id,name FROM topics WHERE type='sensor_msgs/msg/PointCloud2'"))
            for tid, timestamp, header in con.execute(
                    "SELECT topic_id,timestamp,substr(data,1,256) FROM messages "
                    f"WHERE topic_id IN ({','.join(map(str, topics))}) ORDER BY timestamp,id"):
                reader = _Reader(memoryview(header))
                sec, ns = reader.i32(), reader.u32()
                out.append({"stamp": sec + ns * 1e-9, "bag_t": timestamp / 1e9,
                            "frame_id": reader.string(), "topic": topics[tid]})
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--set-o", type=Path, required=True)
    p.add_argument("--ride", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--resource-adapter", type=Path)
    a = p.parse_args()
    if a.out.exists():
        p.error("output already exists")
    repo, data = a.repo.resolve(), a.data.resolve()
    sys.path.insert(0, str(repo))
    judge = repo / "docs/evidence/judgement_2026-10-13/scripts"
    sys.path.insert(0, str(judge))
    import numpy as np
    from judge_runner import db3_files, iter_raw
    from resense.pointcloud import COMPACT16_DTYPE
    from resense_ros import fastcloud
    from scripts.cache_io import (cache_file_stem, cache_files, load_cache_array, load_cache_stamps,
                                  validate_extended_ride_cache, validate_ride_intake_manifest)

    result = {"schema": "resense-p4-h0-intake-v1", "evaluation": identity(repo),
              "runtime": "user Windows computer, local offline replay", "gate": {}, "decoded": {}}
    for bag, count in COUNTS.items():
        raw = a.set_o if bag == "cloud_with_fake_obj" else a.ride if bag == "new_data" else data / "for_hackathon" / bag
        headers = raw_headers(raw)
        files = cache_files(str(data / "cache" / bag))
        stamps = load_cache_stamps(str(data / "cache" / bag))
        if len(files) != count or len(headers) != count or len(stamps) != count:
            raise ValueError(f"incomplete gate/raw/stamp inventory: {bag}")
        inventory = []
        for f, header in zip(files, headers):
            if stamps[cache_file_stem(f)] != header["bag_t"]:
                raise ValueError(f"gate vs raw receive stamp mismatch {f}")
            arr = load_cache_array(f)
            if arr.dtype != COMPACT16_DTYPE or arr.ndim != 1 or not len(arr):
                raise ValueError(f"invalid compact16 array {f}")
            inventory.append({"file": Path(f).name, "sha256": sha256(f)})
        result["gate"][bag] = {"raw_path": str(raw), "cache_path": str(data / "cache" / bag),
                               "frames": count, "stamps_checked": count, "arrays_checked": count,
                               "first": headers[0], "last": headers[-1],
                               "inventory_sha256": hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest()}
        print("gate", bag, count, "raw stamps / arrays checked", flush=True)
        if bag == "new_data":
            ride_report = validate_extended_ride_cache(str(data / "cache/new_data"))
            result["ride_intake"] = validate_ride_intake_manifest(str(data / "cache/new_data"), ride_report)
            result["ride_validation"] = ride_report
            continue
        decoded = data / "decoded" / bag
        if not decoded.exists():
            log_path = a.out.parent / f"build_{bag}.log"
            with open(log_path, "x", encoding="utf-8") as log:
                cmd = [sys.executable, str(judge / "cache_decoded.py"), str(raw), str(decoded)]
                subprocess.run(cmd, cwd=repo, env=environment(repo, a.resource_adapter),
                               stdout=log, stderr=subprocess.STDOUT, check=True)
            result.setdefault("builds", {})[bag] = {"command": cmd, "log": str(log_path), "tool_sha256": sha256(judge / "cache_decoded.py")}
        meta, decoded_files = cache_meta(decoded, count)
        for i, (m, f, header) in enumerate(zip(meta, decoded_files, headers)):
            if any(m[k] != header[k] for k in ("stamp", "bag_t", "frame_id", "topic")):
                raise ValueError(f"node metadata vs raw mismatch {bag}/{i}")
            with np.load(f, allow_pickle=False) as frame:
                xyz, intensity, ring = frame["xyz"], frame["inten"], frame["ring"]
                if (xyz.dtype != np.float32 or intensity.dtype != np.float32 or ring.dtype != np.uint16
                        or xyz.shape != (len(intensity), 3) or ring.shape != intensity.shape
                        or not np.isfinite(xyz).all() or not np.isfinite(intensity).all()):
                    raise ValueError(f"invalid node array {f}")
        # Independently decode first and last raw payload as a sensor-frame identity check.
        samples = []
        k = 0
        for db in db3_files(str(raw)):
            for _, _, payload in iter_raw(db):
                if k in (0, count - 1):
                    msg = fastcloud.parse_pointcloud2(payload)
                    xyz, inten, ring, nraw, nnear = fastcloud.decode(fastcloud.packed(msg), 2.5, 250.)
                    with np.load(decoded_files[k], allow_pickle=False) as frame:
                        for name, arr in (("xyz", xyz), ("inten", inten), ("ring", ring)):
                            np.testing.assert_array_equal(frame[name], arr)
                    assert (meta[k]["n_raw"], meta[k]["n_near"], meta[k]["has_ring"]) == (nraw, nnear, fastcloud.has_field(msg, "ring"))
                    samples.append(k)
                k += 1
        result["decoded"][bag] = {**source_info(decoded, count), "arrays_checked": count,
                                  "raw_header_rows_checked": count, "fresh_decode_samples": samples}
        print("decoded", bag, count, "float32 arrays / raw headers checked", flush=True)
    seal = read_json(repo / "docs/evidence/detector_freeze_2026-09-29_shell_off.json")
    hashes = {}
    for name, expected in seal["files"].items():
        blob = subprocess.check_output(["git", "-C", str(repo), "show", f"HEAD:{name}"])
        hashes[name] = {"expected": expected, "actual": hashlib.sha256(blob).hexdigest()}
    result["seal_committed_blobs"] = {"source_sha256": seal["source_sha256"], "files": hashes,
                                      "passed": all(h["expected"] == h["actual"] for h in hashes.values())}
    result["intake_harness_commit"] = git(Path(__file__).resolve().parents[1], "rev-parse", "HEAD")
    result["status"] = "VERIFIED" if result["seal_committed_blobs"]["passed"] else "ERROR"
    write_new(a.out, result)


if __name__ == "__main__":
    main()
