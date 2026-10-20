"""T3 (P4 handoff 20.10): why variant B loses the tunnels cube (marker id 19). Read-only trace of a jury replay.

Runs ``judge_runner_set.py`` (the jury runner with ``--set`` overrides) unchanged, after installing three read-only
hooks:

* ``track.joint_axis_fit``: an exact copy of the function (its source, executed in the module's namespace) with one
  added line before its result is built that appends the fit's state to a list: the boundary segments (side, bins,
  absolute y), the bins each segment contributed (masks), the solution (c, t, k[, step], per-segment offsets), the rail
  slab midpoints and the boundaries it was given. Nothing it computes changes.
* ``track.estimate_axis_from_walls``: wrapped; the boundaries dict it fills is kept (also on frames without a joint
  fit).
* ``Detector.process``: after the original returns, per frame: the output model (``res.track``), the estimate without
  the joint fit (``.base``), the joint shape, ``joint_used`` / ``joint_reach`` / ``axis_valid`` (``_both``), the far
  axis, the mount correction ``calib.R``; and for ``--frames``, the frame's cloud in the detector frame with every
  point's corridor lateral ``dy`` and height ``h`` (``_frame_hd``; points 0-120 m ahead, |y| < 9 m, subsampled), the
  points inside the marker box (sensor-frame box from the organizers' marker topic, mapped with ``R_vs`` and
  ``calib.R``) with their ``dy`` / ``h``, and each axis' lateral at the box's distance.

The runner's ``.jsonl`` must equal a plain run's (checked by the caller, every field but timing).

    RESENSE_REPO=<tree> python t3_trace.py <out prefix> --markers markers_tunnels.jsonl --id 19 --frames 240-290 \
        -- --bag <bag> --out <runner prefix> --limit 291 --set ...
"""
import argparse
import inspect
import json
import os
import pickle
import runpy
import sys

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--markers", required=True)
ap.add_argument("--id", type=int, default=19)
ap.add_argument("--frames", default="240-290")
cut = sys.argv.index("--")
a = ap.parse_args(sys.argv[1:cut])
rest = sys.argv[cut + 1:]
lo, hi = (int(v) for v in a.frames.split("-"))
ROOT = os.environ["RESENSE_REPO"]
sys.path.insert(0, ROOT)
import resense.detector as detm  # noqa: E402
import resense.track as trk  # noqa: E402

boxes = {}
for line in open(a.markers):
    r = json.loads(line)
    for m in r["markers"]:
        if m["id"] == a.id and m["type"] == "LINE_LIST" and m["action"] == 0 and m["n_points"]:
            boxes[r["i"]] = (np.array(m["pts_min"], float), np.array(m["pts_max"], float))

STASH, BOUNDS = [], []
src = inspect.getsource(trk.joint_axis_fit)
anchor = "    x_max: dict = {}\n"
assert src.count(anchor) == 1
src = src.replace(anchor, "    _T3_STASH.append({'segs': [(n_, x_.copy(), y_.copy()) for n_, x_, y_ in segs], "
                          "'masks': {g_: m_.copy() for g_, m_ in masks.items()}, 'order': list(order), "
                          "'sol': np.array(sol), 'rails_x': xm.copy(), 'rails_y': ym.copy()})\n" + anchor)
trk.__dict__["_T3_STASH"] = STASH
exec(compile(src, trk.__file__, "exec"), trk.__dict__)
_walls = trk.estimate_axis_from_walls


def walls_hook(*args, **kw):
    out = _walls(*args, **kw)
    b = kw.get("boundaries")
    BOUNDS.append(None if b is None else {k: (np.array(x, float), np.array(y, float)) for k, (x, y) in b.items()})
    return out


trk.estimate_axis_from_walls = walls_hook
rows, dumps = [], {}
_process = detm.Detector.process


def shape(m):
    if m is None:
        return None
    return {"center": float(m.center), "yaw": float(m.yaw), "curvature": float(m.curvature),
            "curv_step": float(m.curv_step), "curv_knot": float(m.curv_knot), "axis_valid": float(m.axis_valid),
            "axis_valid_both": float(m.axis_valid_both), "axis_sides": int(m.axis_sides),
            "wall_quality": float(m.wall_quality), "rail_score": float(m.rail_score)}


def process_hook(self, frame, ego_speed=None):
    i = len(rows)
    CL.clear()
    STASH.clear()
    BOUNDS.clear()
    res = _process(self, frame, ego_speed)
    tr = res.track
    base = tr.base if tr.base is not None else None
    js = tr.joint_shape
    far = getattr(self, "_far_axis", None)
    R = np.array(self.calib.R, float)
    r = {"i": i, "decision": None, "out": shape(tr), "base": shape(base), "joint_shape": None if js is None else list(js),
         "joint_used": tr.joint_used, "joint_reach": float(tr.joint_reach),
         "far": None if far is None else far.to_dict() if hasattr(far, "to_dict") else None,
         "calib_R": R.tolist(), "joint_fits": len(STASH)}
    if STASH:
        s = STASH[-1]
        r["joint_sol"] = [float(v) for v in s["sol"]]
        r["joint_segments"] = [{"side": s["segs"][g][0], "x0": float(s["segs"][g][1][0]), "x1": float(s["segs"][g][1][-1]),
                                "n": int(s["segs"][g][1].size), "used": int(s["masks"][g].sum()) if g in s["masks"] else 0,
                                "offset": float(s["sol"][(4 if len(s["sol"]) - len(s["order"]) == 4 else 3) + s["order"].index(g)])
                                if g in s["order"] else None}
                               for g in range(len(s["segs"]))]
    box = boxes.get(i)
    if box is not None:
        rep_R = np.array(R_VS[0], float)
        corners = np.array([[x, y, z] for x in (box[0][0], box[1][0]) for y in (box[0][1], box[1][1])
                            for z in (box[0][2], box[1][2])])
        cdet = corners @ rep_R.T @ R.T
        X = float(cdet[:, 0].min())
        r["box"] = {"near": X, "y_min": float(cdet[:, 1].min()), "y_max": float(cdet[:, 1].max()),
                    "y_c": float(cdet[:, 1].mean()), "z_min": float(cdet[:, 2].min()), "z_max": float(cdet[:, 2].max())}
        xs = np.array([X, float(cdet[:, 0].mean())])
        r["axis_at_box"] = {"out": tr.center_y(xs).tolist(), "base": None if base is None else base.center_y(xs).tolist()}
        if js is not None:
            jm = trk.replace(tr, center=js[0], yaw=js[1], curvature=js[2], curv_step=js[3], curv_knot=js[4])
            r["axis_at_box"]["joint"] = jm.center_y(xs).tolist()
        xyz = self._frame_xyz
        dy, h = self._frame_hd
        xyz_s = np.asarray(xyz, float) @ R @ rep_R           # back to the sensor frame (both rotations orthonormal)
        inb = np.all((xyz_s >= box[0] - 0.05) & (xyz_s <= box[1] + 0.05), axis=1)
        r["box_points"] = {"n": int(inb.sum()),
                           "dy": np.asarray(dy)[inb].round(3).tolist() if inb.any() else [],
                           "h": np.asarray(h)[inb].round(3).tolist() if inb.any() else [],
                           "y": np.asarray(xyz)[inb, 1].round(3).tolist() if inb.any() else [],
                           "x": np.asarray(xyz)[inb, 0].round(3).tolist() if inb.any() else []}
    if box is not None:
        near_ = r["box"]["near"]
        sel = lambda c: near_ - 2.0 <= c["d"] <= near_ + 2.5 and abs(c["cy"] - r["box"]["y_c"]) <= 1.5
        r["box_clusters"] = [c for c in CL.get("cluster", []) + CL.get("confirm", []) if sel(c)]
        r["box_tracks"] = [{"id": t.id, "hits": int(t.hits), "misses": int(t.misses), "age": int(t.age),
                            "zone_hist": [int(v) for v in t.zone_hist], "last": None if t.last is None else cdesc(t.last, "track")}
                           for t in self.tracker.tracks if t.last is not None and sel(cdesc(t.last, "track"))]
    if lo <= i <= hi:
        xyz = np.asarray(self._frame_xyz)
        dy, h = (np.asarray(v) for v in self._frame_hd)
        m = (xyz[:, 0] > 0) & (xyz[:, 0] < 120) & (np.abs(xyz[:, 1]) < 9)
        idx = np.flatnonzero(m)[::3]
        dumps[i] = {"xyz": xyz[idx].astype(np.float32), "dy": dy[idx].astype(np.float32), "h": h[idx].astype(np.float32),
                    "stash": STASH[-1] if STASH else None, "bounds": BOUNDS[-1] if BOUNDS else None,
                    "model": {"out": tr, "base": base}}
    rows.append(r)
    return res


detm.Detector.process = process_hook
CL = {}
_cluster, _confirm = detm.Detector._cluster, detm.Detector._confirm


def cdesc(c, src):
    return {"src": src, "d": round(float(c.distance), 2), "lat": round(float(c.lateral), 3),
            "cy": round(float(c.centroid[1]), 3), "size": [round(float(v), 2) for v in c.size], "n": int(c.n),
            "n_gauge": int(c.n_gauge), "zone": c.zone, "reason": c.reason, "kind": c.kind,
            "thin": bool(getattr(c, "thin", False)), "weak": bool(getattr(c, "weak", False)),
            "top": round(float(c.height_max), 3), "hmin": round(float(c.height_min), 3)}


def cluster_hook(self, *args, **kw):
    out = _cluster(self, *args, **kw)
    CL["cluster"] = [cdesc(c, "cluster") for c in out] + [cdesc(c, "thin_or_weak") for c in getattr(self, "_thin", [])]
    return out


def confirm_hook(self, clusters, *args, **kw):
    CL["confirm"] = [cdesc(c, "to_tracker") for c in clusters]
    return _confirm(self, clusters, *args, **kw)


detm.Detector._cluster = cluster_hook
detm.Detector._confirm = confirm_hook
R_VS = []
sys.path.insert(0, os.path.join(ROOT, "docs/evidence/judgement_2026-10-13/scripts"))
import judge_runner as jr  # noqa: E402
_init = jr.NodeReplica.__init__


def init_hook(self, *args, **kw):
    _init(self, *args, **kw)
    R_VS.append(np.array(self.R_vs, float))


jr.NodeReplica.__init__ = init_hook
runner = os.path.join(ROOT, "docs/evidence/p4_handoff_2026-10-20/scripts/judge_runner_set.py")
sys.argv = [runner] + rest
try:
    runpy.run_path(runner, run_name="__main__")
except SystemExit:
    pass
with open(a.out + ".t3.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
with open(a.out + ".t3dump.pkl", "wb") as f:
    pickle.dump(dumps, f)
print(f"{a.out}: {len(rows)} frames traced, {len(dumps)} dumped", file=sys.stderr)
