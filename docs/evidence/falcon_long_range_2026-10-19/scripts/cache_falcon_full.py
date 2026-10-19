#!/usr/bin/env python3
"""Stream the Falcon recording once and keep a full-range float32 cache with the scan fields.

    cache_falcon_full.py <yadisk url | .zst | .db3> --out <dir> [--limit N]

Per frame ``f_<i>.npz``: ``xyz`` float32 (sensor frame, exactly the node decode's bytes with
``max_range`` 600 m instead of 250 m), and for the same points ``inten`` float32 (as the node),
``scan_id`` / ``scan_idx`` / ``flags`` / ``is2`` / ``t`` (point timestamp minus the frame's first, s).
``meta.json``: header stamp, bag time, frame_id, n_raw (finite returns), n_near (< 2.5 m).
Positive control built in: on every 50th frame the node decode at 2.5–250 m is compared with the
cache cropped to 250 m by the same float32 range test (must be identical).
"""
from __future__ import annotations

import argparse
import heapq
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(os.environ.get("RESENSE_REPO", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "ros2_ws/src/resense_ros"))
sys.path.insert(0, str(REPO))
import numpy as np  # noqa: E402

from stream_falcon import Recover, byte_stream  # noqa: E402
from resense.pointcloud import pointcloud2_to_structured  # noqa: E402
from resense_ros import fastcloud  # noqa: E402

MAX = 600.0


def crop_mask(xyz, lo, hi):
    x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    r2 = x.astype(np.float32) ** 2
    r2 += y * y
    r2 += z * z
    return (r2 >= lo * lo) & (r2 <= hi * hi)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rec = Recover("seyond", 256)
    heap, meta, seen, checks = [], [], set(), []
    t0 = time.time()

    def emit(ts, data):
        i = len(meta)
        msg = fastcloud.packed(fastcloud.parse_pointcloud2(data))
        xyz, inten, _, n_raw, n_near = fastcloud.decode(msg, 2.5, MAX)
        arr = pointcloud2_to_structured(msg)
        # the same index set as decode(): finite, not near, <= MAX
        full = arr.view(np.dtype({"names": ["xyz"], "formats": ["V12"], "offsets": [0],
                                  "itemsize": int(msg.point_step)}))["xyz"].copy().view(np.float32).reshape(-1, 3)
        x, y, z = full[:, 0], full[:, 1], full[:, 2]
        r2 = x.astype(np.float32) ** 2
        r2 += y * y
        r2 += z * z
        fin = np.isfinite(r2) & (r2 > 0.0025)
        ok = fin & ~(r2 < 2.5 * 2.5) & (r2 <= MAX * MAX)
        idx = np.flatnonzero(ok)
        assert np.array_equal(full[idx], xyz)
        t = arr["timestamp"].astype(np.float64)
        extra = {k: arr[k].take(idx) for k in ("scan_id", "scan_idx", "flags", "is_2nd_return")}
        np.savez_compressed(out / f"f_{i:05d}.npz", xyz=xyz, inten=inten,
                            scan_id=extra["scan_id"], scan_idx=extra["scan_idx"], flags=extra["flags"],
                            is2=extra["is_2nd_return"], t=(t.take(idx) - t[fin].min()).astype(np.float32))
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        meta.append({"i": i, "stamp": stamp, "bag_t": ts / 1e9, "frame_id": msg.header.frame_id,
                     "n_raw": n_raw, "n_near": n_near, "n": int(len(xyz))})
        if i % 50 == 0:
            node, _, _, nr, nn = fastcloud.decode(msg, 2.5, 250.0)
            mine = xyz[crop_mask(xyz, 2.5, 250.0)]
            checks.append({"i": i, "identical": bool(np.array_equal(node, mine)), "node": len(node),
                           "n_raw_equal": nr == n_raw, "n_near_equal": nn == n_near})
            print(f"{i} frames {time.time() - t0:.0f}s check {checks[-1]}", flush=True)

    last_pop = [None]
    for chunk in byte_stream(a.src, "falcon_test.zst", "falcon_test_second_dark_0.db3"):
        for topic_id, ts, data in rec.feed(chunk):
            if topic_id != 3 or ts in seen:
                continue
            seen.add(ts)
            heapq.heappush(heap, (ts, data))
        while len(heap) > 50:
            ts, data = heapq.heappop(heap)
            assert last_pop[0] is None or ts > last_pop[0]
            last_pop[0] = ts
            emit(ts, data)
        if a.limit and len(meta) >= a.limit:
            break
    else:
        for topic_id, ts, data in rec.feed(b"", final=True):
            if topic_id == 3 and ts not in seen:
                seen.add(ts)
                heapq.heappush(heap, (ts, data))
        while heap:
            ts, data = heapq.heappop(heap)
            emit(ts, data)
    (out / "meta.json").write_text(json.dumps(meta))
    rep = {"frames": len(meta), "lost": rec.lost, "kept": rec.kept, "checks": len(checks),
           "checks_identical": sum(c["identical"] and c["n_raw_equal"] and c["n_near_equal"] for c in checks),
           "wall_s": round(time.time() - t0, 1)}
    (out / "receipt.json").write_text(json.dumps({**rep, "check_rows": checks}, indent=1))
    print(json.dumps(rep), flush=True)


if __name__ == "__main__":
    main()
