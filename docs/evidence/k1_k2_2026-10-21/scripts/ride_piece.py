#!/usr/bin/env python3
"""Replay one ride piece exactly as the gate does (scripts/eval_real.run_piece: the same 8-way split of the cached
files, a fresh detector, the cached stamps) with the tree's YAML ($RESENSE_REPO) and print, for the listed frames,
the decision, the detections, and the curve model (trusted range, curve_from) and the curve clusters added.

    ride_piece.py <cache root> <piece 0-7> <out.jsonl> <frame> [<frame> ...]
"""
import json
import os
import sys

import numpy as np

REPO = os.environ["RESENSE_REPO"]
sys.path[:0] = [REPO, os.path.join(REPO, "scripts")]
import eval_real  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import frame_from_compact  # noqa: E402
from scripts.cache_io import cache_file_stem, cache_files, load_cache_array, load_cache_stamps  # noqa: E402

root, piece, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
want = {int(f) for f in sys.argv[4:]}
d = os.path.join(root, "new_data")
files = list(np.array_split(np.array(cache_files(d)), 8)[piece])
stamps = load_cache_stamps(d)
cfg = DetectorConfig.from_dict(eval_real.load_cfg_dict(os.path.join(REPO, "configs/default.yaml"), []))
det = Detector(cfg)
with open(out, "w") as fo:
    for i, f in enumerate(files):
        stem = cache_file_stem(f)
        fr = frame_from_compact(load_cache_array(f), cfg.sensor, stamp=stamps.get(stem, i * 0.1), frame_id=stem)
        det._curve_added, det._curve_seen = 0, []
        res = det.process(fr)
        if i in want:
            cv = det.track.curve
            fo.write(json.dumps({"i": i, "stop": res.obstacle,
                                 "dets": [(round(x.distance, 2), round(x.lateral, 2), x.zone, x.reason) for x in res.detections],
                                 "curve_valid": None if cv is None else round(cv.axis_valid, 1),
                                 "curve_from": None if cv is None else round(getattr(cv, "curve_from", 0.0), 1),
                                 "added": det._curve_added,
                                 "seen": [(round(k.distance, 1), round(k.lateral, 2), k.zone, k.reason) for k in det._curve_seen
                                          if k.zone == "gauge" and not k.reason]}) + "\n")
print(out)
