#!/usr/bin/env python3
"""Set F on the original moving recordings, with the train speed from the ICP reference: what
the LiDAR-only speed estimate and a (perfect) given speed add at long range.

    python scripts/speed_setf.py --ref out/speed --out out/speed_setf.json --jobs 2

``scripts/far_range_eval.py`` places a synthetic object at a fixed point of the tunnel ahead of
consecutive frames of the 20-minute ride and moves it with the ride's per-file speed. The ride
is not always at hand; the six original recordings are, and ``scripts/speed_reference.py`` gives
them a per-frame train displacement from frame-to-frame ICP. This script starts an approach at
every ``--step``-th frame of each moving recording where the reference says the train moves
faster than ``--min-speed`` for the whole approach, places the object ``--start`` m ahead, moves
it by the reference displacement of every frame (``far_range_eval.run_sequence``, legacy
placement, the shipped hit rule) and runs three detector variants on the very same draws:

* ``none``: the shipped path, no speed (single frame + persistence);
* ``estimated``: ``accumulation.estimate_speed: true`` (the LiDAR-only estimator feeds the
  5-frame accumulation beyond 40 m);
* ``given``: the reference speed handed to the detector, as odometry would be.

Stamps are snapped to the 10 Hz rotation (``eval_real.nominal_stamps``) as the node's header clock.
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MOVING = ["doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
          "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch"]
VARIANTS = ("none", "estimated", "given")


def _job(args):
    import far_range_eval as fre
    variant, job = args
    return variant, fre.run_sequence(job)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default="/data/cache")
    ap.add_argument("--ref", required=True, help="directory of scripts/speed_reference.py JSONL")
    ap.add_argument("--bags", default=",".join(MOVING))
    ap.add_argument("--kinds", default="person,box1.0")
    ap.add_argument("--start", type=float, default=200.0)
    ap.add_argument("--step", type=int, default=60, help="frames between approach starts")
    ap.add_argument("--min-speed", type=float, default=8.0)
    ap.add_argument("--lateral", default="-0.6:0.6")
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import yaml

    from eval_real import nominal_stamps, reference_speeds
    from resense.io import _natural_key, load_cache_stamps
    from resense.synthetic import OBJECT_CATALOGUE
    raw = yaml.safe_load(open(a.config, encoding="utf-8")) or {}
    base = raw.get("resense", raw)
    rng = np.random.default_rng(a.seed)
    lo, hi = (float(v) for v in a.lateral.split(":"))
    jobs = []
    starts = []
    for bag in a.bags.split(","):
        files = sorted(glob.glob(os.path.join(a.cache, bag, "*.npy")), key=_natural_key)
        stamps = nominal_stamps(load_cache_stamps(os.path.join(a.cache, bag)))
        spd = reference_speeds(os.path.join(a.ref, f"{bag}.jsonl"), len(files))
        k = 0
        while k < len(files):
            # frames the object needs to come from --start to 8 m at the reference speeds
            d, j = a.start, k
            while j < len(files) and d > 8.0 and spd[j] is not None and spd[j] >= a.min_speed:
                d -= spd[j] * 0.1
                j += 1
            if d <= 8.0:
                seq = files[k:j]
                speeds = spd[k:j]
                starts.append({"bag": bag, "frame": k, "frames": len(seq),
                               "speed_mean": round(float(np.mean(speeds)), 2)})
                for kind in a.kinds.split(","):
                    refl = float(rng.uniform(*OBJECT_CATALOGUE[kind].reflectivity))
                    lat = float(rng.uniform(lo, hi))
                    seed = int(rng.integers(1 << 30))
                    for variant in a.variants.split(","):
                        cfg = json.loads(json.dumps(base))
                        cfg.setdefault("accumulation", {})["estimate_speed"] = variant == "estimated"
                        jobs.append((variant, (seq, stamps, speeds, kind, a.start, lat, refl, seed, cfg, None,
                                               variant == "given", "bed", "legacy", None, 0.0, 0.0)))
                k += a.step
            else:
                k += 5
    print(f"{len(starts)} approaches, {len(jobs)} sequences", flush=True)
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        out = list(ex.map(_job, jobs))
    import far_range_eval as fre
    summ = {}
    for variant in a.variants.split(","):
        for kind in a.kinds.split(","):
            seqs = [o for v, o in out if v == variant and o["kind"] == kind and not o.get("skipped")]
            firsts = [o["first"] for o in seqs if o["first"] is not None]
            sus = [s for s in (fre.sustained_range(o["rows"]) for o in seqs) if s is not None]
            bins = {}
            for b0, b1 in fre.BINS:
                vis = [r for o in seqs for r in o["rows"] if b0 <= r["d"] < b1 and r["n"] > 0]
                bins[f"{b0}-{b1}"] = [sum(r["hit"] for r in vis), len(vis)]
            summ[f"{variant}/{kind}"] = {
                "sequences": len(seqs), "detected": len(firsts),
                "first_detection_m": [round(v, 1) for v in firsts],
                "first_detection_median": round(float(np.median(firsts)), 1) if firsts else None,
                "sustained_median": round(float(np.median(sus)), 1) if sus else None,
                "recall_by_bin": bins, "false_detections": sum(o["fp"] for o in seqs)}
    report = {"starts": starts, "summary": summ, "wall_s": round(time.time() - t0, 1),
              "parameters": vars(a),
              "sequences": [{"variant": v, **{k: o[k] for k in ("kind", "d0", "lateral", "first", "fp", "file0")}}
                            for v, o in out]}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(report, open(a.out, "w", encoding="utf-8"), indent=1)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
