#!/usr/bin/env python3
"""B6: gauge range and stability (experts' criteria 2 and 3), measured against the path the train drives.

    gauge_stability.py poses <decoded cache> <poses.json> [--end N]
    gauge_stability.py track <decoded cache> <track.json> [--end N]      (RESENSE_REPO / PYTHONPATH = checkout)
    gauge_stability.py measure <track.json> <poses.json> <out.json>
    gauge_stability.py honesty <track.json> <poses.json> <run.jsonl> <out.json>   (the node's monitored range)

``poses``: frame-to-frame ICP (open3d point-to-plane on 0.15 m voxels of the 3-80 m part, the judge's
``icp_odometry.py`` settings) keeping the full 4x4 motion, so the poses of all frames can be composed.
``track``: the detector's own track model per frame through the judge's node replica (``range_test.run_frame``):
centre, yaw, curvature, trusted range ``axis_valid``, the mount rotation and the node decision.
``measure``:

* **range** (criterion 2): the trusted range ``min(axis_valid, gauge.range_max)`` per frame;
* **blink / disappear** (criterion 3): frames without a track model, frames whose trusted range falls by at
  least half in one frame and recovers within 10 frames, frame-to-frame change of the drawn axis lateral
  at 40 / 80 / 120 m (the N1 acceptance metric, ``jitter``; it includes real change where the car's heading to the
  track changes: curve entry and exit, sway) and the same **motion-compensated** (``jitter_compensated``:
  the previous frame's axis moved into the current frame by the ICP motion, so only flicker is left);
* **off the tracks** (criterion 3): the axis lateral at 20 / 40 / 80 / 120 m against the **driven path**: the
  sensor positions of later frames, composed from the ICP poses and brought into the detector's frame
  (mount rotation of that frame). Both are taken relative to x = 0, so the sensor's lateral offset from the
  track centre cancels. The 8-25 m bin is the control: there the axis comes from the rails in view, so a
  large error there means the driven-path truth (ICP drift), not the detector, is wrong. Measured 18.10: this
  holds on curves, but on a platform the detector's near heading can follow a wall that is not parallel to the
  track, so the 8-25 m bin is a detector metric; the truth is validated separately (README of B6).
``honesty``: within the range the node reports (``monitored`` of the run records: health monitored range /
  clear distance), the share of 5 m steps where the axis is more than 0.5 / 1.05 m off the driven path, and the
  same beyond it: a range that ends where the axis leaves the track is honest.
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


def compensated_jitter(rows, prows, x):
    """|axis lateral at x now - previous frame's axis at the same place, moved by the ICP motion|."""
    xs = np.arange(0.0, 260.0, 1.0)
    out = []
    for k in range(1, len(rows)):
        r0, r1, T = rows[k - 1], rows[k], prows[k]["T"]
        if "center" not in r0 or "center" not in r1 or T is None:
            continue
        # previous axis points (vehicle frame of k-1), then into frame k: p_k = R_k inv(T) R_{k-1}^T p
        p = np.stack([xs, [lateral(r0, v) for v in xs], np.zeros_like(xs)], axis=1)
        q = (np.array(r1["R"]) @ (np.linalg.inv(np.array(T))[:3, :3] @ (np.array(r0["R"]).T @ p.T)
                                  + np.linalg.inv(np.array(T))[:3, 3:4])).T
        if not np.all(np.diff(q[:, 0]) > 0) or not q[0, 0] <= x <= q[-1, 0]:
            continue
        out.append(abs(lateral(r1, x) - float(np.interp(x, q[:, 0], q[:, 1]))))
    return out


def path_errors(rows, ps, xs):
    """{frame: {x: |axis lateral - driven path lateral|}} for the forward distances xs the path reaches."""
    n, out = len(rows), {}
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
            if p[0] > max(xs):
                break
        pts = np.array(pts)
        pts = pts[pts[:, 0] >= np.maximum.accumulate(pts[:, 0])]      # the train does not reverse
        _, first = np.unique(pts[:, 0], return_index=True)
        pts = pts[np.sort(first)]
        if len(pts) < 2:
            continue
        out[k] = {x: abs((lateral(r, x) - r["center"]) - float(np.interp(x, pts[:, 0], pts[:, 1])))
                  for x in xs if pts[0, 0] <= x <= pts[-1, 0]}
    return out


def honesty(a):
    rows = json.load(open(a.track))["rows"]
    ps = driven_path(json.load(open(a.poses))["rows"])
    mon = {r["i"]: (r["monitored"] or 0.0) for r in map(json.loads, open(a.run))}
    xs = [float(x) for x in range(10, 205, 5)]
    errs = path_errors(rows, ps, xs)
    inside, beyond = [], []
    for k, e in errs.items():
        for x, v in e.items():
            (inside if x <= mon.get(k, 0.0) else beyond).append(v)

    def share(v, t):
        return round(float(np.mean(np.array(v) > t)), 3) if v else None
    out = {"run": a.run, "frames_with_path": len(errs), "steps_inside": len(inside), "steps_beyond": len(beyond),
           "inside_over_0.5m": share(inside, 0.5), "inside_over_1.05m": share(inside, 1.05),
           "beyond_over_0.5m": share(beyond, 0.5), "beyond_over_1.05m": share(beyond, 1.05),
           "inside_error_p90": round(float(np.percentile(inside, 90)), 2) if inside else None}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out))


def measure(a):
    tr = json.load(open(a.track))
    rows = tr["rows"]
    rmax = tr["range_max"]
    prows = json.load(open(a.poses))["rows"]
    ps = driven_path(prows)
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
    jitter_comp = {f"{int(x)}m": pct(compensated_jitter(rows, prows, x)) for x in (40.0, 80.0, 120.0)}
    # error against the driven path
    err = {f"{lo}-{hi}": {"in": [], "out": []} for lo, hi in BINS}
    for k, e in path_errors(rows, ps, [0.5 * (lo + hi) for lo, hi in BINS]).items():
        for lo, hi in BINS:
            x = 0.5 * (lo + hi)
            if x in e:
                err[f"{lo}-{hi}"]["in" if min(rows[k]["axis_valid"], rmax) >= x else "out"].append(e[x])
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
           "blinks": blinks, "jitter": jitter, "jitter_compensated": jitter_comp, "offtrack": offtrack,
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
    h = sub.add_parser("honesty")
    h.add_argument("track")
    h.add_argument("poses")
    h.add_argument("run")
    h.add_argument("out")
    a = ap.parse_args()
    {"poses": poses, "track": track, "measure": measure, "honesty": honesty}[a.cmd](a)


if __name__ == "__main__":
    main()
