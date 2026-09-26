#!/usr/bin/env python3
"""Start-up census (26.09, EXPERIMENTS §1j): what a FRESH detector reports in the first seconds of
a bag. The jury plays every hidden bag from a fresh start, so a false STOP there is paid once per bag.

    python scripts/startup_census.py --cache /data/cache --jobs 2 --out out/startup.json
    python scripts/startup_census.py ... --set tracking.startup_low_advisory_m=3.5   # a variant

Starts (each a fresh ``Detector``, the cached receive stamps, the first ``--frames`` frames):

* every split file of the 20-minute ride ``new_data`` (``new_data_<N>_0000`` ..., 221 bags of
  ~5 s as recorded), ``ride_split``;
* the eight starts of the ride pieces of ``scripts/regression_gate.py`` / ``eval_real.py``
  (``np.array_split`` of the whole ride into ``--chunks``), ``ride_chunk``;
* the six organizer recordings and set O (``cloud_with_fake_obj``), ``recording``.

Per start: STOP (alarm) frames, STOP events (distinct confirmed track ids), STOP episodes, and per
event its first frame, distance range, stage (``low`` = a bed-level candidate of the low-object
stage, ``corridor`` otherwise), lateral offset, height, the mount-calibration status at that frame
(``pending`` / ``provisional`` / ..., and whether the provisional decision is still due), the age
of the track model. Real objects: ``doubleT_obstacle``'s labelled hits per label in the window and
its first alarm frame; set O's per-object STOP frames in the window (``score_fake_objects``).
"""
from __future__ import annotations

import os

if __name__ == "__main__":        # one BLAS / OpenMP thread per worker: set before numpy loads
    for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
import datetime  # noqa: E402
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

import eval_real  # noqa: E402  (scripts/)

RIDE = "new_data"
SET_O = "cloud_with_fake_obj"
SET_O_LABELS = "labels/cloud_with_fake_obj.json"
LABELLED = "doubleT_obstacle"


def starts(cache: str, n_frames: int, chunks: int) -> list:
    """[(kind, name, [files])] of every start."""
    from resense.io import _natural_key
    out = []
    ride = sorted(glob.glob(os.path.join(cache, RIDE, "*.npy")), key=_natural_key)
    if ride:
        by_split = {}
        for f in ride:
            by_split.setdefault(int(os.path.basename(f).split("_")[2]), []).append(f)
        for n in sorted(by_split):
            out.append(("ride_split", f"{RIDE}_{n}", by_split[n][:n_frames]))
        for k, part in enumerate(np.array_split(np.array(ride), chunks)):
            out.append(("ride_chunk", f"{RIDE}_chunk{k}", list(part[:n_frames])))
    for name in eval_real.SIX + [SET_O]:
        files = sorted(glob.glob(os.path.join(cache, name, "*.npy")), key=_natural_key)
        if files:
            out.append(("recording", name, files[:n_frames]))
    return out


def run_start(job):
    """One fresh detector over the files of one start; the per-frame rows."""
    kind, name, files, cfg_dict, stamps = job
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    cfg = DetectorConfig.from_dict(cfg_dict)
    det = Detector(cfg)
    rows = []
    for i, f in enumerate(files):
        stem = os.path.splitext(os.path.basename(f))[0]
        fr = frame_from_compact(np.load(f), cfg.sensor, stamp=stamps.get(stem, i * 0.1), frame_id=stem)
        res = det.process(fr)
        d = res.to_dict()
        d.pop("track", None)
        d["frame"] = int(stem.rsplit("_", 1)[1]) if kind == "recording" else i
        d["frame_id"] = stem
        d["model_age"] = int(det.track.age)
        d["rail_slabs"] = int(det.track.rail_slabs)
        cal = det.calib
        d["calib"] = {"status": cal.state.status, "provisional_due": bool(cfg.calibration.enabled
                                                                          and not cal._provisional_done),
                      "rail_obs": len(cal._recent), "spaced_obs": len(cal._obs)}
        rows.append(d)
    return kind, name, rows


def _stage(det: dict) -> str:
    return "low" if det.get("kind") == "low" else "corridor"


def start_summary(kind, name, rows) -> dict:
    """STOP frames / events / episodes of one start and one entry per STOP event."""
    events = {}
    episodes, prev = 0, False
    for d in rows:
        if d["obstacle"] and not prev:
            episodes += 1
        prev = bool(d["obstacle"])
        for det in d["detections"]:
            e = events.get(det["id"])
            if e is None:
                e = events[det["id"]] = {
                    "track_id": det["id"], "first_frame": d["frame"], "t_s": round(d["frame"] * 0.1, 1)
                    if kind != "recording" else None, "frames": 0, "dist": [det["distance"], det["distance"]],
                    "stage": _stage(det), "reason": det.get("reason", ""), "lateral": det["lateral"],
                    "height_min": det["height_min"], "size": det["size"], "n_points": det["n_points"],
                    "mount_status": d["calib"]["status"], "provisional_due": d["calib"]["provisional_due"],
                    "rail_obs": d["calib"]["rail_obs"], "model_age": d["model_age"],
                    "rail_slabs": d["rail_slabs"], "ego_speed": d.get("ego_speed")}
            e["frames"] += 1
            e["dist"] = [min(e["dist"][0], det["distance"]), max(e["dist"][1], det["distance"])]
    first = next((d["frame"] for d in rows if d["obstacle"]), None)
    return {"kind": kind, "name": name, "frames": len(rows),
            "stop_frames": sum(1 for d in rows if d["obstacle"]), "stop_events": len(events),
            "stop_episodes": episodes, "first_stop_frame": first,
            "advisory_frames": sum(1 for d in rows if d["warning"]),
            "provisional_due_frames": sum(1 for d in rows if d["calib"]["provisional_due"]),
            "mount_status_last": rows[-1]["calib"]["status"] if rows else None,
            "events": list(events.values())}


def labelled(rows) -> dict:
    from regression_gate import labelled_hits
    return labelled_hits([(0, d) for d in rows], os.path.join(ROOT, eval_real.LABELS[LABELLED]))


def set_o(rows) -> dict:
    from resense.metrics import load_gt
    from score_fake_objects import score
    objs, bg = score(rows, load_gt(os.path.join(ROOT, SET_O_LABELS)))
    out = {}
    for label, o in sorted(objs.items()):
        e = {"in_gauge": o["in_gauge"], "visible_frames": o["visible_frames"], "stop_frames": o["alarm_frames"],
             "advisory_frames": o["advisory_only_frames"]}
        if o["in_gauge"]:
            e.update({"first_stop_frame": o["first_alarm_frame"], "first_stop_m": o["first_alarm_m"]})
        else:
            e["false_stop_frames"] = o["false_alarm_frames"]
        out[label] = e
    return {"objects": out, "background": {"alarm_frames": bg["background_alarm_frames"],
                                           "track_ids": bg["background_alarm_ids"]}}


def aggregate(entries) -> dict:
    """Totals over the starts of one kind, and the STOP events split by stage and mount state."""
    ev = [e for s in entries for e in s["events"]]
    by = {}
    for e in ev:
        key = f"{e['stage']}|{'provisional_due' if e['provisional_due'] else e['mount_status']}"
        by[key] = by.get(key, 0) + 1
    return {"starts": len(entries), "frames": sum(s["frames"] for s in entries),
            "starts_with_stop": sum(1 for s in entries if s["stop_frames"]),
            "stop_frames": sum(s["stop_frames"] for s in entries),
            "stop_events": len(ev), "stop_episodes": sum(s["stop_episodes"] for s in entries),
            "advisory_frames": sum(s["advisory_frames"] for s in entries),
            "events_by_stage_and_mount": dict(sorted(by.items())),
            "events_first_1_5s": sum(1 for e in ev if e["first_frame"] < 15),
            "events_within_10m": sum(1 for e in ev if e["dist"][0] < 10.0)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default="/data/cache")
    ap.add_argument("--config", default=os.path.join(ROOT, "configs", "default.yaml"))
    ap.add_argument("--set", action="append", default=[], help="section.key=value override (YAML value)")
    ap.add_argument("--frames", type=int, default=40, help="frames of each start (40 = 4 s at 10 Hz)")
    ap.add_argument("--chunks", type=int, default=8, help="ride pieces of regression_gate / eval_real")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--rows", default=None, metavar="JSONL", help="also write every frame row here")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    from resense.io import load_cache_stamps
    cfg_dict = eval_real.load_cfg_dict(a.config, a.set)
    eval_real.load_cfg(a.config, a.set)                 # fail fast on an unknown key
    todo = starts(a.cache, a.frames, a.chunks)
    stamps = {}
    for _, name, files in todo:
        d = os.path.dirname(files[0])
        if d not in stamps:
            stamps[d] = load_cache_stamps(d)
    jobs = [(k, n, f, cfg_dict, stamps[os.path.dirname(f[0])]) for k, n, f in todo]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        results = list(ex.map(run_start, jobs, chunksize=4))
    entries = {k: [] for k in ("ride_split", "ride_chunk", "recording")}
    extra = {}
    for kind, name, rows in results:
        s = start_summary(kind, name, rows)
        if name == LABELLED:
            s["labelled"] = labelled(rows)
        if name == SET_O:
            s["set_O"] = set_o(rows)
        entries[kind].append(s)
        extra[name] = rows
    if a.rows:
        with open(a.rows, "w", encoding="utf-8") as fh:
            for _, name, rows in results:
                for d in rows:
                    fh.write(json.dumps({"start": name, **d}) + "\n")
    out = {"schema": "resense-startup-census-v1",
           "created": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "config": {"path": os.path.relpath(a.config, ROOT) if a.config.startswith(ROOT) else a.config,
                      "set": a.set},
           "frames_per_start": a.frames, "wall_s": round(time.time() - t0, 1),
           "summary": {k: aggregate(v) for k, v in entries.items()},
           "starts": entries}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    for k, s in out["summary"].items():
        print(f"{k:11s} starts {s['starts']:3d}  with STOP {s['starts_with_stop']:3d}  STOP frames "
              f"{s['stop_frames']:4d} events {s['stop_events']:3d} episodes {s['stop_episodes']:3d}  "
              f"{s['events_by_stage_and_mount']}")
    for kind in entries:
        for s in entries[kind]:
            for e in s["events"]:
                print(f"   {s['name']:40s} id {e['track_id']:3d} frame {e['first_frame']:2d} x{e['frames']:2d} "
                      f"{e['dist'][0]:6.1f}-{e['dist'][1]:6.1f} m {e['stage']:8s} {e['reason'] or '-':10s} "
                      f"lat {e['lateral']:+.2f} hmin {e['height_min']:+.2f} mount {e['mount_status']}"
                      f"{' (prov. due)' if e['provisional_due'] else ''} model age {e['model_age']}")
    lab = next((s for s in entries["recording"] if s["name"] == LABELLED), None)
    if lab:
        print(f"{LABELLED}: first STOP frame {lab['first_stop_frame']}, labelled {lab.get('labelled')}")
    print(f"wrote {a.out} ({out['wall_s']} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
