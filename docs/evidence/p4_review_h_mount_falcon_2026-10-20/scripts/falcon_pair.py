#!/usr/bin/env python3
"""The whole Falcon recording through TWO node replicas in one pass of the stream (P4 review of H′ and the
Falcon clear-distance model, 20.10):

* ``on``: the shipped configuration, with ``Detector._mount_cross_check`` (H′) wrapped read-only: after the
  original returns, every cluster it looked at (zone gauge, no reason, within ``mount_cross_range``, with points)
  is recorded with its distance, lateral, the model rail head ``track.rail_z(X)``, the mount plane, the
  disagreement and its threshold, the cluster's heights above the plane, and whether H′ made it advisory
  (``height_conflict``). Its per-frame records must equal the committed shipped run
  (``l16_acceptance_2026-10-20/out/falcon/l16.jsonl``, every non-timing field) before any attribution is used.
* ``off``: ``--set`` overrides (default ``cluster.mount_cross_tol=0``, H′ off), no hook.

Per frame and replica the records of ``falcon_trace.py`` are written (``<out>.<on|off>.jsonl``, ``.x.jsonl``, the
same code). The H′ hook goes to ``<out>.h.jsonl``. For the clear-distance model, on the ``on`` replica's result
the ROS node's own non-legacy path (``detector_node.py``: ``candidate_ranges`` after ``evaluate_decision``) is
replayed read-only for ``clear_range_policy`` conservative and small_candidate, with ``range_sensor_model``
``falcon_prime`` (shipped) and ``unknown`` (the model off: before 19.10 ``falcon_prime`` had no density limit,
the same as ``unknown``), into ``<out>.c.jsonl``. Calls of ``small_target_limit``, ``candidate_ranges`` and
``falcon_expected_points`` made while a replica processes a frame are counted (the replicas must make none).
A frame is dumped (``<out>_dump/f<frame>.<on|off>.npz``) when the replicas differ in decision, detections or
warnings, or when H′ demoted a cluster.

    falcon_pair.py <src: Yandex link | local falcon_test.zst | /dev/stdin> --out OUT --ref l16.jsonl[.xz] [--set k=v]
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
import heapq  # noqa: E402
import json  # noqa: E402
import lzma  # noqa: E402
import resource  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(os.environ["RESENSE_REPO"])
for p in (ROOT, ROOT / "scripts", ROOT / "ros2_ws/src/resense_ros",
          ROOT / "docs/evidence/judgement_2026-10-13/scripts",
          ROOT / "docs/evidence/extended_data_2026-10-17/scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np  # noqa: E402

from stream_falcon import Recover, byte_stream  # noqa: E402

TIMING = {"decode_ms", "detect_ms", "total_ms"}
COUNT = {"active": False, "small_target_limit": 0, "candidate_ranges": 0, "falcon_expected_points": 0}


def r3(v):
    return None if v is None else round(float(v), 3)


def install_counters():
    import resense.sensor as sensor
    from resense_ros import decision_policy as dp

    def counted(mod, name):
        orig = getattr(mod, name)

        def f(*a, **k):
            if COUNT["active"]:
                COUNT[name] += 1
            return orig(*a, **k)
        setattr(mod, name, f)

    counted(dp, "small_target_limit")
    counted(dp, "candidate_ranges")
    counted(sensor, "falcon_expected_points")
    # positive control: the node path, called with the flag up, must be counted
    COUNT["active"] = True
    dp.candidate_ranges({"health": {"monitored_range": 100.0, "level": "ok"}, "clear_distance": 100.0},
                        "v1", sensor_model="falcon_prime", cap_small_target=True, max_range=250.0)
    COUNT["active"] = False
    control = {k: COUNT[k] for k in ("small_target_limit", "candidate_ranges", "falcon_expected_points")}
    for k in control:
        COUNT[k] = 0
    return control


def hook_h(det, sink):
    orig = det._mount_cross_check

    def wrapped(clusters, xyz):
        before = [(c.zone, c.reason) for c in clusters]
        orig(clusters, xyz)
        cc, st = det.cfg.cluster, det.calib.state
        ok = st.height is not None and st.status in ("ok", "identity") and np.isfinite(st.height)
        rows = []
        if ok:
            plane = -float(st.height)
            top = float(np.asarray(det.cfg.gauge.profile, dtype=np.float64)[:, 1].max())
            for k, cl in enumerate(clusters):
                z0, r0 = before[k]
                if z0 != "gauge" or r0 or cl.distance > cc.mount_cross_range or not cl.points_idx.size:
                    continue
                x = float(cl.distance)
                rz = float(det.track.rail_z(x))
                hm = xyz[cl.points_idx, 2].astype(np.float64) - plane
                rows.append({"k": k, "d": r3(x), "lat": r3(cl.lateral), "kind": cl.kind, "n": int(cl.n),
                             "size": [r3(v) for v in cl.size], "centroid": [r3(v) for v in cl.centroid],
                             "rail_z": r3(rz), "plane": r3(plane), "diff": r3(abs(rz - plane)),
                             "thr": r3(cc.mount_cross_tol + cc.mount_cross_grade * x),
                             "hm_min": r3(hm.min()), "hm_max": r3(hm.max()), "top": r3(top),
                             "h_model_min": r3(float(cl.height_min)), "h_model_max": r3(float(cl.height_max)),
                             "demoted": cl.reason == "height_conflict", "idx": cl.points_idx})
        sink.append({"ok": bool(ok), "status": st.status, "rows": rows})
    det._mount_cross_check = wrapped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref", required=True, help="the shipped run's per-frame records (jsonl or jsonl.xz)")
    ap.add_argument("--set", action="append", default=[], help="override of the off replica, section.key=value")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    import yaml
    from judge_runner import NodeReplica, record
    from resense_ros.decision_policy import DecisionPolicy, candidate_ranges, evaluate_decision
    control = install_counters()
    sets = a.set or ["cluster.mount_cross_tol=0"]
    overrides = {}
    for s in sets:
        k, v = s.split("=", 1)
        overrides[k] = yaml.safe_load(v)
    reps = {"on": NodeReplica(), "off": NodeReplica(overrides=overrides)}
    opener = lzma.open if a.ref.endswith(".xz") else open
    with opener(a.ref, "rt") as f:
        ref = [json.loads(line) for line in f]
    policy = DecisionPolicy()
    os.makedirs(a.out + "_dump", exist_ok=True)
    fj = {k: open(f"{a.out}.{k}.jsonl", "w") for k in reps}
    fx = {k: open(f"{a.out}.{k}.x.jsonl", "w") for k in reps}
    fh, fc = open(a.out + ".h.jsonl", "w"), open(a.out + ".c.jsonl", "w")
    rec = Recover("seyond", 256)
    heap, seen, n = [], set(), 0
    log = {"order_violations": 0, "duplicates": 0, "ref_differ_on": 0, "pair_differ": 0, "dumped": 0}
    t0, cpu0, n_bytes, last = time.time(), time.process_time(), 0, None
    det_ids = {"on": None, "off": None}

    def xrec(rep, res, i):
        det = rep.detector
        tracks = {t.id: t for t in det.tracker.tracks}
        x = {"i": i, "track": res.track.to_dict(), "low_range": round(float(det.low_range), 1), "dets": []}
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
        return x

    def dump(tag, rep, res, i, hrows):
        det = rep.detector
        tracks = {t.id: t for t in det.tracker.tracks}
        dy_all, h_all = det._frame_hd
        own = {str(d.id): tracks[d.id].last.points_idx for d in list(res.detections) + list(res.warnings)
               if d.id in tracks and tracks[d.id].last is not None and tracks[d.id].misses == 0}
        grid = np.arange(0.0, 60.01, 0.5)
        st = det.calib.state
        extra = {f"hm_{r['k']}": r["idx"] for r in hrows}
        np.savez_compressed(f"{a.out}_dump/f{i:05d}.{tag}.npz", xyz=det._frame_xyz.astype(np.float32),
                            dy=np.asarray(dy_all, np.float32), h=np.asarray(h_all, np.float32),
                            grid=grid, rail_z=np.asarray(det.track.rail_z(grid), np.float64),
                            plane=np.float64(-st.height if st.height is not None else np.nan),
                            **{f"own_{k}": v for k, v in own.items()}, **extra)

    def emit(ts, data):
        nonlocal n
        out = {}
        for tag, rep in reps.items():
            sink = []
            if tag == "on":
                if det_ids["on"] != id(rep.detector):     # a new Detector after a reset: hook it again
                    hook_h(rep.detector, sink_holder)
                    det_ids["on"] = id(rep.detector)
            sink_holder.clear()
            COUNT["active"] = True
            msg, stamp, res, dec_ms, det_ms = rep.process_raw(data, "/iv_points", n)
            COUNT["active"] = False
            if tag == "on" and det_ids["on"] != id(rep.detector):
                raise RuntimeError("detector replaced during process_raw")
            sink = list(sink_holder)
            r = record(n, ts / 1e9, stamp, res, dec_ms, det_ms, msg.header.frame_id, "/iv_points")
            out[tag] = (rep, res, r, sink)
            fj[tag].write(json.dumps(r) + "\n")
            fx[tag].write(json.dumps(xrec(rep, res, n)) + "\n")
        rep, res, r, sink = out["on"]
        hrows = [row for s in sink for row in s["rows"]]
        fh.write(json.dumps({"i": n, "calls": len(sink), "ok": [s["ok"] for s in sink],
                             "status": [s["status"] for s in sink],
                             "rows": [{k: v for k, v in row.items() if k != "idx"} for row in hrows]}) + "\n")
        strip = lambda x: {k: v for k, v in x.items() if k not in TIMING}  # noqa: E731
        if n >= len(ref) or strip(ref[n]) != strip(r):
            log["ref_differ_on"] += 1
        # the node's non-legacy clear range on the shipped result, model on (falcon_prime) and off (unknown)
        base = {"obstacle": bool(res.obstacle), "warning": bool(res.warning), "health": res.health,
                "clear_distance": float(res.clear_distance), "freshness": {"valid": True},
                "warnings": [{"distance": float(w.distance), "zone": w.zone, "reason": w.reason,
                              "size": [float(v) for v in w.size], "kind": w.kind} for w in res.warnings]}
        dec = evaluate_decision(res, policy).decision
        c = {"i": n, "decision": dec, "detector_clear": round(float(res.clear_distance), 3),
             "monitored": res.health.get("monitored_range")}
        for pol in ("conservative", "small_candidate"):
            for model in ("falcon_prime", "unknown"):
                p = candidate_ranges(base, policy, sensor_model=model,
                                     min_points_far=rep.cfg.cluster.min_points_far, max_range=rep.cfg.sensor.max_range,
                                     cap_small_target=True,
                                     profile="conservative_2026_10_17" if pol == "conservative" else "candidate")
                c[f"{pol}.{model}"] = {"clear": p["clear_distance"], "monitored_small": p["monitored_small"],
                                       "decision": evaluate_decision(p, policy).decision}
        fc.write(json.dumps(c) + "\n")
        key = lambda x: (x["decision"], x["dets"], x["warns"])  # noqa: E731
        differ = key(out["on"][2]) != key(out["off"][2])
        log["pair_differ"] += differ
        if differ or any(row["demoted"] for row in hrows):
            log["dumped"] += 1
            dump("on", *out["on"][:2], n, hrows)
            dump("off", *out["off"][:2], n, [])
        n += 1

    sink_holder = []

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
            "frames": n, "ref_frames": len(ref), "set_off": sets, "repo": str(ROOT),
            "resets": {k: r.resets for k, r in reps.items()},
            "counter_control": control,
            "replica_calls": {k: COUNT[k] for k in ("small_target_limit", "candidate_ranges", "falcon_expected_points")},
            "wall_s": round(time.time() - t0, 1), "cpu_s": round(time.process_time() - cpu0, 1),
            "rss_peak_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)}
    for f in (*fj.values(), *fx.values(), fh, fc):
        f.close()
    json.dump(meta, open(a.out + ".meta.json", "w"), indent=1)
    print(json.dumps(meta))
    return 0


if __name__ == "__main__":
    sys.exit(main())
