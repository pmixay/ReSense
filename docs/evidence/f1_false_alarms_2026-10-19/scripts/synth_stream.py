#!/usr/bin/env python3
"""The organizers' three synthetic bags (``new_synth_data.zst``) streamed once, each bag through its own
node replicas (``judge_runner.NodeReplica``: node decode, continuity rules, decision rule), as a jury would play
each bag, nothing stored but the per-frame records (``judge_runner.record``) of every replica:

* ``off``  — every 19.10 switch at 0 (the ``aec88d2`` behaviour: proved equal on the full gate and Falcon);
* ``cand`` — the committed configuration (the candidate).

Messages are recovered from the sqlite byte stream with ``stream_cache.Recover2`` (the Pandar record layout) and
released in timestamp order. ``synth_stream.py --out PREFIX`` writes ``PREFIX_<replica>_<bag>.jsonl``.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
import heapq  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import tarfile  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("RESENSE_REPO", HERE.parents[3]))
for p in (HERE, ROOT, ROOT / "scripts", ROOT / "ros2_ws/src/resense_ros",
          ROOT / "docs/evidence/judgement_2026-10-13/scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import zstandard  # noqa: E402

from stream_cache import Recover2  # noqa: E402

OFF = {"lowobj.local_rail_margin": 0.0, "cluster.mount_cross_tol": 0.0, "tracking.settle_min_hits": 0,
       "tracking.settle_check_z": True}
URL = "https://disk.yandex.ru/d/SfBeRHbs8bNJAQ"
BAGS = {"synthetic_platform": 386, "synthetic_switch": 736, "synthetic_tunnels": 545}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--src", default=URL)
    a = ap.parse_args()
    from judge_runner import NodeReplica, record
    from unpack_dataset import open_zst_stream
    raw = open_zst_stream(a.src, "new_synth_data.zst")
    stream = zstandard.ZstdDecompressor().stream_reader(raw, read_size=1 << 20)
    meta = {"src": a.src, "bags": {}, "off_overrides": OFF, "repo": str(ROOT)}
    t0 = time.time()
    with tarfile.open(fileobj=stream, mode="r|") as tar:
        for ti in tar:
            if not ti.isfile() or not ti.name.endswith(".db3"):
                continue
            bag = next((b for b in BAGS if os.path.basename(ti.name).startswith(b)), None)
            if bag is None:
                continue
            reps = {"off": NodeReplica(overrides=OFF), "cand": NodeReplica()}
            outs = {k: open(f"{a.out}_{k}_{bag}.jsonl", "w") for k in reps}
            rec = Recover2("hesai_lidar", 256)
            heap, seen, n = [], set(), [0]
            topics = {}

            def emit(ts, data):
                for k, rep in reps.items():
                    msg, stamp, res, dec_ms, det_ms = rep.process_raw(data, "/lidar_points", n[0])
                    outs[k].write(json.dumps(record(n[0], ts / 1e9, stamp, res, dec_ms, det_ms,
                                                    msg.header.frame_id, "/lidar_points")) + "\n")
                n[0] += 1

            def take(items):
                for topic_id, ts, data in items:
                    topics[topic_id] = topics.get(topic_id, 0) + 1
                    if ts not in seen:
                        seen.add(ts)
                        heapq.heappush(heap, (ts, data))

            f = tar.extractfile(ti)
            while chunk := f.read(64 << 20):
                take(rec.feed(chunk))
                while len(heap) > 50:
                    emit(*heapq.heappop(heap))
            take(rec.feed(b"", final=True))
            while heap:
                emit(*heapq.heappop(heap))
            for fh in outs.values():
                fh.close()
            meta["bags"][bag] = {"frames": n[0], "expected": BAGS[bag], "found": rec.found, "kept": rec.kept,
                                 "lost": rec.lost, "topic_ids": topics,
                                 "resets": {k: r.resets for k, r in reps.items()}}
            print(bag, json.dumps(meta["bags"][bag]), flush=True)
    meta["wall_s"] = round(time.time() - t0, 1)
    json.dump(meta, open(a.out + ".meta.json", "w"), indent=1)
    return 0 if all(v["frames"] == v["expected"] and not v["lost"] for v in meta["bags"].values()) \
        and len(meta["bags"]) == 3 else 1


if __name__ == "__main__":
    sys.exit(main())
