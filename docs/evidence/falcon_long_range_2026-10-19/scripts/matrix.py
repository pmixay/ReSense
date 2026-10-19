#!/usr/bin/env python3
"""Injection matrix of PROTOCOL.md section 3 for one detector configuration.

    matrix.py --name <label> --out <dir> [--set sec.key=val ...] [--seeds 0,1,2] [--jobs 4]
              [--check-prefix]

The detector runs frames 0..299 once (no target); its state is deep-copied for every case, which
then runs frames 300.. with the target injected. ``--check-prefix`` re-runs one case from frame 0
without the copied state and requires identical rows (instrumentation must not change results).
Per case one JSONL (rows as run_cache.py) and one summary row in ``<out>/<name>_summary.json``.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import pickle
import zlib
import sys
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np  # noqa: E402

from assoc import associate, summary  # noqa: E402
from inject import Injector  # noqa: E402
import run_cache  # noqa: E402

CACHE = Path("/home/user/data/falcon")
PREFIX = 300
STATIC_FRAMES = 150
RANGES = (150, 200, 250, 300, 350)
APPROACH = {"start": 400.0, "speed": 10.0, "stop_at": 100.0, "frames": 310}
EV = HERE.parent


def targets():
    person = json.loads((EV / "person_model.json").read_text())
    base = {k: person[k] for k in ("size", "bottom", "fill", "rho", "intensity")}
    t = {"person": base, "person_dark": dict(base, rho={"split": 0.8, "lower": 0.05, "upper": 0.10})}
    for rho in (0.1, 0.2, 0.5):
        t[f"cube{int(rho * 100)}"] = {"size": [1, 1, 1], "bottom": -0.2, "rho": rho, "intensity": 20.0}
        t[f"box2_{int(rho * 100)}"] = {"size": [2, 2, 2], "bottom": -0.2, "rho": rho, "intensity": 20.0}
    t["outside"] = {"size": [1, 1, 1], "bottom": -0.2, "rho": 0.5, "lat": 2.5, "intensity": 20.0}
    return t


def cases(seeds):
    out = []
    for name, t in targets().items():
        for seed in seeds:
            for D in RANGES:
                out.append({"case": f"{name}_static{D}_s{seed}", "target": name, "mode": "static", "range": D,
                            "seed": seed, "spec": dict(t, **{"from": PREFIX, "to": PREFIX + STATIC_FRAMES, "dist": D})})
            out.append({"case": f"{name}_approach_s{seed}", "target": name, "mode": "approach", "seed": seed,
                        "spec": dict(t, **{"from": PREFIX, "to": PREFIX + APPROACH["frames"],
                                           "start": APPROACH["start"], "speed": APPROACH["speed"],
                                           "stop_at": APPROACH["stop_at"]})})
    return out


META = None


def run_frames(det, cfg, R_vs, lo, hi, injector, rows):
    last = META[lo - 1]["stamp"] if lo > 0 else None
    for i in range(lo, hi):
        m = META[i]
        stamp = m["stamp"]
        if last is not None:
            gap = stamp - last
            if gap < -0.5 or gap > 30.0 or gap > 1.0:
                raise RuntimeError("unexpected hole in the empty prefix")
        last = stamp
        d = np.load(CACHE / f"f_{i:05d}.npz")
        xyz, inten, info = (d["xyz"], d["inten"], None) if injector is None else injector.apply(i, d)
        k = run_cache.crop(xyz, cfg.sensor.min_range, cfg.sensor.max_range)
        frame = run_cache.Frame(xyz=xyz[k] @ R_vs.T, intensity=inten[k], ring=None, stamp=stamp,
                                frame_id=m["frame_id"], meta={"n_raw": m["n_raw"], "n_near": m["n_near"]})
        res = det.process(frame, ego_speed=None)
        r = run_cache.record(i, m["bag_t"], stamp, res, 0.0, 0.0, m["frame_id"], "/iv_points")
        r["mount_rotation"] = np.asarray(det.mount_rotation).tolist()
        r["track_detail"] = res.track.to_dict()
        if info is not None:
            r["inj"] = info
        rows.append(r)
    return det


def target_path(c, hi):
    t = c["spec"]
    lat = float(t.get("lat", 0.0))
    if c["mode"] == "static":
        return [[t["from"], t["dist"], lat], [t["to"] - 1, t["dist"], lat]]
    return [[i, max(t["start"] - t["speed"] * 0.1 * (i - t["from"]), t["stop_at"]), lat] for i in range(t["from"], hi)]


def run_case(args):
    c, state_path, cfg_sets, out, track = args
    with open(state_path, "rb") as f:
        det = pickle.load(f)
    cfg = run_cache.build_cfg("falcon_ros", cfg_sets)
    R_vs = run_cache.axis_matrix(cfg.sensor).astype(np.float32)
    inj = Injector({"track": track, "seed": 100 + c["seed"] * 7919 + zlib.crc32(c["case"].encode()) % 1000, "targets": [c["spec"]]})
    hi = c["spec"]["to"]
    rows = []
    run_frames(det, cfg, R_vs, PREFIX, hi, inj, rows)
    with open(Path(out) / f"{c['case']}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    path = target_path(c, hi)
    a = associate(rows, path, track, range(PREFIX, hi))
    s = summary(a, [(400, 350), (350, 300), (300, 250), (250, 200), (200, 150), (150, 100)])
    first_stop = s.get("first_stop_frame")
    s["seconds_to_first_stop"] = None if first_stop is None else round((first_stop - PREFIX) * 0.1, 1)
    s["stop_fraction"] = round(sum(x["stop"] for x in a) / len(a), 3)
    s["returns_per_frame"] = round(float(np.mean([r["inj"][0]["returns"] for r in rows if r.get("inj")])), 2)
    s["decisions"] = {k: sum(r["decision"] == k for r in rows) for k in ("GO", "CAUTION", "STOP", "FAULT")}
    return {k: v for k, v in c.items() if k != "spec"} | s


def main():
    global META
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--only", default="", help="comma list of target names")
    ap.add_argument("--check-prefix", action="store_true")
    a = ap.parse_args()
    out = Path(a.out) / a.name
    out.mkdir(parents=True, exist_ok=True)
    META = json.loads((CACHE / "meta.json").read_text())
    track = json.loads((EV / "track_reference.json").read_text())["track"]
    cfg = run_cache.build_cfg("falcon_ros", a.set)
    det = run_cache.Detector(cfg)
    R_vs = run_cache.axis_matrix(cfg.sensor).astype(np.float32)
    prefix_rows = []
    run_frames(det, cfg, R_vs, 0, PREFIX, None, prefix_rows)
    state = out / "prefix_state.pkl"
    with open(state, "wb") as f:
        pickle.dump(det, f)
    cs = cases([int(s) for s in a.seeds.split(",")])
    if a.only:
        cs = [c for c in cs if c["target"] in a.only.split(",")]
    with Pool(a.jobs, initializer=_init, initargs=(META,)) as pool:
        rows = pool.map(run_case, [(c, state, a.set, out, track) for c in cs], chunksize=1)
    res = {"name": a.name, "set": a.set, "cases": rows}
    if a.check_prefix:
        c = next(x for x in cs if x["mode"] == "approach")
        det2 = run_cache.Detector(cfg)
        inj = Injector({"track": track, "seed": 100 + c["seed"] * 7919 + zlib.crc32(c["case"].encode()) % 1000, "targets": [c["spec"]]})
        rows2 = []
        run_frames(det2, cfg, R_vs, 0, c["spec"]["to"], inj, rows2)
        ref = [json.loads(line) for line in open(out / f"{c['case']}.jsonl")]
        keys = ("decision", "dets", "warns", "nearest", "clear", "monitored")
        res["prefix_check"] = {"case": c["case"], "rows": len(ref),
                               "mismatches": sum(any(x[k] != y[k] for k in keys) for x, y in zip(ref, rows2[PREFIX:]))}
    (Path(a.out) / f"{a.name}_summary.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res.get("prefix_check")))


def _init(meta):
    global META
    META = meta


if __name__ == "__main__":
    main()
