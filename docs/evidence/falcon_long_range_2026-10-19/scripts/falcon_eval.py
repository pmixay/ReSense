#!/usr/bin/env python3
"""Full-recording false-alarm and person comparison of a candidate against the baseline (PROTOCOL §5).

    falcon_eval.py --base <baseline.jsonl> --cand <candidate.jsonl> [...] --out <json>

Person association: the N2 raw-geometry association (``n2_falcon_2026-10-18/summarize_falcon.py``,
reviewed anchors, interpolation within 25 frames, margins 1.0/0.6/1.2 m; explicit ROS axes).
"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

REPO = Path(os.environ.get("RESENSE_REPO", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(REPO / "docs/evidence/n2_falcon_2026-10-18"))
import summarize_falcon as N2  # noqa: E402


def episodes(rows, lo=0, hi=None):
    rows = rows[lo:hi]
    return sum(1 for a, b in zip([None] + rows, rows) if b["decision"] == "STOP" and (a is None or a["decision"] != "STOP"))


def evaluate(rows, by_frame):
    s = N2.summarize(rows, "explicit_ros", by_frame)
    person = set(s["associated_targets"]["main_approach"]["stop"]) | set(s["associated_targets"]["early_uncertain"]["stop"])
    stop = [r["i"] for r in rows if r["decision"] == "STOP"]
    out = {"decisions": dict(Counter(r["decision"] for r in rows)), "stop_episodes": episodes(rows),
           "caution_share": round(sum(r["decision"] == "CAUTION" for r in rows) / len(rows), 4),
           "stop_frames_not_person": len([i for i in stop if i not in person]),
           "empty_0_1700": {"stop_episodes": episodes(rows, 0, 1701),
                            "stop_frames": sum(r["decision"] == "STOP" for r in rows[:1701]),
                            "stop_frames_not_person": len([i for i in stop if i <= 1700 and i not in person]),
                            "caution_share": round(sum(r["decision"] == "CAUTION" for r in rows[:1701]) / 1701, 4)},
           "person_stop_frames": sorted(person),
           "main_person": {k: s["associated_targets"]["main_approach"][k]
                           for k in ("stop_frames", "advisory_frames", "first_stop_frame", "first_stop_raw_forward_m",
                                     "first_advisory_raw_forward_m", "suffix_90pct_raw_forward_m")},
           "static_115_stop_frames": s["associated_targets"]["static_support_115"]["stop_frames"],
           "static_105_stop_frames": s["associated_targets"]["static_support_105"]["stop_frames"],
           "unassociated_stop_frames": s["frames_with_any_unassociated_stop_detection"]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--cand", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _, by_frame = N2.references()
    base = evaluate(N2.load_rows(Path(a.base)), by_frame)
    res = {"baseline": {k: v for k, v in base.items() if k != "person_stop_frames"}, "candidates": {}}
    for p in a.cand:
        c = evaluate(N2.load_rows(Path(p)), by_frame)
        lost = sorted(set(base["person_stop_frames"]) - set(c["person_stop_frames"]))
        e0, b0 = c["empty_0_1700"], base["empty_0_1700"]
        checks = {
            "empty_stop_episodes_le": e0["stop_episodes"] <= b0["stop_episodes"],
            "empty_stop_frames_not_person_le": e0["stop_frames_not_person"] <= b0["stop_frames_not_person"],
            "empty_caution_share_le": e0["caution_share"] <= b0["caution_share"],
            "all_stop_episodes_le": c["stop_episodes"] <= base["stop_episodes"],
            "all_caution_share_le": c["caution_share"] <= base["caution_share"],
            "all_stop_frames_not_person_le": c["stop_frames_not_person"] <= base["stop_frames_not_person"],
            "person_stop_rows_kept": not lost}
        res["candidates"][Path(p).stem] = {**{k: v for k, v in c.items() if k != "person_stop_frames"},
                                          "lost_person_stop_frames": lost, "checks": checks,
                                          "pass": all(checks.values())}
    Path(a.out).write_text(json.dumps(res, indent=1))
    short = {k: (v["decisions"], v["stop_episodes"], v["caution_share"], v["stop_frames_not_person"], v["empty_0_1700"],
                 v["main_person"]["first_stop_raw_forward_m"], v.get("checks"), len(v.get("lost_person_stop_frames", [])))
             for k, v in [("baseline", res["baseline"])] + list(res["candidates"].items())}
    for k, v in short.items():
        print(k, v)


if __name__ == "__main__":
    main()
