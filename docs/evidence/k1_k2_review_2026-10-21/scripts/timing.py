#!/usr/bin/env python3
"""Per-frame time (timing_ms.total) of one tree on fixed frames, run alone: ride piece 2 frames 0-899 and the whole
roundT_doubleT / roundT_pressureGate_roundT / doubleT_obstacle caches, the gate's own frame loading and YAML.
    timing.py <out.json>   (RESENSE_REPO / PYTHONPATH = the tree)"""
import json, os, sys
import numpy as np
repo = os.environ["RESENSE_REPO"]; sys.path.insert(0, repo); sys.path.insert(0, os.path.join(repo, "scripts"))
import yaml
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import frame_from_compact
from scripts.cache_io import cache_files, cache_file_stem, load_cache_array, load_cache_stamps
raw = yaml.safe_load(open(os.path.join(repo, "configs/default.yaml"))); cfg = DetectorConfig.from_dict(raw.get("resense", raw))
out = {"union": getattr(cfg.track, "axis_joint_union", None)}
for name, sel in (("new_data_piece2_0-899", ("new_data", 2, 900)), ("roundT_doubleT", ("roundT_doubleT", None, None)),
                  ("roundT_pressureGate_roundT", ("roundT_pressureGate_roundT", None, None)), ("doubleT_obstacle", ("doubleT_obstacle", None, None))):
    d = os.path.join("/data/cache", sel[0]); files = cache_files(d); st = load_cache_stamps(d)
    if sel[1] is not None:
        files = list(np.array_split(np.array(files), 8)[sel[1]])[: sel[2]]
    det = Detector(cfg); t = []
    for i, f in enumerate(files):
        stem = cache_file_stem(f)
        fr = frame_from_compact(load_cache_array(f), cfg.sensor, stamp=st.get(stem, i * 0.1), frame_id=stem)
        t.append(det.process(fr).timing_ms["total"])
    t = np.array(t)
    out[name] = {"frames": int(t.size), "p50": round(float(np.percentile(t, 50)), 1), "p95": round(float(np.percentile(t, 95)), 1),
                 "mean": round(float(t.mean()), 1)}
    print(name, out[name], flush=True)
json.dump(out, open(sys.argv[1], "w"), indent=1)
