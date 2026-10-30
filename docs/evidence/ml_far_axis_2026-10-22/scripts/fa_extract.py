#!/usr/bin/env python3
"""Per-frame extraction for the learned far axis: run the detector, and per frame record

* the detector's track model state (base model, K2 curve model, far line; ``resense.far_axis.model_state``) and the
  observation profile (``resense.far_axis.profile``) - the model's inputs, exactly as the detector would compute them;
* the near-field rail-pair midpoints (5-34 m, own slab-by-slab ridge tracking, independent of the far axis) - the
  label source;
* the frame-to-frame ICP motion (open3d point-to-plane on 0.15 m voxels of the 3-80 m cloud, the B6 / judge settings)
  in the detector's corrected frame - the odometry that brings later frames' rails back.

    fa_extract.py <cache_dir> <out.npz> [--start N --end M] [--synthetic] [--set section.key=value ...]
                  [--config configs/default.yaml] [--profile none|falcon_ros]

``cache_dir``: a gate cache (``scripts/cache_frames.py`` .npy / .npy.zst + stamps) or, with --synthetic, a directory
of vehicle-frame ``f_*.npz`` (raycast_scenes.py). Frames [start, end) of the sorted file list, one fresh detector.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from resense import far_axis  # noqa: E402
from resense.track import _height_profile, _refine_peak, _ridge  # noqa: E402

GAUGE = 1.59 / 2


def near_rails(xyz: np.ndarray, model, x0=4.0, x1=34.0, slab=3.0):
    """Rail-pair midpoints per 3 m slab from x0 to x1, tracked outward: each slab's lateral profile (85th percentile
    of the height above the bed per 3 cm) is taken around the extrapolation of the midpoints found so far (the
    detector's model only seeds the first slab and the bed height), so the far axis plays no part.
    Returns (x, y_mid, prominence) rows."""
    X = xyz[:, 0].astype(np.float64)
    m = (X > x0) & (X < x1)
    X, Y = X[m], xyz[m, 1].astype(np.float64)
    H = xyz[m, 2] - model.floor_z(X)
    sel = (H > -0.4) & (H < 0.8)
    X, Y, H = X[sel], Y[sel], H[sel]
    step, half = 0.03, 1.4
    edges = np.arange(-half, half + step, step)
    yc = edges[:-1] + step / 2
    k = max(1, int(round(0.25 / step)))
    sep = int(round(2 * GAUGE / step))
    xs, ys, ws = [], [], []
    c0, t0 = float(model.center), float(np.tan(model.yaw))
    for s0 in np.arange(x0, x1 - 1e-6, slab):
        xm = s0 + slab / 2
        # prediction of the centreline in this slab from the midpoints found so far
        if len(xs) >= 3:
            deg = 2 if len(xs) >= 5 else 1
            p = np.polyfit(xs, ys, deg)
            pred = lambda x: np.polyval(p, x)  # noqa: E731
        elif len(xs) >= 1:
            pred = lambda x, a=ys[-1], b=xs[-1]: a + t0 * (x - b)  # noqa: E731
        else:
            pred = lambda x: c0 + t0 * x  # noqa: E731
        mm = (X >= s0) & (X < s0 + slab)
        if mm.sum() < 60:
            continue
        yp = Y[mm] - pred(X[mm])
        inn = np.abs(yp) < half
        prof = _height_profile(yp[inn], H[mm][inn], edges, 85.0, min_points=3)
        r = _ridge(prof, k)
        tol = 0.35 if xs else 0.6
        best = None
        for b in range(k, yc.size - k - sep):
            bl, br = b, b + sep
            if abs(0.5 * (yc[bl] + yc[br])) > tol:
                continue
            rl, rr = r[bl], r[br]
            if not (np.isfinite(rl) and np.isfinite(rr)) or min(rl, rr) < 0.03:
                continue
            if not (0.05 < prof[bl] < 0.5 and 0.05 < prof[br] < 0.5):
                continue
            sc = min(rl, rr)
            if best is None or sc > best[0]:
                best = (sc, bl, br)
        if best is None:
            continue
        sc, bl, br = best
        yl = yc[0] + _refine_peak(r, bl) * step
        yr = yc[0] + _refine_peak(r, br) * step
        if abs(abs(yr - yl) - 2 * GAUGE) > 0.08:
            continue
        xs.append(xm)
        ys.append(float(pred(xm) + 0.5 * (yl + yr)))
        ws.append(float(sc))
    return np.array([xs, ys, ws]).T if xs else np.zeros((0, 3))


def icp_cloud(xyz):
    import open3d as o3d
    m = (xyz[:, 0] > 3) & (xyz[:, 0] < 80) & (np.abs(xyz[:, 1]) < 6)
    pc = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(xyz[m].astype(np.float64)))
    pc = pc.voxel_down_sample(0.15)
    pc.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.6, max_nn=20))
    return pc


def icp(cur, prev, guess):
    """cur (frame k) registered onto prev (frame k-1): p_prev = T p_cur. A coarse pass (0.5 m voxels, 2 m
    correspondences) from the guess, then the B6 / judge pass (0.15 m voxels, 0.5 m)."""
    import open3d as o3d
    reg = o3d.pipelines.registration
    cc, pc = cur.voxel_down_sample(0.5), prev.voxel_down_sample(0.5)
    for c in (cc, pc):
        c.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=1.5, max_nn=20))
    coarse = reg.registration_icp(cc, pc, 2.0, guess, reg.TransformationEstimationPointToPlane(),
                                  reg.ICPConvergenceCriteria(max_iteration=30))
    fine = reg.registration_icp(cur, prev, 0.5, coarse.transformation, reg.TransformationEstimationPointToPlane(),
                                reg.ICPConvergenceCriteria(max_iteration=40))
    return fine.transformation.copy(), float(fine.fitness), float(fine.inlier_rmse)


def frames_of(a):
    if a.synthetic:
        from resense.frame import Frame
        files = sorted(glob.glob(os.path.join(a.cache, "f_*.npz")))[a.start:a.end]
        for k, f in enumerate(files):
            d = np.load(f)
            yield os.path.basename(f), Frame(xyz=d["xyz"], intensity=d["inten"], ring=d["ring"],
                                             stamp=(a.start + k) * 0.1, frame_id=os.path.basename(f))
        return
    from resense.frame import frame_from_compact
    from scripts.cache_io import cache_file_stem, cache_files, load_cache_array, load_cache_stamps
    files = cache_files(a.cache)[a.start:a.end]
    stamps = load_cache_stamps(a.cache)
    for k, f in enumerate(files):
        stem = cache_file_stem(f)
        yield stem, frame_from_compact(load_cache_array(f), a.cfg.sensor, stamp=stamps.get(stem, (a.start + k) * 0.1),
                                       frame_id=stem)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("out")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--config", default=os.path.join(ROOT, "configs/default.yaml"))
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--no-icp", action="store_true")
    ap.add_argument("--icp-from", default="", help="an earlier extraction of the same frames: take its ICP motions")
    a = ap.parse_args()
    from eval_real import load_cfg_dict
    from resense.config import DetectorConfig
    from resense.detector import Detector
    a.cfg = DetectorConfig.from_dict(load_cfg_dict(a.config, a.set))
    det = Detector(a.cfg)
    names, profs, states, rails, Ts, fit, rmse, stamps, speed, nearest, stop = [], [], [], [], [], [], [], [], [], [], []
    prev, guess = None, np.eye(4)
    old = {}
    if a.icp_from:
        o = np.load(a.icp_from)
        old = {str(n): (T, f, r) for n, T, f, r in zip(o["names"], o["T"], o["fitness"], o["rmse"])}
        a.no_icp = True
    t0 = time.time()
    for stem, fr in frames_of(a):
        res = det.process(fr)
        xyz = det._frame_xyz
        tr = det.track
        names.append(stem)
        stamps.append(fr.stamp)
        profs.append(far_axis.profile(xyz, tr))
        states.append(far_axis.model_state(tr, tr.curve if a.cfg.track.axis_joint_union else None, det._far_axis))
        rails.append(near_rails(xyz, tr))
        speed.append(np.nan if det._odo_speed is None else det._odo_speed)
        nearest.append(np.nan if res.nearest_distance is None else res.nearest_distance)
        stop.append(bool(res.obstacle))
        dt = fr.stamp - stamps[-2] if len(stamps) > 1 else 0.1
        if a.no_icp:
            T, f, r = old.get(stem, (np.full((4, 4), np.nan), 0.0, 0.0))
            Ts.append(T); fit.append(f); rmse.append(r)
            continue
        cur = icp_cloud(xyz)
        if prev is None or len(cur.points) < 2000 or len(prev.points) < 2000:
            Ts.append(np.full((4, 4), np.nan)); fit.append(0.0); rmse.append(0.0)
        else:
            if not np.isfinite(guess).all():
                guess = np.eye(4)
            if speed[-1] == speed[-1] and abs(guess[0, 3] - speed[-1] * dt) > 0.3:
                # the detector's own speed estimate re-seeds a guess that disagrees with it (a cold start)
                guess = np.eye(4); guess[0, 3] = speed[-1] * dt
            T, f, r = icp(cur, prev, guess)
            guess = T
            Ts.append(T); fit.append(f); rmse.append(r)
        if len(cur.points) >= 2000:
            prev = cur
    nr = max([len(r) for r in rails] + [1])
    R = np.full((len(rails), nr, 3), np.nan, dtype=np.float32)
    for i, r in enumerate(rails):
        R[i, :len(r)] = r
    np.savez_compressed(a.out, names=np.array(names), stamps=np.array(stamps),
                        prof_side=np.stack([p[0] for p in profs]), prof_vault=np.stack([p[1] for p in profs]),
                        prof_bed=np.stack([p[2] for p in profs]),
                        state=np.array([json.dumps(s) for s in states]), rails=R, T=np.stack(Ts),
                        fitness=np.array(fit), rmse=np.array(rmse), speed=np.array(speed),
                        nearest=np.array(nearest), stop=np.array(stop),
                        meta=json.dumps({"cache": a.cache, "start": a.start, "end": a.end, "set": a.set,
                                         "config": a.config, "wall_s": round(time.time() - t0, 1)}))
    print(a.out, len(names), "frames", round(time.time() - t0, 1), "s", flush=True)


if __name__ == "__main__":
    main()
