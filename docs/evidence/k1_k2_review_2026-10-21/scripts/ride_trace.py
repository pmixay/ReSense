#!/usr/bin/env python3
"""Replay one ride piece exactly as the regression gate's eval_real.run_piece does (same file split, stamps, config
from the gate's work directory, fresh detector), and for frames in [lo, hi] record read-only state after process():
the clusters the curve gauge added (Cluster.curve), every STOP detection with its track's curve_seen flag, the
curve model (curve_from, axis_valid). Every frame's res.to_dict() is compared with the gate's plain work row (all
fields except timing_ms and latency-derived health) to show the trace changes nothing.
    ride_trace.py <cache> <gate_work_dir> <piece> <lo> <hi> <out.jsonl>"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
import yaml
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import frame_from_compact
from scripts.cache_io import cache_files, cache_file_stem, load_cache_array, load_cache_stamps

cache, work, piece, lo, hi, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
raw = yaml.safe_load(open(os.path.join(work, "config.yaml")))
cfg_dict = raw.get("resense", raw)
cfg = DetectorConfig.from_dict(cfg_dict)
d = os.path.join(cache, "new_data")
files = cache_files(d)
stamps = load_cache_stamps(d)
part = list(np.array_split(np.array(files), 8)[piece])
plain = [json.loads(l) for l in open(os.path.join(work, f"new_data_{piece}.jsonl"))]
det = Detector(cfg)
mism = 0


def strip(r):
    r = dict(r); r.pop("timing_ms", None)
    h = dict(r.get("health", {}))
    for k in ("latency_p95_ms", "level", "decision_level", "messages", "latency_basis", "latency_sample_age_frames"):
        h.pop(k, None)
    r["health"] = h
    return r


with open(out, "w") as fh:
    for i, f in enumerate(part[: hi + 1]):
        stem = cache_file_stem(f)
        fr = frame_from_compact(load_cache_array(f), cfg.sensor, stamp=stamps.get(stem, i * 0.1), frame_id=stem)
        res = det.process(fr)
        dd = res.to_dict(); dd["frame"] = i; dd["frame_id"] = stem
        same = strip(json.loads(json.dumps(dd))) == strip(plain[i])
        mism += not same
        if i < lo:
            continue
        tr = det.track
        cv = getattr(tr, "curve", None)
        tracks = {t.id: t for t in det.tracker.tracks}
        row = dict(frame=i, same_as_plain=same, stop=bool(res.obstacle),
                   curve=cv is not None, curve_from=None if cv is None else round(float(cv.curve_from), 1),
                   curve_valid=None if cv is None else round(float(cv.axis_valid), 1),
                   base_valid=round(float(min(tr.axis_valid, 9999)), 1),
                   added=[dict(d=round(float(c.distance), 1), lat=round(float(c.lateral), 2),
                               cen=[round(float(v), 1) for v in c.centroid], size=[round(float(v), 2) for v in c.size],
                               hmin=round(float(c.height_min), 2), hmax=round(float(c.height_max), 2), n=int(c.n))
                          for c in res.candidates if getattr(c, "curve", False)],
                   stops=[dict(id=int(x.id), d=round(float(x.distance), 1), lat=round(float(x.lateral), 2),
                               cen=[round(float(v), 1) for v in x.center], reason=x.reason, kind=x.kind,
                               curve_seen=bool(getattr(tracks.get(x.id), "curve_seen", False)),
                               last_curve=bool(getattr(getattr(tracks.get(x.id), "last", None), "curve", False)))
                          for x in res.detections])
        fh.write(json.dumps(row) + "\n")
print("frames", min(len(part), hi + 1), "rows differing from the plain gate run:", mism)
