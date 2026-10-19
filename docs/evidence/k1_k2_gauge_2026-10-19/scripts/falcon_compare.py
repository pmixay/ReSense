#!/usr/bin/env python3
"""Falcon full-stream comparison: reference (falcon_full_v110.jsonl) vs base and candidate wrapped streams.

    falcon_compare.py <ref.jsonl> <base.jsonl> <cand.jsonl>

* instrumentation: base decisions vs the committed reference, frame by frame;
* person STOP frames (protocol F-1): reference STOP frames from bag time t0 + 297 s on, minus the floor-patch
  frames (nearest 9.0-9.8 m after t0 + 437 s); each must stay STOP in the candidate;
* static 115 m STOP frames: STOP frames before t0 + 284 s (the person is not in view before) with nearest
  110-120 m; and every STOP before t0 + 284 s;
* trusted axis range (wrapper field k12.axis_valid, capped at 250 m): p10/p50/p90, share of frames whose
  |change| from the previous frame >= 20 m, p90 of |change|."""
import json
import sys

import numpy as np


def load(p):
    return [json.loads(l) for l in open(p)]


def main():
    ref, base, cand = (load(p) for p in sys.argv[1:4])
    assert len(ref) == len(base) == len(cand), (len(ref), len(base), len(cand))
    t0 = ref[0]["bag_t"]
    diff = [r["i"] for r, b in zip(ref, base) if r["decision"] != b["decision"]]
    person = [r["i"] for r in ref if r["decision"] == "STOP" and r["bag_t"] - t0 >= 297
              and not (r["bag_t"] - t0 >= 437 and r["nearest"] is not None and 9.0 <= r["nearest"] <= 9.8)]
    out = {"frames": len(ref), "base_vs_reference_decision_differences": len(diff), "diff_frames": diff[:20],
           "person_stop_frames_reference": len(person)}
    for tag, run in (("base", base), ("cand", cand)):
        lost = [i for i in person if run[i]["decision"] != "STOP"]
        early = [r for r in run if r["bag_t"] - t0 < 284 and r["decision"] == "STOP"]
        av = np.array([min(r.get("k12", {}).get("axis_valid", np.nan), 250.0) for r in run], dtype=float)
        d = np.abs(np.diff(av))
        d = d[np.isfinite(d)]
        dec = {}
        for r in run:
            dec[r["decision"]] = dec.get(r["decision"], 0) + 1
        out[tag] = {"decisions": dec, "person_stop_lost": len(lost), "lost_frames": lost[:30],
                    "stop_before_284s": len(early),
                    "static_115_stop_frames": [r["i"] for r in early if r["nearest"] and 110 <= r["nearest"] <= 120],
                    "other_early_stop": [(r["i"], r["nearest"]) for r in early if not (r["nearest"] and 110 <= r["nearest"] <= 120)],
                    "axis_range_p10_p50_p90": [round(float(np.nanpercentile(av, q)), 1) for q in (10, 50, 90)],
                    "axis_range_change_ge20_share": round(float(np.mean(d >= 20)), 3),
                    "axis_range_change_p90": round(float(np.percentile(d, 90)), 1),
                    "stop_frames": dec.get("STOP", 0)}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
