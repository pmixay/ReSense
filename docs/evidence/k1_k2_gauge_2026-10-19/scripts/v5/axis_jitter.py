#!/usr/bin/env python3
"""Axis lateral at X m from the per-frame gate rows (track: center, yaw, curvature, curv_step, curv_knot) and its
frame-to-frame change, per recording file group.   axis_jitter.py <gatework> [<gatework> ...]
Groups: the ride's set F files (46,68,98,140,168,172; frames of those splits), the whole ride, roundT_squareT."""
import glob, json, os, sys
import numpy as np

def cy(t, X):
    c, yaw, k = t["center"], t["yaw"], t["curvature"]
    y = c + np.tan(yaw) * X + 0.5 * k * X * X
    s, kn = t.get("curv_step", 0.0), t.get("curv_knot", 0.0)
    d = max(X - kn, 0.0)
    return y + 0.5 * s * d * d, 0.5 * s * d * d

def rows_of(wd, pat):
    out = []
    for f in sorted(glob.glob(os.path.join(wd, pat)), key=lambda p: int(p.rsplit("_", 1)[1].split(".")[0]) if p.rsplit("_", 1)[1].split(".")[0].isdigit() else 0):
        out += [json.loads(l) for l in open(f)]
    return out

SETF = {"46", "68", "98", "140", "168", "172"}
for wd in sys.argv[1:]:
    ride = rows_of(wd, "new_data_*.jsonl")
    groups = {"ride_setF_files": [r for r in ride if r["frame_id"].split("_")[2] in SETF],
              "ride_all": ride,
              "roundT_squareT": rows_of(wd, "roundT_squareT_pressureGate_squareT.jsonl"),
              "roundT_pressureGate_roundT(C)": rows_of(wd, "roundT_pressureGate_roundT.jsonl")}
    print(wd)
    for g, rows in groups.items():
        for X in (100.0, 150.0):
            ys = np.array([cy(r["track"], X)[0] for r in rows])
            st = np.array([cy(r["track"], X)[1] for r in rows])
            # frame-to-frame within the same split (ride) only
            ids = [r["frame_id"].rsplit("_", 1)[0] for r in rows]
            dy = np.array([abs(ys[i] - ys[i - 1]) for i in range(1, len(ys)) if ids[i] == ids[i - 1]])
            bent = np.mean(np.abs(st) > 1e-9)
            print(f"  {g:32s} X={X:5.0f}  |dY| p50 {np.median(dy):.3f} p90 {np.percentile(dy,90):.3f}  "
                  f"step part |.| p50 {np.median(np.abs(st)):.3f} p90 {np.percentile(np.abs(st),90):.3f} max {np.abs(st).max():.2f}  bent {bent:.2f}  n {len(rows)}")
