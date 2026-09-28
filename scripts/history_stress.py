#!/usr/bin/env python3
"""False STOPs on obstacle-free recordings under other processing histories (27.09).

The node does not process every frame of a recording: its start-up catch-up, a loaded machine
or a slow disk drop some, and which ones depends on the run. The clear run of 26.09 failed on a
STOP that only one of three captured histories of the same recording produced
(docs/evidence/results/quality_cycle_2026-09-26_clear_failure/); the 1 cm cache quantisation
alone moves such a marginal alarm to another frame. This script measures that exposure:

* the three captured node histories of ``roundT_doubleT``, replayed exactly from the original
  bag (``--bag``, float coordinates, the node's own frame sequence);
* on the frame caches of the obstacle-free recordings, a fixed set of seeded histories: every
  frame, frames dropped at random (20 %, 40 %), the start-up catch-up (every second frame of the
  first 80, then all), a random start offset, and +-5 mm coordinate dither.

Every history is a fresh detector with the node's parameters (``auto_calibrate`` on). Reported:
per history the STOP frames and STOP events (distinct track ids), and the totals. Obstacle-free
recordings: every STOP is false.

    python scripts/history_stress.py --out out/history.json [--set section.key=value ...] [--jobs 4]
"""
from __future__ import annotations

import os

if __name__ == "__main__":
    for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
import glob  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

CAPTURES = os.path.join(ROOT, "docs", "evidence", "results", "quality_cycle_2026-09-26_clear_failure", "captures")
EMPTY = ("roundT_doubleT", "doubleT_platform", "roundT_pressureGate_roundT",
         "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch")
# (name, kind, parameter): the seeded histories run on every obstacle-free cache
HISTORIES = (("every", "every", 0.0), ("drop20", "drop", 0.2), ("drop40", "drop", 0.4),
             ("catchup", "catchup", 80), ("offset", "offset", 0), ("dither5", "dither", 5.0))


def _history(kind: str, param, n: int, rng) -> np.ndarray:
    if kind == "drop":
        keep = rng.random(n) >= param
        keep[0] = True
        return np.flatnonzero(keep)
    if kind == "catchup":
        head = np.arange(0, min(n, int(param)), 2)
        return np.concatenate([head, np.arange(min(n, int(param)), n)])
    if kind == "offset":
        return np.arange(int(rng.integers(5, max(6, n // 4))), n)
    return np.arange(n)


def run_cache(job):
    bag, name, kind, param, seed, cache, cfg_dict = job
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    from resense.io import _natural_key, load_cache_stamps
    from resense.pointcloud import COMPACT_DTYPE, compact_to_xyz, expand_compact16
    cfg = DetectorConfig.from_dict(cfg_dict)
    cfg.calibration.enabled = True
    d = os.path.join(cache, bag)
    files = sorted(glob.glob(os.path.join(d, "*.npy")), key=_natural_key)
    stamps = load_cache_stamps(d)
    rng = np.random.default_rng(seed)
    det = Detector(cfg)
    stop_frames, events, dists = 0, set(), []
    for i in _history(kind, param, len(files), rng):
        f = files[i]
        stem = os.path.splitext(os.path.basename(f))[0]
        arr = np.load(f)
        if kind == "dither":
            arr = expand_compact16(arr)
            xyz = compact_to_xyz(arr) + rng.uniform(-param, param, (arr.size, 3)).astype(np.float32) * 1e-3
            out = np.zeros(arr.size, dtype=COMPACT_DTYPE)
            out["x"], out["y"], out["z"] = xyz.T
            out["intensity"], out["ring"] = arr["intensity"], arr["ring"]
            arr = out
        r = det.process(frame_from_compact(arr, cfg.sensor, stamp=stamps.get(stem, i * 0.1), frame_id=stem))
        if r.obstacle:
            stop_frames += 1
            for x in r.detections:
                events.add(x.id)
                dists.append(round(float(x.distance), 1))
    return {"source": "cache", "bag": bag, "history": name, "seed": seed, "stop_frames": stop_frames,
            "stop_events": len(events), "stop_distances": sorted(set(dists))[:20]}


def run_capture(job):
    name, bag_dir, cfg_dict = job
    from check_dry_run import load as load_status
    from replay_node_frames import bag_frames
    from resense.config import DetectorConfig
    from resense.detector import Detector
    cfg = DetectorConfig.from_dict(cfg_dict)
    cfg.calibration.enabled = True
    node = [f for f in load_status(os.path.join(CAPTURES, name + ".jsonl.gz"))[0] if f["node"].get("recording") == 1]
    stamps = [f["stamp"] for f in node]
    det = Detector(cfg)
    stop_frames, events, dists, n = 0, set(), [], 0
    for _i, fr in bag_frames(bag_dir, cfg, node[0]["node"].get("input_topic"), stamps, False):
        r = det.process(fr, ego_speed=None)
        n += 1
        if r.obstacle:
            stop_frames += 1
            for x in r.detections:
                events.add(x.id)
                dists.append(round(float(x.distance), 1))
    return {"source": "capture", "bag": "roundT_doubleT", "history": name, "frames": n,
            "stop_frames": stop_frames, "stop_events": len(events), "stop_distances": sorted(set(dists))}


def main(argv=None) -> int:
    import eval_real
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default="/data/cache")
    ap.add_argument("--bag", default="/data/raw/for_hackathon/roundT_doubleT",
                    help="the original roundT_doubleT bag for the captured histories ('' = skip them)")
    ap.add_argument("--config", default=os.path.join(ROOT, "configs", "default.yaml"))
    ap.add_argument("--set", action="append", default=[], help="section.key=value override (YAML value)")
    ap.add_argument("--bags", default=",".join(EMPTY))
    ap.add_argument("--seeds", type=int, default=1, help="seeds per random history")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    cfg_dict = eval_real.load_cfg_dict(a.config, a.set)
    jobs = []
    for bag in [b for b in a.bags.split(",") if b]:
        for name, kind, param in HISTORIES:
            for seed in (range(a.seeds) if kind in ("drop", "offset", "dither") else [0]):
                jobs.append((bag, name, kind, param, seed, a.cache, cfg_dict))
    cap_jobs = []
    if a.bag and os.path.isdir(a.bag):
        cap_jobs = [(c, a.bag, cfg_dict) for c in ("failed_clear", "old_stock", "old_pass")]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        rows = list(ex.map(run_capture, cap_jobs)) + list(ex.map(run_cache, jobs))
    tot = {"histories": len(rows), "stop_frames": sum(r["stop_frames"] for r in rows),
           "stop_events": sum(r["stop_events"] for r in rows),
           "histories_with_stop": sum(r["stop_events"] > 0 for r in rows),
           "captures_stop_events": sum(r["stop_events"] for r in rows if r["source"] == "capture"),
           "cache_stop_events": sum(r["stop_events"] for r in rows if r["source"] == "cache")}
    out = {"schema": "resense-history-stress-v1", "sets": a.set, "wall_s": round(time.time() - t0, 1),
           "totals": tot, "rows": rows}
    for r in rows:
        print(f"{r['source']:7s} {r['bag']:38s} {r['history']:12s} seed {r.get('seed', '-')!s:3s} "
              f"STOP frames {r['stop_frames']:3d} events {r['stop_events']:2d} {r['stop_distances']}")
    print("totals:", json.dumps(tot))
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
