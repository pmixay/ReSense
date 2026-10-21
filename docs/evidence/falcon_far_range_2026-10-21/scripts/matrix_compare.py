#!/usr/bin/env python3
"""Criteria 7-10 of PROTOCOL.md section 4: the injection matrix of the candidate against the v1.2.0 control,
case by case (same case names, seeds 20-22).

    matrix_compare.py <base_summary.json> <cand_summary.json> --out <json> [--md <tables.md>]
"""
import argparse
import json
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("cand")
    ap.add_argument("--out", required=True)
    ap.add_argument("--md", default="")
    a = ap.parse_args()
    B = {c["case"]: c for c in json.load(open(a.base))["cases"]}
    C = {c["case"]: c for c in json.load(open(a.cand))["cases"]}
    assert set(B) == set(C), "case sets differ"
    fails = defaultdict(list)
    rows = []
    for k in sorted(B):
        b, c = B[k], C[k]
        r = {"case": k, "target": b["target"], "mode": b["mode"], "seed": b["seed"]}
        if b["mode"] == "approach":
            r.update(base_first_stop=b.get("first_stop_x"), cand_first_stop=c.get("first_stop_x"),
                     base_held=b.get("held_fraction_after_first_stop"), cand_held=c.get("held_fraction_after_first_stop"))
            if b["target"] != "outside" and b.get("first_stop_x") is not None and (
                    c.get("first_stop_x") is None or c["first_stop_x"] < b["first_stop_x"] - 2.0):
                fails["7_approach"].append(k)
        elif b["mode"] == "static":
            r.update(range=b["range"], base_stop_fraction=b["stop_fraction"], cand_stop_fraction=c["stop_fraction"])
            if b["target"] != "outside" and c["stop_fraction"] < b["stop_fraction"] - 0.05:
                fails["8_static"].append(k)
        else:
            r.update(base_in=b["in_gauge_stop_frames"], cand_in=c["in_gauge_stop_frames"], in_frames=b["in_gauge_frames"],
                     base_out=b["outside_stop_frames"], cand_out=c["outside_stop_frames"], out_frames=b["outside_frames"],
                     base_first_stop=b.get("first_stop_x"), cand_first_stop=c.get("first_stop_x"))
            if c["in_gauge_stop_frames"] < b["in_gauge_stop_frames"] - 2 or c["outside_stop_frames"] > b["outside_stop_frames"] + 2:
                fails["9_moving"].append(k)
        if b["target"] == "outside":
            r.update(base_stop_frames=b["decisions"]["STOP"], cand_assoc_stop=round(c["stop_fraction"] * c["frames"]))
            if c["stop_fraction"] > 0:
                fails["10_outside"].append(k)
        rows.append(r)
    res = {"criteria": {k: {"pass": not fails[k], "failing_cases": fails[k]}
                        for k in ("7_approach", "8_static", "9_moving", "10_outside")},
           "prefix_check": {"base": json.load(open(a.base)).get("prefix_check"), "cand": json.load(open(a.cand)).get("prefix_check")},
           "rows": rows}
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps(res["criteria"], indent=1), json.dumps(res["prefix_check"]))
    if a.md:
        lines = ["| case | base | cand |", "|---|---|---|"]
        for r in rows:
            if r["mode"] == "approach":
                lines.append(f"| {r['case']} | first STOP {r['base_first_stop']} m, held {r['base_held']} | "
                             f"first STOP {r['cand_first_stop']} m, held {r['cand_held']} |")
            elif r["mode"] == "static":
                lines.append(f"| {r['case']} | STOP fraction {r['base_stop_fraction']} | {r['cand_stop_fraction']} |")
            else:
                lines.append(f"| {r['case']} | in-gauge STOP {r['base_in']}/{r['in_frames']}, outside STOP {r['base_out']}/{r['out_frames']}, "
                             f"first STOP {r['base_first_stop']} | {r['cand_in']}/{r['in_frames']}, {r['cand_out']}/{r['out_frames']}, {r['cand_first_stop']} |")
        open(a.md, "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
