#!/usr/bin/env python3
"""Synthetic attack scenes for the K2 union review (21.10): curved / S-curved / double-track / wrong-boundary scenes
with a moving train (ego motion along the true track), line-of-sight occlusion by the walls, and objects whose
true position is known. Runs ONE detector configuration per call (the tree in PYTHONPATH, its own configs/default.yaml,
optionally the K2 union switch values on top) and writes one JSON row per frame.

    attack_synth.py --scene NAME --mode yaml|union --out rows.jsonl [--frames N]

Each row: frame, ego s, STOP flag, every STOP / warning detection (vehicle centre, distance, lateral, zone, reason,
kind), the object each matches by truth (|dX| <= max(2, 3 %) + L/2, |dY| <= 1 + W/2 in the vehicle frame, or None),
and read-only detector state after process (curve model present, curve_from, curve axis_valid, base axis_valid and
curvature, number of curve clusters added). Nothing in the detector is changed or hooked.
"""
import argparse
import json
from dataclasses import replace

import numpy as np
from scipy.spatial import cKDTree

from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
import resense
import os

UNION = dict(axis_joint_fit=True, axis_joint_range=False, axis_joint_min_curvature=1e-4, axis_joint_union=True)
DS = 0.05
SMAX = 900.0


class Track:
    """A planar track from curvature k(s) (1/m, + left); s = arc length."""

    def __init__(self, kfun):
        s = np.arange(0.0, SMAX, DS)
        k = kfun(s)
        th = np.concatenate([[0.0], np.cumsum(0.5 * (k[1:] + k[:-1]) * DS)])
        x = np.concatenate([[0.0], np.cumsum(0.5 * (np.cos(th[1:]) + np.cos(th[:-1])) * DS)])
        y = np.concatenate([[0.0], np.cumsum(0.5 * (np.sin(th[1:]) + np.sin(th[:-1])) * DS)])
        self.s, self.k, self.th, self.x, self.y = s, k, th, x, y
        self.tree = cKDTree(np.stack([x, y], 1))

    def at(self, s, l=0.0):
        s = np.asarray(s, dtype=np.float64)
        i = np.clip(np.round(s / DS).astype(int), 0, self.s.size - 1)
        th = self.th[i]
        return self.x[i] - np.sin(th) * l, self.y[i] + np.cos(th) * l, th

    def sl(self, px, py):
        """Arc length and signed lateral of world points (nearest centreline sample)."""
        d, i = self.tree.query(np.stack([px, py], 1))
        th = self.th[i]
        l = -(px - self.x[i]) * np.sin(th) + (py - self.y[i]) * np.cos(th)
        return self.s[i], l


def k_const(R):
    return lambda s: np.full_like(s, 1.0 / R if R else 0.0)


def k_entry(x0, R, L):          # straight to x0 (arc), clothoid to 1/R over L, then constant
    return lambda s: np.clip((s - x0) / L, 0.0, 1.0) / R


def k_exit(x1, R):              # constant 1/R to x1, then straight
    return lambda s: np.where(s < x1, 1.0 / R, 0.0)


def k_s(x1, R1, R2, L=20.0):    # 1/R1 to x1, linear change over L to -1/R2
    return lambda s: np.interp(s, [0, x1, x1 + L, SMAX], [1.0 / R1, 1.0 / R1, -1.0 / R2, -1.0 / R2])


# --- scene definitions --------------------------------------------------------------------------------------------
# walls: (track, lateral, s0, s1, ztop) vertical surfaces from the bed (-1.5) to ztop; they also occlude.
# boxes: dict(track, s, l, L, W, H, z0=-1.15, vs=0, vl=0, name, t0, t1) moving in (s, l) at (vs, vl) m/s; a box exists
# for frames whose time is in [t0, t1).
def scene(name):
    S0 = 100.0                  # ego start arc (the scene is built on [0, SMAX])
    w = 2.2
    P = lambda s, l=0.0, **k: dict(track=0, s=S0 + s, l=l, L=0.5, W=0.5, H=1.75, **k)    # person-sized, s ahead of the start
    sc = dict(tracks=[], walls=[], boxes=[], speed=15.0, frames=60, rails=[0])
    base = name.split("+")[0]
    obj = name.split("+")[1] if "+" in name else "none"
    if base.startswith("R"):                      # tunnel on a constant curve R (m), inner wall seen fully
        R = float(base[1:])
        sc["tracks"] = [Track(lambda s: np.where(s < S0 + 20, 0.0, 1.0 / R))]
        sc["walls"] = [(0, w, 0, SMAX, 3.3), (0, -w, 0, SMAX, 3.3)]
    elif base.startswith("open"):                  # open line on a curve R: no walls, masts every 40 m at 2.6 m outside
        R = float(base[4:])
        sc["tracks"] = [Track(lambda s: np.where(s < S0 + 20, 0.0, 1.0 / R))]
        sc["walls"] = []
        sc["masts"] = (0, -2.6, 40.0)
    elif base == "entry":
        sc["tracks"] = [Track(k_entry(S0 + 40, 400.0, 100.0))]
        sc["walls"] = [(0, w, 0, SMAX, 3.3), (0, -w, 0, SMAX, 3.3)]
    elif base == "exit":
        sc["tracks"] = [Track(lambda s: np.where(s < S0 + 60, 1.0 / 400.0, 0.0))]
        sc["walls"] = [(0, w, 0, SMAX, 3.3), (0, -w, 0, SMAX, 3.3)]
    elif base.startswith("scurve"):
        R = float(base[6:] or 500)
        sc["tracks"] = [Track(k_s(S0 + 70, R, R))]
        sc["walls"] = [(0, w, 0, SMAX, 3.3), (0, -w, 0, SMAX, 3.3)]
    elif base.startswith("double"):                # double-track tunnel, ours on the right, the other 4.1 m left
        R = float(base[6:] or 500)
        t = Track(lambda s: np.where(s < S0 + 20, 0.0, 1.0 / R))
        sc["tracks"] = [t]
        sc["walls"] = [(0, 4.1 + w, 0, SMAX, 3.3), (0, -w, 0, SMAX, 3.3)]
        sc["rails"] = [0, 4.1]
    elif base.startswith("siding"):                # ours mildly curved (R 2500 left) in an open area; a siding leaves
        # to the left at S0+30 on R 300 with its own wall on its far side; our right side has a wall
        Rs = float(base[6:] or 300)
        t0 = Track(lambda s: np.full_like(s, 1.0 / 2500.0))
        t1 = Track(lambda s: np.where(s < S0 + 30, 1.0 / 2500.0, 1.0 / Rs))
        sc["tracks"] = [t0, t1]
        sc["walls"] = [(1, 2.0 + w, S0 + 30, SMAX, 3.3), (0, w, 0, S0 + 30, 3.3), (0, -w, 0, SMAX, 3.3)]
    elif base.startswith("diverge"):               # mild curve R 2500 left; the right boundary diverges (a platform /
        # retaining wall leaving the track, 3 cm/m from 50 m), the left one ends at 60 m (open area)
        t0 = Track(lambda s: np.full_like(s, 1.0 / 2500.0))
        sc["tracks"] = [t0]
        sc["walls"] = [(0, w, 0, S0 + 60, 3.3), ("div", -w, 0, SMAX, 3.3)]
        sc["masts"] = (0, -2.0, 25.0)
    else:
        raise SystemExit(f"unknown scene {name}")
    sc["S0"] = S0
    # objects
    if obj == "none":
        pass
    elif obj.startswith("p"):                      # p<d>[l<lat>]: a standing person at d m ahead (of the start), lateral lat
        d, _, lat = obj[1:].partition("l")
        sc["boxes"].append(P(float(d), float(lat or 0.0), name="person"))
    elif obj.startswith("walk"):                   # walk<d>: a person at d walking away at 1.5 m/s
        sc["boxes"].append(P(float(obj[4:]), 0.0, vs=1.5, name="walker"))
    elif obj.startswith("cross"):                  # cross<d>: crossing from -4 m to +4 m at 1.2 m/s
        sc["boxes"].append(P(float(obj[5:]), -4.0, vl=1.2, name="crosser"))
    elif obj.startswith("adjtrain"):               # a train standing on the other (left) track from d to d + 80 m
        d = float(obj[8:] or 90)
        sc["boxes"].append(dict(track=1 if len(sc["tracks"]) > 1 else 0, s=S0 + d,
                                l=0.0 if len(sc["tracks"]) > 1 else 4.1, L=80.0, W=3.0, H=3.6, name="adjtrain"))
    elif obj.startswith("recede"):                 # a 2 x 3 m vehicle receding from d at 6 m/s on our track
        sc["boxes"].append(dict(track=0, s=S0 + float(obj[6:]), l=0.0, L=10.0, W=2.6, H=3.0, vs=6.0, name="vehicle"))
    else:
        raise SystemExit(f"unknown object {obj}")
    return sc


def sample_frame(sc, t, rng):
    """World points for the train at arc S0 + speed t on track 0, transformed into the vehicle frame."""
    tr0 = sc["tracks"][0]
    sv = sc["S0"] + sc["speed"] * t
    vx, vy, vth = (float(v) for v in tr0.at(sv))
    c, s_ = np.cos(vth), np.sin(vth)
    parts, labels = [], []

    def add(px, py, pz, lab):
        parts.append(np.stack([px, py, pz], 1))
        labels.append(np.full(px.size, lab, dtype=np.int16))

    # bed (both tracks' corridors) and the near rails
    for ti, tr in enumerate(sc["tracks"]):
        n = 45000
        ss = sv + 3 + 197 * rng.random(n) ** 0.5
        l = rng.uniform(-1.3, 1.3, n)
        px, py, _ = tr.at(ss, l)
        add(px, py, -1.5 + rng.normal(0, 0.01, n), -1)
    for ti in sc["rails"]:
        tr = sc["tracks"][0]
        off = ti if ti else 0.0
        for side in (-1, 1):
            ss = sv + 3 + 57 * rng.random(12000) ** 0.5
            px, py, _ = tr.at(ss, off + side * 0.795 + rng.uniform(-0.03, 0.03, ss.size))
            add(px, py, -1.15 + rng.normal(0, 0.005, ss.size), -3)
    for wl in sc["walls"]:
        ti, lat, s0, s1, top = wl
        a, b = max(s0, sv + 2), min(s1, sv + 260)
        if b <= a:
            continue
        n = int(220 * (b - a))
        ss = rng.uniform(a, b, n)
        if ti == "div":
            lat_s = lat - 0.03 * np.clip(ss - (sv + 50), 0, None) if False else lat - 0.03 * np.clip(ss - (sc["S0"] + 50), 0, None)
            px, py, _ = tr0.at(ss, lat_s + rng.normal(0, 0.02, n))
        else:
            px, py, _ = sc["tracks"][ti].at(ss, lat + rng.normal(0, 0.02, n))
        add(px, py, rng.uniform(-1.4, top, n), -1)
    if "masts" in sc:
        ti, lat, step = sc["masts"]
        for sm in np.arange(sc["S0"] + 10, sc["S0"] + 260, step):
            if sm < sv + 3:
                continue
            n = 300
            px, py, _ = sc["tracks"][ti].at(np.full(n, sm) + rng.uniform(-0.15, 0.15, n), lat + rng.uniform(-0.15, 0.15, n))
            add(px, py, rng.uniform(-1.15, 5.0, n), -2)
    for bi, b in enumerate(sc["boxes"]):
        sb, lb = b["s"] + b.get("vs", 0.0) * t, b["l"] + b.get("vl", 0.0) * t
        tr = sc["tracks"][b["track"]]
        # front face (toward the train) and the side facing our track for long boxes; dense, thinned by range below
        n = 4000
        if b["L"] > 5:
            ss = sb + b["L"] * rng.random(n)
            side = -1.0 if b["l"] + (4.1 if b["track"] == 1 else 0) > 0 else 1.0
            ll = np.full(n, lb + side * b["W"] / 2)
            ss = np.concatenate([ss, np.full(n // 4, sb)])
            ll = np.concatenate([ll, lb + rng.uniform(-b["W"] / 2, b["W"] / 2, n // 4)])
        else:
            ss = np.full(n, sb)
            ll = lb + rng.uniform(-b["W"] / 2, b["W"] / 2, n)
        px, py, _ = tr.at(ss, ll)
        add(px, py, b.get("z0", -1.15) + b["H"] * rng.random(px.size), bi)
    P = np.concatenate(parts)
    lab = np.concatenate(labels)
    # world -> vehicle
    dx, dy = P[:, 0] - vx, P[:, 1] - vy
    X = c * dx + s_ * dy
    Y = -s_ * dx + c * dy
    Z = P[:, 2]
    keep = (X > 2.0) & (X < 250.0)
    X, Y, Z, lab, Pw = X[keep], Y[keep], Z[keep], lab[keep], P[keep]
    # thin to a LiDAR-like angular density: keep a point with probability min(1, (r0 / r)^2)
    r = np.hypot(X, Y)
    pk = np.minimum(1.0, (40.0 / np.maximum(r, 1.0)) ** 1.5)
    pk[lab == -3] = 1.0              # the near rails: dense as on the recordings
    for bi, b in enumerate(sc["boxes"]):   # objects: expected returns at 0.1 deg x 0.125 deg (front face)
        m = lab == bi
        if m.any():
            rb = float(np.median(r[m]))
            exp_n = (b["W"] if b["L"] <= 5 else b["L"]) / (rb * 0.00175) * b["H"] / (rb * 0.0022)
            pk[m] = min(1.0, exp_n / m.sum())
    keep = rng.random(r.size) < pk
    X, Y, Z, lab, Pw = X[keep], Y[keep], Z[keep], lab[keep], Pw[keep]
    # occlusion by the walls: a ray is blocked if it crosses a wall line (of a wall that exists there) before the point
    if sc["walls"]:
        f = np.linspace(0.05, 0.97, 24)[None, :]
        qx = vx + f * (Pw[:, 0:1] - vx)
        qy = vy + f * (Pw[:, 1:2] - vy)
        qz = f * Z[:, None]
        qs, ql = tr0.sl(qx.ravel(), qy.ravel())
        qs, ql = qs.reshape(qx.shape), ql.reshape(qx.shape)
        blocked = np.zeros(X.size, dtype=bool)
        for wl in sc["walls"]:
            ti, lat, s0, s1, top = wl
            if ti == "div":
                wlat = lat - 0.03 * np.clip(qs - (sc["S0"] + 50), 0, None)
            elif ti == 0:
                wlat = np.full_like(qs, lat)
            else:
                # the siding's wall: its lateral from track 0 at that arc
                t1 = sc["tracks"][ti]
                wx, wy, _ = t1.at(qs, lat)
                _, wlat = tr0.sl(wx.ravel(), wy.ravel())
                wlat = wlat.reshape(qs.shape)
            inside = (qs >= s0) & (qs <= s1) & (qz < top)
            beyond = np.where(wlat > 0, ql > wlat + 0.05, ql < wlat - 0.05)
            blocked |= (inside & beyond).any(1)
        keep = ~blocked
        X, Y, Z, lab = X[keep], Y[keep], Z[keep], lab[keep]
    xyz = np.stack([X, Y, Z], 1).astype(np.float32)
    return xyz, lab, sv


def truth(sc, t, sv):
    """Each box's nearest-face centre and size in the vehicle frame at time t."""
    tr0 = sc["tracks"][0]
    vx, vy, vth = (float(v) for v in tr0.at(sv))
    c, s_ = np.cos(vth), np.sin(vth)
    out = []
    for b in sc["boxes"]:
        sb, lb = b["s"] + b.get("vs", 0.0) * t, b["l"] + b.get("vl", 0.0) * t
        px, py, _ = sc["tracks"][b["track"]].at(sb, lb)
        dx, dy = float(px) - vx, float(py) - vy
        out.append(dict(name=b["name"], X=c * dx + s_ * dy, Y=-s_ * dx + c * dy, L=b["L"], W=b["W"], H=b["H"],
                        lat_true=lb))
    return out


def match(d, objs):
    for i, o in enumerate(objs):
        if o["L"] > 5:     # long box: anywhere along it
            ok = (o["X"] - 2 <= d["center"][0] <= o["X"] + o["L"] + 2)
        else:
            ok = abs(d["center"][0] - o["X"]) <= max(2.0, 0.03 * o["X"]) + o["L"] / 2 + 0.5
        if ok and abs(d["center"][1] - o["Y"]) <= 1.0 + o["W"] / 2:
            return i
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--mode", choices=("yaml", "union"), required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", type=int, default=None)
    ap.add_argument("--speed", type=float, default=None, help="ego speed m/s (default: the scene's)")
    ap.add_argument("--start", type=float, default=None, help="ego start arc offset (m)")
    a = ap.parse_args()
    repo = os.environ.get("RESENSE_REPO", os.path.dirname(os.path.dirname(resense.__file__)))
    cfg = DetectorConfig.from_yaml(os.path.join(repo, "configs/default.yaml"))
    if a.mode == "union":
        cfg = replace(cfg, track=replace(cfg.track, **UNION))
    sc = scene(a.scene)
    if a.speed is not None:
        sc["speed"] = a.speed
    if a.start is not None:
        sc["S0"] += a.start
    n = a.frames or sc["frames"]
    det = Detector(cfg)
    with open(a.out, "w") as f:
        for k in range(n):
            t = 0.1 * k
            rng = np.random.default_rng(1000 + k)
            xyz, lab, sv = sample_frame(sc, t, rng)
            objs = truth(sc, t, sv)
            res = det.process(Frame(xyz=xyz, intensity=np.full(len(xyz), 30.0, np.float32), stamp=t),
                              ego_speed=sc["speed"])
            dets = []
            for zone, lst in (("gauge", res.detections), ("warning", res.warnings)):
                for d in lst:
                    dd = dict(zone=d.zone, distance=round(float(d.distance), 2), lateral=round(float(d.lateral), 2),
                              center=[round(float(v), 2) for v in d.center], reason=d.reason, kind=d.kind, id=int(d.id),
                              n=int(d.n_points))
                    dd["obj"] = match(dd, objs)
                    dets.append(dd)
            tr = det.track
            cv = getattr(tr, "curve", None)
            row = dict(frame=k, sv=round(sv, 2), stop=bool(res.obstacle), n_points=int(len(xyz)),
                       obj_pts=[int((lab == i).sum()) for i in range(len(sc["boxes"]))],
                       objs=[{kk: (round(v, 2) if isinstance(v, float) else v) for kk, v in o.items()} for o in objs],
                       dets=dets, base_k=float(tr.curvature), base_valid=round(float(min(tr.axis_valid, 9999)), 1),
                       base_y100=round(float(tr.center_y(np.array([100.0]))[0]), 2),
                       curve=cv is not None,
                       curve_from=round(float(cv.curve_from), 1) if cv is not None else None,
                       curve_valid=round(float(cv.axis_valid), 1) if cv is not None else None,
                       curve_y100=round(float(cv.center_y(np.array([100.0]))[0]), 2) if cv is not None else None,
                       added=int(getattr(det, "_curve_added", 0)) if cv is not None else 0,
                       clear=float(res.clear_distance) if res.clear_distance is not None else None)
            # the true track's lateral at X = 100 m in the vehicle frame
            tr0 = sc["tracks"][0]
            vx, vy, vth = (float(v) for v in tr0.at(sv))
            ss = np.arange(sv, sv + 200, 0.5)
            px, py, _ = tr0.at(ss)
            X = np.cos(vth) * (px - vx) + np.sin(vth) * (py - vy)
            Y = -np.sin(vth) * (px - vx) + np.cos(vth) * (py - vy)
            row["true_y100"] = round(float(np.interp(100.0, X, Y)), 2)
            f.write(json.dumps(row) + "\n")
            if hasattr(det, "_curve_added"):
                det._curve_added = 0


if __name__ == "__main__":
    main()
