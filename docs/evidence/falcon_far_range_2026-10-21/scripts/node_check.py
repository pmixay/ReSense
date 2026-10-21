#!/usr/bin/env python3
"""Criterion 14: the ROS node path. Streams the raw Falcon recording, feeds the raw CDR bytes of frames
[lo, hi) to the real ``resense_ros.detector_node.DetectorNode`` (rclpy and the message packages are the
stand-ins of ``tests/test_node.py``; ``sensor_profile:=falcon_ros``, ``config_file`` = configs/default.yaml
plus the given ``farrange`` keys), records every detector result the node computes (a read-only wrapper of
``Detector.process``) and the published decisions, and writes them as replay rows (``judge_runner.record``)
for comparison with ``run_far.py --frames lo:hi`` on the cache (fresh detector at ``lo``, same config).

    node_check.py <yadisk url> --frames 2650:2900 --farrange with_falcon_profile=true,axis_stable=true --out <prefix>
"""
import argparse
import heapq
import json
import os
import sys
import tempfile
from pathlib import Path

import yaml

REPO = Path(os.environ.get("RESENSE_REPO", Path(__file__).resolve().parents[4]))
for p in (REPO / "scripts", REPO / "ros2_ws/src/resense_ros", REPO / "tests",
          REPO / "docs/evidence/judgement_2026-10-13/scripts", REPO):
    sys.path.insert(0, str(p))

import test_node as T  # noqa: E402  (stand-ins for rclpy and the message packages)

for name, md in T._stub_modules().items():
    sys.modules[name] = md

from judge_runner import record  # noqa: E402
from stream_falcon import Recover, byte_stream  # noqa: E402
import resense.detector as D  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--frames", required=True)
    ap.add_argument("--farrange", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lo, hi = (int(v) for v in a.frames.split(":"))
    base = yaml.safe_load(open(REPO / "configs/default.yaml"))
    far = {}
    for kv in filter(None, a.farrange.split(",")):
        k, v = kv.split("=", 1)
        far[k] = yaml.safe_load(v)
    if far:
        base["resense"].setdefault("farrange", {}).update(far)
    cfg_path = Path(tempfile.mkdtemp()) / "detector_check.yaml"
    cfg_path.write_text(yaml.safe_dump(base, sort_keys=False))
    T._Node.overrides = {"config_file": str(cfg_path), "sensor_profile": "falcon_ros", "input_topic": "/iv_points",
                         "auto_discover": False, "publish_markers": False, "publish_corridor_cloud": False}
    from resense_ros.detector_node import DetectorNode
    results = []
    orig = D.Detector.process

    def process(self, frame, *args, **kw):
        res = orig(self, frame, *args, **kw)
        results.append(res)
        return res
    D.Detector.process = process
    node = DetectorNode()
    assert node.sensor_profile == "falcon_ros" and node.cfg.farrange.enabled == bool(far.get("with_falcon_profile", False))
    info = {"farrange": {k: getattr(node.cfg.farrange, k) for k in ("enabled", "with_falcon_profile", "axis_stable")},
            "max_range": node.cfg.sensor.max_range, "config": str(cfg_path)}
    print(info, flush=True)
    rec = Recover("seyond", 256)
    heap, seen, n = [], set(), [0]
    rows = []

    buf = []

    def emit(ts, data):
        i = n[0]
        n[0] += 1
        if lo <= i < hi:
            buf.append((i, ts, bytes(data)))       # fed after streaming: the decompression must not pace the node
        return i + 1 >= hi

    done = False
    for chunk in byte_stream(a.src, "falcon_test.zst", "falcon_test_second_dark_0.db3"):
        for topic_id, ts, data in rec.feed(chunk):
            if topic_id != 3 or ts in seen:
                continue
            seen.add(ts)
            heapq.heappush(heap, (ts, data))
        while len(heap) > 50 and not done:
            ts, data = heapq.heappop(heap)
            done = emit(ts, data)
        if done:
            break
    import time
    for i, ts, data in buf:
        k0 = len(results)
        # a replay publisher's DDS source timestamp (publisher UTC, freshness_mode replay) as rclpy gives it
        node.on_cloud(data, "/iv_points", {"source_timestamp": time.time_ns()})
        dec = node.published["/resense/decision"][-1].data if node.published["/resense/decision"] else None
        assert len(results) == k0 + 1, (i, len(results), k0)
        res = results[-1]
        r = record(i, ts / 1e9, res.stamp, res, 0.0, 0.0, "", "/iv_points")
        r["node_published_decision"] = dec
        rows.append(r)
        time.sleep(0.05)
    with open(a.out + ".jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    json.dump({**info, "frames": [lo, hi], "rows": len(rows)}, open(a.out + ".meta.json", "w"), indent=1)
    print("rows", len(rows), flush=True)


if __name__ == "__main__":
    main()
