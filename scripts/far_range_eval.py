#!/usr/bin/env python3
"""Long-range evaluation on a *moving* real background (set F, v0.6).

Earlier synthetic sequences (``resense inject --sequence``) moved the object towards a frozen
background frame: the tunnel did not move, so neither the track model nor the tracker saw a
real approach. Here an object is placed at a fixed point of the tunnel ahead of a run of
**consecutive frames of the organizers' 20-minute ride** (``new_data``) and ray-cast into every
frame at the distance it has at that moment: ``d_k = d_0 - sum(v_i * dt_i)``, with the frame
interval from the bag stamps and the train speed of the ride (``--speeds``, the per-file speed
measured from static tracks in ``docs/extended_dataset_intake.json``). Background, motion,
far-field sparsity and sightline are real; only the object is synthetic.

Placement: laterally uniform inside the envelope (``--lateral``), standing on the bed measured
under it where the bed returns (``resense.synthetic.local_bed_z``, up to ~80 m); beyond, on the
model's rail level minus the bed depth, **corrected by the drift of the vault** measured in the
same frame (the extrapolated rail level of the model runs 0.2-0.5 m low at 100-200 m on the
straight sections, EXPERIMENTS.md §2d) - so a far object stands where the real bed is, not where
the detector's model thinks it is.

With ``--given-speed`` the train speed is handed to the detector, which then merges frames
beyond ``accumulation.min_range`` (the multi-frame path; off without a speed).

For each sequence a fresh detector runs over the frames; a frame counts as a hit when a
confirmed gauge detection lies within ``max(2 m, 3 %)`` of the object's distance and 1.2 m
laterally. Reported: first confirmed detection distance per object, recall per range bin over
the frames in which the object returned >= 1 point, false confirmed gauge detections.

    python scripts/far_range_eval.py --cache /data/cache/new_data --files 46,47,48 --kinds person,box1.0 \\
        --start 220 --out out/far/person.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

BINS = [(0, 50), (50, 100), (100, 150), (150, 200), (200, 250)]


def vault_drift(xyz, track, x0=40.0, x1=230.0, step=10.0):
    """Robust line dz(X) of the vault (tunnel crown) above the model's rail level, relative to its
    height at 20-60 m: how far the model's extrapolated rail level drifts from the tunnel."""
    from resense.gauge import corridor_coordinates
    dy, h = corridor_coordinates(xyz, track)
    X = xyz[:, 0]
    top = (np.abs(dy) < 1.5) & (h > 2.0) & (h < 8.0)
    near = top & (X > 20) & (X < 60)
    if near.sum() < 20:
        return lambda x: np.zeros_like(np.asarray(x, dtype=float))
    ref = float(np.median(h[near]))
    xs, zs = [], []
    for a in np.arange(x0, x1, step):
        m = top & (X >= a) & (X < a + step)
        r = h[m] - ref
        r = r[np.abs(r) < 1.2]
        if r.size >= 3:
            xs.append(a + step / 2)
            zs.append(float(np.median(r)))
    if len(xs) < 3:
        return lambda x: np.zeros_like(np.asarray(x, dtype=float))
    xs, zs = np.array(xs), np.array(zs)
    # line through the origin region: dz = k * max(X - 40, 0), k from the bins (median of slopes)
    k = float(np.median(zs / np.maximum(xs - 40.0, 1.0)))
    return lambda x: k * np.maximum(np.asarray(x, dtype=float) - 40.0, 0.0)


def run_sequence(job):
    (files, stamps, speeds, kind, d0, lateral, refl, seed, cfg_dict, far_min_height, given_speed) = job
    sys.path.insert(0, os.getcwd())
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    from resense.synthetic import catalogue_spec, inject_obstacles, local_bed_z
    from resense.track import estimate_track
    from dataclasses import replace
    cfg = DetectorConfig.from_dict(cfg_dict)
    if far_min_height is not None:
        cfg.cluster.far_min_height = far_min_height
    det = Detector(cfg)
    rng = np.random.default_rng(seed)
    d = d0
    prev_t = None
    rows = []
    fp = 0
    first = None
    for f, spd in zip(files, speeds):
        stem = os.path.splitext(os.path.basename(f))[0]
        t = stamps.get(stem)
        if prev_t is not None and t is not None:
            dt = t - prev_t
            d -= spd * (dt if 0 < dt < 10 else 0.1)
        prev_t = t
        if d < 8.0:
            break
        fr = frame_from_compact(np.load(f), cfg.sensor, stamp=t or 0.0, frame_id=stem)
        # placement from the frame's own (unsmoothed) track model and the vault drift
        tm = estimate_track(fr.xyz, cfg.track, prev=det.track)
        spec = catalogue_spec(kind, d, lateral, reflectivity=refl)
        x = d + spec.size[0] / 2
        if spec.base is None:
            zb = local_bed_z(fr.xyz, tm, x, lateral)
            if zb is None:
                zb = float(tm.rail_z(x)) - 0.25 + float(vault_drift(fr.xyz, tm)(x))
            spec = replace(spec, base_z=zb)
        inj = inject_obstacles(fr, tm, [spec], rng=rng, dropout_start=60.0, dropout_full=200.0)
        n_pts = int(inj.n_added[0])
        res = det.process(inj.frame, ego_speed=spd if given_speed else None)
        tol = max(2.0, 0.03 * d)
        hit = False
        fps = []
        for det_ in res.detections:
            if abs(det_.distance - d) <= tol and abs(det_.lateral - lateral) <= 1.2:
                hit = True
            else:
                fp += 1
                fps.append([round(det_.distance, 1), round(det_.lateral, 2), [round(float(v), 2) for v in det_.size], det_.kind])
        if hit and first is None:
            first = d
        rows.append({"frame": stem, "d": round(d, 1), "n": n_pts, "hit": hit, "fp_dets": fps,
                     "cand": any(abs(c.distance - d) <= tol for c in res.candidates),
                     "mon": res.health.get("monitored_range"), "vis": res.health.get("visibility")})
    return {"kind": kind, "d0": d0, "lateral": lateral, "refl": refl, "first": first, "fp": fp, "rows": rows,
            "file0": os.path.basename(files[0])}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default="/data/cache/new_data")
    ap.add_argument("--files", required=True, help="comma-separated split-file numbers; each starts a sequence")
    ap.add_argument("--kinds", default="person")
    ap.add_argument("--start", type=float, default=220.0, help="object distance at the first frame (m)")
    ap.add_argument("--frames", type=int, default=110, help="max frames per sequence")
    ap.add_argument("--lateral", default="-0.6:0.6")
    ap.add_argument("--speeds", default="docs/extended_dataset_intake.json")
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--far-min-height", type=float, default=None, help="override cluster.far_min_height")
    ap.add_argument("--given-speed", action="store_true",
                    help="hand the ride's train speed to the detector (enables multi-frame accumulation)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import yaml
    from resense.config import DetectorConfig
    from resense.io import _natural_key, load_cache_stamps
    from resense.synthetic import OBJECT_CATALOGUE
    raw = yaml.safe_load(open(a.config, encoding="utf-8")) or {}
    cfg_dict = raw.get("resense", raw)          # read once: every sequence runs the same parameters
    DetectorConfig.from_dict(cfg_dict)
    intake = json.load(open(a.speeds))
    spd_file = {f["n"]: (f.get("speed_tracks") or 0.0) for f in intake["files"]}
    stamps = load_cache_stamps(a.cache)
    allf = sorted(glob.glob(os.path.join(a.cache, "*.npy")), key=_natural_key)
    lo, hi = (float(v) for v in a.lateral.split(":"))
    rng = np.random.default_rng(a.seed)
    jobs = []
    for fn in [int(v) for v in a.files.split(",") if v]:
        start = next(i for i, f in enumerate(allf) if os.path.basename(f).startswith(f"new_data_{fn}_"))
        files = allf[start:start + a.frames]
        speeds = [spd_file.get(int(os.path.basename(f).split("_")[2]), 0.0) for f in files]
        for kind in a.kinds.split(","):
            refl = float(rng.uniform(*OBJECT_CATALOGUE[kind].reflectivity))
            jobs.append((files, stamps, speeds, kind, a.start, float(rng.uniform(lo, hi)), refl,
                         int(rng.integers(1 << 30)), cfg_dict, a.far_min_height, a.given_speed))
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        out = list(ex.map(run_sequence, jobs))
    # summary
    summ = {"per_kind": {}, "jobs": len(jobs), "wall_s": round(time.time() - t0, 1)}
    for kind in a.kinds.split(","):
        seqs = [o for o in out if o["kind"] == kind]
        firsts = [o["first"] for o in seqs if o["first"] is not None]
        bins = {}
        for lo_b, hi_b in BINS:
            vis = [r for o in seqs for r in o["rows"] if lo_b <= r["d"] < hi_b and r["n"] > 0]
            bins[f"{lo_b}-{hi_b}"] = [sum(r["hit"] for r in vis), len(vis)]
        summ["per_kind"][kind] = {"sequences": len(seqs), "detected": len(firsts),
                                  "first_detection_m": sorted(round(v, 1) for v in firsts),
                                  "first_detection_median": round(float(np.median(firsts)), 1) if firsts else None,
                                  "recall_by_bin": bins, "false_detections": sum(o["fp"] for o in seqs)}
    json.dump({"summary": summ, "sequences": out}, open(a.out, "w"), indent=1)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
