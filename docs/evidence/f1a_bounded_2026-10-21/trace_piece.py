#!/usr/bin/env python3
"""Attribution of changed gate rows (PROTOCOL §4): re-run one gate piece in ONE process exactly as the gate does
(``scripts/eval_real.run_piece`` with the gate's own effective config from its work directory and the same file
split), with read-only wraps that record, per frame, every cluster the bounded branch rejected (the switch-off
decision of the same call is computed alongside and compared). The traced piece's JSONL must equal the gate's
plain JSONL outside timing (checked by the caller with compare_rows.py).

    RESENSE_REPO=<cand> python trace_piece.py <cache> <gate work> <bag> <piece k> <chunks> <out prefix>
"""
import dataclasses
import json
import os
import sys

import numpy as np
import yaml

ROOT = os.environ["RESENSE_REPO"]
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import eval_real  # noqa: E402
from cache_io import cache_files, load_cache_stamps  # noqa: E402
import resense.detector as detm  # noqa: E402

cache, work, bag, k, chunks, out = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
cfg_dict = yaml.safe_load(open(os.path.join(work, "config.yaml")))
d = os.path.join(cache, bag)
files = cache_files(d)
stamps = load_cache_stamps(d)
part = list(np.array_split(np.array(files), chunks)[k]) if chunks > 1 else list(files)
frame = {"i": -1}
DUMP = os.environ.get("TRACE_DUMP") == "1"
events = []
orig_process, orig_check = detm.Detector.process, detm.rail_reference_check


def process(self, *a, **kw):
    frame["i"] += 1
    return orig_process(self, *a, **kw)


def check(clusters, X, dy, h, cfg, sp, free=None):
    out_ = orig_check(clusters, X, dy, h, cfg, sp, free)
    if cfg.rail_head_bounded:
        off = orig_check(clusters, X, dy, h, dataclasses.replace(cfg, rail_head_bounded=False), sp, free)
        for c in out_:
            if not any(c is o for o in off):
                events.append(dict(row=frame["i"], d=round(float(c.distance), 2), lat=round(float(c.lateral), 3),
                                   width=round(float(c.size[1]), 3), cap=round(float(c.height_max), 3)))
                if DUMP:   # raw points around the cluster (copies; nothing is modified)
                    m = (np.abs(X - float(c.distance)) < 6.0) & (np.abs(dy) < 1.7) & (h > -0.6) & (h < 0.6)
                    own = np.zeros(X.size, bool)
                    own[c.points_idx] = True
                    np.savez_compressed(f"{out}_r{frame['i']:04d}_{len(events):03d}.npz", X=X[m], dy=dy[m], h=h[m],
                                        own=own[m], free=(free[m] if free is not None else np.ones(int(m.sum()), bool)),
                                        bbox=np.r_[c.bbox_min, c.bbox_max])
    return out_


detm.Detector.process = process
detm.rail_reference_check = check
res = eval_real.run_piece((bag, part, cfg_dict, out + ".jsonl", stamps, None))
json.dump(dict(bag=bag, piece=k, rows=len(part), new_branch_rejections=events), open(out + ".attrib.json", "w"), indent=1)
print(bag, k, len(part), "rows;", len(events), "new-branch rejections in rows", sorted({e["row"] for e in events}))
