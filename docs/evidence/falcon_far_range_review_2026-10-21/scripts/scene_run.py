#!/usr/bin/env python3
"""Reviewer's scene runner (falcon far range 1.3 review, 21.10): replay real Falcon frames through the detector of
the checkout in RESENSE_REPO, after a geometric edit of the raw scene, and record per-frame rows plus the far-axis
state (read-only).

Edits (raw sensor frame, ROS axes; lateral = y - (a + b x) of the track reference ``track_reference.json``):
  * inject   ray-cast targets with the author's injector (inject.py), placed on the straight track reference;
             applied BEFORE the warp, so the targets follow the warped (curved) track.
  * warp     y += dir * 0.5 * (x - xc)^2 / R for x > xc (a curve starting at xc), applied to the point groups listed:
             centre |lat| <= 1.0 (bed, rails, people, injected targets), left lat > 1.0, right -4.5 < lat < -1.0
             (this track's column row), farright lat <= -4.5 (the neighbour structure), high h > 3.0 (ceiling/wires).
  * skew     y += slope * (x - x0) for x > x0, on the listed groups (structures diverging from a straight track).
  * shift    y += dy for the listed groups and x in [x0, x1] (a parallel but offset row).
  * scroll   a moving train: frame k of the window (k = i - first) shows the scene of the base frame moved towards
             the sensor by v * 0.1 * k for x > x_from (structures beyond 400 m are not invented: what scrolls in is
             empty). The curve start moves with it (xc - v * 0.1 * k).
  * outer_wall  add a vertical wall face at lateral (track-relative, curved) -dir * w beyond xc on the outside of the
             curve: every ray whose return lies behind that face (or which had no return out to 400 m along +x) gets
             its return on the face instead (ray-consistent, no extra rays invented).

    scene_run.py --cache DIR --frames a:b --out PREFIX [--spec spec.json] [--pre sec.key=val ...] [--plain]

``--plain`` runs without any edit (must equal the author's run_far.py rows: instrumentation check).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(os.environ["RESENSE_REPO"])
EV = Path("/home/user/ReSense/docs/evidence")          # the evidence scripts are read from the review checkout
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "ros2_ws/src/resense_ros"))
sys.path.insert(0, str(EV / "judgement_2026-10-13/scripts"))
sys.path.insert(0, str(EV / "falcon_long_range_2026-10-19/scripts"))
import numpy as np  # noqa: E402
import yaml  # noqa: E402

import resense  # noqa: E402
assert str(Path(resense.__file__).resolve()).startswith(str(REPO.resolve())), resense.__file__
from judge_runner import CONFIG, record  # noqa: E402,F401
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import Frame, axis_matrix  # noqa: E402
from resense_ros.sensor_profiles import apply_sensor_profile  # noqa: E402
from inject import Injector  # noqa: E402

TRACK = json.loads((EV / "falcon_long_range_2026-10-19/track_reference.json").read_text())["track"]


def build_cfg(profile, pre):
    cfg = DetectorConfig.from_yaml(str(REPO / "configs/default.yaml"))
    cfg.calibration.enabled = True
    for s in pre:
        k, v = s.split("=", 1)
        sec, key = k.split(".", 1)
        setattr(getattr(cfg, sec), key, yaml.safe_load(v))
    cfg, _ = apply_sensor_profile(cfg, profile)
    return cfg


def crop(xyz, lo, hi):
    x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    r2 = x.astype(np.float32) ** 2
    r2 += y * y
    r2 += z * z
    return (r2 >= lo * lo) & (r2 <= hi * hi)


def groups(xyz):
    x = xyz[:, 0].astype(np.float64)
    lat = xyz[:, 1] - (TRACK["a"] + TRACK["b"] * x)
    h = xyz[:, 2] - (TRACK["z0"] + TRACK["c"] * x)
    g = {"centre": np.abs(lat) <= 1.0, "left": lat > 1.0, "right": (lat < -1.0) & (lat > -4.5), "farright": lat <= -4.5}
    hi = h > 3.0
    for k in g:
        g[k] = g[k] & ~hi
    g["high"] = hi
    return g


def arc(x, xc, R):
    return np.where(x > xc, 0.5 * (x - xc) ** 2 / R, 0.0)


def edit(xyz, k, spec):
    """The geometric edit of frame k of the window (raw frame). Returns (float32 xyz, kept mask of the input)."""
    xyz = xyz.astype(np.float64).copy()
    keep = np.ones(len(xyz), dtype=bool)
    sc = spec.get("scroll")
    shift_x = 0.0
    if sc:
        shift_x = float(sc["v"]) * 0.1 * k
        m = xyz[:, 0] > sc.get("x_from", 50.0)
        xyz[m, 0] -= shift_x
        keep = ~(m & (xyz[:, 0] <= sc.get("x_from", 50.0)))   # scrolled into the near field: dropped (not real)
        xyz = xyz[keep]
    g = groups(xyz)
    for s in spec.get("skew", []):
        sel = np.zeros(len(xyz), dtype=bool)
        for name in s["groups"]:
            sel |= g[name]
        x0 = float(s["x0"])
        sel &= xyz[:, 0] > x0
        xyz[sel, 1] += float(s["slope"]) * (xyz[sel, 0] - x0)
    for s in spec.get("shift", []):
        sel = np.zeros(len(xyz), dtype=bool)
        for name in s["groups"]:
            sel |= g[name]
        sel &= (xyz[:, 0] >= float(s.get("x0", 0.0))) & (xyz[:, 0] <= float(s.get("x1", 1e9)))
        xyz[sel, 1] += float(s["dy"])
    g = groups(xyz)
    for w in spec.get("warp", []):
        xc = float(w["xc"]) - shift_x
        sel = np.zeros(len(xyz), dtype=bool)
        for name in w["groups"]:
            sel |= g[name]
        xyz[sel, 1] += float(w.get("dir", 1.0)) * arc(xyz[sel, 0], xc, float(w["R"]))
        if w.get("clear_envelope"):
            # structures (not warped with the track) that the curved track would run into: removed (an opening)
            e = float(w["clear_envelope"])
            rel = xyz[:, 1] - (TRACK["a"] + TRACK["b"] * xyz[:, 0]) - float(w.get("dir", 1.0)) * arc(xyz[:, 0], xc, float(w["R"]))
            struct = ~sel & ~g["high"]
            gone = struct & (xyz[:, 0] > xc) & (np.abs(rel) < e)
            xyz = xyz[~gone]
            keep[np.flatnonzero(keep)[gone]] = False
            g = groups(xyz)
        if w.get("outer_wall"):
            xyz = outer_wall(xyz, xc, float(w["R"]), float(w.get("dir", 1.0)), float(w["outer_wall"]))
            g = groups(xyz)
    return xyz.astype(np.float32), keep


def outer_wall(xyz, xc, R, d, w):
    """Vertical face y = a + b x + d * (arc(x) - w) for x > xc (outside of a curve of direction d), heights from the
    rail head to 4.5 m. A return behind the face along its own ray is moved onto the face. Closed form: along a ray
    y = m x, g(s) = d (y_ray - y_face) at x = xc + s is -s^2 / (2R) + k s + g0 with k = d (m - b), g0 = g(0); the ray
    crosses the face at s = 0 when g0 <= 0, else at the positive root (checked against outer_wall_loop)."""
    a, b, z0, c = TRACK["a"], TRACK["b"], TRACK["z0"], TRACK["c"]
    p = xyz.astype(np.float64)
    r = np.linalg.norm(p, axis=1)
    u = p / np.maximum(r, 1e-9)[:, None]
    idx = np.flatnonzero((u[:, 0] > 0.3) & (r * u[:, 0] > xc))
    if idx.size == 0:
        return xyz
    m = u[idx, 1] / u[idx, 0]
    k = d * (m - b)
    g0 = d * (m * xc - a - b * xc) + w
    s = np.where(g0 <= 0, 0.0, R * (k + np.sqrt(np.maximum(k * k + 2.0 * g0 / R, 0.0))))
    rr = (xc + s) / u[idx, 0]
    hit = rr < r[idx]
    q = p[idx[hit]] / r[idx[hit], None] * rr[hit, None]
    h = q[:, 2] - (z0 + c * q[:, 0])
    ok = (h > -0.3) & (h < 4.5)
    p[idx[hit][ok]] = q[ok]
    return p


def outer_wall_loop(xyz, xc, R, d, w):
    """Reference implementation (sampled every 0.5 m along x; slow): the check of outer_wall()."""
    a, b, z0, c = TRACK["a"], TRACK["b"], TRACK["z0"], TRACK["c"]
    p = xyz.astype(np.float64)
    r = np.linalg.norm(p, axis=1)
    u = p / np.maximum(r, 1e-9)[:, None]
    cand = (u[:, 0] > 0.3) & (r * u[:, 0] > xc)
    idx = np.flatnonzero(cand)
    if idx.size == 0:
        return xyz
    ts = np.arange(xc, 420.0, 0.5)                                  # along-x samples
    best = np.full(idx.size, np.inf)
    for t in ts:                                                    # first x where the ray crosses the face
        rr = t / u[idx, 0]
        y = rr * u[idx, 1]
        face = a + b * t + d * (0.5 * (t - xc) ** 2 / R - w)
        crossed = (d * (y - face) <= 0) & ~np.isfinite(best) & (rr < r[idx])
        best[crossed] = rr[crossed]
    hit = np.isfinite(best)
    q = p[idx[hit]] / r[idx[hit], None] * best[hit, None]
    h = q[:, 2] - (z0 + c * q[:, 0])
    ok = (h > -0.3) & (h < 4.5)
    p[idx[hit][ok]] = q[ok]
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/home/user/data/falcon")
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--spec", default="")
    ap.add_argument("--pre", action="append", default=[])
    ap.add_argument("--profile", default="falcon_ros")
    ap.add_argument("--plain", action="store_true")
    a = ap.parse_args()
    cache = Path(a.cache)
    meta = json.loads((cache / "meta.json").read_text())
    lo, hi = (int(v) for v in a.frames.split(":"))
    spec = {} if a.plain or not a.spec else json.loads(Path(a.spec).read_text())
    cfg = build_cfg(a.profile, a.pre)
    det = Detector(cfg)
    R_vs = axis_matrix(cfg.sensor).astype(np.float32)
    inj = Injector(dict(spec["inject"], track=TRACK)) if spec.get("inject") else None
    base = spec.get("scroll", {}).get("base_frame")
    t0 = time.time()
    last = None
    with open(a.out + ".jsonl", "w") as fj:
        for i in range(lo, hi):
            m = meta[i]
            stamp = m["stamp"]
            if last is not None:
                gap = stamp - last
                if gap < -0.5 or gap > 30.0:
                    det = Detector(cfg)
                elif gap > 1.0:
                    det.reset()
            last = stamp
            src = i if base is None else int(base)
            d = dict(np.load(cache / f"f_{src:05d}.npz"))
            xyz, inten = d["xyz"], d["inten"]
            info = None
            if inj is not None:
                xyz, inten, info = inj.apply(i, d, det)
            if spec:
                xyz, keep = edit(xyz, i - lo, spec)
                inten = inten[keep]
            k = crop(xyz, cfg.sensor.min_range, cfg.sensor.max_range)
            frame = Frame(xyz=xyz[k] @ R_vs.T, intensity=inten[k], ring=None, stamp=stamp, frame_id=m["frame_id"],
                          meta={"n_raw": m["n_raw"], "n_near": m["n_near"]})
            res = det.process(frame, ego_speed=None)
            r = record(i, m["bag_t"], stamp, res, 0.0, 0.0, m["frame_id"], "/iv_points")
            r["mount_rotation"] = np.asarray(det.mount_rotation).tolist()
            if info is not None:
                r["inj"] = info
            fa = getattr(det, "_far_axis", None)
            r["far"] = None if fa is None else fa.to_dict()
            r["axis_valid_near"] = round(float(det.track.axis_valid), 1) if det.track is not None else None
            fj.write(json.dumps(r) + "\n")
    json.dump({"frames": [lo, hi], "spec": spec, "pre": a.pre, "repo": str(REPO), "wall_s": round(time.time() - t0, 1)},
              open(a.out + ".meta.json", "w"), indent=1)


if __name__ == "__main__":
    main()
