#!/usr/bin/env python3
"""Summary of an orientation battery run against the plain run of the same recording.

    analyse_b4.py <battery .json> <plain probe .jsonl> <out.json>

Per rotation: whether the adopted orientation is the correct one (``expected``; the identity keeps
``configured``), the first frame with the final orientation, the calibration status at the end, the
decisions before adoption (a silent GO is a GO while the orientation is still wrong), and after adoption
the frames whose decision equals the plain run, and the STOP frames of both.
"""
import json
import sys
from collections import Counter


def main():
    bat = json.load(open(sys.argv[1]))
    plain = [json.loads(x)["decision"] for x in open(sys.argv[2])]
    out = []
    for c in bat["cases"]:
        rows = c["rows"]
        want = "configured" if c["index"] == 0 else c["expected"]
        correct = rows[-1]["orientation"] == want
        first = next((r["i"] for r in rows if r["orientation"] == want), None)
        if c["index"] == 0:
            first = 0
        before = Counter(r["decision"] for r in rows if first is None or r["i"] < first)
        after = [r for r in rows if first is not None and r["i"] >= first]
        equal = sum(r["decision"] == plain[r["i"]] for r in after)
        out.append({"index": c["index"], "expected": c["expected"], "up_vertical": c["up_vertical"],
                    "native_falcon": c["native_falcon"], "adopted": rows[-1]["orientation"], "correct": correct,
                    "first_frame_correct": first, "status_end": rows[-1]["status"],
                    "statuses": dict(Counter(r["status"] for r in rows)),
                    "decisions_before": dict(before), "silent_go_before": before.get("GO", 0),
                    "after_frames": len(after), "after_equal_plain": equal,
                    "stop_frames": sum(r["decision"] == "STOP" for r in rows),
                    "stop_frames_plain": sum(d == "STOP" for d in plain),
                    "first_msgs": sorted({r["msg"][:70] for r in rows[:5] if r["msg"]})})
    json.dump({"battery": sys.argv[1], "plain": sys.argv[2], "cases": out}, open(sys.argv[3], "w"), indent=1)
    for o in out:
        print(f"{o['index']:2d} {o['expected']:28s} {'vert' if o['up_vertical'] else 'side'}{' NATIVE' if o['native_falcon'] else '':7s} "
              f"correct={o['correct']!s:5s} first={o['first_frame_correct']!s:4s} end={o['status_end']:11s} "
              f"before={o['decisions_before']} after_equal={o['after_equal_plain']}/{o['after_frames']} "
              f"STOP {o['stop_frames']}/{o['stop_frames_plain']}")


if __name__ == "__main__":
    main()
