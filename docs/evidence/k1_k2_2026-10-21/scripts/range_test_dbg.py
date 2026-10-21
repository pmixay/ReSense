#!/usr/bin/env python3
"""Jury range test (8.2): a world-static cuboid ray-cast into real moving-train frames, approaching the train.

Background: cached node-decoded clouds of an organizer recording (cache_decoded.py).
Ego-motion: ICP odometry (icp_odometry.py; validated on set O against the organizers' object motion:
  ~2 cm/frame error, +3 % cumulative bias), smoothed (median of 7) and clipped at >= 0.
Placement: at insertion frame s the object's front face is D0 m ahead; at frame k it is D0 - travel(s..k).
  Lateral / height follow the detector's own BASELINE track model of frame k (a run without the object):
  Y = center_y(X) + lateral_offset, base Z = rail_z(X) (rail-head level) + base_offset, mapped from the
  detector's calibrated frame to the configured vehicle frame (mount rotation of the baseline).
  (Placement along the detector's axis is favourable to it: errors of its far axis do not count here; the
  +-0.5 m lateral variants probe that.)
Ray cast: the sensor's own grid (ring elevations measured from the frame, 0.1 deg azimuth columns with the
  frame's phase), slab intersection with the box; a ray is occluded when the background has a nearer return
  in the same (ring, column) slot; otherwise the background returns of the slot are replaced by the hit
  (written twice, as the recordings hold each echo twice), intensity 30. No range-dependent dropout (ideal).
Scoring per frame: STOP detection matching the object (|d - X| <= max(2, 3 %) + L/2, |Yc - Y| <= 1 + W/2).

  range_test.py <cache> <icp.json> <out_prefix> --obj L,W,H --start s --d0 230 [--lat 0] [--base 0]
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from judge_runner import NodeReplica, node_decision  # noqa: E402
from resense.frame import Frame  # noqa: E402
from resense.track import TrackModel  # noqa: E402

AZ_STEP = 0.1


def load_cache(cache):
    meta = json.load(open(os.path.join(cache, "meta.json")))
    return meta, sorted(glob.glob(os.path.join(cache, "f_*.npz")))


def run_frame(rep, xyz_s, inten, ring, m, idx):
    rep.continuity(m["topic"], m["frame_id"], m["stamp"], idx)
    xyz_v = xyz_s @ rep.R_vs.T
    fr = Frame(xyz=xyz_v.astype(np.float32), intensity=inten, ring=ring if m["has_ring"] else None,
               stamp=m["stamp"], frame_id=m["frame_id"], meta={"n_raw": m["n_raw"], "n_near": m["n_near"]})
    return rep.detector.process(fr, ego_speed=None)


def baseline(cache, out):
    if os.path.exists(out):
        return json.load(open(out))
    meta, files = load_cache(cache)
    rep = NodeReplica()
    rows = []
    for k, (m, f) in enumerate(zip(meta, files)):
        d = np.load(f)
        res = run_frame(rep, d["xyz"], d["inten"], d["ring"], m, k)
        t = res.track
        rows.append({"center": t.center, "yaw": t.yaw, "curv": t.curvature, "floor_coef": list(map(float, t.floor_coef)),
                     "floor_range": list(map(float, t.floor_range)), "rail_offset": t.rail_offset,
                     "axis_valid": t.axis_valid, "R": np.asarray(rep.detector.mount_rotation).tolist(),
                     "decision": node_decision(res),
                     # K1/K2 19.10: the curvature step of a C1 piecewise axis (absent for a quadratic: unchanged rows)
                     **({"curv_step": t.curv_step, "curv_knot": t.curv_knot} if getattr(t, "curv_step", 0.0) else {})})
    json.dump(rows, open(out, "w"))
    return rows


def ring_table(xyz_v, ring):
    el = np.degrees(np.arctan2(xyz_v[:, 2], np.hypot(xyz_v[:, 0], xyz_v[:, 1])))
    tab = np.full(int(ring.max()) + 1, np.nan)
    for r in np.unique(ring):
        tab[r] = np.median(el[ring == r])
    return tab


def raycast_box(lo, hi, rings_el, phase):
    """Rays of the grid hitting the axis-aligned box [lo, hi] (vehicle frame). Returns ring ids, column ids,
    hit points (N, 3), ranges."""
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    az = np.degrees(np.arctan2(corners[:, 1], corners[:, 0]))
    el = np.degrees(np.arctan2(corners[:, 2], np.hypot(corners[:, 0], corners[:, 1])))
    c0 = int(np.floor((az.min() - phase) / AZ_STEP)) - 1
    c1 = int(np.ceil((az.max() - phase) / AZ_STEP)) + 1
    rr = np.flatnonzero((rings_el >= el.min() - 0.3) & (rings_el <= el.max() + 0.3))
    if rr.size == 0 or c1 < c0:
        return None
    cols = np.arange(c0, c1 + 1)
    R, C = np.meshgrid(rr, cols, indexing="ij")
    R, C = R.ravel(), C.ravel()
    a = np.radians(phase + C * AZ_STEP)
    e = np.radians(rings_el[R])
    d = np.c_[np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)]
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = (lo[None, :] - 0.0) / d
        t2 = (hi[None, :] - 0.0) / d
    tmin = np.nanmax(np.minimum(t1, t2), axis=1)
    tmax = np.nanmin(np.maximum(t1, t2), axis=1)
    hit = (tmax >= tmin) & (tmin > 0)
    if not hit.any():
        return None
    t = tmin[hit]
    return R[hit], C[hit], d[hit] * t[:, None], t


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cache")
    p.add_argument("icp")
    p.add_argument("out")
    p.add_argument("--obj", required=True, help="L,W,H in m")
    p.add_argument("--start", type=int, required=True)
    p.add_argument("--d0", type=float, default=230.0)
    p.add_argument("--lat", type=float, default=0.0)
    p.add_argument("--base", type=float, default=0.0, help="m above the rail head of the box bottom")
    p.add_argument("--end", type=int, default=10 ** 9)
    p.add_argument("--vx", type=float, default=0.0, help="object's own speed along the track, m/s (+ = away)")
    p.add_argument("--vy", type=float, default=0.0, help="object's own lateral speed, m/s (crossing)")
    p.add_argument("--appear", type=float, default=0.0, help="object appears only when X <= this (m), e.g. falls on the track")
    p.add_argument("--dropout", action="store_true",
                   help="keep a hit with probability 1 up to 120 m, falling linearly to 0.5 at 200 m (assumption)")
    a = p.parse_args()
    L, W, H = (float(v) for v in a.obj.split(","))
    meta, files = load_cache(a.cache)
    base_rows = baseline(a.cache, a.cache.rstrip("/") + "_baseline.json")
    icp = json.load(open(a.icp))
    dx = np.zeros(len(files))
    for i, v in zip(icp["i"], icp["dx"]):
        dx[i] = v
    from scipy.ndimage import median_filter
    dx = np.clip(median_filter(dx, size=7, mode="nearest"), 0.0, None)
    cum = np.cumsum(dx)
    rep = NodeReplica()
    rows = []
    tab = None
    for k, (m, f) in enumerate(zip(meta, files)):
        if k >= a.end:
            break
        d = np.load(f)
        xyz_s, inten, ring = d["xyz"], d["inten"], d["ring"]
        info = {"k": k, "X": None, "n_obj": 0}
        if k >= a.start:
            tsec = meta[k]["stamp"] - meta[a.start]["stamp"]
            X = a.d0 - (cum[k] - cum[a.start]) + a.vx * tsec
            lat_k = a.lat + a.vy * tsec
            info["X"] = round(float(X), 2)
            info["lat"] = round(float(lat_k), 2)
            if a.appear > 0 and X > a.appear and not info.get("_appeared"):
                info["X"] = None
            if info["X"] is not None and X > 3.0:
                b = base_rows[k]
                tm = TrackModel(floor_coef=np.array(b["floor_coef"]), floor_range=tuple(b["floor_range"]),
                                center=b["center"], yaw=b["yaw"], curvature=b["curv"], rail_offset=b["rail_offset"],
                                **({"curv_step": b["curv_step"], "curv_knot": b["curv_knot"]} if "curv_step" in b else {}))
                Rm = np.array(b["R"])
                Xc = X + 0.5 * L
                yc = float(tm.center_y(Xc)) + lat_k
                zb = float(tm.rail_z(Xc)) + a.base
                info.update(Y=round(yc, 2), Zb=round(zb, 2), axis_valid=b["axis_valid"])
                # box corners in the processed frame -> configured vehicle frame (p_cfg = Rm^T p_proc)
                lo_p, hi_p = np.array([X, yc - W / 2, zb]), np.array([X + L, yc + W / 2, zb + H])
                cen = Rm.T @ (0.5 * (lo_p + hi_p))
                lo, hi = cen - 0.5 * (hi_p - lo_p), cen + 0.5 * (hi_p - lo_p)
                xyz_v = xyz_s.astype(np.float64) @ rep.R_vs.T.astype(np.float64)
                if tab is None:
                    tab = ring_table(xyz_v, ring)
                az = np.degrees(np.arctan2(xyz_v[:, 1], xyz_v[:, 0]))
                frac = ((az / AZ_STEP) % 1.0)
                phase = float(np.median(frac)) * AZ_STEP
                rc = raycast_box(lo, hi, tab, phase)
                if rc is not None:
                    R_, C_, P_, T_ = rc
                    col_bg = np.round((az - phase) / AZ_STEP).astype(np.int64)
                    key_bg = ring.astype(np.int64) * 100000 + (col_bg + 50000)
                    key_ob = R_.astype(np.int64) * 100000 + (C_ + 50000)
                    rng_bg = np.linalg.norm(xyz_v, axis=1)
                    order = np.argsort(key_bg)
                    ks, rs = key_bg[order], rng_bg[order]
                    lo_i = np.searchsorted(ks, key_ob, "left")
                    hi_i = np.searchsorted(ks, key_ob, "right")
                    nearest = np.array([rs[i:j].min() if j > i else np.inf for i, j in zip(lo_i, hi_i)])
                    vis = nearest > T_ - 0.05
                    if a.dropout:
                        pk = np.clip(1.0 - 0.5 * (T_ - 120.0) / 80.0, 0.3, 1.0)
                        vis &= np.random.default_rng(10_000 + k).random(len(T_)) < pk
                    if vis.any():
                        drop = np.isin(key_bg, key_ob[vis]) & (rng_bg >= np.repeat(0, len(rng_bg)))
                        keep = ~drop
                        P = np.repeat(P_[vis], 2, axis=0)
                        P += np.random.default_rng(k).normal(0, 0.01, P.shape)
                        P_s = P @ rep.R_vs.astype(np.float64)          # vehicle -> sensor
                        xyz_s = np.vstack([xyz_s[keep], P_s.astype(np.float32)])
                        inten = np.concatenate([inten[keep], np.full(len(P), 30.0, np.float32)])
                        ring = np.concatenate([ring[keep], np.repeat(R_[vis], 2).astype(ring.dtype)])
                        info["n_obj"] = int(vis.sum())
        res = run_frame(rep, xyz_s, inten, ring, m, k)
        if os.environ.get("TRKDBG") and int(os.environ["TRKDBG"].split(",")[0]) <= k <= int(os.environ["TRKDBG"].split(",")[1]):
            print(k, node_decision(res), "added", getattr(rep.detector, "_curve_added", None),
                  [(t.id, round(t.last.distance, 1), round(t.last.lateral, 2), t.zone, t.rule_zone, t.withheld, getattr(t, "curve_seen", None),
                    t.last.zone, t.last.reason, getattr(t.last, "curve", False), t.misses, t.zone_hist[-6:]) for t in rep.detector.tracker.tracks
                   if t.last is not None and 75 < t.last.distance < 95], file=sys.stderr)
        dec = node_decision(res)
        hit = warn = False
        if info["X"] is not None and info["X"] > 3.0 and info.get("Y") is not None:
            tol = max(2.0, 0.03 * info["X"]) + L / 2
            hit = any(abs(dd.distance - info["X"]) <= tol and abs(dd.center[1] - info["Y"]) <= 1.0 + W / 2
                      for dd in res.detections)
            warn = any(abs(dd.distance - info["X"]) <= tol and abs(dd.center[1] - info["Y"]) <= 1.0 + W / 2
                       for dd in res.warnings)
        if info["X"] is not None and info["X"] > 3.0 and info.get("Y") is not None:
            info["cand_near"] = [{"d": round(float(c.distance), 1), "lat": round(float(c.lateral), 2),
                                  "zone": c.zone, "reason": c.reason, "n": int(c.n), "n_gauge": int(c.n_gauge),
                                  "hmin": round(float(c.height_min), 2), "hmax": round(float(c.height_max), 2),
                                  "size": [round(float(v), 2) for v in c.size], "thin": c.thin, "weak": c.weak}
                                 for c in res.candidates if abs(c.distance - info["X"]) < 6 + L]
            ex = getattr(rep.detector, "_curve_seen", None) or []
            info["curve_seen"] = [{"d": round(float(c.distance), 1), "lat": round(float(c.lateral), 2), "zone": c.zone,
                                   "reason": c.reason, "ng": int(c.n_gauge), "size": [round(float(v), 2) for v in c.size]}
                                  for c in ex if abs(c.distance - info["X"]) < 6 + L]
            rep.detector._curve_seen = None
            info["track_live"] = {"center_at_X": round(float(res.track.center_y(info["X"])), 2),
                                  "railz_at_X": round(float(res.track.rail_z(info["X"])), 2),
                                  "axis_valid": round(float(res.track.axis_valid), 1)}
        info.update(decision=dec, hit=bool(hit), warn=bool(warn),
                    nearest=None if res.nearest_distance is None else round(float(res.nearest_distance), 2))
        rows.append(info)
    # summary
    obj = [r for r in rows if r["X"] is not None and r["X"] > 3.0]
    vis = [r for r in obj if r["n_obj"] > 0]
    hits = [r for r in vis if r["hit"]]
    first_stop = hits[0]["X"] if hits else None
    held = None
    arr = sorted(vis, key=lambda r: r["X"])
    n_hit = 0
    for n, r in enumerate(arr, 1):
        n_hit += r["hit"]
        if n_hit >= 0.9 * n:
            held = r["X"]
    first_vis = vis[0]["X"] if vis else None
    bins = {}
    for lo_, hi_ in [(3, 30), (30, 60), (60, 100), (100, 150), (150, 200), (200, 260)]:
        b = [r for r in vis if lo_ <= r["X"] < hi_]
        if b:
            bins[f"{lo_}-{hi_}"] = f"{sum(r['hit'] for r in b)}/{len(b)}"
    summ = {"cache": os.path.basename(a.cache.rstrip("/")), "obj": [L, W, H], "lat": a.lat, "base": a.base,
            "start": a.start, "d0": a.d0, "first_visible_X": first_vis, "first_stop_X": first_stop, "held_from_X": held,
            "visible_frames": len(vis), "stop_frames": len(hits), "bins": bins,
            "decisions_while_visible": {k: sum(1 for r in vis if r["decision"] == k) for k in ("GO", "CAUTION", "STOP", "FAULT")},
            "go_within_60m": sum(1 for r in vis if r["X"] < 60 and r["decision"] == "GO"),
            "n_obj_at": {str(int(t)): next((r["n_obj"] for r in vis if r["X"] <= t), None) for t in (200, 150, 100, 60, 30)}}
    json.dump({"summary": summ, "rows": rows}, open(a.out + ".json", "w"))
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
