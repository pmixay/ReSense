#!/usr/bin/env python3
"""Play the cached Falcon messages (cache_falcon_raw.py) through ONE node replica of the checkout named by
RESENSE_REPO (resense.__file__ is checked) and write, per frame, the judge record plus the clear-distance
terms and the track state, and the ROS node's non-legacy range path (decision_policy.candidate_ranges,
policies conservative and small_candidate, sensor model falcon_prime) replayed read-only on the result.
Nothing here changes the detector; the node path is called after the frame is processed.

    run_falcon.py /data/falcon/raw.bin --out OUT [--set section.key=value ...] [--limit N] [--dump 4396,4405]
Writes OUT.jsonl (judge records, every field the P4 falcon_pair 'on' replica writes), OUT.x.jsonl (terms),
OUT.c.jsonl (node range path), OUT.meta.json and, for --dump, OUT_dump/f<frame>.npz (vehicle-frame cloud,
corridor coordinates, rail model).
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse, json, struct, sys, time  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(os.environ["RESENSE_REPO"])
for p in (ROOT, ROOT / "scripts", ROOT / "ros2_ws/src/resense_ros", ROOT / "docs/evidence/judgement_2026-10-13/scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np  # noqa: E402
import yaml  # noqa: E402
import resense  # noqa: E402
from judge_runner import NodeReplica, record  # noqa: E402
from resense_ros.decision_policy import DecisionPolicy, candidate_ranges, evaluate_decision  # noqa: E402

assert Path(resense.__file__).resolve().is_relative_to(ROOT.resolve()), (resense.__file__, ROOT)


def bed_excess(det):
    """Read-only trace: the largest excess of |model rail head - calibrated mount plane| over the H' tolerance
    (cluster.mount_cross_tol + mount_cross_grade * X) at X = 5, 10 .. 30 m; None without a final mount calibration."""
    st = det.calib.state
    if st.height is None or st.status not in ("ok", "identity") or not np.isfinite(st.height):
        return None
    xs = np.arange(5.0, 30.01, 5.0)
    cc = det.cfg.cluster
    return round(float((np.abs(np.asarray(det.track.rail_z(xs)) + float(st.height))
                        - (cc.mount_cross_tol + cc.mount_cross_grade * xs)).max()), 3)


def messages(path):
    import zstandard
    with open(path, "rb") as raw:
        f = zstandard.ZstdDecompressor().stream_reader(raw) if path.endswith(".zst") else raw
        while True:
            h = f.read(12)
            if not h:
                return
            ts, n = struct.unpack("<qI", h)
            b = bytearray()
            while len(b) < n:
                part = f.read(n - len(b))
                if not part:
                    raise EOFError("truncated cache")
                b += part
            yield ts, bytes(b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("--out", required=True)
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--first", type=int, default=0, help="skip nothing; only write dumps from this frame on")
    ap.add_argument("--dump", default="")
    a = ap.parse_args()
    overrides = {}
    for s in a.set:
        k, v = s.split("=", 1)
        overrides[k] = yaml.safe_load(v)
    rep = NodeReplica(overrides=overrides)
    policy = DecisionPolicy()
    dump = {int(v) for v in a.dump.split(",") if v}
    if dump:
        os.makedirs(a.out + "_dump", exist_ok=True)
    fj, fx, fc = (open(f"{a.out}{s}", "w") for s in (".jsonl", ".x.jsonl", ".c.jsonl"))
    t0 = time.time()
    n = 0
    for ts, data in messages(a.raw):
        msg, stamp, res, dec_ms, det_ms = rep.process_raw(data, "/iv_points", n)
        det = rep.detector
        r = record(n, ts / 1e9, stamp, res, dec_ms, det_ms, msg.header.frame_id, "/iv_points")
        fj.write(json.dumps(r) + "\n")
        h = res.health
        tr = res.track
        tracks = {t.id: t for t in det.tracker.tracks}
        x = {"i": n, "clear_raw": float(res.clear_distance), "monitored": h.get("monitored_range"),
             "visibility": h.get("visibility"), "candidate_distance": h.get("candidate_distance"),
             "wall_drift": h.get("wall_drift"), "nearest": res.nearest_distance,
             "rail_score": float(tr.rail_score), "rail_lock": h.get("rail_lock"),
             "floor_range": [float(v) for v in tr.floor_range], "floor_verified": float(tr.floor_verified),
             "axis_valid": float(tr.axis_valid), "floor_shadow": float(getattr(tr, "floor_shadow", 0.0)),
             "floor_held": bool(getattr(tr, "floor_held", False)),
             "rail_slabs": int(tr.rail_slabs), "msgs": h.get("messages", []), "level": h.get("level"),
             "n_cl": len(res.candidates), "rule": getattr(det.health, "last_clear_rule", None),
             "bed_excess": bed_excess(det),
             "cl_gauge": [{"d": round(float(c.distance), 2), "lat": round(float(c.lateral), 2), "n": int(c.n),
                           "n_gauge": int(c.n_gauge), "kind": c.kind, "reason": c.reason, "zone": c.zone,
                           "hmin": round(float(c.height_min), 2), "hmax": round(float(c.height_max), 2)}
                          for c in sorted(res.candidates, key=lambda c: c.distance)[:6] if c.distance < 15.0]}
        fx.write(json.dumps(x) + "\n")
        base = {"obstacle": bool(res.obstacle), "warning": bool(res.warning), "health": res.health,
                "clear_distance": float(res.clear_distance), "freshness": {"valid": True},
                "warnings": [{"distance": float(w.distance), "zone": w.zone, "reason": w.reason,
                              "size": [float(v) for v in w.size], "kind": w.kind} for w in res.warnings]}
        c = {"i": n, "decision": evaluate_decision(res, policy).decision, "detector_clear": float(res.clear_distance),
             "monitored": h.get("monitored_range")}
        for pol in ("conservative", "small_candidate"):
            p = candidate_ranges(base, policy, sensor_model="falcon_prime",
                                 min_points_far=rep.cfg.cluster.min_points_far, max_range=rep.cfg.sensor.max_range,
                                 cap_small_target=True,
                                 profile="conservative_2026_10_17" if pol == "conservative" else "candidate")
            c[pol] = {"clear": p["clear_distance"], "monitored_small": p["monitored_small"],
                      "decision": evaluate_decision(p, policy).decision}
        fc.write(json.dumps(c) + "\n")
        if n in dump:
            dy_all, h_all = det._frame_hd
            grid = np.arange(0.0, 60.01, 0.5)
            st = det.calib.state
            np.savez_compressed(f"{a.out}_dump/f{n:05d}.npz", xyz=det._frame_xyz.astype(np.float32),
                                dy=np.asarray(dy_all, np.float32), h=np.asarray(h_all, np.float32), grid=grid,
                                rail_z=np.asarray(det.track.rail_z(grid), np.float64),
                                plane=np.float64(-st.height if st.height is not None else np.nan),
                                corridor_idx=np.asarray(res.corridor_idx, np.int64),
                                cl_meta=np.asarray(json.dumps([
                                    {"k": k, "d": round(float(c.distance), 2), "lat": round(float(c.lateral), 2), "n": int(c.n),
                                     "n_gauge": int(c.n_gauge), "zone": c.zone, "reason": c.reason, "kind": c.kind,
                                     "hmin": round(float(c.height_min), 2), "hmax": round(float(c.height_max), 2),
                                     "track": next(({"id": t.id, "hits": int(t.hits), "misses": int(t.misses),
                                                     "reported": bool(t.reported), "zone": t.zone}
                                                    for t in det.tracker.tracks if t.last is c), None)}
                                    for k, c in enumerate(res.candidates)])),
                                **{f"cl_{k}": np.asarray(c.points_idx, np.int64) for k, c in enumerate(res.candidates)
                                   if c.points_idx is not None and c.points_idx.size})
        n += 1
        if a.limit and n >= a.limit:
            break
    for f in (fj, fx, fc):
        f.close()
    meta = {"raw": a.raw, "frames": n, "repo": str(ROOT), "resense_file": resense.__file__, "set": a.set,
            "resets": rep.resets, "wall_s": round(time.time() - t0, 1)}
    json.dump(meta, open(a.out + ".meta.json", "w"), indent=1)
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
