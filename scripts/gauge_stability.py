#!/usr/bin/env python3
"""B6: gauge range and stability (experts' criteria 2 and 3), measured against the path the train drives.

    gauge_stability.py poses <decoded cache> <poses.json> [--end N]
    gauge_stability.py track <decoded cache> <track.json> [--end N]      (RESENSE_REPO / PYTHONPATH = checkout)
    gauge_stability.py measure <track.json> <poses.json> <out.json>

``poses``: frame-to-frame ICP (open3d point-to-plane on 0.15 m voxels of the 3-80 m part, the judge's
``icp_odometry.py`` settings) keeping the full 4x4 motion, so the poses of all frames can be composed.
``track``: the detector's own track model per frame through the judge's node replica (``range_test.run_frame``):
centre, yaw, curvature, trusted range ``axis_valid``, the mount rotation and the node decision.
``measure``:

* **range** (criterion 2): the trusted range ``min(axis_valid, gauge.range_max)`` per frame;
* **blink / disappear** (criterion 3): frames without a track model, frames whose trusted range falls by at
  least half in one frame and recovers within 10 frames, frame-to-frame change of the drawn axis lateral
  at 40 / 80 / 120 m (the N1 acceptance metric);
* **off the tracks** (criterion 3): the axis lateral at 20 / 40 / 80 / 120 m against the **driven path**: the
  sensor positions of later frames, composed from the ICP poses and brought into the detector's frame
  (mount rotation of that frame). Both are taken relative to x = 0, so the sensor's lateral offset from the
  track centre cancels. The 8-25 m bin is the control: there the axis comes from the rails in view, so a
  large error there means the driven-path truth (ICP drift), not the detector, is wrong.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
JUDGE = ROOT / "docs/evidence/judgement_2026-10-13/scripts"
XS = (20.0, 40.0, 80.0, 120.0)
BINS = [(8, 25), (25, 40), (40, 60), (60, 80), (80, 100), (100, 120), (120, 150), (150, 200)]


def cache_files(cache, end):
    files = sorted(glob.glob(os.path.join(cache, "f_*.npz")))
    return files[:end] if end else files


def poses(a):
    import open3d as o3d
    sys.path.insert(0, str(JUDGE))
    from judge_runner import NodeReplica
    R = NodeReplica().R_vs

    def pcd_of(f):
        xyz = np.load(f)["xyz"].astype(np.float64) @ R.T
        m = (xyz[:, 0] > 3) & (xyz[:, 0] < 80) & (np.abs(xyz[:, 1]) < 6)
        pc = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(xyz[m]))
        pc = pc.voxel_down_sample(0.15)
        pc.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.6, max_nn=20))
        return pc

    rows, prev, guess = [], None, np.eye(4)
    for k, f in enumerate(cache_files(a.cache, a.end)):
        cur = pcd_of(f)
        if prev is None or len(cur.points) < 2000 or len(prev.points) < 2000:
            rows.append({"i": k, "T": None, "fitness": 0.0})
        else:
            reg = o3d.pipelines.registration.registration_icp(
                cur, prev, 0.5, guess, o3d.pipelines.registration.TransformationEstimationPointToPlane(),
                o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=40))
            guess = reg.transformation.copy()
            rows.append({"i": k, "T": np.round(reg.transformation, 7).tolist(), "fitness": round(float(reg.fitness), 4)})
        if len(cur.points) >= 2000:
            prev = cur
    json.dump({"cache": a.cache, "rows": rows}, open(a.out, "w"))
    print(a.out, len(rows), "frames")


def track(a):
    sys.path.insert(0, str(JUDGE))
    from judge_runner import NodeReplica, node_decision
    from range_test import run_frame
    meta = json.loads(Path(a.cache, "meta.json").read_text())
    rep = NodeReplica()
    range_max = float(rep.detector.cfg.gauge.range_max)
    rows = []
    for k, f in enumerate(cache_files(a.cache, a.end)):
        d = np.load(f)
        res = run_frame(rep, d["xyz"], d["inten"], d["ring"], meta[k], k)
        t = res.track
        row = {"i": k, "decision": node_decision(res), "R": np.round(rep.detector.mount_rotation, 7).tolist()}
        if t is not None:
            row.update(center=float(t.center), tan_yaw=float(np.tan(t.yaw)), half_curv=float(0.5 * t.curvature),
                       axis_valid=float(t.axis_valid))
        rows.append(row)
    json.dump({"cache": a.cache, "repo": os.environ.get("RESENSE_REPO", ""), "range_max": range_max,
               "rows": rows}, open(a.out, "w"))
    print(a.out, len(rows), "frames")


def lateral(r, x):
    return r["center"] + r["tan_yaw"] * x + r["half_curv"] * x * x


def driven_path(prows):
    """(segment, 4x4 pose) of every frame. A frame without a registration to its predecessor starts a new
    segment at the identity; poses are only comparable within one segment."""
    seg, P, out = 0, np.eye(4), []
    for k, r in enumerate(prows):
        if r["T"] is None:
            if k:
                seg += 1
            P = np.eye(4)
        else:
            P = P @ np.array(r["T"])
        out.append((seg, P.copy()))
    return out


def pct(v, qs=(50, 90)):
    v = np.asarray(v, dtype=float)
    return {f"p{q}": round(float(np.percentile(v, q)), 3) for q in qs} | {"n": int(v.size)} if v.size else {"n": 0}


def measure(a):
    tr = json.load(open(a.track))
    rows = tr["rows"]
    rmax = tr["range_max"]
    ps = driven_path(json.load(open(a.poses))["rows"])
    n = len(rows)
    have = [r for r in rows if "center" in r]
    rng = [min(r["axis_valid"], rmax) for r in have]
    # blinks: trusted range halves in one frame and recovers within 10 frames
    blinks = 0
    for k in range(1, n):
        a0, a1 = rows[k - 1].get("axis_valid"), rows[k].get("axis_valid")
        if a0 is None or a1 is None or min(a1, rmax) > 0.5 * min(a0, rmax):
            continue
        ahead = [rows[j].get("axis_valid") for j in range(k + 1, min(n, k + 11))]
        if any(v is not None and min(v, rmax) >= 0.9 * min(a0, rmax) for v in ahead):
            blinks += 1
    jitter = {}
    for x in (40.0, 80.0, 120.0):
        allf, trusted = [], []
        for k in range(1, n):
            r0, r1 = rows[k - 1], rows[k]
            if "center" in r0 and "center" in r1:
                d = abs(lateral(r1, x) - lateral(r0, x))
                allf.append(d)
                if min(r1["axis_valid"], rmax) >= x:
                    trusted.append(d)
        jitter[f"{int(x)}m"] = {"all": pct(allf), "within_trusted": pct(trusted)}
    # error against the driven path
    err = {f"{lo}-{hi}": {"in": [], "out": []} for lo, hi in BINS}
    for k, r in enumerate(rows):
        if "center" not in r:
            continue
        seg, Pk = ps[k]
        Pk_inv = np.linalg.inv(Pk)
        Rk = np.array(r["R"])
        pts = [np.zeros(3)]
        for j in range(k + 1, n):
            if ps[j][0] != seg:
                break
            p = Rk @ (Pk_inv @ ps[j][1])[:3, 3]
            pts.append(p)
            if p[0] > BINS[-1][1]:
                break
        pts = np.array(pts)
        pts = pts[pts[:, 0] >= np.maximum.accumulate(pts[:, 0])]      # the train does not reverse
        _, first = np.unique(pts[:, 0], return_index=True)
        pts = pts[np.sort(first)]
        if len(pts) < 2:
            continue
        for lo, hi in BINS:
            x = 0.5 * (lo + hi)
            if pts[-1, 0] < x or pts[0, 0] > x:
                continue
            y_true = float(np.interp(x, pts[:, 0], pts[:, 1]))
            e = (lateral(r, x) - r["center"]) - y_true
            err[f"{lo}-{hi}"]["in" if min(r["axis_valid"], rmax) >= x else "out"].append(abs(e))
    offtrack = {}
    for key, v in err.items():
        both = v["in"] + v["out"]
        offtrack[key] = {"within_trusted": pct(v["in"], (50, 90, 99)), "beyond_trusted": pct(v["out"], (50, 90, 99)),
                         "share_over_0.5m": round(float(np.mean(np.array(both) > 0.5)), 3) if both else None,
                         "share_over_1.05m": round(float(np.mean(np.array(both) > 1.05)), 3) if both else None}
    out = {"track": a.track, "poses": a.poses, "frames": n, "frames_without_track": n - len(have),
           "decisions": {d: sum(r["decision"] == d for r in rows) for d in sorted({r["decision"] for r in rows})},
           "range": pct(rng, (10, 50, 90)) | {f"share_ge_{x}m": round(float(np.mean(np.array(rng) >= x)), 3)
                                              for x in (60, 100, 150)},
           "blinks": blinks, "jitter": jitter, "offtrack": offtrack,
           "path_segments": ps[-1][0] + 1 if ps else 0}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("poses", "track"):
        s = sub.add_parser(name)
        s.add_argument("cache")
        s.add_argument("out")
        s.add_argument("--end", type=int, default=0)
    m = sub.add_parser("measure")
    m.add_argument("track")
    m.add_argument("poses")
    m.add_argument("out")
    a = ap.parse_args()
    {"poses": poses, "track": track, "measure": measure}[a.cmd](a)


if __name__ == "__main__":
    main()
