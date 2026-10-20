"""Sensor-agnostic ray-cast injector for real Falcon frames (sensor README backlog W5).

Rays are the frame's own raster: a ray is (scan_id, channel = flags & 3, scan_idx). A ray that
returned has its measured direction; a ray that did not return (into the open tunnel) is
reconstructed by linear interpolation in scan_idx between the nearest returned rays of the same
line on either side (validated by leave-out, ``validate_raster.py``). Rays beyond a line's
outermost returns are not invented.

Targets are boxes in a fixed track frame defined from the raw data, not from the detector:
along = raw x, lateral = y - (a + b x), height = z - (z0 + c x) above the rail head
(``TRACK`` below, fitted by ``track_reference.py``). Every coordinate is linear in the ray
parameter, so the slab test is exact for the sheared box. A ray hitting the box nearer than its
own nearest return is occluded. Each ray carries a Gaussian beam (datasheet divergence 0.1 deg):
its return probability is ``fill * pod(range, reflectivity * beam fraction on the face)``; a
returned ray (or one with more than half its beam on the face) loses its own returns, and a
return is added on the face (range noise 2 cm 1 sigma).

POD model (stated assumption, see PROTOCOL.md): ``pod = 1 - exp(-(x / x0) ** k)`` with
``x = rho / r**2``, anchored to the datasheet (rho 10 %, 250 m: POD 0.90) and k = 2.35
(POD 0.5 at 0.6 of the anchor signal). The person-like target (``calibrate_person.py``) is a 0.5 x 0.5 m box from -0.2 to 1.55 m with a
silhouette fill factor (``fill`` 0.78: the real person's ray-return fraction at 30..100 m, where
POD is saturated) and two reflectivities by height (``rho = {"split": 0.8, "lower": .., "upper": ..}``).
"""
from __future__ import annotations

import math

import numpy as np

TRACK = {"a": 0.05, "b": 0.0, "z0": -1.77, "c": -0.04174}   # overwritten from spec["track"]
K_POD = 2.35
X90 = 0.10 / 250.0 ** 2
X0 = X90 / (-math.log(0.1)) ** (1.0 / K_POD)


def pod(r, rho, k=K_POD):
    x = rho / np.maximum(np.asarray(r, dtype=np.float64), 1.0) ** 2
    x0 = X90 / (-math.log(0.1)) ** (1.0 / k)
    return 1.0 - np.exp(-(x / x0) ** k)


def angles(xyz):
    xyz = np.asarray(xyz, dtype=np.float64)
    r = np.linalg.norm(xyz, axis=1)
    return np.degrees(np.arctan2(xyz[:, 1], xyz[:, 0])), np.degrees(np.arcsin(xyz[:, 2] / np.maximum(r, 1e-9))), r


def unit(az, el):
    a, e = np.radians(az), np.radians(el)
    return np.stack([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)], axis=-1)


def raster_rays(d, az_lo, az_hi, el_lo, el_hi, line_margin_deg=1.5, side_deg=15.0):
    """Rays of this frame inside the angular window: (key, az, el, observed, nearest_range).
    key = line * 4096 + scan_idx; observed rays keep their measured direction."""
    az, el, r = angles(d["xyz"])
    line = d["scan_id"].astype(np.int64) * 4 + (d["flags"].astype(np.int64) & 3)
    six = d["scan_idx"].astype(np.int64)
    near = (az > az_lo - side_deg) & (az < az_hi + side_deg) & (el > el_lo - line_margin_deg) & (el < el_hi + line_margin_deg)
    out_k, out_a, out_e, out_obs, out_r = [], [], [], [], []
    for ln in np.unique(line[near]):
        m = np.flatnonzero((line == ln) & (az > az_lo - side_deg) & (az < az_hi + side_deg))
        s, a, e, rr = six[m], az[m], el[m], r[m]
        # one direction per ray (multi-return rays: mean direction, nearest range)
        us, inv = np.unique(s, return_inverse=True)
        cnt = np.bincount(inv)
        ua = np.bincount(inv, a) / cnt
        ue = np.bincount(inv, e) / cnt
        ur = np.full(us.size, np.inf)
        np.minimum.at(ur, inv, rr)
        if us.size < 2:
            continue
        full = np.arange(us[0], us[-1] + 1)
        fa = np.interp(full, us, ua)
        fe = np.interp(full, us, ue)
        obs = np.isin(full, us)
        fr = np.full(full.size, np.inf)
        fr[obs] = ur
        fa[obs], fe[obs] = ua, ue
        w = (fa >= az_lo) & (fa <= az_hi) & (fe >= el_lo) & (fe <= el_hi)
        if w.any():
            out_k.append(ln * 4096 + full[w])
            out_a.append(fa[w])
            out_e.append(fe[w])
            out_obs.append(obs[w])
            out_r.append(fr[w])
    if not out_k:
        z = np.zeros(0)
        return z.astype(np.int64), z, z, z.astype(bool), z
    return (np.concatenate(out_k), np.concatenate(out_a), np.concatenate(out_e),
            np.concatenate(out_obs), np.concatenate(out_r))


def box_hit(dirs, box, track):
    """Entry range of each unit ray (origin 0) into the sheared track-frame box, inf if none.
    box = (s0, s1, l0, l1, h0, h1): along, lateral, height above the rail head."""
    a, b, z0, c = track["a"], track["b"], track["z0"], track["c"]
    dx, dy, dz = dirs[:, 0], dirs[:, 1], dirs[:, 2]
    # coordinate(t) = alpha + beta t
    slabs = [(0.0, dx, box[0], box[1]), (-a, dy - b * dx, box[2], box[3]), (-z0, dz - c * dx, box[4], box[5])]
    t0 = np.zeros(len(dirs))
    t1 = np.full(len(dirs), np.inf)
    for alpha, beta, lo, hi in slabs:
        with np.errstate(divide="ignore", invalid="ignore"):
            ta = (lo - alpha) / beta
            tb = (hi - alpha) / beta
        tmin = np.where(beta != 0, np.minimum(ta, tb), np.where((alpha >= lo) & (alpha <= hi), -np.inf, np.inf))
        tmax = np.where(beta != 0, np.maximum(ta, tb), np.where((alpha >= lo) & (alpha <= hi), np.inf, -np.inf))
        t0 = np.maximum(t0, tmin)
        t1 = np.minimum(t1, tmax)
    return np.where((t1 > t0) & (t0 > 0), t0, np.inf)


def track_to_raw(s, lat, h, track):
    x = np.asarray(s, dtype=np.float64)
    return np.stack([x, lat + track["a"] + track["b"] * x, h + track["z0"] + track["c"] * x], axis=-1)


class Injector:
    """spec = {"track": {...}, "seed": int, "targets": [{"from": f0, "to": f1, "size": [L, W, H],
    "lat": 0.0, "bottom": -0.2, "rho": 0.2 | "person", "dist": D | "start": D0, "speed": v (m/s, toward the
    sensor), "stop_at": Dmin, "intensity": 20}]}"""

    def __init__(self, spec):
        self.spec = spec
        self.track = dict(TRACK, **spec.get("track", {}))
        self.rng = np.random.default_rng(int(spec.get("seed", 0)))
        self.k = float(spec.get("k_pod", K_POD))

    def target_dist(self, t, i):
        if "path" in t:          # [[frame, along, lateral], ...], linear between rows
            P = np.asarray(t["path"], dtype=np.float64)
            return float(np.interp(i, P[:, 0], P[:, 1]))
        if "dist" in t:
            return float(t["dist"])
        d = float(t["start"]) - float(t["speed"]) * 0.1 * (i - int(t["from"]))
        return max(d, float(t.get("stop_at", 0.0)))

    def cast(self, d, box, t, occlusion=True):
        """Rays of frame ``d`` that see the box's front face: (keys, dirs, range, beam fraction,
        return probability, hit height). Beam: Gaussian, sigma = ``sigma_deg`` (datasheet divergence
        0.1 deg taken as the 1/e^2 full width: sigma 0.025 deg); the fraction of the beam on the face
        is the product of the azimuth and elevation fractions; the return probability is
        fill * POD(range, rho * fraction). Rays whose own nearest return is in front of the face
        are untouched (occluded by the scene)."""
        from scipy.special import ndtr
        sig = float(self.spec.get("sigma_deg", 0.025))
        s0 = box[0]
        cy = np.array([box[2], box[3]]) + self.track["a"] + self.track["b"] * s0
        cz = np.array([box[4], box[5]]) + self.track["z0"] + self.track["c"] * s0
        az_b = np.degrees(np.arctan2(cy, s0))
        el_b = np.degrees(np.arctan2(cz, np.hypot(s0, cy.mean())))
        pad = max(0.1, 5 * sig)
        keys, raz, rel, obs, rnear = raster_rays(d, az_b.min() - pad, az_b.max() + pad, el_b.min() - pad, el_b.max() + pad)
        if not len(keys):
            return None
        dirs = unit(raz, rel)
        tf = s0 / dirs[:, 0]
        f = ((ndtr((az_b.max() - raz) / sig) - ndtr((az_b.min() - raz) / sig))
             * (ndtr((el_b.max() - rel) / sig) - ndtr((el_b.min() - rel) / sig)))
        ok = (f > 1e-3) & ((tf < rnear - 0.05) | (not occlusion))
        keys, dirs, tf, f = keys[ok], dirs[ok], tf[ok], f[ok]
        pt = dirs * tf[:, None]
        hh = pt[:, 2] - (self.track["z0"] + self.track["c"] * pt[:, 0])
        rho = t["rho"]
        if isinstance(rho, dict):
            # two-band target (the person model): reflectivity by hit height above the rail head
            rr_ = np.where(hh < float(rho["split"]), float(rho["lower"]), float(rho["upper"]))
        else:
            rr_ = float(rho)
        p = float(t.get("fill", 1.0)) * pod(tf, rr_ * f, self.k)
        return keys, dirs, tf, f, p, hh

    def apply(self, i, d, det=None):
        xyz, inten = d["xyz"], d["inten"]
        info = []
        drop = np.zeros(len(xyz), dtype=bool)
        add_p, add_i = [], []
        line = None
        for t in self.spec["targets"]:
            if not (int(t["from"]) <= i < int(t["to"])):
                continue
            D = self.target_dist(t, i)
            L, W, H = t["size"]
            lat, bottom = float(t.get("lat", 0.0)), float(t.get("bottom", -0.2))
            if "path" in t:
                P = np.asarray(t["path"], dtype=np.float64)
                lat = float(np.interp(i, P[:, 0], P[:, 2]))
            box = (D - L / 2, D + L / 2, lat - W / 2, lat + W / 2, bottom, bottom + H)
            ray = self.cast(d, box, t)
            if ray is None:
                info.append({"d": round(D, 2), "rays": 0, "rays_inside": 0, "returns": 0, "occluded": 0})
                continue
            keys, dirs, tf, f, p, hh = ray
            u = self.rng.random(len(keys))
            ret = u < p
            occl = ret | (f > 0.5)
            if line is None:
                line = d["scan_id"].astype(np.int64) * 4 + (d["flags"].astype(np.int64) & 3)
                pkey = line * 4096 + d["scan_idx"].astype(np.int64)
            gone = np.isin(pkey, keys[occl])
            drop |= gone
            rr = tf[ret] + self.rng.normal(0.0, 0.02, int(ret.sum()))
            add_p.append(dirs[ret] * rr[:, None])
            add_i.append(np.full(int(ret.sum()), float(t.get("intensity", 20.0))))
            info.append({"d": round(D, 2), "rays": int((f > 0.01).sum()), "rays_inside": int((f > 0.5).sum()),
                         "returns": int(ret.sum()), "expected": round(float(p.sum()), 2), "occluded": int(gone.sum())})
        if not info:
            return xyz, inten, None
        if add_p:
            xyz = np.concatenate([xyz[~drop], np.concatenate(add_p).astype(np.float32)])
            inten = np.concatenate([inten[~drop], np.concatenate(add_i).astype(np.float32)])
        return xyz, inten, info
