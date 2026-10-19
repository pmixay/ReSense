#!/usr/bin/env python3
"""B6 before/after table: measure + honesty of two track/run sets against both truths.

    b6_table.py <b6 dir base> <b6 dir cand> <poses dir> <out.json>

Each b6 dir holds gauge_stability.py track_<bag>.json and probe run_<bag>.jsonl. Truths: poses_<bag>.json
(original B6) and posesV_<bag>.json (ICP steps with forward motion < -0.05 m turned into segment breaks)."""
import json
import os
import subprocess
import sys

BAGS = ["doubleT_obstacle", "doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
        "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch", "cloud_with_fake_obj",
        "synthetic_platform", "synthetic_switch", "synthetic_tunnels"]
G = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../../scripts/gauge_stability.py")


def run(cmd, *a):
    out = subprocess.run([sys.executable, G, cmd, *a], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(out.stderr)


def main():
    base, cand, pdir, outp = sys.argv[1:5]
    table = {}
    for b in BAGS:
        for tag, d in (("base", base), ("cand", cand)):
            tr, rn = os.path.join(d, f"track_{b}.json"), os.path.join(d, f"run_{b}.jsonl")
            if not os.path.exists(tr):
                continue
            for truth in ("poses", "posesV"):
                p = os.path.join(pdir, f"{truth}_{b}.json")
                m, h = os.path.join(d, f"m_{truth}_{b}.json"), os.path.join(d, f"h_{truth}_{b}.json")
                run("measure", tr, p, m)
                row = json.load(open(m))
                rec = {"range_p50": row["range"]["p50"], "blinks": row["blinks"],
                       "flicker_p90": [row["jitter_compensated"][k].get("p90") for k in ("40m", "80m", "120m")],
                       "offtrack_p50": {k: v["within_trusted"].get("p50") for k, v in row["offtrack"].items()}}
                if b != "doubleT_obstacle" and os.path.exists(rn):
                    run("honesty", tr, p, rn, h)
                    hh = json.load(open(h))
                    rec["reported_over_1.05"] = hh["inside_over_1.05m"]
                    rec["reported_over_0.5"] = hh["inside_over_0.5m"]
                table.setdefault(b, {}).setdefault(tag, {})[truth] = rec
    json.dump(table, open(outp, "w"), indent=1)
    for b, v in table.items():
        for truth in ("posesV", "poses"):
            cells = []
            for tag in ("base", "cand"):
                r = v.get(tag, {}).get(truth)
                if r:
                    o = r["offtrack_p50"]
                    cells.append(f"{tag}: rng {r['range_p50']:.0f} bl {r['blinks']} hon {r.get('reported_over_1.05')} "
                                 f"off90 {o['80-100']} off135 {o['120-150']} fl {r['flicker_p90']}")
            print(f"{b[:26]:26s} {truth:6s} | " + " | ".join(cells))


if __name__ == "__main__":
    main()
