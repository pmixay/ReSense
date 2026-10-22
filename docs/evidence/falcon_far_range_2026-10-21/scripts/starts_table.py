#!/usr/bin/env python3
"""First / held STOP on the main person, STOP episodes, false episodes and GO-with-person-inside-clear per start frame
(the review's evalrows.py and person_frames.py logic), v1.2.0 rows against candidate rows.

    starts_table.py --base-dir <dir with s<N>__wt_v120.jsonl> --cand-dir <dir with s<N>__wt_cand.jsonl> [--full0 cand_full.jsonl]"""
import argparse
import json
import subprocess
import sys

sys.path.insert(0, "/home/user/rv/s")
from evalrows import evaluate  # noqa: E402
import person_frames as PF  # noqa: E402


def row(rows):
    e = evaluate(rows)
    t = e["targets"]["main_approach"]
    st = PF.state(rows)
    go = sum(1 for v in st.values() if v["dec"] == "GO" and v["mon"] is not None and v["x"] <= min(v["clear"], v["mon"]))
    return {"first": t["first_stop_x"], "first_frame": t["first_stop_frame"], "held": t["held_stop_x"],
            "held_frame": t["held_stop_frame"], "episodes": e["stop_episodes"], "false": e["false_episodes"],
            "go_inside_clear": go, "stop_frames": t["stop_frames"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-dir", required=True)
    ap.add_argument("--cand-dir", required=True)
    ap.add_argument("--full0", default="")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    out = {}
    for s in (0, 600, 1200, 1800, 2100, 2400):
        b = [json.loads(line) for line in open(f"{a.base_dir}/s{s}__wt_v120.jsonl")]
        if s == 0 and a.full0:
            c = [json.loads(line) for line in open(a.full0)][:3300]
        else:
            c = [json.loads(line) for line in open(f"{a.cand_dir}/s{s}__wt_cand.jsonl")]
        out[s] = {"v1.2.0": row(b), "cand": row(c)}
        print(s, out[s])
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
