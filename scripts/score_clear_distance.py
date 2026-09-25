#!/usr/bin/env python3
"""Does ``clear_distance`` claim clear track past an object inside the envelope? And what does a
run's verified-clear distance and decision look like, against a reference run?

    # set O: the overclaim count (SCORECARD §6 row 6; criteria 8.1 / 8.4)
    python scripts/score_clear_distance.py out/gate/cloud_with_fake_obj.jsonl --gt labels/cloud_with_fake_obj.json
    # any recording(s): decisions and clear_distance, compared frame by frame with a reference run
    python scripts/score_clear_distance.py out/new/new_data_*.jsonl --base out/old/new_data_*.jsonl

The input is the per-frame JSONL of ``scripts/eval_real.py`` / ``scripts/regression_gate.py
--work`` (``FrameResult.to_dict()`` plus ``frame``). The decision is the node's
(``DetectorNode.decision``, ros2_ws/src/resense_ros/resense_ros/detector_node.py): ``STOP`` when
a confirmed obstacle is in the envelope, ``FAULT`` on a health error, ``CAUTION`` on an advisory
object or a health warning, else ``GO``. It does not depend on ``clear_distance``.

**Overclaim** (``--gt``): an object-frame of an object the organizers put inside the envelope
(``in_gauge``), visible (``n_points`` > 0) and ``plausible`` (labels of
``scripts/label_fake_objects.py``), whose ``clear_distance`` exceeds the object's distance (its
nearest point along X, the axis ``clear_distance`` is measured on) by more than ``--tol``
(0.5 m: a STOP on the object itself reports its own nearest point, which differs from the label
by a few decimetres). ``target`` counts the object-frames with points inside the envelope
*measured from the rails* (``n_in_envelope`` > 0); ``intent`` all of them; ``go_judge`` is the
criteria judgement's count of 24.09 (decision ``GO``, no tolerance, the organizers' intent).
Objects outside the envelope are listed for information: an object-frame whose clear distance
stops at the object (within ``--tol``) is a verified-clear range shortened by something that is
not in the way.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from resense.metrics import gt_meta, load_gt  # noqa: E402


def decision(r: dict) -> str:
    """The node's decision word for a result row (DetectorNode.decision)."""
    level = (r.get("health") or {}).get("level", "ok")
    if r.get("obstacle"):
        return "STOP"
    if level == "error":
        return "FAULT"
    if r.get("warning") or level == "warn":
        return "CAUTION"
    return "GO"


def read(paths):
    rows = []
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            rows.extend(json.loads(line) for line in fh if line.strip())
    return rows


def overclaim(results, gt, tol: float = 0.5) -> dict:
    per = {}
    tot = {"target": 0, "target_frames": 0, "intent": 0, "intent_frames": 0, "go_judge": 0,
           "go_judge_in_envelope": 0, "target_by_decision": {}}
    outside = {}
    for r in results:
        rows = [g for g in gt.get(f"{int(r['frame']):05d}", []) if g.get("n_points", 1) > 0 and g.get("plausible", True)]
        if not rows:
            continue
        clear = float(r.get("clear_distance", 0.0))
        dec = decision(r)
        for g in rows:
            d = float(g["distance"])
            if not g.get("in_gauge"):
                o = outside.setdefault(g["label"], {"frames": 0, "clear_stops_at_object": 0})
                o["frames"] += 1
                o["clear_stops_at_object"] += int(abs(clear - d) <= tol)
                continue
            env = g.get("n_in_envelope", 1) > 0
            over = clear > d + tol
            e = per.setdefault(g["label"], {"frames": 0, "frames_in_envelope": 0, "overclaim": 0,
                                            "overclaim_in_envelope": 0, "overclaim_in_envelope_go": 0,
                                            "max_excess_m": 0.0})
            e["frames"] += 1
            e["frames_in_envelope"] += int(env)
            e["overclaim"] += int(over)
            tot["intent_frames"] += 1
            tot["intent"] += int(over)
            if env:
                tot["target_frames"] += 1
                if over:
                    tot["target"] += 1
                    e["overclaim_in_envelope"] += 1
                    e["overclaim_in_envelope_go"] += int(dec == "GO")
                    tot["target_by_decision"][dec] = tot["target_by_decision"].get(dec, 0) + 1
            if over:
                e["max_excess_m"] = round(max(e["max_excess_m"], clear - d), 1)
            if dec == "GO" and clear > d:
                tot["go_judge"] += 1
                tot["go_judge_in_envelope"] += int(env)
    return {"tolerance_m": tol, "totals": tot, "inside_objects": per, "outside_objects": outside}


def clear_stats(results, base=None) -> dict:
    dec = {}
    for r in results:
        k = decision(r)
        dec[k] = dec.get(k, 0) + 1
    c = np.array([float(r.get("clear_distance", 0.0)) for r in results])
    out = {"frames": len(results), "decisions": dec,
           "clear_distance_m": {"median": round(float(np.median(c)), 1) if c.size else None,
                                "p10": round(float(np.percentile(c, 10)), 1) if c.size else None,
                                "mean": round(float(c.mean()), 1) if c.size else None}}
    if base is not None:
        if len(base) != len(results) or any(a.get("frame_id", a.get("frame")) != b.get("frame_id", b.get("frame"))
                                            for a, b in zip(base, results)):
            raise SystemExit("--base: not the same frames in the same order")
        b = np.array([float(r.get("clear_distance", 0.0)) for r in base])
        short = b - c
        changed = sum(1 for x, y in zip(base, results) if decision(x) != decision(y))
        out["against_base"] = {
            "base_decisions": clear_stats(base)["decisions"],
            "decision_changed_frames": changed,
            "base_clear_median_m": round(float(np.median(b)), 1) if b.size else None,
            "base_clear_p10_m": round(float(np.percentile(b, 10)), 1) if b.size else None,
            "median_change_pct": (round(100.0 * (np.median(c) - np.median(b)) / np.median(b), 1)
                                  if b.size and np.median(b) > 0 else None),
            "frames_shortened": int((short > 0.05).sum()),
            "frames_shortened_gt_10m": int((short > 10.0).sum()),
            "frames_shortened_gt_20pct": int((short > 0.2 * np.maximum(b, 1e-6)).sum()),
            "frames_pushed_under_60m": int(((b >= 60.0) & (c < 60.0)).sum()),
            "frames_lengthened": int((short < -0.05).sum()),
        }
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("results", nargs="+", help="per-frame JSONL (one recording, or the pieces of one in order)")
    p.add_argument("--gt", default=None, help="labels of the organizers' objects (set O): score the overclaim")
    p.add_argument("--tol", type=float, default=0.5, help="m beyond the object's nearest point still counted as at it")
    p.add_argument("--base", nargs="+", default=None, help="the same frames from a reference run")
    p.add_argument("--out", default=None, help="write the JSON here")
    a = p.parse_args()
    results = read(a.results)
    out = {"results": a.results, "stats": clear_stats(results, read(a.base) if a.base else None)}
    if a.gt:
        out["gt"] = a.gt
        out["overclaim"] = overclaim(results, load_gt(a.gt), a.tol)
        out["overclaim"]["order"] = list(gt_meta(a.gt).get("objects", {}))
    print(json.dumps(out, indent=1, ensure_ascii=False))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
