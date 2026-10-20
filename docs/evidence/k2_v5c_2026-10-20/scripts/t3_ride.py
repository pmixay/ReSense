"""T3, ride part: for strict detections K2 removes at 30-60 m (k2_removed.py rows), which axis do the rails support?

Replays one gate piece (``eval_real.run_piece``'s loop: the gate's cache files, stamps and config, a fresh detector)
twice, K2 off and variant B (``--set``), and for the listed rows saves the cloud in the detector frame with each
return's corridor lateral and height (``_frame_hd``), the output track model and the strict detections. Then, per
row and detection of the K2-off run: the rail-head returns (|h| < 0.06 m) in front of the detection (from
max(4, d - 25) m to d - 1 m), split into the two rails by their lateral from the K2-off axis (0.45-1.15 m; selection
only), each fitted as a robust line in absolute Y, the midpoint extrapolated to the detection's distance; accepted
when the fitted gauge is within 0.08 m of 1.52 m and each rail has >= 8 returns. Printed: each axis at the detection
minus that midpoint, and the detection's lateral from the midpoint (the true axis) next to its laterals from both
axes. Each piece's per-frame rows must equal the gate's (checked here against the gate work files, every field but
timing).

    RESENSE_REPO=<tree> python t3_ride.py <cache dir> <gate work off> <gate work K2> <piece, e.g. new_data_4> <rows>
        <out prefix> [--set k=v ...]  (the --set values define the K2 run)
"""
import json
import os
import pickle
import sys

import numpy as np

ROOT = os.environ["RESENSE_REPO"]
for p in (ROOT, os.path.join(ROOT, "scripts")):
    sys.path.insert(0, p)
import yaml  # noqa: E402

cache, work_off, work_k2, piece, rows_arg, out = sys.argv[1:7]
sets = []
it = iter(sys.argv[7:])
for a in it:
    if a == "--set":
        sets.append(next(it))
rows = set()
for part in rows_arg.split(","):
    a, _, b = part.partition("-")
    rows.update(range(int(a), int(b or a) + 1))
TIMING = ("timing_ms",)


def replay(set_list):
    import eval_real
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    from scripts.cache_io import cache_file_stem, cache_files, load_cache_array, load_cache_stamps
    name, k = piece.rsplit("_", 1)
    d = os.path.join(cache, name)
    files = np.array_split(np.array(cache_files(d)), 8)[int(k)]
    stamps = load_cache_stamps(d)
    cfg_dict = eval_real.load_cfg_dict(os.path.join(ROOT, "configs", "default.yaml"), set_list)
    cfg = DetectorConfig.from_dict(cfg_dict)
    det = Detector(cfg)
    rec, dumps = [], {}
    for i, f in enumerate(files[: max(rows) + 1]):
        stem = cache_file_stem(f)
        fr = frame_from_compact(load_cache_array(f), cfg.sensor, stamp=stamps.get(stem, i * 0.1), frame_id=stem)
        res = det.process(fr)
        r = res.to_dict()
        r["frame"] = i
        r["frame_id"] = stem
        rec.append(r)
        if i in rows:
            xyz = np.asarray(det._frame_xyz)
            dy, h = (np.asarray(v) for v in det._frame_hd)
            m = (xyz[:, 0] > 0) & (xyz[:, 0] < 90) & (np.abs(xyz[:, 1]) < 6)
            dumps[i] = {"xyz": xyz[m].astype(np.float32), "dy": dy[m].astype(np.float32), "h": h[m].astype(np.float32),
                        "model": res.track, "dets": [d.to_dict() for d in res.detections]}
    return rec, dumps


def check(rec, work):
    ref = [json.loads(line) for _, line in zip(range(len(rec)), open(os.path.join(work, piece + ".jsonl")))]
    strip = lambda r: {k: v for k, v in r.items() if k not in TIMING}  # noqa: E731
    hstrip = lambda r: {**strip(r), "health": {k: v for k, v in (r.get("health") or {}).items()  # noqa: E731
                                               if k not in ("latency_p95_ms", "messages", "level", "decision_level")}}
    return sum(hstrip(a) != hstrip(json.loads(json.dumps(b))) for a, b in zip(ref, rec))


def rails_mid(d, X):
    xyz, h, m_ = d["xyz"], d["h"], d["model"]
    x0, x1 = max(4.0, X - 25.0), X - 1.0
    m = (xyz[:, 0] > x0) & (xyz[:, 0] < x1) & (h > -0.06) & (h < 0.06)
    xs, ya = xyz[m, 0].astype(float), xyz[m, 1].astype(float)
    rel = ya - m_.center_y(xs)
    sides = {"L": (rel > 0.45) & (rel < 1.15), "R": (rel < -0.45) & (rel > -1.15)}
    if min(s.sum() for s in sides.values()) < 8:
        return None
    fits = {}
    for k, s in sides.items():
        p = np.polyfit(xs[s], ya[s], 1)
        for _ in range(3):
            res = ya[s] - np.polyval(p, xs[s])
            keep = np.abs(res) < max(0.05, 2.5 * np.median(np.abs(res)))
            p = np.polyfit(xs[s][keep], ya[s][keep], 1)
        fits[k] = p
    xm = 0.5 * (x0 + x1)
    return {"gauge": float(np.polyval(fits["L"], xm) - np.polyval(fits["R"], xm)),
            "mid": 0.5 * float(np.polyval(fits["L"], X) + np.polyval(fits["R"], X)),
            "n": {k: int(s.sum()) for k, s in sides.items()}, "window": (x0, x1)}


rec_off, dump_off = replay([])
rec_k2, dump_k2 = replay(sets)
print(f"{piece}: replayed {len(rec_off)} frames; rows differing from the gate work (beyond timing/latency): "
      f"off {check(rec_off, work_off)}, K2 {check(rec_k2, work_k2)}")
pickle.dump({"off": dump_off, "k2": dump_k2}, open(out + ".pkl", "wb"))
print(" row   d     window     nL  nR gauge  | off-mid  K2-mid | det from: true   off    K2  | K2 strict det within 2 m")
for i in sorted(rows):
    do, dk = dump_off[i], dump_k2[i]
    for det in do["dets"]:
        if det["zone"] != "gauge" or det["reason"]:
            continue
        X, Y = det["center"][0], det["center"][1]
        f = rails_mid(do, X)
        ao, ak = float(do["model"].center_y(np.array([X]))[0]), float(dk["model"].center_y(np.array([X]))[0])
        kept = any(abs(e["distance"] - det["distance"]) <= 2 and e["zone"] == "gauge" and not e["reason"] for e in dk["dets"])
        if f is None:
            print(f"{i:4d} {det['distance']:5.1f}  rails not measurable | det from: off {Y - ao:+.2f} K2 {Y - ak:+.2f} | {kept}")
            continue
        ok = abs(f["gauge"] - 1.52) < 0.08
        print(f"{i:4d} {det['distance']:5.1f} {f['window'][0]:4.0f}-{f['window'][1]:4.0f} {f['n']['L']:4d} {f['n']['R']:3d} "
              f"{f['gauge']:.3f}{' ' if ok else '?'}| {ao - f['mid']:+.2f}  {ak - f['mid']:+.2f}  | "
              f"{Y - f['mid']:+.2f}  {Y - ao:+.2f} {Y - ak:+.2f} | {kept}")
