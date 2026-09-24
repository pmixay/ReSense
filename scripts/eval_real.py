#!/usr/bin/env python3
"""Run one detector configuration over every cached organizer recording at full rate and print
the real-data report card: false alarms on the obstacle-free recordings, the labelled person of
``doubleT_obstacle``, latency.

    python scripts/eval_real.py --cache /data/cache --out out/eval/v06            # defaults
    python scripts/eval_real.py --cache /data/cache --out out/eval/x --config my.yaml --set cluster.eps=0.3
    python scripts/eval_real.py --cache /data/cache --out out/eval/x --bags roundT_doubleT,new_data --jobs 4

``--cache`` holds one directory of ``*.npy`` frames per bag (``scripts/cache_frames.py --every 1
--int16 --stamps``); the extended recording ``new_data`` (11 271 frames) is split into
``--chunks`` consecutive pieces processed in parallel, each with a fresh detector (the tracker
restarts at a piece boundary: a few events can be split in two). Per-frame JSONL results go to
``--out/<bag>[_<chunk>].jsonl`` and the summary to ``--out/summary.json``.
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
import yaml

SIX = ["doubleT_obstacle", "doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
       "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch"]
LABELS = {"doubleT_obstacle": "labels/doubleT_obstacle.json"}


def _apply_overrides(d: dict, sets):
    for s in sets or []:
        key, val = s.split("=", 1)
        sec, k = key.split(".", 1)
        d.setdefault(sec, {})[k] = yaml.safe_load(val)
    return d


def load_cfg_dict(path, sets) -> dict:
    """The parameter dict of ``path`` with the ``--set`` overrides, read once in the parent so
    that every job runs the same parameters even if the file changes during the run."""
    import copy
    d = {}
    if path:
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        d = raw.get("resense", raw)
    return _apply_overrides(copy.deepcopy(d), sets)


def load_cfg(path, sets):
    from resense.config import DetectorConfig
    return DetectorConfig.from_dict(load_cfg_dict(path, sets))


def run_piece(job):
    """Process one sequence of cached files with a fresh detector; returns per-piece stats."""
    name, files, cfg_dict, out_path, stamps, speeds = job
    sys.path.insert(0, os.getcwd())
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    cfg = DetectorConfig.from_dict(cfg_dict)
    det = Detector(cfg)
    lat = []
    with open(out_path, "w", encoding="utf-8") as fh:
        for i, f in enumerate(files):
            stem = os.path.splitext(os.path.basename(f))[0]
            idx = int(stem.rsplit("_", 1)[1])
            fr = frame_from_compact(np.load(f), cfg.sensor, stamp=stamps.get(stem, i * 0.1), frame_id=stem)
            res = det.process(fr, ego_speed=speeds[i]) if speeds is not None else det.process(fr)
            d = res.to_dict()
            d["frame"] = idx if name in SIX else i
            d["frame_id"] = stem
            fh.write(json.dumps(d) + "\n")
            lat.append(res.timing_ms["total"])
    return name, out_path, lat


def summarize(name, paths, labels_path=None, confirm_hits=5, frame_dt=0.1):
    from resense.metrics import Evaluation, gt_objects, load_gt
    gt = load_gt(labels_path) if labels_path else {}
    alarm_frames = adv_frames = frames = 0
    events = set()
    dists = []
    health = {"ok": 0, "warn": 0, "error": 0}
    mon = []
    ev = Evaluation(confirm_hits=confirm_hits, frame_dt=frame_dt) if labels_path else None
    for pi, p in enumerate(paths):
        for line in open(p, encoding="utf-8"):
            d = json.loads(line)
            frames += 1
            if d["obstacle"]:
                alarm_frames += 1
                for det in d["detections"]:
                    events.add((pi, det["id"]))
                    dists.append(det["distance"])
            if d["warning"]:
                adv_frames += 1
            h = d.get("health") or {}
            if h:
                health[h["level"]] += 1
                mon.append(h["monitored_range"])
            if ev is not None:
                key = f"{int(d['frame']):05d}"
                ev.add_frame(d, gt_objects(gt.get(key, [])))
    out = {"frames": frames, "alarm_frames": alarm_frames, "alarm_events": len(events),
           "advisory_frames": adv_frames,
           "alarm_dist": [round(min(dists), 1), round(max(dists), 1)] if dists else None,
           "health": health, "monitored_range_median": round(float(np.median(mon)), 1) if mon else None}
    if ev is not None:
        s = ev.summary()
        out["labelled"] = {"recall": None if s["recall"] is None else round(s["recall"], 3),
                           "first_alarm_frame": s["first_alarm_frame"], "fp_frames": s["fp_frames"],
                           "fp_events": s["fp_events"], "per_bin": s["per_bin_counts"],
                           "distance_error_max_abs": s["distance_error_max_abs"]}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default="/data/cache")
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--set", action="append", default=[], help="section.key=value override (YAML value)")
    ap.add_argument("--bags", default=",".join(SIX + ["new_data"]))
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--chunks", type=int, default=8, help="parallel pieces of new_data")
    ap.add_argument("--given-speed", default="", metavar="INTAKE_JSON",
                    help="hand the train speed of new_data to the detector (per split file, 'speed_tracks' of "
                         "docs/extended_dataset_intake.json): the multi-frame accumulation path")
    a = ap.parse_args()
    from resense.io import _natural_key, load_cache_stamps
    os.makedirs(a.out, exist_ok=True)
    cfg_dict = load_cfg_dict(a.config, a.set)
    cfg = load_cfg(a.config, a.set)                # fail fast on an unknown key
    with open(os.path.join(a.out, "config.yaml"), "w", encoding="utf-8") as fh:
        yaml.safe_dump({"resense": cfg_dict}, fh, sort_keys=False)
    spd_file = {}
    if a.given_speed:
        spd_file = {f["n"]: (f.get("speed_tracks") or 0.0) for f in json.load(open(a.given_speed))["files"]}
    jobs = []
    pieces = {}
    for bag in [b for b in a.bags.split(",") if b]:
        d = os.path.join(a.cache, bag)
        files = sorted(glob.glob(os.path.join(d, "*.npy")), key=_natural_key)
        if not files:
            print(f"skip {bag}: no cache in {d}", file=sys.stderr)
            continue
        stamps = load_cache_stamps(d)
        n = a.chunks if bag == "new_data" else 1
        for k, part in enumerate(np.array_split(np.array(files), n)):
            out = os.path.join(a.out, f"{bag}.jsonl" if n == 1 else f"{bag}_{k}.jsonl")
            speeds = None
            if spd_file and bag == "new_data":
                speeds = [float(spd_file.get(int(os.path.basename(f).split("_")[2]), 0.0)) for f in part]
            jobs.append((bag, list(part), cfg_dict, out, stamps, speeds))
            pieces.setdefault(bag, []).append(out)
    t0 = time.time()
    lat = {}
    # longest first
    jobs.sort(key=lambda j: -len(j[1]))
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for name, path, lats in ex.map(run_piece, jobs):
            lat.setdefault(name, []).extend(lats)
    summary = {"config": a.config, "set": a.set, "given_speed": bool(spd_file), "wall_s": round(time.time() - t0, 1), "bags": {}}
    tot_f = tot_e = tot_n = 0
    for bag, paths in pieces.items():
        s = summarize(bag, paths, LABELS.get(bag),
                      confirm_hits=cfg.tracking.frames_to_confirm(), frame_dt=cfg.tracking.frame_dt)
        L = np.array(lat[bag])
        s["latency_ms"] = [round(float(L.mean()), 1), round(float(np.percentile(L, 95)), 1), round(float(L.max()), 1)]
        summary["bags"][bag] = s
        if bag in SIX and bag != "doubleT_obstacle":
            tot_f += s["alarm_frames"]
            tot_e += s["alarm_events"]
            tot_n += s["frames"]
    summary["five_empty_bags"] = {"frames": tot_n, "alarm_frames": tot_f, "alarm_events": tot_e}
    json.dump(summary, open(os.path.join(a.out, "summary.json"), "w"), indent=1)
    print(f"{'bag':40s} {'frames':>6s} {'alarmF':>6s} {'events':>6s} {'advis':>6s} {'dist':>14s} {'lat mean/p95':>14s} health(ok/warn/err) mon")
    for bag, s in summary["bags"].items():
        dist = "-" if not s["alarm_dist"] else f"{s['alarm_dist'][0]}-{s['alarm_dist'][1]}"
        h = s["health"]
        print(f"{bag:40s} {s['frames']:6d} {s['alarm_frames']:6d} {s['alarm_events']:6d} {s['advisory_frames']:6d} {dist:>14s} "
              f"{s['latency_ms'][0]:6.1f}/{s['latency_ms'][1]:6.1f} {h['ok']}/{h['warn']}/{h['error']} {s['monitored_range_median']}")
        if "labelled" in s:
            print("   labelled:", s["labelled"])
    print("five empty bags:", summary["five_empty_bags"], f"wall {summary['wall_s']} s")


if __name__ == "__main__":
    main()
