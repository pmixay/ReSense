#!/usr/bin/env python3
"""Extended ray-cast acceptance scenes for the F1a bounded head top (pre-registered, PROTOCOL.md A3).

The repo's analytic first-return caster (``docs/evidence/f1a_b1_2026-10-20/raycast.py``: lining, bed, benches, two
rails with a flat 0.07 m head and vertical faces, opaque boxes, Pandar128 rays, range noise 1 cm * (1 + r/100)),
one fresh Detector with the checkout's default config per scene, a relative approach 58 -> 22 m at 0.8 m per frame
(45 frames, a fresh noise seed per frame), exactly as the review's ``approach`` families. ``matched`` = a gauge
detection whose distance is within [d - 1, d + L + 1] and whose centre is within 0.6 m laterally of the box centre
(the review's definition). The rail is raised by ``raise`` beyond 32 m (the model, learned nearer, is then low).

Families:
  sizes : boxes from the bed up (enclosing the rail), width 0.05 / 0.07 / 0.3 / 0.6 m, top = real head + delta
          (0.05 / 0.10 / 0.15 / 0.20), on either rail; plus a 0.3 m box between the rails
  slope : the rail head rises / falls by +-0.5 / +-1 / +-2 cm/m over a ramp of at most 0.16 m from 36 m on;
          box 0.3 m wide, 0.3 or 4 m long, top = head(x) + delta (0.05 / 0.10)
  rise  : a 1 m local rise (+0.05 / +0.10) of the rail head 1-2 m before or 1-2 m after the box (moves with it)
  rest  : boxes resting on the head (bottom = head top), width 0.07 / 0.3, delta 0.05 / 0.10 / 0.20

    RESENSE_REPO=<checkout> python ext_scenes.py --family sizes --out out.json [--jobs 4] [--trace]
"""
import argparse
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
sys.path.insert(0, str(Path(ROOT) / "docs/evidence/f1a_b1_2026-10-20"))

import raycast as rc  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import Frame  # noqa: E402

NFRAMES, START, STEP = 45, 58.0, 0.8


def rail_raise_fn(spec, d):
    raise_, slope = spec["raise_"], spec.get("slope", 0.0)
    bump, where, length = spec.get("bump", 0.0), spec.get("where", ""), spec["length"]
    ramp = min(16.0, 0.16 / abs(slope)) if slope else 0.0

    def f(x):
        x = np.asarray(x, float)
        r = np.where((x >= 32) & (x <= 70), raise_, 0.0)
        if slope:
            r = r + slope * np.clip(x - 36.0, 0.0, ramp)
        if bump:
            b0 = d - 2.0 if where == "before" else d + length + 1.0
            r = r + np.where((x >= b0) & (x <= b0 + 1.0), bump, 0.0)
        return r
    return f


def make_scene(spec, d):
    rr = rail_raise_fn(spec, d)
    kind, side, width, length, delta = spec["kind"], spec["side"], spec["width"], spec["length"], spec["delta"]
    yc = rc.AY + side * 0.8 if kind == "rail" else rc.AY
    head = rc.FLOOR + 0.18 + float(rr(np.array([d]))[0])     # the real head top at the box's front
    z1 = head + delta
    z0 = head if spec["bottom"] == "rest" else rc.FLOOR
    return rr, [(d, d + length, yc - width / 2, yc + width / 2, z0, z1)], yc, head


def run_scene(spec):
    t0 = time.time()
    det = Detector(DetectorConfig())
    log = []
    if spec.get("trace"):
        import resense.detector as detm
        orig = detm.rail_reference_check

        def check(clusters, X, dy, h, cfg, sp, free=None):
            out = orig(clusters, X, dy, h, cfg, sp, free)
            log.append([dict(d=round(float(c.distance), 2), lat=round(float(c.lateral), 3),
                             width=round(float(c.size[1]), 3), height_max=round(float(c.height_max), 3),
                             rejected=any(c is o for o in out))
                        for c in clusters if c.kind == "low" and c.zone == "gauge" and not c.reason])
            return out
        detm.rail_reference_check = check
    rows = []
    try:
        for k in range(NFRAMES):
            d = START - STEP * k
            rr, boxes, yc, head = make_scene(spec, d)
            fr = rc.frame(rail_raise=rr, boxes=boxes, seed=1000 * k + 7, stamp=0.1 * k)
            res = det.process(Frame(xyz=fr.xyz, intensity=fr.intensity, stamp=0.1 * k))
            matched = [x for x in res.detections if x.zone == "gauge" and d - 1.0 <= x.distance <= d + spec["length"] + 1.0
                       and abs(float(x.center[1]) - yc) < 0.6]
            rows.append(dict(frame=k, dist=round(d, 2), matched=bool(matched), matched_kind=[x.kind for x in matched],
                             any_gauge=[(round(float(x.distance), 1), round(float(x.lateral), 2), x.kind)
                                        for x in res.detections if x.zone == "gauge"],
                             rail_model_err=round(float(det.track.rail_z(d)) - head, 3)))
    finally:
        if spec.get("trace"):
            detm.rail_reference_check = orig
    out = dict(spec=spec, matched_frames=sum(r["matched"] for r in rows), rows=rows, secs=round(time.time() - t0, 1))
    if spec.get("trace"):
        out["trace"] = log
    return out


def scenes(family):
    base = dict(kind="rail", bottom="bed", length=0.3, slope=0.0, bump=0.0, where="")
    out = []
    if family == "sizes":
        for raise_, side, width, delta in itertools.product((0.0, 0.18), (1, -1), (0.05, 0.07, 0.3, 0.6),
                                                            (0.05, 0.10, 0.15, 0.20)):
            out.append(dict(base, raise_=raise_, side=side, width=width, delta=delta))
        for raise_, delta in itertools.product((0.0, 0.18), (0.05, 0.10, 0.15, 0.20)):
            out.append(dict(base, kind="centre", raise_=raise_, side=1, width=0.3, delta=delta))
    elif family == "slope":
        for slope, raise_, delta, length in itertools.product((-0.02, -0.01, -0.005, 0.005, 0.01, 0.02), (0.0, 0.10),
                                                              (0.05, 0.10), (0.3, 4.0)):
            out.append(dict(base, raise_=raise_, side=1, width=0.3, delta=delta, length=length, slope=slope))
    elif family == "rise":
        for bump, where, raise_, delta in itertools.product((0.05, 0.10), ("before", "after"), (0.0, 0.10), (0.05, 0.10)):
            out.append(dict(base, raise_=raise_, side=-1, width=0.3, delta=delta, length=1.0, bump=bump, where=where))
    elif family == "rest":
        for raise_, width, delta in itertools.product((0.0, 0.18), (0.07, 0.3), (0.05, 0.10, 0.20)):
            out.append(dict(base, raise_=raise_, side=1, width=width, delta=delta, bottom="rest"))
    else:
        raise SystemExit("unknown family")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--trace", action="store_true")
    a = ap.parse_args()
    specs = scenes(a.family)
    for s in specs:
        s["trace"] = a.trace
    import resense
    print(ROOT, resense.__file__, a.family, len(specs), "scenes", flush=True)
    assert Path(resense.__file__).resolve().is_relative_to(Path(ROOT).resolve()), "resense not from RESENSE_REPO"
    with Pool(a.jobs) as pool:
        res = []
        for i, r in enumerate(pool.imap(run_scene, specs)):
            res.append(r)
            print(f"{i + 1}/{len(specs)} {r['spec']}: matched {r['matched_frames']}/{NFRAMES} ({r['secs']}s)", flush=True)
    Path(a.out).write_text(json.dumps(dict(repo=ROOT, family=a.family, results=res)) + "\n")


if __name__ == "__main__":
    main()
