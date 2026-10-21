#!/usr/bin/env python3
"""Replay the doubt rule (``scripts/track_opinion.py simulate``) with a given model JSON and thresholds on
collected rows (opinion pinned off): false events kept on obstacle-free rows, positive sequences / rows
delayed on labelled or synthetic rows. In-sample for whatever the model was trained on.

    replay_model.py --model resense/models/track_opinion.json --thr 0.015,0.03 \\
        --set ride=neg_ride.npz --set empty=neg_empty.npz --set syn=p1.npz,p2.npz --out replay.json
"""
import argparse
import json
import os
import sys

import numpy as np

ROOT = os.environ.get("RESENSE_REPO", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from track_opinion import load, simulate  # noqa: E402

from resense.opinion import TrackOpinion  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--thr", required=True)
    ap.add_argument("--set", action="append", required=True, help="name=a.npz,b.npz")
    ap.add_argument("--extra", type=int, default=10)
    ap.add_argument("--near", type=float, default=25.0)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    op = TrackOpinion(json.load(open(a.model)))
    res = {"model": a.model, "extra": a.extra, "near": a.near, "sets": {}}
    for spec in a.set:
        name, paths = spec.split("=", 1)
        X, P, M = load(paths.split(","))
        # only STOP-candidate rows are ever asked (simulate reads p only there)
        p = np.ones(len(X))
        ask = M[:, 2] > 0
        p[ask] = [op.prob(x) for x in X[ask]]
        out = {}
        for t in [float(v) for v in a.thr.split(",")]:
            ev, kept, fr, fk, delayed = simulate(P, M, p, t, a.extra, a.near, True)
            out[str(t)] = {"events": ev, "events_kept": kept, "stop_rows": fr, "stop_rows_kept": fk,
                           "delayed_rows": len(delayed), "delayed_sequences": sorted({d[0] for d in delayed}),
                           "delayed": delayed[:100]}
        res["sets"][name] = out
        print(name, {t: (v["events"], v["events_kept"], v["delayed_rows"], len(v["delayed_sequences"]))
                     for t, v in out.items()})
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
