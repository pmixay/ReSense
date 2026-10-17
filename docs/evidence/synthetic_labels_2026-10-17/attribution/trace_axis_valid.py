#!/usr/bin/env python3
"""Record which branch of the track model sets the trusted axis range on each frame (A5).

    trace_axis_valid.py <decoded cache> <out.json> [--end N] [--plain <probe .jsonl>]

Observation only: ``sys.settrace`` on ``resense.track.estimate_track`` (and the rail-yaw helper
that can shorten the range) records every executed line that assigns ``axis_valid`` or the
no-boundary floor, named by its source text (so 707ea9c and 1.1.0 read alike), plus the wall
estimate's ``x_valid`` / ``n_sides`` / ``disagreement`` where it fired. The detector's code and
results are not touched; ``--plain`` compares every decision with a plain probe run.
Run with RESENSE_REPO / PYTHONPATH set to the checkout.
"""
import argparse
import glob
import json
import linecache
import os
import sys
from pathlib import Path

import numpy as np

JUDGE = Path(__file__).resolve().parents[2] / "judgement_2026-10-13/scripts"
BRANCHES = {
    "model.axis_valid = x_valid + cfg.axis_valid_margin": "walls_fit",
    "model.axis_valid = min(model.axis_valid, cfg.axis_one_side_range)": "cap_one_side",
    "model.axis_valid = min(model.axis_valid, cfg.axis_disagree_range)": "cap_disagree",
    "floor_valid = cfg.rails_range[1] + cfg.axis_valid_margin": "no_boundary_rails_floor",
    "floor_valid = cfg.walls_range[0] + cfg.axis_valid_margin": "no_boundary_floor",
    "model.axis_valid = max(floor_valid, prior.axis_valid - 20.0)": "no_boundary_decay",
    "model.axis_valid = min(model.axis_valid, end + cfg.axis_valid_margin)": "cap_rail_yaw_dev",
    "model.axis_valid = 1e9": "walls_off",
    "return prior": "floor_fit_failed_keep_prior",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("out")
    ap.add_argument("--end", type=int, default=10 ** 9)
    ap.add_argument("--plain", default="")
    a = ap.parse_args()
    sys.path.insert(0, str(JUDGE))
    from judge_runner import NodeReplica, node_decision
    from range_test import run_frame
    import resense.track as T

    events = []
    track_file = os.path.realpath(T.__file__)

    def local(frame, event, arg):
        if event == "line":
            text = linecache.getline(frame.f_code.co_filename, frame.f_lineno).strip()
            name = BRANCHES.get(text)
            if name:
                ev = {"branch": name, "line": frame.f_lineno}
                if name == "walls_fit":
                    loc = frame.f_locals
                    ev.update(x_valid=round(float(loc["x_valid"]), 2), n_sides=int(loc["n_sides"]),
                              disagreement=float(loc["disagreement"]))
                events.append(ev)
        return local

    def tracer(frame, event, arg):
        if event == "call" and os.path.realpath(frame.f_code.co_filename) == track_file:
            return local
        return None

    meta = json.loads(Path(a.cache, "meta.json").read_text())
    files = sorted(glob.glob(os.path.join(a.cache, "f_*.npz")))
    rep = NodeReplica()
    rows = []
    for k, (m, f) in enumerate(zip(meta, files)):
        if k >= a.end:
            break
        d = np.load(f)
        events.clear()
        sys.settrace(tracer)
        try:
            res = run_frame(rep, d["xyz"], d["inten"], d["ring"], m, k)
        finally:
            sys.settrace(None)
        rows.append({"i": k, "decision": node_decision(res), "axis_valid": round(float(res.track.axis_valid), 2),
                     "events": list(events)})
    out = {"cache": a.cache, "repo": os.environ.get("RESENSE_REPO", ""), "rows": rows}
    if a.plain:
        plain = {r["i"]: r["decision"] for r in map(json.loads, open(a.plain))}
        out["plain_equal_decisions"] = all(plain.get(r["i"]) == r["decision"] for r in rows)
    json.dump(out, open(a.out, "w"))
    print(a.out, len(rows), "frames; plain decisions equal:", out.get("plain_equal_decisions"))


if __name__ == "__main__":
    main()
