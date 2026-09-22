#!/usr/bin/env python3
"""Cluster-level dataset for the learned second opinion (experiment, v0.6).

Every single-frame candidate cluster that the geometric pipeline places inside the envelope
(``zone == 'gauge'``) becomes a row of descriptors. Negatives: all of them on obstacle-free
recordings (the 20-minute ride ``new_data`` and the five empty bags - every such cluster is
infrastructure or noise). Positives: clusters that match an object ray-cast into consecutive
frames of the moving ride (the set-F injection of ``scripts/far_range_eval.py``: person, crates,
trolley, cable, from 220 m).

    python scripts/ml_dataset.py --cache /data/cache --out out/ml/dataset.npz

Columns: see ``FEATURES``. ``group`` is the ride minute (negatives) or the sequence id
(positives) so that the classifier can be validated on parts of the ride it never saw.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

FEATURES = ["distance", "abs_lateral", "length", "width", "height", "n_vox", "n_raw", "vis_ratio",
            "height_min", "height_max", "intensity", "is_low", "demoted", "n_gauge_frac"]


def features(c) -> list:
    return [c.distance, abs(c.lateral), float(c.size[0]), float(c.size[1]), float(c.size[2]), c.n, c.n_raw,
            c.n / max(c.n_expected, 1.0), c.height_min, c.height_max, c.intensity, float(c.kind == "low"),
            float(bool(c.reason)), c.n_gauge / max(c.n, 1)]


def negatives(job):
    files, stamps, group = job
    sys.path.insert(0, os.getcwd())
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    cfg = DetectorConfig.from_yaml("configs/default.yaml")
    det = Detector(cfg)
    rows, groups = [], []
    for f in files:
        stem = os.path.splitext(os.path.basename(f))[0]
        fr = frame_from_compact(np.load(f), cfg.sensor, stamp=stamps.get(stem, 0.0))
        res = det.process(fr)
        for c in res.candidates:
            if c.zone == "gauge" or c.reason:
                rows.append(features(c))
                groups.append(group)
    return rows, groups


def positives(job):
    files, stamps, speeds, kind, d0, lateral, refl, seed, gid = job
    sys.path.insert(0, os.getcwd())
    sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
    from dataclasses import replace
    from far_range_eval import vault_drift
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    from resense.synthetic import catalogue_spec, inject_obstacles, local_bed_z
    from resense.track import estimate_track
    cfg = DetectorConfig.from_yaml("configs/default.yaml")
    det = Detector(cfg)
    rng = np.random.default_rng(seed)
    d, prev_t = d0, None
    pos, neg = [], []
    for f, spd in zip(files, speeds):
        stem = os.path.splitext(os.path.basename(f))[0]
        t = stamps.get(stem)
        if prev_t is not None and t is not None:
            dt = t - prev_t
            d -= spd * (dt if 0 < dt < 10 else 0.1)
        prev_t = t
        if d < 8.0:
            break
        fr = frame_from_compact(np.load(f), cfg.sensor, stamp=t or 0.0)
        tm = estimate_track(fr.xyz, cfg.track, prev=det.track)
        spec = catalogue_spec(kind, d, lateral, reflectivity=refl)
        x = d + spec.size[0] / 2
        if spec.base is None:
            zb = local_bed_z(fr.xyz, tm, x, lateral)
            spec = replace(spec, base_z=zb if zb is not None else float(tm.rail_z(x)) - 0.25 + float(vault_drift(fr.xyz, tm)(x)))
        inj = inject_obstacles(fr, tm, [spec], rng=rng, dropout_start=60.0, dropout_full=200.0)
        res = det.process(inj.frame)
        tol = max(2.0, 0.03 * d)
        for c in res.candidates:
            if not (c.zone == "gauge" or c.reason):
                continue
            (pos if abs(c.distance - d) <= tol and abs(c.lateral - lateral) <= 1.2 else neg).append(features(c) + [d])
    return pos, neg, gid, kind


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default="/data/cache")
    ap.add_argument("--out", required=True)
    ap.add_argument("--neg-every", type=int, default=2, help="use every N-th split file of new_data for negatives")
    ap.add_argument("--pos-files", default="30,46,68,98,120,140,150,168,172,190,200,210")
    ap.add_argument("--kinds", default="person,box1.0,box0.5,trolley,cable")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    from resense.io import _natural_key, load_cache_stamps
    from resense.synthetic import OBJECT_CATALOGUE
    nd = os.path.join(a.cache, "new_data")
    stamps = load_cache_stamps(nd)
    allf = sorted(glob.glob(os.path.join(nd, "*.npy")), key=_natural_key)
    by_file = {}
    for f in allf:
        by_file.setdefault(int(os.path.basename(f).split("_")[2]), []).append(f)
    neg_jobs = [(by_file[k], stamps, float(stamps.get(os.path.splitext(os.path.basename(by_file[k][0]))[0], 0.0)))
                for k in sorted(by_file) if k % a.neg_every == 0]
    for bag in ("doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
                "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch"):
        fs = sorted(glob.glob(os.path.join(a.cache, bag, "*.npy")), key=_natural_key)
        neg_jobs.append((fs, load_cache_stamps(os.path.join(a.cache, bag)), -1.0))
    intake = json.load(open("docs/extended_dataset_intake.json"))
    spd = {f["n"]: (f.get("speed_tracks") or 0.0) for f in intake["files"]}
    rng = np.random.default_rng(7)
    pos_jobs = []
    gid = 0
    for fn in [int(v) for v in a.pos_files.split(",")]:
        start = allf.index(by_file[fn][0])
        files = allf[start:start + 110]
        speeds = [spd.get(int(os.path.basename(f).split("_")[2]), 0.0) for f in files]
        for kind in a.kinds.split(","):
            pos_jobs.append((files, stamps, speeds, kind, 220.0, float(rng.uniform(-0.7, 0.7)),
                             float(rng.uniform(*OBJECT_CATALOGUE[kind].reflectivity)), int(rng.integers(1 << 30)), gid))
            gid += 1
    X_neg, g_neg, X_pos, g_pos, k_pos, d_pos = [], [], [], [], [], []
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for rows, groups in ex.map(negatives, neg_jobs):
            X_neg += rows
            g_neg += groups
        for pos, neg, g, kind in ex.map(positives, pos_jobs):
            X_pos += [p[:-1] for p in pos]
            d_pos += [p[-1] for p in pos]
            g_pos += [g] * len(pos)
            k_pos += [kind] * len(pos)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    np.savez_compressed(a.out, X_neg=np.array(X_neg), g_neg=np.array(g_neg), X_pos=np.array(X_pos),
                        g_pos=np.array(g_pos), k_pos=np.array(k_pos), d_pos=np.array(d_pos),
                        features=np.array(FEATURES))
    print(f"negatives {len(X_neg)} rows, positives {len(X_pos)} rows -> {a.out}")


if __name__ == "__main__":
    main()
