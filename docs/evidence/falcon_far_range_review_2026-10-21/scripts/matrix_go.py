#!/usr/bin/env python3
"""Matrix cases (matrix2.py outputs of both checkouts): per case, the frames where the decision is GO although the
injected target is inside the reported clear distance and monitored range and in the gauge (|lateral| <= 0.8 m),
and the first STOP / held STOP of the target; summed per mode.

    matrix_go.py <matrixdir> --json out.json
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/home/user/ReSense/docs/evidence/falcon_far_range_2026-10-21/scripts")
sys.path.insert(0, "/home/user/ReSense/docs/evidence/falcon_long_range_2026-10-19/scripts")
import numpy as np  # noqa: E402

from assoc import associate  # noqa: E402
from matrix2 import moving_path, APPROACH, PREFIX  # noqa: E402

TRACK = json.loads(Path("/home/user/ReSense/docs/evidence/falcon_long_range_2026-10-19/track_reference.json").read_text())["track"]


def path_of(c, n):
    if c["mode"].startswith("M"):
        return moving_path(c["mode"], c["seed"])
    if c["mode"] == "static":
        return [[PREFIX + k, float(c["range"]), 2.5 if c["target"] == "outside" else 0.0] for k in range(n)]
    return [[PREFIX + k, max(APPROACH["start"] - APPROACH["speed"] * 0.1 * k, APPROACH["stop_at"]), 2.5 if c["target"] == "outside" else 0.0]
            for k in range(n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--json", required=True)
    a = ap.parse_args()
    d = Path(a.dir)
    out = {}
    for w in ("wt_v120", "wt_cand"):
        summ = json.loads((d / f"{w}_summary.json").read_text())
        per = {}
        agg = defaultdict(lambda: defaultdict(int))
        for c in summ["cases"]:
            rows = [json.loads(line) for line in open(d / w / f"{c['case']}.jsonl")]
            path = path_of(c, len(rows))
            P = {int(f): (x, l) for f, x, l in path}
            assoc = {x["i"]: x for x in associate(rows, path, TRACK, [r["i"] for r in rows])}
            go = 0
            stops = []
            for r in rows:
                x, lat = P[r["i"]]
                if abs(lat) <= 0.8 and r["decision"] == "GO" and r["monitored"] is not None and x <= min(r["clear"], r["monitored"]):
                    go += 1
                if assoc.get(r["i"], {}).get("stop"):
                    stops.append(r["i"])
            st = set(stops)
            held = next((i for i in sorted(st) if sum((j in st) for j in range(i, i + 30)) >= 27), None)
            per[c["case"]] = {"go_inside_clear": go, "first_stop_x": None if not stops else round(P[stops[0]][0], 1),
                              "held_stop_x": None if held is None else round(P[held][0], 1), "stop_frames": len(stops),
                              "decisions": c["decisions"]}
            key = c["mode"] if c["mode"] != "static" else f"static{c['range']}"
            agg[key]["cases"] += 1
            agg[key]["go_inside_clear"] += go
            agg[key]["cases_with_go_inside_clear"] += int(go > 0)
        out[w] = {"cases": per, "by_mode": {k: dict(v) for k, v in agg.items()}, "prefix_check": summ.get("prefix_check")}
    Path(a.json).write_text(json.dumps(out, indent=1))
    for w in out:
        print(w, json.dumps(out[w]["by_mode"]), out[w]["prefix_check"])


if __name__ == "__main__":
    main()
