#!/usr/bin/env python3
"""The whole Falcon recording through ONE node replica, as ``scripts/stream_falcon.py`` (same stream
recovery, same ``judge_runner.NodeReplica`` and ``record``), plus a read-only trace for the F1 lane:

* ``<out>.jsonl`` / ``.csv``: the per-frame records of ``stream_falcon.py`` (B4 compares them with the
  committed ``falcon_full_v110.jsonl``);
* ``<out>.x.jsonl``: per frame the track model (``TrackModel.to_dict``), rail slabs / score, and for every
  reported detection its track's last cluster (kind, zone, reason, top/bottom above the rail head,
  lateral extent, voxels, strict-gauge voxels, track hits / zone votes);
* ``<out>_dump/f<frame>.npz`` for ``--dump`` frames: the processed cloud (detector frame after the mount
  correction) with each point's corridor lateral ``dy`` and height ``h`` above the model's rail head, and
  the point indices of every reported detection's cluster.

The trace reads detector state only after ``process`` returns; a traced run's ``.jsonl`` must equal a plain
run's (checked against the committed reference, every non-timing field).

    falcon_trace.py https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --out OUT [--dump 150-165,4380-4405] [--set k=v]
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
import csv  # noqa: E402
import heapq  # noqa: E402
import json  # noqa: E402
import resource  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(os.environ.get("RESENSE_REPO", Path(__file__).resolve().parents[4]))
for p in (ROOT, ROOT / "scripts", ROOT / "ros2_ws/src/resense_ros",
          ROOT / "docs/evidence/judgement_2026-10-13/scripts",
          ROOT / "docs/evidence/extended_data_2026-10-17/scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np  # noqa: E402

from stream_falcon import Recover, byte_stream  # noqa: E402


def frames_arg(s: str) -> set:
    out = set()
    for part in filter(None, s.split(",")):
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dump", default="")
    ap.add_argument("--set", action="append", default=[], help="section.key=value (YAML value)")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    import yaml
    from judge_runner import CSV_COLS, NodeReplica, csv_row, record
    overrides = {}
    for s in a.set:
        k, v = s.split("=", 1)
        overrides[k] = yaml.safe_load(v)
    rep = NodeReplica(overrides=overrides)
    dump = frames_arg(a.dump)
    if dump:
        os.makedirs(a.out + "_dump", exist_ok=True)
    fj, fc, fx = open(a.out + ".jsonl", "w"), open(a.out + ".csv", "w", newline=""), open(a.out + ".x.jsonl", "w")
    w = csv.writer(fc)
    w.writerow(CSV_COLS)
    rec = Recover("seyond", 256)
    heap, seen, n = [], set(), 0
    log = {"order_violations": 0, "duplicates": 0}
    t0, cpu0, n_bytes = time.time(), time.process_time(), 0
    last = None

    def emit(ts, data):
        nonlocal n
        msg, stamp, res, dec_ms, det_ms = rep.process_raw(data, "/iv_points", n)
        r = record(n, ts / 1e9, stamp, res, dec_ms, det_ms, msg.header.frame_id, "/iv_points")
        fj.write(json.dumps(r) + "\n")
        w.writerow(csv_row(r))
        det = rep.detector
        tracks = {t.id: t for t in det.tracker.tracks}
        x = {"i": n, "track": res.track.to_dict(), "low_range": round(float(det.low_range), 1), "dets": []}
        for d in list(res.detections) + list(res.warnings):
            t = tracks.get(d.id)
            if t is None or t.last is None:
                continue
            c = t.last
            x["dets"].append({"id": d.id, "zone": d.zone, "reason": d.reason, "kind": c.kind, "creason": c.reason,
                              "czone": c.zone, "d": round(float(c.distance), 2), "lat": round(float(c.lateral), 3),
                              "top": round(float(c.height_max), 3), "hmin": round(float(c.height_min), 3),
                              "size": [round(float(v), 3) for v in c.size], "n": int(c.n), "n_gauge": int(c.n_gauge),
                              "hits": int(t.hits), "misses": int(t.misses), "zone_hist": [int(v) for v in t.zone_hist],
                              "age": int(t.age), "centroid": [round(float(v), 3) for v in c.centroid]})
        fx.write(json.dumps(x) + "\n")
        if n in dump:
            xyz = det._frame_xyz
            dy_all, h_all = det._frame_hd
            own = {str(d.id): tracks[d.id].last.points_idx for d in list(res.detections) + list(res.warnings)
                   if d.id in tracks and tracks[d.id].last is not None and tracks[d.id].misses == 0}
            np.savez_compressed(f"{a.out}_dump/f{n:05d}.npz", xyz=xyz.astype(np.float32),
                                dy=np.asarray(dy_all, np.float32), h=np.asarray(h_all, np.float32),
                                **{f"own_{k}": v for k, v in own.items()})
        n += 1

    def release(force=False):
        nonlocal last
        while heap and (force or len(heap) > 50):
            ts, data = heapq.heappop(heap)
            if last is not None and ts < last:
                log["order_violations"] += 1
            last = ts
            emit(ts, data)
            if a.limit and n >= a.limit:
                return True
        return False

    done = False
    for chunk in byte_stream(a.src, "falcon_test.zst", "falcon_test_second_dark_0.db3"):
        n_bytes += len(chunk)
        for topic_id, ts, data in rec.feed(chunk):
            if topic_id != 3:
                continue
            if ts in seen:
                log["duplicates"] += 1
                continue
            seen.add(ts)
            heapq.heappush(heap, (ts, data))
        if release():
            done = True
            break
    if not done:
        for topic_id, ts, data in rec.feed(b"", final=True):
            if topic_id == 3 and ts not in seen:
                seen.add(ts)
                heapq.heappush(heap, (ts, data))
        release(force=True)
    meta = {"src": a.src, "bytes": n_bytes, "found": rec.found, "kept": rec.kept, "lost": rec.lost, **log,
            "frames": n, "set": a.set, "repo": str(ROOT), "resets": rep.resets,
            "wall_s": round(time.time() - t0, 1), "cpu_s": round(time.process_time() - cpu0, 1),
            "rss_peak_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)}
    for f in (fj, fc, fx):
        f.close()
    json.dump(meta, open(a.out + ".meta.json", "w"), indent=1)
    print(json.dumps(meta))
    return 0


if __name__ == "__main__":
    sys.exit(main())
