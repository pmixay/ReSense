#!/usr/bin/env python3
"""Train-speed reference for the cached organizer recordings, with the LiDAR-only estimator
(``resense/egomotion.py``) run on the same frames, side by side.

    python scripts/speed_reference.py --cache /data/cache --out out/speed --jobs 2
    python scripts/speed_reference.py --out out/speed --bags roundT_doubleT --limit 100

There is no odometry in any recording, so the reference is built from the point clouds by a
method that shares nothing with the estimator:

1. every frame is run through the shipped detector (``accumulation.estimate_speed`` on, so the
   estimator's opinion is recorded), and its processed cloud (the mount-corrected vehicle frame)
   is cropped to 3-60 m ahead, |Y| < 8 m, voxelised at 0.1 m and given point normals;
2. **coarse 1-D scan**: the points of the current frame whose normal faces along the track
   (|n_x| > 0.5: sleeper sides, bracket and cabinet faces, niche edges, platform ends, gates;
   the lining and the bed constrain nothing along a straight tunnel) are shifted by
   s = -2.0 ... 3.5 m and matched to the previous frame (nearest neighbour, point-to-plane
   distance, truncated at 0.15 m). The minimum of the mean truncated cost is the shift; the
   ratio of the second-best minimum (> 0.3 m away) to the best measures ambiguity;
3. **refinement**: 6-DOF point-to-plane ICP (Open3D, Tukey loss) of the whole cropped cloud,
   started at the scanned shift; its X translation is the reference displacement ``ref_dx``
   (+ = the train moved forward). ``ref_ok`` requires the ICP to stay within 0.15 m of the scan,
   an unambiguous scan minimum (second minimum >= 1.3 x best cost) and at least 150 X-facing
   points. The displacement is per frame; the speed uses the 10 Hz nominal interval times the
   number of rotations between the two frames (``round(receive gap / 0.1)``), because the bag
   receive stamps of the cache jitter by +-20 % while the sensor turns at exactly 10 Hz.

The estimator's values are those of the detector (``FrameResult.ego_speed_estimate`` /
``ego_speed_confidence``) plus the raw profile and track cues. The detector gets the cached
receive stamps snapped to the 10 Hz rotation (``eval_real.nominal_stamps``), as the node's
header clock (``--receive-stamps`` for the raw receive times). One JSONL row per frame goes to
``--out/<bag>.jsonl``; ``scripts/speed_accuracy.py`` summarises coverage and error.

Measured on 24.09 (docs/EXPERIMENTS.md §9): the reference is valid on 89-100 % of the frames
of every recording, its frame-to-frame noise is 0.01-0.03 m/s and the scan and the
ICP agree within 1-4 mm; on the stationary ``doubleT_obstacle`` it reads 0.00 m/s (0.1 m in 20 s).
Needs Open3D (a tool dependency, not part of the node image).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

MOVING = ["doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
          "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch", "cloud_with_fake_obj"]
SHIFTS = np.round(np.arange(-2.0, 3.5001, 0.04), 3)
TRUNC = 0.15


def _crop(xyz):
    m = ((xyz[:, 0] > 3.0) & (xyz[:, 0] < 60.0) & (np.abs(xyz[:, 1]) < 8.0)
         & (xyz[:, 2] > -3.0) & (xyz[:, 2] < 6.0))
    return xyz[m].astype(np.float64)


def prepare(xyz):
    import open3d as o3d
    pts = _crop(xyz)
    if pts.shape[0] < 500:          # the view is blocked (an object right at the sensor)
        return None
    p = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(pts))
    p = p.voxel_down_sample(0.1)
    p.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.4, max_nn=30))
    return p


def scan_shift(src, tgt, tree, rng):
    """(best shift, best cost, second-best cost, n X-facing points, cost curve)."""
    P = np.asarray(src.points)
    N = np.asarray(src.normals)
    Qn = np.asarray(tgt.normals)
    Q = np.asarray(tgt.points)
    xf = np.flatnonzero(np.abs(N[:, 0]) > 0.5)
    if xf.size > 4000:
        xf = rng.choice(xf, 4000, replace=False)
    if xf.size < 30:
        return None, None, None, int(xf.size), None
    Px = P[xf]
    S = SHIFTS[:, None, None] * np.array([1.0, 0.0, 0.0])[None, None, :]
    pts = (Px[None, :, :] + S).reshape(-1, 3)
    _, j = tree.query(pts, k=1, workers=1)
    d = np.abs(np.einsum("ij,ij->i", pts - Q[j], Qn[j]))
    d = np.minimum(d, TRUNC).reshape(SHIFTS.size, -1)
    cost = (d * d).mean(axis=1) / (TRUNC * TRUNC)
    i = int(np.argmin(cost))
    far = np.abs(SHIFTS - SHIFTS[i]) > 0.3
    # local minima away from the best one
    loc = np.r_[False, (cost[1:-1] <= cost[:-2]) & (cost[1:-1] <= cost[2:]), False]
    cand = cost[far & loc]
    second = float(cand.min()) if cand.size else float(cost[far].min())
    s = float(SHIFTS[i])
    if 0 < i < SHIFTS.size - 1:
        den = cost[i - 1] - 2 * cost[i] + cost[i + 1]
        if den > 1e-12:
            s += 0.5 * (cost[i - 1] - cost[i + 1]) / den * (SHIFTS[1] - SHIFTS[0])
    return s, float(cost[i]), second, int(xf.size), cost


def refine(src, tgt, s0):
    import open3d as o3d
    reg = o3d.pipelines.registration
    T = np.eye(4)
    T[0, 3] = s0
    est = reg.TransformationEstimationPointToPlane(reg.TukeyLoss(k=0.1))
    r = reg.registration_icp(src, tgt, 0.3, T, est, reg.ICPConvergenceCriteria(max_iteration=30))
    return r


def run_bag(job):
    bag, cache, out_path, limit, cfg_sets, receive_stamps = job
    sys.path.insert(0, os.getcwd())
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from scipy.spatial import cKDTree

    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    from resense.io import _natural_key, load_cache_stamps

    d = {"accumulation": {"estimate_speed": True}}
    for s in cfg_sets or []:
        key, val = s.split("=", 1)
        sec, k = key.split(".", 1)
        import yaml
        d.setdefault(sec, {})[k] = yaml.safe_load(val)
    cfg = DetectorConfig.from_dict(d)
    det = Detector(cfg)
    captured = {}
    orig = det._speed

    def spy(*a, **kw):
        r = orig(*a, **kw)
        captured["est"] = r[2]
        return r
    det._speed = spy
    files = sorted(glob.glob(os.path.join(cache, bag, "*.npy")), key=_natural_key)
    if limit:
        files = files[:limit]
    stamps = load_cache_stamps(os.path.join(cache, bag))
    recv = dict(stamps)
    if not receive_stamps:
        from eval_real import nominal_stamps
        stamps = nominal_stamps(stamps)
    rng = np.random.default_rng(0)
    prev = prev_tree = None
    prev_stamp = prev_rstamp = None
    rows = []
    t_start = time.time()
    with open(out_path, "w", encoding="utf-8") as fh:
        for i, f in enumerate(files):
            stem = os.path.splitext(os.path.basename(f))[0]
            stamp = stamps.get(stem, i * 0.1)
            rstamp = recv.get(stem, stamp)
            fr = frame_from_compact(np.load(f), cfg.sensor, stamp=stamp, frame_id=stem)
            captured.clear()
            res = det.process(fr)
            est = captured.get("est")
            cur = prepare(res.xyz)
            row = {"bag": bag, "frame": i, "stamp": stamp,
                   "gap": None if prev_stamp is None else round(stamp - prev_stamp, 4),
                   "recv_gap": None if prev_stamp is None else round(rstamp - prev_rstamp, 4),
                   "est_speed": res.ego_speed_estimate, "est_conf": round(res.ego_speed_confidence, 3),
                   "est_method": None if est is None else est.method,
                   "est_profile": None if est is None or est.speed_profile is None else round(float(est.speed_profile), 3),
                   "est_tracks": None if est is None or est.speed_tracks is None else round(float(est.speed_tracks), 3),
                   "est_corr": None if est is None else round(float(est.corr), 3),
                   "obstacle": bool(res.obstacle), "n_acc": int(res.n_accumulated),
                   "egomotion_ms": round(res.timing_ms.get("egomotion", 0.0), 2),
                   "rail_score": round(float(res.track.rail_score), 3)}
            if prev is not None and cur is not None:
                s, c1, c2, nxf, _ = scan_shift(cur, prev, prev_tree, rng)
                row.update(scan_dx=None if s is None else round(s, 3), scan_cost=c1, scan_second=c2, n_xface=nxf)
                if s is not None:
                    r = refine(cur, prev, s)
                    T = r.transformation
                    dx = float(T[0, 3])
                    yaw = float(np.degrees(np.arctan2(T[1, 0], T[0, 0])))
                    ok = (abs(dx - s) < 0.15 and c2 >= 1.3 * c1 and nxf >= 150 and r.fitness > 0.5)
                    n_rot = max(1, int(round((rstamp - prev_rstamp) / 0.1)))
                    row.update(ref_dx=round(dx, 4), ref_dy=round(float(T[1, 3]), 4), ref_dz=round(float(T[2, 3]), 4),
                               ref_yaw_deg=round(yaw, 4), ref_fitness=round(float(r.fitness), 3),
                               ref_rmse=round(float(r.inlier_rmse), 4), ref_ok=bool(ok), n_rot=n_rot,
                               ref_speed=round(dx / (0.1 * n_rot), 3))
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            rows.append(row)
            prev, prev_stamp, prev_rstamp = cur, stamp, rstamp
            prev_tree = None if cur is None else cKDTree(np.asarray(cur.points))
    return bag, out_path, time.time() - t_start


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default="/data/cache")
    ap.add_argument("--out", required=True)
    ap.add_argument("--bags", default=",".join(["doubleT_obstacle"] + MOVING))
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--set", action="append", default=[], help="section.key=value detector override")
    ap.add_argument("--receive-stamps", action="store_true",
                    help="give the detector the cached bag receive stamps (default: snapped to 10 Hz, as the "
                         "node's header clock)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    jobs = [(b, a.cache, os.path.join(a.out, f"{b}.jsonl"), a.limit, a.set, a.receive_stamps) for b in a.bags.split(",") if b]
    jobs.sort(key=lambda j: -len(glob.glob(os.path.join(a.cache, j[0], "*.npy"))))
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for bag, path, wall in ex.map(run_bag, jobs):
            print(f"{bag}: {path} ({wall:.0f} s)", flush=True)


if __name__ == "__main__":
    main()
