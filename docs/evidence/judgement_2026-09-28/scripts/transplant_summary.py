"""Collect transplant.py outputs into one table: per range, the windows in which the pasted person got
a sustained STOP (STOP at the person on at least 15 of the 30 frames, i.e. from confirmation on for
most of the window) and any STOP at the person.

    python transplant_summary.py transplant/*.json > transplant.json
"""
import json
import sys

SUSTAINED = 15


def main(paths):
    cases = [json.load(open(p)) for p in paths]
    ranges = sorted({float(r) for c in cases for r in c["ranges"]})
    table = {}
    for r in ranges:
        rows = [(c["bag"], c["start"], c["ranges"][str(r)]) for c in cases if str(r) in c["ranges"]]
        table[r] = {"windows": len(rows),
                    "sustained": sum(v["stop_at_person"] >= SUSTAINED for _, _, v in rows),
                    "any_stop": sum(v["stop_at_person"] > 0 for _, _, v in rows),
                    "stop_frames_at_person": [v["stop_at_person"] for _, _, v in rows]}
    per_window = [{"bag": c["bag"], "start": c["start"], "control_stop_frames": c["control_stop_frames"],
                   "stop_at_person": {r: v["stop_at_person"] for r, v in c["ranges"].items()}} for c in cases]
    print(json.dumps({"sustained_threshold_frames": SUSTAINED, "by_range": table, "windows": per_window}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
