#!/usr/bin/env python3
"""The whole Falcon recording, streamed once, through several node replicas (one per config).

Stream recovery as ``scripts/stream_falcon.py`` / ``f1_false_alarms_2026-10-19/scripts/falcon_trace.py``
(same ``Recover``, same order release, same ``judge_runner.NodeReplica`` decode, continuity and decision);
the config of each replica is built in the node's order (``falcon_long_range_2026-10-19/scripts/run_cache.py``
``build_cfg``: YAML, auto_calibrate, ``pre``, the sensor profile, ``set``). Per config ``<out>/<name>.jsonl``:
``judge_runner.record`` plus ``mount_rotation`` (what ``falcon_eval.py`` / ``score_falcon_pos.py`` read).
With ``"rows": true`` also ``<name>.rows.npz``: the track-opinion rows of ``scripts/track_opinion.py collect``
(features of every matched track per frame, rule STOP flag, onset flag, distance, lateral; label 0, the
person is attributed afterwards from the records). Rows need the tracker's observation record, switched on
in that replica only (it does not change a decision: it only appends observations).

    falcon_multi.py https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --out DIR --spec configs.json [--limit N]

``configs.json``: ``[{"name": "ctl_manual", "profile": "manual", "pre": [], "set": [], "rows": false}, ...]``.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
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
import yaml  # noqa: E402

from stream_falcon import Recover, byte_stream  # noqa: E402


def _apply(cfg, sets):
    for s in sets:
        k, v = s.split("=", 1)
        sec, key = k.split(".", 1)
        setattr(getattr(cfg, sec), key, yaml.safe_load(v))


def make_replica(spec):
    from judge_runner import CONFIG, NodeReplica
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import axis_matrix
    from resense_ros.sensor_profiles import apply_sensor_profile
    rep = NodeReplica()
    cfg = DetectorConfig.from_yaml(CONFIG)
    cfg.calibration.enabled = True
    _apply(cfg, spec.get("pre", []))
    cfg, _ = apply_sensor_profile(cfg, spec.get("profile", "manual"))
    _apply(cfg, spec.get("set", []))
    rep.cfg = cfg
    rep.detector = Detector(cfg)
    rep.R_vs = axis_matrix(cfg.sensor).astype(np.float32)
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--out", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    from judge_runner import record
    from resense.opinion import FEATURES, track_features
    specs = json.loads(Path(a.spec).read_text())
    os.makedirs(a.out, exist_ok=True)
    reps = [make_replica(s) for s in specs]
    outs = [open(os.path.join(a.out, s["name"] + ".jsonl"), "w") for s in specs]
    rows = [[] for _ in specs]
    prev = [{} for _ in specs]
    cfgs = [{"name": s["name"], "doubt_model": r.cfg.tracking.doubt_model,
             "doubt_threshold": r.cfg.tracking.doubt_threshold, "doubt_extra_hits": r.cfg.tracking.doubt_extra_hits,
             "max_range": r.cfg.sensor.max_range, "forward": r.cfg.sensor.forward} for s, r in zip(specs, reps)]
    rec = Recover("seyond", 256)
    heap, seen, n = [], set(), 0
    log = {"order_violations": 0, "duplicates": 0}
    t0, n_bytes = time.time(), 0
    last = None
    cpu = [0.0] * len(specs)

    def emit(ts, data):
        nonlocal n
        for k, (s, rep) in enumerate(zip(specs, reps)):
            if s.get("rows"):
                rep.detector.tracker.record = True
            c0 = time.process_time()
            msg, stamp, res, dec_ms, det_ms = rep.process_raw(data, "/iv_points", n)
            cpu[k] += time.process_time() - c0
            r = record(n, ts / 1e9, stamp, res, dec_ms, det_ms, msg.header.frame_id, "/iv_points")
            r["mount_rotation"] = np.asarray(rep.detector.mount_rotation).tolist()
            r["track_detail"] = {"axis_valid": res.track.to_dict().get("axis_valid")}
            outs[k].write(json.dumps(r) + "\n")
            if s.get("rows"):
                if rep.detector.tracker.record is not True:
                    rep.detector.tracker.record = True
                for t in rep.detector.tracker.tracks:
                    stop = bool(t.reported and t.rule_zone == "gauge")
                    was = prev[k].get(t.id, False)
                    prev[k][t.id] = bool(t.reported and t.zone == "gauge")
                    if t.misses or not t.obs or t.last is None:
                        continue
                    f = track_features(t.obs, t.hits, t.hit_fraction)
                    c = t.last.centroid
                    rows[k].append((f, [n, t.id, float(stop), float(stop and not was), t.last.distance,
                                        t.last.lateral, float(c[0]), float(c[1]), float(c[2])]))
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
    for f in outs:
        f.close()
    for k, s in enumerate(specs):
        if s.get("rows"):
            X = np.array([r[0] for r in rows[k]], dtype=np.float32).reshape(-1, len(FEATURES))
            M = np.array([r[1] for r in rows[k]], dtype=np.float64).reshape(-1, 9)
            np.savez_compressed(os.path.join(a.out, s["name"] + ".rows.npz"), X=X, M=M, features=np.array(FEATURES),
                                meta_cols=np.array(["frame", "track", "stop", "onset", "dist", "lat", "cx", "cy", "cz"]))
    meta = {"src": a.src, "bytes": n_bytes, "found": rec.found, "kept": rec.kept, "lost": rec.lost, **log,
            "frames": n, "configs": cfgs, "specs": specs, "repo": str(ROOT), "resets": [r.resets for r in reps],
            "cpu_s": [round(v, 1) for v in cpu], "wall_s": round(time.time() - t0, 1),
            "rss_peak_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)}
    json.dump(meta, open(os.path.join(a.out, "meta.json"), "w"), indent=1)
    print(json.dumps({k: meta[k] for k in ("frames", "found", "kept", "lost", "wall_s", "cpu_s")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
