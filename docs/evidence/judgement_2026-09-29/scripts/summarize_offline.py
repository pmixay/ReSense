"""29.09 (new; 28.09 assembled offline_summary.json by hand): score_bag.py over the six offline runs,
plus the five-empty totals and, for doubleT_obstacle, the first STOP frame and the non-STOP frames
after it (gaps).

    python summarize_offline.py <dir with <bag>.jsonl> > offline_summary.json
"""
import json
import sys

from score_bag import score

BAGS = ["doubleT_obstacle", "roundT_doubleT", "doubleT_platform", "roundT_pressureGate_roundT",
        "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch"]


def main(d: str) -> None:
    out = {}
    for b in BAGS:
        s = score(f"{d}/{b}.jsonl")
        s["caution_pct"] = round(100 * s["caution_frames"] / s["frames"], 1)
        out[b] = s
    rows = [json.loads(line) for line in open(f"{d}/doubleT_obstacle.jsonl")]
    first = next((i for i, r in enumerate(rows) if r["obstacle"]), None)
    out["doubleT_obstacle"]["first_stop_frame"] = first
    out["doubleT_obstacle"]["non_stop_frames_after_first_stop"] = (
        [i for i, r in enumerate(rows) if first is not None and i > first and not r["obstacle"]])
    empty = [out[b] for b in BAGS[1:]]
    out["_five_empty"] = dict(frames=sum(s["frames"] for s in empty), stop_frames=sum(s["stop_frames"] for s in empty),
                              caution_frames=sum(s["caution_frames"] for s in empty),
                              go_frames=sum(s["go_frames"] for s in empty),
                              stop_episodes=sum(len(s["stop_episodes"]) for s in empty))
    out["_five_empty"]["caution_pct"] = round(100 * out["_five_empty"]["caution_frames"] / out["_five_empty"]["frames"], 1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
