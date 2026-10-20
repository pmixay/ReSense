#!/usr/bin/env python3
"""Reviewer script (own): positive/adversarial controls for "the F1a completion loses no real detection".

Full detector on analytic first-return scenes (the repo's ray caster ``docs/evidence/f1a_b1_2026-10-20/raycast.py``:
tunnel lining, bed, benches, two rails with flat head and vertical faces, opaque boxes, Pandar128 ray pattern, range
noise sigma = 1 cm * (1 + r/100)), one fresh Detector per scene, 12 stationary frames with a fresh noise seed each.

Scene family (``--family``):

* rail   : a box ON a rail line (narrow low cluster reaching the rail line = the geometry the new rule can reject);
           top = (real rail-head top) + delta, delta in DELTAS; length L in LENGTHS; width W in WIDTHS; side = +1/-1;
           bottom mode 'bed' (box from the bed up, it encloses the rail) or 'rest' (box starts at the head top).
* beside : the same box beside the rail (inner edge >= 0.25 m from the rail line, i.e. not rail-line eligible).
* centre : box at the track centre (the author's own physical scenes).
* empty  : no box (false-alarm control).

The rail is raised by ``raise`` between 32 and 70 m (the track model, learned in 4..30 m, then sits ``raise`` below
the real head: the situation F1a completion claims to handle).  'matched' = a gauge-zone detection whose nearest
point is within [dist-1, dist+L+1] m and whose centre is within 0.6 m laterally of the box centre.

Read-only branch tracing (``--trace``): ``resense.detector.rail_reference_check`` and ``lowobj._rail_surface_reference``
are wrapped to log, per frame, every checked cluster and whether the surface branch was reached/returned a value; a
traced run must equal the plain run (checked by the caller: compare the 'matched' fields of both JSONs).

    RESENSE_REPO=<checkout> python synth_controls.py --family rail --out out.json [--trace] [--jobs 4]
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

NFRAMES = 12
DELTAS = [-0.02, 0.0, 0.02, 0.04, 0.05, 0.06, 0.08, 0.10, 0.20]


def make_scene(raise_, dist, kind, side, length, width, delta, bottom, lateral_off=0.0):
    head = rc.FLOOR + 0.18 + raise_
    rr = lambda x: np.where((x >= 32) & (x <= 70), raise_, 0.0)  # noqa: E731
    boxes = []
    yc = None
    if kind in ("rail", "beside", "centre"):
        if kind == "rail":
            yc = rc.AY + side * 0.8 + lateral_off
        elif kind == "beside":
            # inner edge 0.25 m beyond the rail line on the outside: not within rail_start_lateral (0.10)
            yc = rc.AY + side * (0.8 + 0.25 + width / 2)
        else:
            yc = rc.AY
        z1 = head + delta
        z0 = rc.FLOOR if (bottom == "bed" or delta <= 0.0) else head
        boxes = [(dist, dist + length, yc - width / 2, yc + width / 2, z0, z1)]
    return rr, boxes, yc, head


def run_scene(spec):
    """spec: dict(raise_, dist, kind, side, length, width, delta, bottom, trace). Returns a result dict."""
    t0 = time.time()
    raise_, dist, kind, side = spec["raise_"], spec["dist"], spec["kind"], spec["side"]
    length, width, delta, bottom = spec["length"], spec["width"], spec["delta"], spec["bottom"]
    rr, boxes, yc, head = make_scene(raise_, dist, kind, side, length, width, delta, bottom, spec.get("lat_off", 0.0))
    nframes = int(spec.get("nframes", NFRAMES))
    step = float(spec.get("approach_step", 0.0))   # m per frame the object comes closer (relative motion)
    det = Detector(DetectorConfig())
    if spec.get("neutralize"):
        from resense import lowobj as _lo
        _lo._rail_surface_reference = lambda *a, **k: None
    log = []
    if spec.get("trace"):
        import resense.detector as detm
        from resense import lowobj
        orig_check, orig_surf = detm.rail_reference_check, getattr(lowobj, "_rail_surface_reference", None)
        cur = {}

        def surf(c, X, dy, h, d0, d1, cfg, sp):
            r = orig_surf(c, X, dy, h, d0, d1, cfg, sp)
            cur.setdefault("surf", []).append(None if r is None else round(float(r), 4))
            return r

        def check(clusters, X, dy, h, cfg, sp, free=None):
            cur.clear()
            out = orig_check(clusters, X, dy, h, cfg, sp, free)
            rows = []
            for c in clusters:
                if c.kind == "low" and c.zone == "gauge" and not c.reason:
                    rows.append(dict(d=round(float(c.distance), 2), lat=round(float(c.lateral), 3),
                                     width=round(float(c.size[1]), 3), height_max=round(float(c.height_max), 3),
                                     rejected=any(c is o for o in out)))
            log.append(dict(clusters=rows, surface_calls=list(cur.get("surf", []))))
            return out
        if orig_surf is not None:
            lowobj._rail_surface_reference = surf
        detm.rail_reference_check = check
    rows = []
    try:
        for k in range(nframes):
            d_k = dist - step * k
            if step:
                rr, boxes, yc, head = make_scene(raise_, d_k, kind, side, length, width, delta, bottom,
                                                 spec.get("lat_off", 0.0))
            fr = rc.frame(rail_raise=rr, boxes=boxes, seed=1000 * k + 7, stamp=0.1 * k)
            res = det.process(Frame(xyz=fr.xyz, intensity=fr.intensity, stamp=0.1 * k))
            dets = res.detections
            if yc is None:
                matched = []
            else:
                matched = [d for d in dets if d.zone == "gauge" and d_k - 1.0 <= d.distance <= d_k + length + 1.0
                           and abs(float(d.center[1]) - yc) < 0.6]
            rows.append(dict(frame=k, dist=round(d_k, 2), matched=bool(matched),
                             matched_kind=[d.kind for d in matched],
                             any_gauge=[(round(float(d.distance), 1), round(float(d.lateral), 2), d.kind)
                                        for d in dets if d.zone == "gauge"],
                             rail_model_err=round(float(det.track.rail_z(dist)) - head, 3)))
    finally:
        if spec.get("trace"):
            detm.rail_reference_check = orig_check
            if orig_surf is not None:
                lowobj._rail_surface_reference = orig_surf
    out = dict(spec=spec, matched_frames=sum(r["matched"] for r in rows), rows=rows, secs=round(time.time() - t0, 1))
    if spec.get("trace"):
        out["trace"] = log
    return out


def scenes(family, trace):
    specs = []
    base = dict(trace=trace)
    if family == "rail":
        for raise_, dist, side, (length, width), delta, bottom in itertools.product(
                (0.0, 0.18), (40.0,), (1,), ((0.3, 0.3), (0.3, 0.1), (4.0, 0.1), (4.0, 0.3)), DELTAS, ("bed", "rest")):
            if bottom == "rest" and delta <= 0.0:
                continue
            specs.append(dict(base, raise_=raise_, dist=dist, kind="rail", side=side, length=length, width=width,
                              delta=delta, bottom=bottom))
    elif family == "rail_ranges":
        # the organizers' 30x30x10 box (top = head + 0.10) on a rail at several ranges, both rails, plus +0.06
        for raise_, dist, side, delta in itertools.product((0.0, 0.18), (20.0, 30.0, 40.0, 50.0, 55.0), (1, -1),
                                                            (0.06, 0.10)):
            specs.append(dict(base, raise_=raise_, dist=dist, kind="rail", side=side, length=0.3, width=0.3,
                              delta=delta, bottom="rest"))
    elif family == "approach":
        # relative approach 58 m -> 22 m, 0.8 m per frame (45 frames), a fresh noise seed each frame
        for raise_, side, (length, width), delta, bottom in itertools.product(
                (0.0, 0.18), (1, -1), ((0.3, 0.3), (1.0, 0.3), (4.0, 0.3), (4.0, 0.1)), (0.0, 0.05, 0.10), ("rest",)):
            if delta <= 0.0:
                bottom = "bed"
            specs.append(dict(base, raise_=raise_, dist=58.0, kind="rail", side=side, length=length, width=width,
                              delta=delta, bottom=bottom, nframes=45, approach_step=0.8))
    elif family == "approach_bed":
        # objects that stand on the bed against the rail (box from the bed up, top = head + delta) in the ride-like
        # regime (model plane below the heads): these produce low clusters on the rail line
        for raise_, side, (length, width), delta in itertools.product(
                (0.10, 0.18), (1, -1), ((0.3, 0.3), (1.0, 0.3), (4.0, 0.3), (4.0, 0.1)), (0.05, 0.10, 0.20)):
            specs.append(dict(base, raise_=raise_, dist=58.0, kind="rail", side=side, length=length, width=width,
                              delta=delta, bottom="bed", nframes=45, approach_step=0.8))
    elif family == "approach_empty":
        for raise_ in (0.0, 0.10, 0.18):
            specs.append(dict(base, raise_=raise_, dist=58.0, kind="empty", side=1, length=0.3, width=0.3,
                              delta=0.0, bottom="bed", nframes=45, approach_step=0.8))
    elif family == "beside":
        for raise_, dist, side, delta in itertools.product((0.0, 0.18), (40.0,), (1, -1), (0.0, 0.05, 0.10, 0.20)):
            specs.append(dict(base, raise_=raise_, dist=dist, kind="beside", side=side, length=4.0, width=0.1,
                              delta=delta, bottom="bed"))
    elif family == "centre":
        for raise_, dist, delta in itertools.product((0.0, 0.18), (40.0,), (0.0, 0.05, 0.10, 0.20)):
            specs.append(dict(base, raise_=raise_, dist=dist, kind="centre", side=1, length=0.3, width=0.3,
                              delta=delta, bottom="bed"))
    elif family == "empty":
        for raise_, dist in itertools.product((0.0, 0.10, 0.18), (40.0,)):
            specs.append(dict(base, raise_=raise_, dist=dist, kind="empty", side=1, length=0.3, width=0.3,
                              delta=0.0, bottom="bed"))
    else:
        raise SystemExit("unknown family")
    return specs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--trace", action="store_true")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--neutralize", action="store_true",
                    help="evaluation-side monkeypatch: lowobj._rail_surface_reference always returns None "
                         "(= the new branch can never reject); no repository file is changed")
    a = ap.parse_args()
    specs = scenes(a.family, a.trace)
    if a.neutralize:
        for sp in specs:
            sp["neutralize"] = True
    print(ROOT, a.family, len(specs), "scenes", flush=True)
    with Pool(a.jobs) as pool:
        res = []
        for i, r in enumerate(pool.imap(run_scene, specs)):
            res.append(r)
            s = r["spec"]
            print(f"{i + 1}/{len(specs)} {s['kind']} raise{s['raise_']} d{s['dist']} side{s['side']} L{s['length']} "
                  f"W{s['width']} delta{s['delta']} {s['bottom']}: matched {r['matched_frames']}/{len(r['rows'])} ({r['secs']}s)",
                  flush=True)
    Path(a.out).write_text(json.dumps(dict(repo=ROOT, family=a.family, results=res)) + "\n")


if __name__ == "__main__":
    main()
