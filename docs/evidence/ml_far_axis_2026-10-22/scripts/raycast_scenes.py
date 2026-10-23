#!/usr/bin/env python3
"""Ray-cast tunnel sequences along a KNOWN track centreline, for validating the far-axis label pipeline.

A centreline is given by its curvature profile k(s) (1/m, + left); heading and position are integrated
exactly (0.05 m steps). The tunnel (bed, two rails 1.59 m apart, benches, a round lining or flat walls,
wall fixtures every 0.4-2.5 m and irregular sleepers for odometry texture) is swept along it and ray-cast from a sensor that drives
along the centreline (lateral mount offset, small heading sway) at ~11 m/s on the Pandar ray grid.

    raycast_scenes.py <out_dir> [--scenes straight,r300,...] [--frames 420]

Writes <out_dir>/<scene>/f_00000.npz (vehicle-frame xyz float32, intensity, ring) and
<out_dir>/<scene>/truth.json: per frame the sensor pose in the world and the centreline in that frame's
vehicle coordinates (y at X = 0..260 m, 1 m steps), so labels can be checked against the exact answer.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from resense.sensor import RING_ELEVATION_DEG, ray_directions  # noqa: E402

DS = 0.05
BED = -1.6              # bed below the sensor (m)


def _ramp(s, s0, L):
    return np.clip((s - s0) / L, 0.0, 1.0) if L > 0 else (s >= s0).astype(float)


def scene_curvature(name: str, s: np.ndarray) -> np.ndarray:
    """k(s) of the named scene; clothoid transitions of 40-60 m between straight and arc."""
    z = np.zeros_like(s)
    if name == "straight":
        return z
    if name.startswith("r") and name[1:].isdigit():          # straight 60 m, clothoid 50 m, constant arc
        R = float(name[1:])
        return _ramp(s, 60.0, 50.0) / R
    if name.startswith("l") and name[1:].isdigit():          # the same to the right
        R = float(name[1:])
        return -_ramp(s, 60.0, 50.0) / R
    if name == "entry400":                                   # long straight, the curve starts ahead (curve entry)
        return _ramp(s, 330.0, 40.0) / 400.0
    if name == "scurve400":                                  # left R 400, reversing to right R 400
        return _ramp(s, 60.0, 50.0) / 400.0 - 2.0 * _ramp(s, 260.0, 60.0) / 400.0
    if name == "scurve700":
        return -_ramp(s, 100.0, 50.0) / 700.0 + 2.0 * _ramp(s, 330.0, 60.0) / 700.0
    if name == "exit500":                                    # in a curve, it straightens ahead
        return (1.0 - _ramp(s, 300.0, 50.0)) / 500.0
    raise ValueError(name)


def centreline(name: str, length: float):
    s = np.arange(0.0, length + DS, DS)
    k = scene_curvature(name, s)
    psi = np.concatenate([[0.0], np.cumsum(0.5 * (k[1:] + k[:-1]) * DS)])
    x = np.concatenate([[0.0], np.cumsum(0.5 * (np.cos(psi[1:]) + np.cos(psi[:-1])) * DS)])
    y = np.concatenate([[0.0], np.cumsum(0.5 * (np.sin(psi[1:]) + np.sin(psi[:-1])) * DS)])
    return s, x, y, psi, k


def _sweep(px, py, nx, ny, prof):
    """Triangles of a cross-section polyline prof [(u, z), ...] swept along the path (px, py, normal n)."""
    prof = np.asarray(prof, dtype=np.float64)
    n, m = px.size, prof.shape[0]
    V = np.empty((n, m, 3))
    V[:, :, 0] = px[:, None] + nx[:, None] * prof[None, :, 0]
    V[:, :, 1] = py[:, None] + ny[:, None] * prof[None, :, 0]
    V[:, :, 2] = prof[None, :, 1]
    idx = np.arange(n * m).reshape(n, m)
    a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
    T = np.concatenate([np.stack([a, b, c], -1).reshape(-1, 3), np.stack([a, c, d], -1).reshape(-1, 3)])
    return V.reshape(-1, 3), T


def _box(cx, cy, cz, L, W, H, yaw):
    c, s_ = np.cos(yaw), np.sin(yaw)
    v = np.array([[sx * L / 2, sy * W / 2, sz * H / 2] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
    v = np.stack([cx + c * v[:, 0] - s_ * v[:, 1], cy + s_ * v[:, 0] + c * v[:, 1], cz + v[:, 2]], 1)
    f = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                  [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return v, f


def build_scene(name: str, length: float, rng, kind: str = "round"):
    import open3d as o3d
    s, x, y, psi, _ = centreline(name, length)
    step = 10                                   # sweep every 0.5 m
    px, py, ps = x[::step], y[::step], psi[::step]
    nx, ny = -np.sin(ps), np.cos(ps)
    g = 1.59 / 2
    rail = lambda u: [(u - 0.036, BED), (u - 0.036, BED + 0.16), (u + 0.036, BED + 0.16), (u + 0.036, BED)]
    profs = [[(-2.0, BED), (2.0, BED)], rail(-g), rail(g)]
    if kind == "round":
        R, zc = 2.75, BED + 1.9
        profs += [[(-2.0, BED), (-2.0, BED + 0.9), (-2.6, BED + 0.9)], [(2.0, BED), (2.0, BED + 0.9), (2.6, BED + 0.9)]]
        a = np.radians(np.linspace(-35.0, 215.0, 60))
        profs.append(list(zip(R * np.cos(a), zc + R * np.sin(a))))
        wall_u = 2.6
    else:                                       # box tunnel: flat walls, flat ceiling
        profs += [[(-2.4, BED), (-2.4, BED + 5.0), (2.4, BED + 5.0), (2.4, BED)]]
        wall_u = 2.4
    Vs, Ts, off = [], [], 0
    for p in profs:
        V, T = _sweep(px, py, nx, ny, p)
        Vs.append(V)
        Ts.append(T + off)
        off += V.shape[0]
    # odometry texture: wall fixtures (brackets, cable clamps, boxes) every 0.4-2.5 m on either side at random
    # heights and sizes, and sleepers every 0.55-0.75 m (0.07 m above the bed, between and beyond the rails)
    def add(v, f):
        nonlocal off
        Vs.append(v)
        Ts.append(f + off)
        off += v.shape[0]
    si = 3.0
    while si < length - 3:
        j = int(si / DS)
        side = rng.choice([-1.0, 1.0])
        u = side * (wall_u - 0.2)
        add(*_box(x[j] - np.sin(psi[j]) * u, y[j] + np.cos(psi[j]) * u, BED + rng.uniform(0.9, 3.0),
                  rng.uniform(0.1, 0.6), rng.uniform(0.15, 0.4), rng.uniform(0.1, 0.5), psi[j]))
        si += rng.uniform(0.4, 2.5)
    si = 1.0
    while si < length - 1:
        j = int(si / DS)
        add(*_box(x[j], y[j], BED + 0.035, 0.26, 2.5, 0.07, psi[j]))
        si += rng.uniform(0.55, 0.75)
    V = np.concatenate(Vs).astype(np.float32)
    T = np.concatenate(Ts).astype(np.uint32)
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(o3d.core.Tensor(V), o3d.core.Tensor(T))
    return scene, (s, x, y, psi)


def render(scene, pose, dirs, ring, rng, noise=0.015):
    import open3d as o3d
    X0, Y0, Z0, h = pose
    c, s_ = np.cos(h), np.sin(h)
    dw = np.stack([c * dirs[:, 0] - s_ * dirs[:, 1], s_ * dirs[:, 0] + c * dirs[:, 1], dirs[:, 2]], 1)
    rays = np.concatenate([np.tile([X0, Y0, Z0], (dirs.shape[0], 1)), dw], 1).astype(np.float32)
    t = scene.cast_rays(o3d.core.Tensor(rays))["t_hit"].numpy()
    ok = np.isfinite(t) & (t > 2.5) & (t < 205.0)
    t = t[ok] + rng.normal(0.0, noise, int(ok.sum())) * (1.0 + t[ok] / 100.0)
    keep = rng.random(t.size) > 0.05                      # 5 % dropout
    xyz = (dirs[ok][keep] * t[keep, None]).astype(np.float32)
    return xyz, ring[ok][keep]


def truth_y(vx, vy, Xq):
    """Centreline lateral at Xq from samples along the track; NaN beyond where the track still advances in X
    (a sharp curve turns away before reaching the far query distances)."""
    stop = np.flatnonzero(np.diff(vx) <= 0)
    n = stop[0] + 1 if stop.size else vx.size
    y = np.interp(Xq, vx[:n], vy[:n])
    y[(Xq < vx[0]) | (Xq > vx[n - 1])] = np.nan
    return np.round(y, 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--scenes", default="straight,r300,r500,l700,r1000,entry400,scurve400,scurve700,exit500")
    ap.add_argument("--frames", type=int, default=420)
    ap.add_argument("--speed", type=float, default=11.0)
    ap.add_argument("--box", default="r500", help="scenes built as a box tunnel instead of a round one")
    a = ap.parse_args()
    dirs = ray_directions()
    ring = np.repeat(np.arange(RING_ELEVATION_DEG.size, dtype=np.uint16)[::-1][:, None],
                     dirs.shape[0] // RING_ELEVATION_DEG.size, 1).reshape(-1)
    for name in a.scenes.split(","):
        rng = np.random.default_rng(abs(hash(name)) % 2 ** 31)
        length = a.frames * a.speed / 10.0 + 280.0
        scene, (s, x, y, psi) = build_scene(name, length, rng, "box" if name in a.box.split(",") else "round")
        d = os.path.join(a.out, name)
        os.makedirs(d, exist_ok=True)
        truth = {"scene": name, "frames": []}
        sway = 0.0
        for k in range(a.frames):
            sk = 5.0 + k * a.speed / 10.0 * (1.0 + 0.05 * np.sin(k / 37.0))
            j = int(round(sk / DS))
            sway = 0.9 * sway + rng.normal(0.0, 0.0004)        # heading sway of the car body on the track (rad)
            off = 0.10                                         # sensor 0.1 m left of the track centre
            h = psi[j] + sway
            X0 = x[j] - np.sin(psi[j]) * off
            Y0 = y[j] + np.cos(psi[j]) * off
            # the firing azimuths of a spinning LiDAR are not locked to the frame: a random sub-step phase per frame
            ph = np.radians(rng.uniform(0.0, 0.1))
            cph, sph = np.cos(ph), np.sin(ph)
            dj = np.stack([cph * dirs[:, 0] - sph * dirs[:, 1], sph * dirs[:, 0] + cph * dirs[:, 1], dirs[:, 2]], 1)
            xyz, rg = render(scene, (X0, Y0, 0.0, h), dj, ring, rng)
            np.savez_compressed(os.path.join(d, f"f_{k:05d}.npz"), xyz=xyz, inten=np.full(len(xyz), 20.0, np.float32),
                                ring=rg)
            # the centreline ahead in this frame's vehicle coordinates
            m = (s >= sk - 5) & (s <= sk + 280)
            dx, dy = x[m] - X0, y[m] - Y0
            c, s_ = np.cos(h), np.sin(h)
            vx, vy = c * dx + s_ * dy, -s_ * dx + c * dy
            Xq = np.arange(0.0, 261.0, 1.0)
            truth["frames"].append({"i": k, "s": round(float(sk), 3), "pose": [float(X0), float(Y0), float(h)],
                                    "y": truth_y(vx, vy, Xq).tolist()})
        json.dump(truth, open(os.path.join(d, "truth.json"), "w"))
        print(name, a.frames, "frames", flush=True)


if __name__ == "__main__":
    main()
