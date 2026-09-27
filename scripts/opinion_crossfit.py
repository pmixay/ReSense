#!/usr/bin/env python3
"""Cross-fitted ride measurement of the learned track opinion (27.09, the judges' review).

The ride is split into the regression gate's 8 pieces. Each fold's model (``scripts/track_opinion.py
train --exclude new_data:K,...``) never saw its held-out pieces, nor the synthetic objects injected
into them; every piece is run by the full detector with the model of the fold that held it out, and
the ride is summarised exactly as the regression gate does (``recording_entry``). So the false alarm
figure is measured on pieces the learned component was not trained on, not simulated.

    python scripts/opinion_crossfit.py --fold 0,1:foldA.json:0.02 --fold 2,3:foldB.json:0.03 ... \\
        --work out/crossfit --out crossfit.json [--set k=v ...]

``--fold PIECES:MODEL:THRESHOLD``; ``--baseline-model`` also runs every piece with one model (the
shipped one) or with the opinion off (``off``) for comparison on the same pieces.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import eval_real  # noqa: E402
from regression_gate import RIDE, recording_entry  # noqa: E402


def _pieces(cache, chunks):
    from resense.io import _natural_key
    files = sorted(glob.glob(os.path.join(cache, RIDE, "*.npy")), key=_natural_key)
    return [list(p) for p in np.array_split(np.array(files), chunks)]


def run(assign, a, tag):
    """``assign``: {piece index: list of --set overrides}; returns the ride entry of those pieces."""
    from resense.io import load_cache_stamps
    stamps = load_cache_stamps(os.path.join(a.cache, RIDE))
    pieces = _pieces(a.cache, a.chunks)
    work = os.path.join(a.work, tag)
    os.makedirs(work, exist_ok=True)
    jobs, outs = [], []
    for k, sets in sorted(assign.items()):
        cfg_dict = eval_real.load_cfg_dict(a.config, a.set + sets)
        out = os.path.join(work, f"{RIDE}_{k}.jsonl")
        jobs.append((RIDE, pieces[k], cfg_dict, out, stamps, None))
        outs.append(out)
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        list(ex.map(eval_real.run_piece, jobs))
    cfg = eval_real.load_cfg(a.config, a.set)
    e = recording_entry(RIDE, outs, cfg)
    return {k: e[k] for k in ("frames", "alarm_frames", "alarm_events", "stop_episodes", "advisory_frames")}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default="/data/cache")
    ap.add_argument("--config", default=os.path.join(ROOT, "configs", "default.yaml"))
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--chunks", type=int, default=8)
    ap.add_argument("--fold", action="append", required=True, help="PIECES:MODEL:THRESHOLD, pieces comma-separated")
    ap.add_argument("--baseline-model", action="append", default=[], help="MODEL:THRESHOLD or off")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--work", default="out/opinion_crossfit")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    assign, folds = {}, []
    for f in a.fold:
        pcs, model, thr = f.split(":")
        ks = [int(k) for k in pcs.split(",")]
        folds.append({"pieces": ks, "model": model, "threshold": float(thr)})
        for k in ks:
            assign[k] = [f"tracking.doubt_model={os.path.abspath(model)}", f"tracking.doubt_threshold={thr}"]
    res = {"what": "ride false alarms with each piece run by the model of the fold that never saw it",
           "pieces": sorted(assign), "folds": folds, "cross_fitted": run(assign, a, "crossfit")}
    for b in a.baseline_model:
        if b == "off":
            sets = ["tracking.doubt_extra_hits=0"]
        else:
            model, thr = b.split(":")
            sets = [f"tracking.doubt_model={model if not os.path.exists(model) else os.path.abspath(model)}",
                    f"tracking.doubt_threshold={thr}"]
        res[f"same_pieces_{os.path.basename(b).replace('.json', '')}"] = run({k: sets for k in assign}, a, os.path.basename(b))
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
