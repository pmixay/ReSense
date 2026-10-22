#!/usr/bin/env python3
"""Reviewer's adversarial scenes for the F1a bounded head top (own code, not the author's).

Full detector (fresh ``Detector(DetectorConfig())`` of RESENSE_REPO per scene) on the reviewer's extended caster
``rc2.py``. Every scene is a relative approach START -> START - STEP * (NFRAMES - 1) (default 58 -> 22.8 m, 0.8 m per
frame, 45 frames, a fresh noise seed per frame), exactly the review's ``approach_bed`` protocol. ``matched`` = the
review's definition: a gauge detection whose distance is within [d - 1, d + L + 1] and whose centre is within 0.6 m
laterally of the target's centre (the first object of the scene is the target).

``--trace`` (read-only): ``resense.detector.rail_reference_check`` is wrapped; at every call the CONTROL's function
(v1.2.0's ``resense/lowobj.py``, loaded from /home/user/wt/control by file path) is evaluated on the same arguments,
and every cluster the candidate rejects but v1.2.0 keeps is logged as a new-branch rejection, together with
  * pre0: the condition in the code (capped top < all-returns line + margin),
  * pre1: the pre-repair rule as it was in 0acb18c (capped top < low-free line + margin, that line present),
  * is it the target (distance / lateral within the match window),
  * the candidate's H (``lowobj.rail_head_top`` called again, read-only) and the uncapped top.
A traced run must equal its plain run (caller compares ``matched`` / ``any_gauge``).

    RESENSE_REPO=<checkout> python attack.py --family NAME --out out.json [--trace] [--jobs 4]
"""
import argparse
import importlib.util
import itertools
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = os.environ["RESENSE_REPO"]
sys.path.insert(0, ROOT)
sys.path.insert(0, str(Path(__file__).resolve().parent))

import rc2  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import Frame  # noqa: E402

CONTROL_LOWOBJ = "/home/user/wt/control/resense/lowobj.py"
HEAD = rc2.FLOOR + 0.18


def _ctrl_module():
    spec = importlib.util.spec_from_file_location("ctrl_lowobj", CONTROL_LOWOBJ)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def head_at(spec, x, side):
    """real head top (vehicle z) of rail ``side`` (+1 left / -1 right) at x."""
    if spec.get("head_mode") == "const":       # the review's approach_bed world: top = FLOOR + 0.18 + raise_ + delta
        z = HEAD + spec.get("raise_", 0.18)
    else:                                     # the real head top at the object's front (ext_scenes, physical)
        z = HEAD + rail_raise(spec)(np.array([x]))[0]
    cant = spec.get("cant", 0.0)          # left rail raised by cant (m), right rail at 0
    if side > 0:
        z += cant
    return float(z)


def rail_raise(spec):
    raise_ = spec.get("raise_", 0.18)
    return lambda x: np.where((np.asarray(x) >= 32) & (np.asarray(x) <= 70), raise_, 0.0)


def objects_at(spec, d, k):
    """list of ('box', (x0,x1,y0,y1,z0,z1,yaw)) / ('poly', planes); the first is the target. Returns objs, yc_target."""
    cr = spec.get("curve_r", 0.0)
    ycur = (lambda x: 0.0) if not cr else (lambda x: x * x / (2.0 * cr))
    objs, ytarget = [], None
    for i, o in enumerate(spec["objects"]):
        x0 = d + o.get("dx", 0.0)
        side = o.get("side", 1)
        lat = o.get("lat_off", 0.0) + o.get("lat_speed", 0.0) * k
        yr = rc2.AY + side * 0.8 + lat + ycur(x0)
        if o.get("centre"):
            yr = rc2.AY + lat + ycur(x0)
        L, W = o["length"], o["width"]
        top = head_at(spec, x0, side) + o["delta"]
        z0 = rc2.FLOOR if o.get("bottom", "bed") == "bed" else head_at(spec, x0, side)
        t = o.get("type", "box")
        if t == "box":
            objs.append(("box", (x0, x0 + L, yr - W / 2, yr + W / 2, z0, top, o.get("yaw", 0.0))))
        elif t == "wedge_away":       # front edge at full height, top slopes down away from the sensor
            objs.append(("poly", rc2.wedge_planes(x0, x0 + L, yr - W / 2, yr + W / 2, z0, top, top - o["drop"])))
        elif t == "wedge_toward":     # ramp: low at the front, full height at the back (no face toward the sensor)
            objs.append(("poly", rc2.wedge_planes(x0, x0 + L, yr - W / 2, yr + W / 2, z0, top - o["drop"], top)))
        elif t == "cyl_x":            # lying along the track
            r = 0.5 * W
            objs.append(("poly", rc2.cyl_planes("x", x0, x0 + L, yr, top - r, r)))
        elif t == "cyl_y":            # lying across the track (axis along y), length W across, diameter L
            r = 0.5 * L
            objs.append(("poly", rc2.cyl_planes("y", yr - W / 2, yr + W / 2, x0 + r, top - r, r)))
        else:
            raise ValueError(t)
        if i == 0:
            ytarget = yr
    return objs, ytarget


def build_frame(spec, d, k, d_rays):
    objs, yt = objects_at(spec, d, k)
    cant = spec.get("cant", 0.0)
    fr = rc2.frame(d=d_rays, rail_raise=rail_raise(spec),
                   rail_top_l=(lambda x: 0.0 * x + cant) if cant else None,
                   curve_r=spec.get("curve_r", 0.0),
                   boxes=[o[1] for o in objs if o[0] == "box"], polys=[o[1] for o in objs if o[0] == "poly"],
                   seed=1000 * k + 7 + spec.get("seed_off", 0), stamp=0.1 * k)
    return fr, yt


def ray_set(spec):
    if spec.get("rays") == "falcon":
        return rc2.falcon_rays()
    off = spec.get("az_off")
    if off is None:
        return rc2.rays()
    rng = np.random.default_rng(int(off.get("seed", 0)))
    n = len(rc2.RING_ELEVATION_DEG)
    if off["mode"] == "uniform":         # sub-step phase per ring, uniform in [-a, a] deg
        o = rng.uniform(-off["a"], off["a"], n)
    elif off["mode"] == "measured":      # per-ring phase measured on doubleT_obstacle (az_phase_measured.json)
        tab = json.load(open(Path(__file__).resolve().parent / "az_phase_measured.json"))
        o = np.array([tab[str(k)]["phase_deg"] if str(k) in tab else 0.0 for k in range(n)])
    elif off["mode"] == "alternate":     # adjacent rings half a step apart
        o = np.where(np.arange(n) % 2 == 0, 0.0, off["a"])
    else:
        raise ValueError(off)
    return rc2.rays(az_offsets_deg=o)


def run_scene(spec):
    t0 = time.time()
    cfg = DetectorConfig()
    if spec.get("cfg_profile"):
        from resense.config import load_config  # noqa
        cfg = load_config(spec["cfg_profile"])
    if spec.get("switch_off"):           # attribution control: the candidate with lowobj.rail_head_bounded off
        cfg.lowobj.rail_head_bounded = False
    det = Detector(cfg)
    d_rays = ray_set(spec)
    nframes, start, step = spec.get("nframes", 45), spec.get("start", 58.0), spec.get("step", 0.8)
    tgt = spec["objects"][0]
    log = []
    if spec.get("trace"):
        import resense.detector as detm
        from resense import lowobj
        ctrl = _ctrl_module()
        orig = detm.rail_reference_check
        cur = {}

        def check(clusters, X, dy, h, lcfg, sp, free=None):
            out = orig(clusters, X, dy, h, lcfg, sp, free)
            cout = ctrl.rail_reference_check(clusters, X, dy, h, lcfg, sp, free)
            ids_o, ids_c = {id(c) for c in out}, {id(c) for c in cout}
            new = [c for c in out if id(c) not in ids_c]
            only_ctrl = [c for c in cout if id(c) not in ids_o]
            rows = []
            Xr, dyr, hr = (X, dy, h) if free is None else (X[free], dy[free], h[free])
            for c in new:
                d_ = dy[c.points_idx]
                foot = ((X >= c.bbox_min[0]) & (X <= c.bbox_max[0]) & (dy >= d_.min()) & (dy <= d_.max())
                        & (h < lcfg.foot_max_top))
                top = max(float(c.height_max), float(h[foot].max()) if foot.any() else -9)
                orig_line = ctrl.local_rail_reference(c, X, dy, h, lcfg, sp)
                free_line = ctrl.local_rail_reference(c, Xr, dyr, hr, lcfg, sp)
                H = lowobj.rail_head_top(c, Xr, dyr, hr, float(d_.min()), float(d_.max()), lcfg, sp) \
                    if hasattr(lowobj, "rail_head_top") else None
                m = lcfg.local_rail_margin
                dist_k = cur.get("d", 0.0)
                is_t = (dist_k - 1.0 <= float(c.distance) <= dist_k + tgt["length"] + 1.0
                        and abs(float(c.centroid[1]) - cur.get("yt", 0.0)) < 0.6)
                rows.append(dict(d=round(float(c.distance), 2), lat=round(float(c.lateral), 3),
                                 w=round(float(c.size[1]), 3), cap=round(float(c.height_max), 3), top=round(top, 3),
                                 H=None if H is None else round(H, 3),
                                 orig_line=None if orig_line is None else round(orig_line, 3),
                                 free_line=None if free_line is None else round(free_line, 3),
                                 pre0=orig_line is not None and float(c.height_max) < orig_line + m,
                                 pre1=free_line is not None and float(c.height_max) < free_line + m,
                                 target=bool(is_t), n=int(c.points_idx.size)))
            log.append(dict(frame=cur.get("k"), new=rows, only_ctrl=len(only_ctrl)))
            return out
        detm.rail_reference_check = check
    rows = []
    try:
        for k in range(nframes):
            d = start - step * k
            fr, yt = build_frame(spec, d, k, d_rays)
            if spec.get("trace"):
                cur.update(k=k, d=d, yt=yt)
            res = det.process(Frame(xyz=fr.xyz, intensity=fr.intensity, stamp=0.1 * k))
            dets = res.detections
            matched = [x for x in dets if x.zone == "gauge" and d - 1.0 <= x.distance <= d + tgt["length"] + 1.0
                       and abs(float(x.center[1]) - yt) < 0.6]
            rows.append(dict(frame=k, dist=round(d, 2), matched=bool(matched),
                             matched_kind=[x.kind for x in matched],
                             obstacle=bool(res.obstacle),
                             any_gauge=[(round(float(x.distance), 1), round(float(x.lateral), 2), x.kind)
                                        for x in dets if x.zone == "gauge"]))
    finally:
        if spec.get("trace"):
            detm.rail_reference_check = orig
    out = dict(spec=spec, matched_frames=sum(r["matched"] for r in rows), rows=rows, secs=round(time.time() - t0, 1))
    if spec.get("trace"):
        out["trace"] = log
    return out


def O(**kw):
    base = dict(type="box", side=1, length=0.3, width=0.3, delta=0.05, bottom="bed")
    base.update(kw)
    return base


def scenes(family):
    S = []
    if family == "apb":              # the review's approach_bed family re-created (positive-control harness check)
        for raise_, side, (L, W), delta in itertools.product((0.10, 0.18), (1, -1), ((0.3, 0.3), (1.0, 0.3), (4.0, 0.3), (4.0, 0.1)),
                                                              (0.05, 0.10, 0.20)):
            S.append(dict(raise_=raise_, head_mode="const", objects=[O(side=side, length=L, width=W, delta=delta)]))
    elif family == "apb_meas":       # the same 48 scenes with the real sensor's per-ring azimuth phases
        S = [dict(x, az_off=dict(mode="measured")) for x in scenes("apb")]
    elif family == "ext_meas":       # the author's ext_sizes rail scenes (top = real head + delta), real ring phases
        for raise_, side, width, delta in itertools.product((0.0, 0.10, 0.18), (1, -1), (0.07, 0.3),
                                                            (0.03, 0.05, 0.10, 0.15)):
            S.append(dict(raise_=raise_, az_off=dict(mode="measured"), objects=[O(side=side, width=width, delta=delta)]))
    elif family in ("seeds", "seeds_off"):   # the losing configurations, 5 noise seeds each (+ switch off)
        base = [dict(raise_=0.18, head_mode="const", az_off=dict(mode="measured"), objects=[O(side=-1, length=0.3)]),
                dict(raise_=0.18, az_off=dict(mode="measured"), objects=[O(side=-1, delta=0.03)]),
                dict(raise_=0.18, objects=[O(side=-1, type="wedge_toward", drop=0.15, length=1.0, delta=0.10)]),
                dict(raise_=0.18, objects=[O(side=-1, type="cyl_y", length=0.3, width=0.4, delta=0.05)]),
                dict(raise_=0.18, cant=0.10, objects=[O(side=1, delta=0.10)]),
                dict(raise_=0.18, az_off=dict(mode="uniform", a=0.05, seed=1), objects=[O(side=-1, length=4.0, delta=0.10)])]
        for b in base:
            for so in (0, 101, 202, 303, 404):
                S.append(dict(b, seed_off=so, switch_off=(family == "seeds_off")))
    elif family == "smoke":            # equals the review's approach_bed scene (raise 0.18, left, 0.3x0.3, delta 0.05)
        S.append(dict(raise_=0.18, objects=[O()]))
    elif family == "fine_delta":     # objects just above the head (the H + 0.03 tolerance), both rails
        for raise_, side, (L, W), delta in itertools.product((0.0, 0.10, 0.18), (1, -1), ((0.3, 0.3), (1.0, 0.3), (0.3, 0.1)),
                                                               (0.0, 0.01, 0.02, 0.03, 0.04, 0.06)):
            S.append(dict(raise_=raise_, objects=[O(side=side, length=L, width=W, delta=delta)]))
    elif family == "azoff":          # per-ring azimuth phase (real sensors are not on one azimuth grid)
        for mode, raise_, side, (L, W), delta in itertools.product(
                (dict(mode="measured"), dict(mode="uniform", a=0.05, seed=1)), (0.10, 0.18), (1, -1),
                ((0.3, 0.3), (1.0, 0.3), (4.0, 0.3), (4.0, 0.1)), (0.05, 0.10)):
            S.append(dict(raise_=raise_, az_off=mode, objects=[O(side=side, length=L, width=W, delta=delta)]))
    elif family == "shapes":         # no face toward the sensor / yawed / round
        for raise_, side, delta, shp in itertools.product((0.10, 0.18), (1, -1), (0.05, 0.10), (
                dict(type="box", yaw=20.0), dict(type="box", yaw=45.0),
                dict(type="wedge_toward", drop=0.15, length=0.3), dict(type="wedge_toward", drop=0.15, length=1.0),
                dict(type="wedge_away", drop=0.15, length=0.3),
                dict(type="cyl_x", length=1.0, width=0.3), dict(type="cyl_y", length=0.3, width=0.4))):
            S.append(dict(raise_=raise_, objects=[O(side=side, delta=delta, **shp)]))
    elif family == "two":            # a second object on the other rail / both rails / own rail at the region edges
        for raise_, delta, conf in itertools.product((0.10, 0.18), (0.05, 0.10), (
                "other_same", "other_same_tall", "pipes_both", "own_before_4.9", "own_after_4.9", "four_corners")):
            t = O(side=1, delta=delta)
            objs = [t]
            if conf == "other_same":
                objs.append(O(side=-1, delta=delta))
            elif conf == "other_same_tall":
                objs.append(O(side=-1, delta=0.6))
            elif conf == "pipes_both":   # target box + a 10 cm pipe 8 m long lying on each rail head, from 3 m before
                objs += [O(type="cyl_x", side=s, length=8.0, width=0.10, delta=delta + 0.0, bottom="rest", dx=-3.0)
                         for s in (1, -1)]
            elif conf == "own_before_4.9":
                objs.append(O(side=1, delta=delta, dx=-4.9, length=0.3))
            elif conf == "own_after_4.9":
                objs.append(O(side=1, delta=delta, dx=4.9, length=0.3))
            elif conf == "four_corners":  # small objects at the same height in all four regions
                objs += [O(side=1, delta=delta, dx=-3.0), O(side=1, delta=delta, dx=3.0),
                         O(side=-1, delta=delta, dx=-2.0), O(side=-1, delta=delta, dx=2.0)]
            S.append(dict(raise_=raise_, objects=objs, conf=conf))
    elif family == "cant":           # superelevation: left rail raised by cant (the model plane learns it)
        for cant, raise_, side, delta in itertools.product((0.05, 0.10, 0.15), (0.0, 0.10, 0.18), (1, -1), (0.05, 0.10)):
            S.append(dict(raise_=raise_, cant=cant, objects=[O(side=side, delta=delta)]))
    elif family == "curve":
        for cr, raise_, side, delta in itertools.product((800.0, -800.0, 2000.0, -2000.0), (0.10, 0.18), (1, -1), (0.05, 0.10)):
            S.append(dict(raise_=raise_, curve_r=cr, objects=[O(side=side, delta=delta)]))
    elif family == "moving":         # lateral motion onto the rail, receding, fast approach
        for raise_, delta, mv in itertools.product((0.10, 0.18), (0.05, 0.10), (
                dict(lat_off=-0.4, lat_speed=0.01), dict(lat_off=0.3, lat_speed=-0.008),
                dict(step=1.6, nframes=23), dict(step=-0.5, start=25.0, nframes=45))):
            o = O(side=1, delta=delta, lat_off=mv.get("lat_off", 0.0), lat_speed=mv.get("lat_speed", 0.0))
            sc = dict(raise_=raise_, objects=[o])
            for k in ("step", "nframes", "start"):
                if k in mv:
                    sc[k] = mv[k]
            S.append(sc)
    elif family == "falcon":         # Falcon-like raster, default Hesai config (geometry stress only)
        for raise_, side, delta in itertools.product((0.10, 0.18), (1, -1), (0.05, 0.10)):
            S.append(dict(raise_=raise_, rays="falcon", objects=[O(side=side, delta=delta)]))
    elif family == "empty":          # false-alarm control (target spec only defines the match window)
        for raise_, cant in itertools.product((0.0, 0.10, 0.18), (0.0, 0.10)):
            S.append(dict(raise_=raise_, cant=cant, objects=[O(delta=-1.0)], empty=True))
    else:
        raise SystemExit("unknown family " + family)
    for s in S:
        if s.get("empty"):
            s["objects"][0]["delta"] = -1.0   # below the bed: no object is drawn above the floor
    return S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--trace", action="store_true")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    import resense
    assert Path(resense.__file__).resolve().is_relative_to(Path(ROOT).resolve()), resense.__file__
    specs = scenes(a.family)
    for s in specs:
        s["trace"] = a.trace
    print(ROOT, resense.__file__, a.family, len(specs), "scenes", flush=True)
    with Pool(a.jobs) as pool:
        res = []
        for i, r in enumerate(pool.imap(run_scene, specs)):
            res.append(r)
            print(f"{i + 1}/{len(specs)} matched {r['matched_frames']}/{len(r['rows'])} ({r['secs']}s)", flush=True)
    Path(a.out).write_text(json.dumps(dict(repo=ROOT, family=a.family, results=res)) + "\n")


if __name__ == "__main__":
    main()
