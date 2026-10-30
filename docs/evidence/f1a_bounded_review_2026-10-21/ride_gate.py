#!/usr/bin/env python3
"""The ride part of scripts/regression_gate.py only (the recordings' caches were deleted for disk space): the same
config dump, the same split of the ride cache into --chunks pieces (np.array_split of cache_files), the same
eval_real.run_piece jobs and the gate's own recording_entry() for the ride's numbers (alarm frames / events, STOP
episodes, advisory frames). Positive control: the caller compares this on the control worktree with the archived
gate's ride block of the author's control run.

    RESENSE_REPO=<checkout> python ride_gate.py --cache /data/cache --work <dir> --out <json> [--jobs 2]
"""
import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

ROOT = os.environ["RESENSE_REPO"]
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import numpy as np  # noqa: E402
import yaml  # noqa: E402

import scripts.regression_gate as rg  # noqa: E402
from scripts import eval_real  # noqa: E402
from scripts.cache_io import cache_files, load_cache_stamps  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/data/cache")
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--chunks", type=int, default=8)
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    cfg_path_in = os.path.join(ROOT, "configs", "default.yaml")
    cfg_dict = eval_real.load_cfg_dict(cfg_path_in, [])
    cfg = eval_real.load_cfg(cfg_path_in, [])
    with open(os.path.join(a.work, "config.yaml"), "w", encoding="utf-8") as fh:
        yaml.safe_dump({"resense": cfg_dict}, fh, sort_keys=False)
    d = os.path.join(a.cache, rg.RIDE)
    files = cache_files(d)
    stamps = load_cache_stamps(d)
    jobs, pieces = [], []
    for k, part in enumerate(np.array_split(np.array(files), a.chunks)):
        out = os.path.join(a.work, f"{rg.RIDE}_{k}.jsonl")
        jobs.append((rg.RIDE, list(part), cfg_dict, out, stamps, None))
        pieces.append(out)
    jobs.sort(key=lambda j: -len(j[1]))
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        list(ex.map(eval_real.run_piece, jobs))
    r = rg.recording_entry(rg.RIDE, pieces, cfg)
    ride = {"available": True, "chunks": a.chunks,
            **{k: v for k, v in r.items() if k not in ("labelled", "first_alarm_frame")}}
    json.dump(dict(code=rg.code_info(), ride=ride), open(a.out, "w"), indent=1)
    print(json.dumps(ride))


if __name__ == "__main__":
    main()
